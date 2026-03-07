from __future__ import annotations
import asyncio
import logging
import os
import time
import json
from typing import Any

import reflex as rx

from dashboard.models.bbl_models import SessionCounters, StreamStats
from dashboard.models.reflex_models import InstanceRow
from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env
from dashboard.models.bbl_models import InstanceStatus
from dashboard.models.bbl_models import SessionCounters
from dashboard.models.bbl_models import StreamStats

logger = logging.getLogger("dashboard.state.instances")


DEFAULT_START_PARAMS = {
    "logging": True,
    "logging_flags": ["error", "ip"],
    "pcap_capture": True,
    "report": True,
    "report_flags": ["sessions", "stream"],
}

DEFAULT_CONTROLLER_URL = "http://127.0.0.1:5711"
DEFAULT_DB_PREFIX = "bbl-db"

DEFAULT_POLL_INTERVAL_SEC = 1
DEFAULT_REDIS_SUMMARIES_TTL_SEC = 60
DEFAULT_INITIAL_BACKOFF_SEC = 0.5
DEFAULT_MAX_BACKOFF_SEC = 3
DEFAULT_SLEEP_SLICE_SEC = 0.1

class InstancesState(rx.State):
    """Main state for the instances dashboard."""

    instances: list[str] = []
    items: list[InstanceRow] = []

    @rx.event
    async def fetch_instances(self) -> None:
        client = BngBlasterControllerClient()
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        try:
            fetched_names = await client.list_instances()
            self.instances = fetched_names

            rows: list[InstanceRow] = []

            for instance_name in fetched_names:
                status = await client.get_instance_status(instance_name)
                config = await client.get_instance_config(instance_name)
                config_str = json.dumps(config)

                meta = store.load_instance_meta(instance_name) or {}
                sess_raw = store.get_session_counters(instance_name) or {}
                stream_raw = store.get_stream_stats(instance_name) or {}

                established = int(sess_raw.get("sessions_established", 0))
                pppoe = int(sess_raw.get("sessions_pppoe", 0))
                dhcp = int(sess_raw.get("dhcp_sessions", 0))
                dhcpv6 = int(sess_raw.get("dhcpv6_sessions", 0))

                session_total = pppoe + dhcp + dhcpv6
                session_text = f"{established} / {session_total}" if session_total else "-"
                total = int(stream_raw.get("total_flows", 0))
                verified = int(stream_raw.get("verified_flows", 0))

                streams_text = f"{total} / {verified}" if total else "-"

                rows.append(
                    InstanceRow(
                        name=instance_name,
                        status=status,
                        config_json_str="",  # load config on demand later
                        session_text=session_text,
                        streams_text=streams_text,
                    )
                )

            self.items = rows

        except Exception as exc:
            logger.exception("fetch_instances failed")


    @rx.event
    async def update_instances(self) -> None:
        client = BngBlasterControllerClient()
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        try:
            rows: list[InstanceRow] = []
            for instance_name in self.instances:
                status = await client.get_instance_status(instance_name)
                status_enum = InstanceStatus(status)

                store.update_instance_meta(
                    instance_name,
                    {
                        "name": instance_name,
                        "status": status_enum.value if status_enum else None,
                        "last_seen_ts": int(time.time()),
                    },
                )

                logger.info("instance=%s status=%s", instance_name, status)

                if status_enum == InstanceStatus.STARTED:
                    try:
                        session_counters = await client.instance_command_with_retries(
                            instance_name,
                            "session-counters",
                            {},
                        )
                        counters = SessionCounters.model_validate(
                            session_counters["session-counters"]
                        )
                        store.set_session_counters(
                            instance_name,
                            counters.model_dump(),
                            ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
                        )
                    except Exception:
                        logger.exception(
                            "failed to fetch session counters for instance=%s", name
                        )

                    try:
                        stream_stats = await client.instance_command_with_retries(
                            instance_name,
                            "stream-stats",
                            {},
                        )
                        counters = StreamStats.model_validate(
                            stream_stats["stream-stats"]
                        )
                        store.set_stream_stats(
                            instance_name,
                            counters.model_dump(),
                            ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
                        )
                    except Exception:
                        logger.exception(
                            "failed to fetch stream stats for instance=%s", instance_name
                        )
                else:
                    logger.debug("instance=%s not running -> reset counters", instance_name)

                    store.set_session_counters(
                        instance_name,
                        {
                            "sessions-established": 0,
                            "sessions-pppoe": 0,
                            "dhcp-sessions": 0,
                            "dhcpv6-sessions": 0,
                        },
                        ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
                    )

                    store.set_stream_stats(
                        instance_name,
                        {
                            "total-flows": 0,
                            "verified-flows": 0,
                        },
                        ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
                    )
        except Exception as exc:
            logger.exception("update_instances failed")


    # ----------------------------
    # start/stop mechanism
    # ----------------------------
    @rx.event
    async def start_instance(self, instance_name: str) -> None:
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)
        meta = store.load_instance_meta(instance_name) or {}
        logger.info(f"Starting instance {instance_name} with meta {meta}")
        client = BngBlasterControllerClient()
        await client.start_instance(instance_name, DEFAULT_START_PARAMS)
        # await self.fetch_instances()

    @rx.event
    async def stop_instance(self, instance_name: str) -> None:
        client = BngBlasterControllerClient()
        await client.stop_instance(instance_name)
        # await self.fetch_instances()

    @rx.event
    def set_max_counter(self, value: str):
        self.max_counter = int(value)

    @rx.event(background=True)
    async def update_dashboard(self):
        while True:
            async with self:
                # Check for stopping conditions inside context
                await self.update_instances()
                await self.fetch_instances()
            # Await long operations outside the context to avoid blocking UI
            await asyncio.sleep(0.5)
