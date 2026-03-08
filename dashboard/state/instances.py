from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import reflex as rx
import yaml

from dashboard.models.bbl_models import InstanceStatus, SessionCounters, StreamStats
from dashboard.models.reflex_models import InstanceRow
from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env

logger = logging.getLogger("dashboard.state.instances")


DEFAULT_START_PARAMS = {
    "logging": True,
    "logging_flags": ["error", "ip"],
    "pcap_capture": True,
    "report": True,
    "report_flags": ["sessions", "stream"],
}

DEFAULT_DB_PREFIX = "bbl-db"
DEFAULT_REDIS_SUMMARIES_TTL_SEC = 60
DEFAULT_DASHBOARD_REFRESH_SEC = 0.5


def _now_ts() -> int:
    """Return the current Unix timestamp in seconds."""
    return int(time.time())


def _make_store():
    """Create the key-value store using the configured Redis prefix."""
    return make_store_from_env(prefix=os.getenv("BBL_DB_PREFIX", DEFAULT_DB_PREFIX))


def _safe_status(status: str) -> InstanceStatus:
    """Convert a raw controller status string into an InstanceStatus enum."""
    try:
        return InstanceStatus(status)
    except Exception:
        return InstanceStatus.ERROR


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(value)
    except Exception:
        return default


