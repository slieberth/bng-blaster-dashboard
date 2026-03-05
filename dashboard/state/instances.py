# dashboard/state/instances.py
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import reflex as rx

from dashboard.models.bbl_models import SessionCounters, StreamStats
from dashboard.models.reflex_models import InstanceRow
from dashboard.services.controller_client import BngBlasterControllerClient
from dashboard.services.key_value_store import make_store_from_env

logger = logging.getLogger("wui.instances_dashboard")

DEFAULT_START_PARAMS = {
    "logging": True,
    "logging_flags": ["error", "ip"],
    "pcap_capture": True,
    "report": True,
    "report_flags": ["sessions", "stream"],
}


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


class InstancesState(rx.State):
    """Main state for managing multiple instances."""

    instances: list[str] = []
    items: list[InstanceRow] = []

    # --- auto refresh ---
    auto_refresh: bool = True
    refresh_interval_ms: int = 3000
    _refresh_running: bool = False  # prevents multiple loops


    @rx.event
    def set_auto_refresh(self, v: bool) -> None:
        self.auto_refresh = bool(v)

    @rx.event
    def set_refresh_interval_ms(self, v: str) -> None:
        # v comes from select -> string
        try:
            self.refresh_interval_ms = int(v)
        except Exception:
            self.refresh_interval_ms = 3000

    @rx.event
    async def start_refresh_loop(self) -> None:
        # do not start twice
        if self._refresh_running:
            return
        self._refresh_running = True

        try:
            while self.auto_refresh:
                await self.fetch_instances()
                await rx.sleep(self.refresh_interval_ms / 1000)
        finally:
            self._refresh_running = False

    @rx.event
    def stop_refresh_loop(self) -> None:
        # this stops the loop at next iteration boundary
        self.auto_refresh = False

    # ------------------------------------
    # your existing fetch implementation
    # ------------------------------------
    @rx.event
    async def fetch_instances(self) -> None:
        t0 = time.time()
        self.refresh_status = "Refreshing..."
        self.last_refresh_ts = int(t0)

        client = BngBlasterControllerClient()
        prefix = os.getenv("BBL_DB_PREFIX", "bbl-db")
        store = make_store_from_env(prefix=prefix)

        fetched_names = await client.list_instances()
        self.instances = fetched_names

        rows: list[InstanceRow] = []

        for instance_name in fetched_names:
            status_str = await client.get_instance_status(instance_name)
            cfg = await client.get_instance_config(instance_name)
            cfg_str = json.dumps(cfg, ensure_ascii=False)

            # Redis summaries
            sess_raw = store.get_session_counters(instance_name) or {}
            stream_raw = store.get_stream_stats(instance_name) or {}

            # --- session counters ---
            established = pppoe = dhcp = dhcpv6 = 0
            if sess_raw:
                try:
                    sc = SessionCounters.model_validate(sess_raw)
                    established = sc.sessions_established
                    pppoe = sc.sessions_pppoe
                    dhcp = sc.dhcp_sessions
                    dhcpv6 = sc.dhcpv6_sessions
                except Exception:
                    established = _safe_int(sess_raw.get("sessions-established"))
                    pppoe = _safe_int(sess_raw.get("sessions-pppoe"))
                    dhcp = _safe_int(sess_raw.get("dhcp-sessions"))
                    dhcpv6 = _safe_int(sess_raw.get("dhcpv6-sessions"))

            session_total = pppoe + dhcp + dhcpv6
            session_text = "-" if (established == 0 and session_total == 0) else f"{established} / {session_total}"

            # --- stream stats ---
            total = verified = 0
            if stream_raw:
                try:
                    st = StreamStats.model_validate(stream_raw)
                    total = st.total_flows
                    verified = st.verified_flows
                except Exception:
                    total = _safe_int(stream_raw.get("total-flows"))
                    verified = _safe_int(stream_raw.get("verified-flows"))

            streams_text = "-" if (total == 0 and verified == 0) else f"{total} / {verified}"

            rows.append(
                InstanceRow(
                    name=instance_name,
                    status=status_str or "unknown",
                    config_json_str=cfg_str,
                    session_text=session_text,
                    streams_text=streams_text,
                )
            )

        self.items = rows
        self.refresh_status = f"Updated ({len(rows)}) in {int((time.time() - t0)*1000)}ms"

    # ----------------------------
    # start/stop mechanism
    # ----------------------------
    @rx.event
    async def start_instance(self, instance_name: str) -> None:
        client = BngBlasterControllerClient()
        await client.start_instance(instance_name, DEFAULT_START_PARAMS)

        store = make_store_from_env(prefix=os.getenv("BBL_DB_PREFIX", "bbl-db"))
        store.update_instance_meta(instance_name, {"started_ts": int(time.time())})

        await self.fetch_instances()

    @rx.event
    async def stop_instance(self, instance_name: str) -> None:
        client = BngBlasterControllerClient()
        await client.stop_instance(instance_name)

        store = make_store_from_env(prefix=os.getenv("BBL_DB_PREFIX", "bbl-db"))
        store.update_instance_meta(instance_name, {"stopped_ts": int(time.time())})

        await self.fetch_instances()