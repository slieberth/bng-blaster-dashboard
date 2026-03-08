from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import reflex as rx

from dashboard.models.bbl_models import InstanceMeta
from dashboard.models.bbl_models import SessionInfo
from dashboard.services.key_value_store import make_store_from_env
from dashboard.services.session_memory_cache import get_instance_sessions

DEFAULT_DASHBOARD_REFRESH_SEC = 10

logger = logging.getLogger("dashboard.state.instance_dashboard")


class InstanceDashboard(rx.State):
    """State for the instance dashboard page."""

    # ----------------------------
    # Instance context
    # ----------------------------
    instance_name: str = ""
    instance_meta: InstanceMeta | None = None
    sessions: list[SessionInfo] = []

    # ----------------------------
    # Active tab
    # ----------------------------
    active_tab: str = "counters"

    # ----------------------------
    # Session counters tab
    # ----------------------------
    session_counters: dict[str, Any] = {}
    session_counters_status: str = ""
    session_counters_is_not_running: bool = False

    # ----------------------------
    # Session info tab
    # ----------------------------
    session_info_status: str = ""
    session_info_search: str = ""
    session_info_filter_type: str = "all"
    session_info_filter_state: str = "all"
    session_info_page: int = 0
    session_info_page_size: int = 10

    @rx.var
    def session_info_page_size_str(self) -> str:
        """Return the page size as string for the select component."""
        return str(self.session_info_page_size)

    @rx.var
    def session_counters_items(self) -> list[list[str]]:
        """Return session counters as key/value rows for the table."""
        if not self.session_counters:
            return []
        return [[str(k), str(v)] for k, v in self.session_counters.items()]

    @rx.var
    def session_info_columns(self) -> list[str]:
        """Return the visible columns for the session info table."""
        if not self.sessions:
            return []

        preferred = [
            "session-id",
            "type",
            "session-state",
            "username",
            "ipv4-address",
            "ipv6-address",
            "tx-packets",
            "rx-packets",
        ]

        first_row = self.sessions[0].model_dump(by_alias=True)
        keys = list(first_row.keys())

        return [k for k in preferred if k in keys] or keys[:8]

    @rx.var
    def filtered_sessions(self) -> list[SessionInfo]:
        """Return filtered session models based on UI filters."""
        rows = self.sessions

        if self.session_info_search:
            needle = self.session_info_search.lower()
            rows = [
                row
                for row in rows
                if needle in str(row.model_dump(by_alias=True)).lower()
            ]

        if self.session_info_filter_type != "all":
            wanted = self.session_info_filter_type.lower()
            rows = [
                row
                for row in rows
                if wanted in str(row.type).lower()
            ]

        if self.session_info_filter_state != "all":
            wanted = self.session_info_filter_state.lower()
            rows = [
                row
                for row in rows
                if wanted in str(row.session_state).lower()
            ]

        return rows

    @rx.var
    def session_info_filtered_count(self) -> str:
        """Return the number of filtered sessions as string."""
        return str(len(self.filtered_sessions))

    @rx.var
    def session_info_has_rows(self) -> bool:
        """Return True if the current page contains rows."""
        return len(self.session_info_table_rows) > 0

    @rx.var
    def session_info_is_not_running(self) -> bool:
        """Return True if the instance is not currently running."""
        if self.instance_meta is None or self.instance_meta.status is None:
            return True
        return self.instance_meta.status.value != "started"

    @rx.var
    def session_info_table_rows(self) -> list[dict[str, str]]:
        """Convert paginated session models into stringified table rows."""
        start = self.session_info_page * self.session_info_page_size
        end = start + self.session_info_page_size

        sliced = self.filtered_sessions[start:end]

        result: list[dict[str, str]] = []
        for row in sliced:
            raw = row.model_dump(by_alias=True)
            result.append({k: str(v) for k, v in raw.items()})
        return result

    @rx.event
    async def on_load(self) -> None:
        """Initialize the instance dashboard from query parameters."""
        page_params = self.router.page.params or {}
        self.instance_name = page_params.get("instance_name", "") or "(unknown)"

        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        self.instance_meta = store.load_instance_meta(self.instance_name)

        await self.refresh_session_counters()
        await self.refresh_session_infos()

    @rx.event
    async def refresh_session_counters(self) -> None:
        """Refresh cached session counters from Redis."""
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        self.instance_meta = store.load_instance_meta(self.instance_name)

        if (
            self.instance_meta is None
            or self.instance_meta.status is None
            or self.instance_meta.status.value != "started"
        ):
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
        """Refresh session info models from the in-memory cache/service."""
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        self.instance_meta = store.load_instance_meta(self.instance_name)

        if (
            self.instance_meta is None
            or self.instance_meta.status is None
            or self.instance_meta.status.value != "started"
        ):
            self.sessions = []
            self.session_info_status = "Instance is not running."
            return

        self.sessions = await get_instance_sessions(
            self.instance_name,
            force_refresh=True,
        )
        self.session_info_status = f"Loaded {len(self.sessions)} sessions."
        self.session_info_page = 0

    @rx.event
    def set_active_tab(self, value: str) -> None:
        """Set the active dashboard tab."""
        self.active_tab = value

    @rx.event
    def set_session_info_search(self, value: str) -> None:
        """Set the session search term and reset paging."""
        self.session_info_search = value or ""
        self.session_info_page = 0

    @rx.event
    def set_session_info_filter_type(self, value: str) -> None:
        """Set the session type filter and reset paging."""
        self.session_info_filter_type = value or "all"
        self.session_info_page = 0

    @rx.event
    def set_session_info_filter_state(self, value: str) -> None:
        """Set the session state filter and reset paging."""
        self.session_info_filter_state = value or "all"
        self.session_info_page = 0

    @rx.event
    def clear_session_info_filters(self) -> None:
        """Clear all session info filters."""
        self.session_info_search = ""
        self.session_info_filter_type = "all"
        self.session_info_filter_state = "all"
        self.session_info_page = 0

    @rx.event
    def session_info_first(self) -> None:
        """Go to the first page."""
        self.session_info_page = 0

    @rx.event
    def session_info_prev(self) -> None:
        """Go to the previous page."""
        self.session_info_page = max(0, self.session_info_page - 1)

    @rx.event
    def session_info_next(self) -> None:
        """Go to the next page."""
        filtered_count = len(self.filtered_sessions)
        max_page = max(0, (filtered_count - 1) // self.session_info_page_size)
        self.session_info_page = min(max_page, self.session_info_page + 1)

    @rx.event
    def session_info_set_page_size(self, value: str) -> None:
        """Set the session info page size."""
        try:
            self.session_info_page_size = max(1, int(value))
        except Exception:
            self.session_info_page_size = 10
        self.session_info_page = 0

    @rx.event(background=True)
    async def background_refresh(self):
        """Continuously refresh dashboard data in the background."""
        async with self:
            await self.on_load()

        while True:
            async with self:
                prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
                store = make_store_from_env(prefix=prefix)
                self.instance_meta = store.load_instance_meta(self.instance_name)

                await self.refresh_session_counters()
                await self.refresh_session_infos()

                if self.active_tab == "session_info":
                    await self.refresh_session_infos()

            await asyncio.sleep(DEFAULT_DASHBOARD_REFRESH_SEC)