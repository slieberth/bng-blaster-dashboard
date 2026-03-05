#!/usr/bin/env python3
# dashboard/worker/instance_watcher.py
from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from typing import Optional, Any

from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env
from dashboard.models.bbl_models import InstanceStatus
from dashboard.models.bbl_models import SessionCounters
from dashboard.models.bbl_models import StreamStats

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("dashboard.worker.instance_watcher")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _to_instance_status(status_str: str) -> Optional[InstanceStatus]:
    """Map controller status string -> InstanceStatus enum (or None if empty)."""
    s = (status_str or "").strip().lower()
    if not s:
        return None
    try:
        return InstanceStatus(s)
    except Exception:
        return InstanceStatus.ERROR

async def run_forever(stop_event: asyncio.Event) -> None:
    controller_url = os.getenv("BNG_CONTROLLER_BASE_URL", "http://127.0.0.1:5711")
    prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
    poll_interval = _env_int("BBL_DB_POLL_INTERVAL_SEC", 5)
    summaries_ttl = _env_int("BBL_DB_REDIS_SUMMARIES_TTL_SEC", 60)

    store = make_store_from_env(prefix=prefix)
    client = BngBlasterControllerClient(base_url=controller_url)

    logger.info(
        "Instance watcher starting (controller=%s, redis_prefix=%s, poll=%ss, summaries_ttl=%ss)",
        controller_url,
        prefix,
        poll_interval,
        summaries_ttl,
    )

    backoff_sec = 2

    while not stop_event.is_set():
        try:
            names = await client.list_instances()
            now = int(time.time())

            for name in names:
                status_str = await client.get_instance_status(name)  # <- returns string
                status_enum = _to_instance_status(status_str)

                # Write runtime status + last_seen_ts into the instance meta hash
                store.update_instance_meta(
                    name,
                    {
                        "name": name,
                        "status": status_enum.value if status_enum else None,
                        "last_seen_ts": now,
                    },
                )

                logger.info("instance=%s status=%s", name, status_str)

                # If started: try to fetch summaries via run_report.json
                if status_enum == InstanceStatus.STARTED:
                    try:
                        session_counters = await client.instance_command_with_retries(
                            name,
                            "session-counters",
                            {})
                        # logger.info("!!! instance=%s session_counters=%s", name, session_counters)
                        counters = SessionCounters.model_validate(session_counters["session-counters"])
                        store.set_session_counters(
                            name,
                            counters.model_dump(),
                            ex=summaries_ttl,
                        )
                    except Exception:
                        logger.exception("failed to fetch session counters for instance=%s", name)
                    try:
                        stream_stats = await client.instance_command_with_retries(
                            name,
                            "stream-stats",
                            {})
                        logger.info("!!! instance=%s stream_stats=%s", name, stream_stats)
                        counters = StreamStats.model_validate(stream_stats["stream-stats"])
                        store.set_stream_stats(
                            name,
                            counters.model_dump(),
                            ex=summaries_ttl,
                        )
                    except Exception:
                        logger.exception("failed to fetch stream stats for instance=%s", name)

            backoff_sec = 2

            # interruptible sleep
            for _ in range(poll_interval * 10):
                if stop_event.is_set():
                    break
                await asyncio.sleep(0.1)

        except Exception:
            logger.exception("worker loop failed (controller may be down)")
            for _ in range(backoff_sec * 10):
                if stop_event.is_set():
                    break
                await asyncio.sleep(0.1)
            backoff_sec = min(backoff_sec * 2, 30)

    logger.info("Instance watcher stopping")


def main() -> None:
    stop_event = asyncio.Event()

    def _stop(*_args):
        logger.info("shutdown signal received")
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    async def _runner():
        task = asyncio.create_task(run_forever(stop_event), name="instance-watcher")
        await stop_event.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_runner())


if __name__ == "__main__":
    main()