import json
import logging
import os
from pathlib import Path
from enum import Enum

import reflex as rx

from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env

from dashboard.models.bbl_models import InstanceMeta


logger = logging.getLogger("dashboard.state.instance_dashboard")

class InstanceDashboard(rx.State):
    # --- instance controls ---
    instance_name: str = ""
    instance_meta: InstanceMeta | None = None

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