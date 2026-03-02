import reflex as rx
import json
import yaml
import logging
from enum import Enum
from pathlib import Path
from typing import Any
from datetime import datetime

from dashboard.models.bbl_models import InstanceModel
from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env

ASSETS_DIR = Path("/workspaces/Bng-Blaster-Controller-WUI/assets")

logger = logging.getLogger("wui.instances_dashboard")
# store = make_store_from_env(prefix="bbl-db")


DEFAULT_START_PARAMS = {
    "logging": True,
    "logging_flags": ["error", "ip"],
    "pcap_capture": True,
    "report": True,
    "report_flags": ["sessions", "stream"],
}

class InstancesState(rx.State):
    """Main state for managing multiple instances."""

    instances: list[str] = []
    items: list[InstanceModel] = []

    async def fetch_instances(self):
        client = BngBlasterControllerClient()
        fetched_names = await client.list_instances()
        self.instances = fetched_names
        self.items = [] 
        for instance_name in fetched_names:
            _status = await client.get_instance_status(instance_name)
            _config = await client.get_instance_config(instance_name)
            _config_str = json.dumps(_config)
            self.items.append(InstanceModel(name=instance_name, status=_status, config_json_str= _config_str))

    # ----------------------------
    # start/stop mechanism
    # ----------------------------

    @rx.event
    async def start_instance(self, instance_name: str) -> None:
        client = BngBlasterControllerClient()
        await client.start_instance(instance_name, DEFAULT_START_PARAMS)
        await self.fetch_instances()

    @rx.event
    async def stop_instance(self, instance_name: str) -> None:
        client = BngBlasterControllerClient()
        await client.stop_instance(instance_name)
        await self.fetch_instances()
