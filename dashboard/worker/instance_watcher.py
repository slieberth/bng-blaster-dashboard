#!/usr/bin/env python3
# dashboard/worker/instance_watcher.py
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import time
from typing import Optional

from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env
from dashboard.models.bbl_models import InstanceStatus
from dashboard.models.bbl_models import SessionCounters
from dashboard.models.bbl_models import StreamStats


# ---------------------------------------------------------------------------
# Default constants
# ---------------------------------------------------------------------------
DEFAULT_CONTROLLER_URL = "http://127.0.0.1:5711"
DEFAULT_DB_PREFIX = "bbl-db"

DEFAULT_POLL_INTERVAL_SEC = 1
DEFAULT_REDIS_SUMMARIES_TTL_SEC = 60
DEFAULT_INITIAL_BACKOFF_SEC = 0.5
DEFAULT_MAX_BACKOFF_SEC = 3
DEFAULT_SLEEP_SLICE_SEC = 0.1


def _configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s",
    )
    return logging.getLogger("dashboard.worker.instance_watcher")


logger = _configure_logging()


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


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch BNG Blaster instances and persist runtime summaries."
    )

    parser.add_argument(
        "--controller-url",
        default=os.getenv("BNG_CONTROLLER_BASE_URL", DEFAULT_CONTROLLER_URL),
        help="BNG controller base URL",
    )
    parser.add_argument(
        "--db-prefix",
        default=os.getenv("BBL_DB_PREFIX", DEFAULT_DB_PREFIX),
        help="Redis key prefix",
    )
    parser.add_argument(
        "--poll-interval-sec",
        type=_positive_int,
        default=_env_int("BBL_DB_POLL_INTERVAL_SEC", DEFAULT_POLL_INTERVAL_SEC),
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--summaries-ttl-sec",
        type=_positive_int,
        default=_env_int(
            "BBL_DB_REDIS_SUMMARIES_TTL_SEC",
            DEFAULT_REDIS_SUMMARIES_TTL_SEC,
        ),
        help="TTL for stored summary data in seconds",
    )
    parser.add_argument(
        "--initial-backoff-sec",
        type=_positive_int,
        default=DEFAULT_INITIAL_BACKOFF_SEC,
        help="Initial retry backoff in seconds after worker loop errors",
    )
    parser.add_argument(
        "--max-backoff-sec",
        type=_positive_int,
        default=DEFAULT_MAX_BACKOFF_SEC,
        help="Maximum retry backoff in seconds after worker loop errors",
    )
    parser.add_argument(
        "--sleep-slice-sec",
        type=_positive_float,
        default=DEFAULT_SLEEP_SLICE_SEC,
        help="Interruptible sleep slice duration in seconds",
    )

    return parser.parse_args()


async def _interruptible_sleep(
    total_seconds: float,
    sleep_slice_sec: float,
    stop_event: asyncio.Event,
) -> None:
    end_time = time.monotonic() + total_seconds
    while not stop_event.is_set():
        remaining = end_time - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(sleep_slice_sec, remaining))


async def run_forever(
    stop_event: asyncio.Event,
    *,
    controller_url: str,
    prefix: str,
    poll_interval_sec: int,
    summaries_ttl_sec: int,
    initial_backoff_sec: int,
    max_backoff_sec: int,
    sleep_slice_sec: float,
) -> None:
    store = make_store_from_env(prefix=prefix)
    client = BngBlasterControllerClient(base_url=controller_url)

    logger.info(
        "Instance watcher starting "
        "(controller=%s, redis_prefix=%s, poll=%ss, summaries_ttl=%ss, "
        "initial_backoff=%ss, max_backoff=%ss, sleep_slice=%ss)",
        controller_url,
        prefix,
        poll_interval_sec,
        summaries_ttl_sec,
        initial_backoff_sec,
        max_backoff_sec,
        sleep_slice_sec,
    )

    backoff_sec = initial_backoff_sec

    while not stop_event.is_set():
        try:
            names = await client.list_instances()
            now = int(time.time())

            for name in names:
                status_str = await client.get_instance_status(name)
                status_enum = _to_instance_status(status_str)

                store.update_instance_meta(
                    name,
                    {
                        "name": name,
                        "status": status_enum.value if status_enum else None,
                        "last_seen_ts": now,
                    },
                )

                logger.info("instance=%s status=%s", name, status_str)

                if status_enum == InstanceStatus.STARTED:
                    try:
                        session_counters = await client.instance_command_with_retries(
                            name,
                            "session-counters",
                            {},
                        )
                        counters = SessionCounters.model_validate(
                            session_counters["session-counters"]
                        )
                        store.set_session_counters(
                            name,
                            counters.model_dump(),
                            ex=summaries_ttl_sec,
                        )
                    except Exception:
                        logger.exception(
                            "failed to fetch session counters for instance=%s", name
                        )

                    try:
                        stream_stats = await client.instance_command_with_retries(
                            name,
                            "stream-stats",
                            {},
                        )
                        counters = StreamStats.model_validate(
                            stream_stats["stream-stats"]
                        )
                        store.set_stream_stats(
                            name,
                            counters.model_dump(),
                            ex=summaries_ttl_sec,
                        )
                    except Exception:
                        logger.exception(
                            "failed to fetch stream stats for instance=%s", name
                        )
                else:
                    logger.debug("instance=%s not running -> reset counters", name)

                    store.set_session_counters(
                        name,
                        {
                            "sessions-established": 0,
                            "sessions-pppoe": 0,
                            "dhcp-sessions": 0,
                            "dhcpv6-sessions": 0,
                        },
                        ex=summaries_ttl_sec,
                    )

                    store.set_stream_stats(
                        name,
                        {
                            "total-flows": 0,
                            "verified-flows": 0,
                        },
                        ex=summaries_ttl_sec,
                    )

            backoff_sec = initial_backoff_sec
            await _interruptible_sleep(
                total_seconds=poll_interval_sec,
                sleep_slice_sec=sleep_slice_sec,
                stop_event=stop_event,
            )

        except Exception:
            logger.exception("worker loop failed (controller may be down)")
            await _interruptible_sleep(
                total_seconds=backoff_sec,
                sleep_slice_sec=sleep_slice_sec,
                stop_event=stop_event,
            )
            backoff_sec = min(backoff_sec * 2, max_backoff_sec)

    logger.info("Instance watcher stopping")


def main() -> None:
    args = parse_args()
    stop_event = asyncio.Event()

    def _stop(*_args) -> None:
        logger.info("shutdown signal received")
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    async def _runner() -> None:
        task = asyncio.create_task(
            run_forever(
                stop_event,
                controller_url=args.controller_url,
                prefix=args.db_prefix,
                poll_interval_sec=args.poll_interval_sec,
                summaries_ttl_sec=args.summaries_ttl_sec,
                initial_backoff_sec=args.initial_backoff_sec,
                max_backoff_sec=args.max_backoff_sec,
                sleep_slice_sec=args.sleep_slice_sec,
            ),
            name="instance-watcher",
        )
        await stop_event.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_runner())


if __name__ == "__main__":
    main()