class InstancesState(rx.State):
    """State for the main instances dashboard."""

    instances: list[str] = []
    items: list[InstanceRow] = []

    selected_instance_name: str | None = None
    selected_config_yaml: str | None = None
    edited_config_yaml: str | None = None
    is_config_dirty: bool = False
    is_config_open: bool = True
    load_status: str = ""
    config_save_status: str = ""

    async def _fetch_and_store_session_counters(
        self,
        client: BngBlasterControllerClient,
        store,
        instance_name: str,
    ) -> None:
        """Fetch session counters from the controller and store them in Redis."""
        session_counters = await client.instance_command_with_retries(
            instance_name,
            "session-counters",
            {},
        )
        counters = SessionCounters.model_validate(session_counters["session-counters"])
        store.set_session_counters(
            instance_name,
            counters.model_dump(),
            ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
        )

    async def _fetch_and_store_stream_stats(
        self,
        client: BngBlasterControllerClient,
        store,
        instance_name: str,
    ) -> None:
        """Fetch stream statistics from the controller and store them in Redis."""
        stream_stats = await client.instance_command_with_retries(
            instance_name,
            "stream-stats",
            {},
        )
        stats = StreamStats.model_validate(stream_stats["stream-stats"])
        store.set_stream_stats(
            instance_name,
            stats.model_dump(),
            ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
        )

    def _reset_runtime_counters(self, store, instance_name: str) -> None:
        """Reset session and stream counters for stopped instances."""
        store.set_session_counters(
            instance_name,
            {
                "sessions_established": 0,
                "sessions_pppoe": 0,
                "dhcp_sessions": 0,
                "dhcpv6_sessions": 0,
            },
            ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
        )

        store.set_stream_stats(
            instance_name,
            {
                "total_flows": 0,
                "verified_flows": 0,
            },
            ex=DEFAULT_REDIS_SUMMARIES_TTL_SEC,
        )

    def _build_instance_row(self, instance_name: str, status: str, store) -> InstanceRow:
        """Build a UI row object from Redis-backed runtime data."""
        sess_raw = store.get_session_counters(instance_name) or {}
        stream_raw = store.get_stream_stats(instance_name) or {}

        established = _safe_int(sess_raw.get("sessions_established", 0))
        pppoe = _safe_int(sess_raw.get("sessions_pppoe", 0))
        dhcp = _safe_int(sess_raw.get("dhcp_sessions", 0))
        dhcpv6 = _safe_int(sess_raw.get("dhcpv6_sessions", 0))

        session_total = pppoe + dhcp + dhcpv6
        session_text = f"{established} / {session_total}" if session_total else "-"

        total = _safe_int(stream_raw.get("total_flows", 0))
        verified = _safe_int(stream_raw.get("verified_flows", 0))
        streams_text = f"{total} / {verified}" if total else "-"

        return InstanceRow(
            name=instance_name,
            status=status,
            config_json_str="",  # config is loaded on demand
            session_text=session_text,
            streams_text=streams_text,
        )

    async def _fetch_one_instance(
        self,
        client: BngBlasterControllerClient,
        store,
        instance_name: str,
    ) -> InstanceRow:
        """Fetch, cache, and format all dashboard data for one instance."""
        status = await client.get_instance_status(instance_name)
        status_enum = _safe_status(status)

        store.update_instance_meta(
            instance_name,
            {
                "name": instance_name,
                "status": status_enum.value,
                "last_seen_ts": _now_ts(),
            },
        )

        logger.debug("instance=%s status=%s", instance_name, status)

        if status_enum == InstanceStatus.STARTED:
            try:
                await self._fetch_and_store_session_counters(client, store, instance_name)
            except Exception:
                logger.exception(
                    "failed to fetch session counters for instance=%s",
                    instance_name,
                )

            try:
                await self._fetch_and_store_stream_stats(client, store, instance_name)
            except Exception:
                logger.exception(
                    "failed to fetch stream stats for instance=%s",
                    instance_name,
                )
        else:
            logger.debug("instance=%s not running -> reset counters", instance_name)
            self._reset_runtime_counters(store, instance_name)

        return self._build_instance_row(instance_name, status, store)

    @rx.event
    async def fetch_instances(self) -> None:
        """Refresh the full instances dashboard."""
        client = BngBlasterControllerClient()
        store = _make_store()

        try:
            fetched_names = await client.list_instances()
            self.instances = fetched_names

            rows = await asyncio.gather(
                *[
                    self._fetch_one_instance(client, store, instance_name)
                    for instance_name in fetched_names
                ]
            )

            self.items = list(rows)

        except Exception:
            logger.exception("fetch_instances failed")

    # ----------------------------
    # Start / stop actions
    # ----------------------------
    @rx.event
    async def start_instance(self, instance_name: str) -> None:
        """Start an instance and update its metadata."""
        client = BngBlasterControllerClient()
        await client.start_instance(instance_name, DEFAULT_START_PARAMS)

        store = _make_store()
        store.update_instance_meta(
            instance_name,
            {
                "started_ts": _now_ts(),
                "startup_params": DEFAULT_START_PARAMS,
            },
        )

        await self.fetch_instances()

    @rx.event
    async def stop_instance(self, instance_name: str) -> None:
        """Stop an instance and update its metadata."""
        client = BngBlasterControllerClient()
        await client.stop_instance(instance_name)

        store = _make_store()
        store.update_instance_meta(
            instance_name,
            {
                "stopped_ts": _now_ts(),
            },
        )

        await self.fetch_instances()

    # ----------------------------
    # Config editor
    # ----------------------------
    @rx.event
    async def edit_config(self, instance_name: str) -> None:
        """Load the selected instance config into the YAML editor."""
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
    async def save_config(self) -> None:
        """Validate the YAML editor content and upload it to the controller."""
        self.config_save_status = "Saving..."

        try:
            if not self.selected_instance_name:
                raise RuntimeError("No instance selected.")

            cfg_obj = yaml.safe_load(self.edited_config_yaml or "")
            if not isinstance(cfg_obj, dict):
                raise RuntimeError("YAML must be a dict/object at the top level.")

            client = BngBlasterControllerClient()
            await client.upload_config(self.selected_instance_name, cfg_obj)

            self.selected_config_yaml = self.edited_config_yaml
            self.is_config_dirty = False
            self.config_save_status = "Saved ✅"

            await self.fetch_instances()

        except Exception as exc:
            self.config_save_status = f"Save error: {exc}"

    @rx.event
    def set_selected_config_yaml(self, value: str) -> None:
        """Set the original YAML config string."""
        self.selected_config_yaml = value or ""

    @rx.event
    def close_config(self) -> None:
        """Close the config editor drawer/panel."""
        self.is_config_open = False
        self.config_save_status = ""
        self.is_config_dirty = False
        self.selected_instance_name = None

    @rx.event
    def on_config_editor_change(self, value: str) -> None:
        """Handle YAML editor changes and mark the config as dirty if needed."""
        self.edited_config_yaml = value or ""
        self.is_config_dirty = self.edited_config_yaml != (self.selected_config_yaml or "")

    # ----------------------------
    # Background refresh loop
    # ----------------------------
    @rx.event(background=True)
    async def update_dashboard(self):
        """Continuously refresh the dashboard in the background."""
        while True:
            async with self:
                await self.fetch_instances()
            await asyncio.sleep(DEFAULT_DASHBOARD_REFRESH_SEC)