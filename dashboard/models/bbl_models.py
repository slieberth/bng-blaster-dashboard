# dashboard/models/bbl_models.py
from __future__ import annotations
from pydantic.dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

from enum import Enum


class InstanceStatus(str, Enum):
    STARTED = "started"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class InstanceModel:
    name: str
    status: InstanceStatus
    config_json_str: Optional[str] = None

@dataclass
class InstanceMeta:
    name: str
    status: Optional[InstanceStatus] = None  # <- recommended

    created_ts: Optional[int] = None
    started_ts: Optional[int] = None
    stopped_ts: Optional[int] = None

    config_json_str: Optional[str] = None
    startup_params: Optional[Dict[str, Any]] = None

    session_counters: Optional[Dict[str, Any]] = None
    stream_stats: Optional[Dict[str, Any]] = None

    last_seen_ts: Optional[int] = None

class SessionCounters(BaseModel):
    sessions: int

    sessions_pppoe: int = Field(alias="sessions-pppoe")
    sessions_ipoe: int = Field(alias="sessions-ipoe")

    sessions_established: int = Field(alias="sessions-established")
    sessions_established_max: int = Field(alias="sessions-established-max")

    sessions_outstanding: int = Field(alias="sessions-outstanding")
    sessions_terminated: int = Field(alias="sessions-terminated")
    sessions_flapped: int = Field(alias="sessions-flapped")

    dhcp_sessions: int = Field(alias="dhcp-sessions")
    dhcp_sessions_established: int = Field(alias="dhcp-sessions-established")
    dhcp_sessions_established_max: int = Field(alias="dhcp-sessions-established-max")

    dhcpv6_sessions: int = Field(alias="dhcpv6-sessions")
    dhcpv6_sessions_established: int = Field(alias="dhcpv6-sessions-established")
    dhcpv6_sessions_established_max: int = Field(alias="dhcpv6-sessions-established-max")

    setup_time: int = Field(alias="setup-time")

    setup_rate: float = Field(alias="setup-rate")
    setup_rate_min: float = Field(alias="setup-rate-min")
    setup_rate_avg: float = Field(alias="setup-rate-avg")
    setup_rate_max: float = Field(alias="setup-rate-max")

    session_traffic_flows: int = Field(alias="session-traffic-flows")
    session_traffic_flows_verified: int = Field(alias="session-traffic-flows-verified")

    stream_traffic_flows: int = Field(alias="stream-traffic-flows")
    stream_traffic_flows_verified: int = Field(alias="stream-traffic-flows-verified")

class StreamStats(BaseModel):
    total_flows: int = Field(alias="total-flows")
    verified_flows: int = Field(alias="verified-flows")