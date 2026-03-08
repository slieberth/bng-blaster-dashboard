from __future__ import annotations
import asyncio
import logging
import os
import time
import json
import yaml
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

def _now_ts() -> int:
    return int(time.time())

def _make_store():
    return make_store_from_env(prefix=os.getenv("BBL_DB_PREFIX", "bbl-db"))

class InstancesState(rx.State):
    """Main state for the instances dashboard."""

    instances: list[str] = []
    items: list[InstanceRow] = []

    selected_instance_name: str | None = None
    selected_config_yaml: str | None = None
    edited_config_yaml: str | None = None
    is_config_dirty: bool = False
    is_config_open: bool = True
    load_status: str = ""
    config_save_status: str = ""

    @rx.event
    async def fetch_instances(self) -> None:
        client = BngBlasterControllerClient()
        store = _make_store()

        try:
            fetched_names = await client.list_instances()
            self.instances = fetched_names

            rows: list[InstanceRow] = []

            for instance_name in fetched_names:
                status = await client.get_instance_status(instance_name)
                status_enum = InstanceStatus(status)
                # config = await client.get_instance_config(instance_name)
                # config_str = json.dumps(config)

                store.update_instance_meta(
                    instance_name,
                    {
                        "name": instance_name,
                        "status": status,
                        "last_seen_ts": int(time.time()),
                    },
                )

                logger.debug("instance=%s status=%s", instance_name, status)

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


    # ----------------------------
    # start/stop mechanism
    # ----------------------------
    @rx.event
    async def start_instance(self, instance_name: str) -> None:
        client = BngBlasterControllerClient()
        await client.start_instance(instance_name, DEFAULT_START_PARAMS)
        store = _make_store()
        store.update_instance_meta(instance_name,{"started_ts": _now_ts(),})

    @rx.event
    async def stop_instance(self, instance_name: str) -> None:
        client = BngBlasterControllerClient()
        await client.stop_instance(instance_name)
        store = _make_store()
        store.update_instance_meta(instance_name,{"stopped_ts": _now_ts(),})

    @rx.event
    async def edit_config(self, instance_name: str) -> None:
        self.load_status = f"Fetching config for {instance_name}..."
        self.config_save_status = ""
        try:
            client = BngBlasterControllerClient()
            config_data = await client.get_instance_config(instance_name)

            yaml_str = yaml.dump(
                config_data,
                default_flow_style=False,
                sort_keys=False,
            )

            self.selected_instance_name = instance_name
            self.selected_config_yaml = yaml_str
            self.edited_config_yaml = yaml_str
            self.is_config_dirty = False
            self.is_config_open = True
            self.load_status = "Config loaded."
        except Exception as exc:
            self.load_status = f"Error loading config: {exc}"

    @rx.event
    async def save_config(self):
        """Validate YAML and push it to controller."""
        self.config_save_status = "Saving..."
        try:
            if not self.selected_instance_name:
                raise RuntimeError("No instance selected.")

            cfg_obj = yaml.safe_load(self.edited_config_yaml or "")
            if not isinstance(cfg_obj, dict):
                raise RuntimeError("YAML must be a dict/object at top-level.")

            client = BngBlasterControllerClient()
            await client.upload_config(self.selected_instance_name, cfg_obj)

            self.selected_config_yaml = self.edited_config_yaml
            self.is_config_dirty = False
            self.config_save_status = "Saved ✅"
        except Exception as exc:
            self.config_save_status = f"Save error: {exc}"

    def set_selected_config_yaml(self, value: str) -> None:
        self.selected_config_yaml = value or ""

    def set_selected_config_yaml(self, value: str) -> None:
        self.selected_config_yaml = value or ""

    @rx.event
    def close_config(self):
        self.is_config_open = False
        self.config_save_status = ""
        self.is_config_dirty = False
        self.selected_instance_name = ""

    @rx.event
    def on_config_editor_change(self, value: str):
        self.edited_config_yaml = value or ""
        self.is_config_dirty = (self.edited_config_yaml != (self.selected_config_yaml or ""))


    @rx.event(background=True)
    async def update_dashboard(self):
        while True:
            async with self:
                # Check for stopping conditions inside context
                await self.fetch_instances()
            # Await long operations outside the context to avoid blocking UI
            await asyncio.sleep(0.5)
