from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import reflex as rx

from dashboard.models.bbl_models import InstanceMeta
from dashboard.services.key_value_store import make_store_from_env
from dashboard.services.session_memory_cache import get_instance_sessions

DEFAULT_DASHBOARD_REFRESH_SEC = 10

logger = logging.getLogger("dashboard.state.instance_dashboard")


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


class InstanceDashboard(rx.State):
    # --- instance context ---
    instance_name: str = ""
    instance_meta: InstanceMeta | None = None
    sessions: list[dict[str, Any]] = []

    # --- tabs ---
    active_tab: str = "counters"

    # --- session counters tab ---
    session_counters: dict[str, Any] = {}
    session_counters_status: str = ""
    session_counters_is_not_running: bool = False

    # --- session info tab ---
    session_info_status: str = ""
    session_info_search: str = ""
    session_info_filter_type: str = "all"
    session_info_filter_state: str = "all"
    session_info_page: int = 0
    session_info_page_size: int = 10

    @rx.var
    def session_info_page_size_str(self) -> str:
        return str(self.session_info_page_size)

    @rx.var
    def session_counters_items(self) -> list[list[str]]:
        if not self.session_counters:
            return []
        return [[str(k), str(v)] for k, v in self.session_counters.items()]

    @rx.var
    def session_info_columns(self) -> list[str]:
        if not self.sessions:
            return []
        preferred = [
            "session-id",
            "session-type",
            "session-state",
            "username",
            "agent-circuit-id",
            "agent-remote-id",
            "mac",
            "ipv4-address",
            "ipv6-address",
        ]
        keys = list(self.sessions[0].keys())
        return [k for k in preferred if k in keys] or keys[:8]

    @rx.var
    def filtered_sessions(self) -> list[dict[str, Any]]:
        rows = self.sessions

        if self.session_info_search:
            needle = self.session_info_search.lower()
            rows = [
                row
                for row in rows
                if needle in str(row).lower()
            ]

        if self.session_info_filter_type != "all":
            wanted = self.session_info_filter_type.lower()
            rows = [
                row
                for row in rows
                if wanted in str(row.get("session-type", "")).lower()
            ]

        if self.session_info_filter_state != "all":
            wanted = self.session_info_filter_state.lower()
            rows = [
                row
                for row in rows
                if wanted in str(row.get("session-state", "")).lower()
            ]

        return rows

    @rx.var
    def session_info_filtered_count(self) -> str:
        return str(len(self.filtered_sessions))

    @rx.var
    def session_info_has_rows(self) -> bool:
        return len(self.session_info_table_rows) > 0

    @rx.var
    def session_info_is_not_running(self) -> bool:
        if self.instance_meta is None or self.instance_meta.status is None:
            return True
        return self.instance_meta.status.value != "started"

    @rx.var
    def session_info_table_rows(self) -> list[dict[str, str]]:
        start = self.session_info_page * self.session_info_page_size
        end = start + self.session_info_page_size

        sliced = self.filtered_sessions[start:end]

        result: list[dict[str, str]] = []
        for row in sliced:
            result.append({k: str(v) for k, v in row.items()})
        return result

    @rx.event
    async def on_load(self) -> None:
        page_params = self.router.page.params or {}
        # page_params_new = self.router.url or {}    # FIXME router.page willl be deprecated in 9
        # logger.warning("Page params: %s, URL params: %s", page_params, page_params_new)
        self.instance_name = page_params.get("instance_name", "") or "(unknown)"

        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        self.instance_meta = store.load_instance_meta(self.instance_name)
        await self.refresh_session_counters()
        await self.refresh_session_infos()

    @rx.event
    async def refresh_session_counters(self) -> None:
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        self.instance_meta = store.load_instance_meta(self.instance_name)

        if self.instance_meta is None or self.instance_meta.status is None or self.instance_meta.status.value != "started":
            self.session_counters = {}
            self.session_counters_status = "Instance is not running."
            self.session_counters_is_not_running = True
            return

        data = store.get_session_counters(self.instance_name) or {}
        self.session_counters = data
        self.session_counters_status = "Loaded from Redis cache."
        self.session_counters_is_not_running = False

    @rx.event
    async def refresh_session_infos(self) -> None:
        self.instance_meta = store = make_store_from_env(prefix=os.getenv("BBL_DB_PREFIX", "bbl-db")).load_instance_meta(self.instance_name)

        if self.instance_meta is None or self.instance_meta.status is None or self.instance_meta.status.value != "started":
            self.sessions = []
            self.session_info_status = "Instance is not running."
            return

        self.sessions = await get_instance_sessions(self.instance_name, force_refresh=True)
        self.session_info_status = f"Loaded {len(self.sessions)} sessions."
        self.session_info_page = 0

    @rx.event
    def set_active_tab(self, value: str) -> None:
        self.active_tab = value

    @rx.event
    def set_session_info_search(self, value: str) -> None:
        self.session_info_search = value or ""
        self.session_info_page = 0

    @rx.event
    def set_session_info_filter_type(self, value: str) -> None:
        self.session_info_filter_type = value or "all"
        self.session_info_page = 0

    @rx.event
    def set_session_info_filter_state(self, value: str) -> None:
        self.session_info_filter_state = value or "all"
        self.session_info_page = 0

    @rx.event
    def clear_session_info_filters(self) -> None:
        self.session_info_search = ""
        self.session_info_filter_type = "all"
        self.session_info_filter_state = "all"
        self.session_info_page = 0

    @rx.event
    def session_info_first(self) -> None:
        self.session_info_page = 0

    @rx.event
    def session_info_prev(self) -> None:
        self.session_info_page = max(0, self.session_info_page - 1)

    @rx.event
    def session_info_next(self) -> None:
        filtered_count = len(self.filtered_sessions)
        max_page = max(0, (filtered_count - 1) // self.session_info_page_size)
        self.session_info_page = min(max_page, self.session_info_page + 1)

    @rx.event
    def session_info_set_page_size(self, value: str) -> None:
        try:
            self.session_info_page_size = max(1, int(value))
        except Exception:
            self.session_info_page_size = 10
        self.session_info_page = 0

    @rx.event(background=True)
    async def background_refresh(self):
        async with self:
            await self.on_load()

        while True:
            async with self:
                prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
                store = make_store_from_env(prefix=prefix)
                self.instance_meta = store.load_instance_meta(self.instance_name)

                await self.refresh_session_counters()

                if self.active_tab == "session_info":
                    await self.refresh_session_infos()

            await asyncio.sleep(DEFAULT_DASHBOARD_REFRESH_SEC)