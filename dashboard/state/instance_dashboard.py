import asyncio
import json
import logging
import os
from pathlib import Path
from enum import Enum
from typing import Any

import reflex as rx

from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env
from dashboard.services.session_memory_cache import get_instance_sessions

from dashboard.models.bbl_models import InstanceMeta

DEFAULT_DASHBOARD_REFRESH_SEC = 10

logger = logging.getLogger("dashboard.state.instance_dashboard")

class InstanceDashboard(rx.State):
    # --- instance controls ---
    instance_name: str = ""
    instance_meta: InstanceMeta | None = None
    sessions: list[dict[str, Any]] = []

    @rx.event
    async def on_load(self) -> None:
        page_params = self.router.page.params or {}
        # page_params_new = self.router.url or {}    # FIXME router.page willl be deprecated in 9
        # logger.warning("Page params: %s, URL params: %s", page_params, page_params_new)
        self.instance_name = page_params.get("instance_name", "") or "(unknown)"
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)
        self.instance_meta = store.load_instance_meta(self.instance_name) or {}
        # logger.info("Loaded instance meta: %s", self.instance_meta)

    # ----------------------------
    # Background refresh loop for instance dashboard
    # ----------------------------
    @rx.event(background=True)
    async def background_refresh(self):
        """Continuously refresh the dashboard in the background."""
        async with self:
            await self.on_load()
        while True:
            async with self:
                # logger.info("Updating dashboard data...")
                self.sessions = await get_instance_sessions(self.instance_name)
                # logger.info("sessions updated: %d", len(self.sessions))
                # logger.info("sessions: %s", self.sessions)
            await asyncio.sleep(DEFAULT_DASHBOARD_REFRESH_SEC)