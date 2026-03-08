from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from dashboard.services.controller_client import BngBlasterControllerClient

log = logging.getLogger("dashboard.session_memory_cache")

DEFAULT_CACHE_SECONDS = 10
DEFAULT_CONCURRENCY = 3
DEFAULT_CHUNK_SIZE = 50

# In-memory cache:
# {
#   "instance_name": {
#       "ts": 1234567890.0,
#       "sessions": [ {...}, {...} ]
#   }
# }
_MEMORY_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_LOCK = asyncio.Lock()


def _norm(name: str) -> str:
    """Normalize instance names."""
    return (name or "").strip()


def _coerce_int(v: Any) -> int | None:
    """Try to convert a value to int."""
    try:
        if v is None:
            return None
        s = str(v).strip()
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            s = s[1:-1].strip()
        if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
            s = s[1:-1].strip()
        return int(s)
    except Exception:
        return None


async def _fetch_one_session_info(
    client: BngBlasterControllerClient,
    instance_name: str,
    sid: int,
    sem: asyncio.Semaphore,
) -> dict[str, Any] | None:
    """Fetch one session-info record with retries."""
    max_retries = 3
    backoff_s = [0.05, 0.15, 0.35]

    for attempt in range(max_retries + 1):
        async with sem:
            try:
                resp = await client.instance_command(
                    instance_name,
                    "session-info",
                    {"session-id": int(sid)},
                )
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code if exc.response is not None else None
                body_text = ""
                try:
                    body_text = exc.response.text if exc.response is not None else ""
                except Exception:
                    body_text = ""

                # Session does not exist or is not yet available
                if code in (400, 404):
                    return None

                # Controller temporary error
                if code == 500 and "not able to send command" in (body_text or ""):
                    if attempt < max_retries:
                        await asyncio.sleep(backoff_s[min(attempt, len(backoff_s) - 1)])
                        continue
                    return None

                raise

        raw = resp.get("session-info") if isinstance(resp, dict) else None
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    return item
        return None

    return None


async def _load_sessions_from_controller(
    instance_name: str,
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """Load all sessions for one instance from the controller."""
    client = BngBlasterControllerClient()
    name = _norm(instance_name)

    counters_resp = await client.instance_command_with_retries(name, "session-counters", {})
    counters = counters_resp.get("session-counters") if isinstance(counters_resp, dict) else None

    total = 0
    if isinstance(counters, dict):
        try:
            total = int(counters.get("sessions") or 0)
        except Exception:
            total = 0

    if total <= 0:
        return []

    sem = asyncio.Semaphore(max(1, int(concurrency)))
    chunk_size = max(1, int(chunk_size))

    sessions_by_id: dict[int, dict[str, Any]] = {}

    for start in range(1, total + 1, chunk_size):
        end = min(total, start + chunk_size - 1)
        ids = list(range(start, end + 1))

        tasks = [_fetch_one_session_info(client, name, sid, sem) for sid in ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for sid_req, result in zip(ids, results):
            if isinstance(result, Exception) or result is None or not isinstance(result, dict):
                continue

            sid_val = _coerce_int(result.get("session-id"))
            if sid_val is None or sid_val != sid_req:
                continue

            sessions_by_id[sid_req] = result

    # Return as sorted list
    return [sessions_by_id[sid] for sid in sorted(sessions_by_id.keys())]


async def get_instance_sessions(
    instance_name: str,
    *,
    cache_seconds: int = DEFAULT_CACHE_SECONDS,
    force_refresh: bool = False,
    concurrency: int = DEFAULT_CONCURRENCY,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """
    Return all sessions for one instance as a list.

    The result is cached in memory for `cache_seconds`.
    Use `force_refresh=True` to bypass the cache.
    """
    name = _norm(instance_name)
    now = time.time()

    async with _CACHE_LOCK:
        cached = _MEMORY_CACHE.get(name)
        if (
            not force_refresh
            and cached is not None
            and (now - float(cached.get("ts", 0))) < cache_seconds
        ):
            return list(cached.get("sessions", []))

    sessions = await _load_sessions_from_controller(
        name,
        concurrency=concurrency,
        chunk_size=chunk_size,
    )

    async with _CACHE_LOCK:
        _MEMORY_CACHE[name] = {
            "ts": now,
            "sessions": sessions,
        }

    log.info("Loaded %d sessions for instance=%s", len(sessions), name)
    return sessions


async def invalidate_instance_sessions(instance_name: str) -> None:
    """Remove one instance from the in-memory cache."""
    name = _norm(instance_name)
    async with _CACHE_LOCK:
        _MEMORY_CACHE.pop(name, None)


async def clear_session_cache() -> None:
    """Clear the full in-memory session cache."""
    async with _CACHE_LOCK:
        _MEMORY_CACHE.clear()