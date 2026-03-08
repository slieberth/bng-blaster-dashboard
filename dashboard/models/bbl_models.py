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

class SessionTraffic(BaseModel):
    total_flows: int = Field(alias="total-flows")
    verified_flows: int = Field(alias="verified-flows")

    downstream_ipv4_flow_id: Optional[int] = Field(None, alias="downstream-ipv4-flow-id")
    downstream_ipv4_tx_packets: Optional[int] = Field(None, alias="downstream-ipv4-tx-packets")
    downstream_ipv4_rx_packets: Optional[int] = Field(None, alias="downstream-ipv4-rx-packets")
    downstream_ipv4_rx_first_seq: Optional[int] = Field(None, alias="downstream-ipv4-rx-first-seq")
    downstream_ipv4_loss: Optional[int] = Field(None, alias="downstream-ipv4-loss")
    downstream_ipv4_wrong_session: Optional[int] = Field(None, alias="downstream-ipv4-wrong-session")

    upstream_ipv4_flow_id: Optional[int] = Field(None, alias="upstream-ipv4-flow-id")
    upstream_ipv4_tx_packets: Optional[int] = Field(None, alias="upstream-ipv4-tx-packets")
    upstream_ipv4_rx_packets: Optional[int] = Field(None, alias="upstream-ipv4-rx-packets")
    upstream_ipv4_rx_first_seq: Optional[int] = Field(None, alias="upstream-ipv4-rx-first-seq")
    upstream_ipv4_loss: Optional[int] = Field(None, alias="upstream-ipv4-loss")
    upstream_ipv4_wrong_session: Optional[int] = Field(None, alias="upstream-ipv4-wrong-session")


class A10NSPStats(BaseModel):
    interface: str
    s_vlan: Optional[int] = Field(None, alias="s-vlan")
    qinq_send: Optional[bool] = Field(None, alias="qinq-send")
    qinq_received: Optional[bool] = Field(None, alias="qinq-received")

    tx_packets: Optional[int] = Field(None, alias="tx-packets")
    rx_packets: Optional[int] = Field(None, alias="rx-packets")


class SessionInfo(BaseModel):
    type: str

    session_id: int = Field(alias="session-id")
    session_state: str = Field(alias="session-state")
    session_version: Optional[int] = Field(None, alias="session-version")

    flapped: Optional[int] = None
    interface: Optional[str] = None

    outer_vlan: Optional[int] = Field(None, alias="outer-vlan")
    inner_vlan: Optional[int] = Field(None, alias="inner-vlan")

    mac: Optional[str] = None
    username: Optional[str] = None
    reply_message: Optional[str] = Field(None, alias="reply-message")

    lcp_state: Optional[str] = Field(None, alias="lcp-state")
    ipcp_state: Optional[str] = Field(None, alias="ipcp-state")
    ip6cp_state: Optional[str] = Field(None, alias="ip6cp-state")

    ipv4_address: Optional[str] = Field(None, alias="ipv4-address")
    ipv4_dns1: Optional[str] = Field(None, alias="ipv4-dns1")
    ipv4_dns2: Optional[str] = Field(None, alias="ipv4-dns2")

    dhcpv6_state: Optional[str] = Field(None, alias="dhcpv6-state")

    tx_packets: Optional[int] = Field(None, alias="tx-packets")
    rx_packets: Optional[int] = Field(None, alias="rx-packets")
    rx_fragmented_packets: Optional[int] = Field(None, alias="rx-fragmented-packets")

    tx_bytes: Optional[int] = Field(None, alias="tx-bytes")
    rx_bytes: Optional[int] = Field(None, alias="rx-bytes")

    tx_accounting_packets: Optional[int] = Field(None, alias="tx-accounting-packets")
    rx_accounting_packets: Optional[int] = Field(None, alias="rx-accounting-packets")

    tx_accounting_bytes: Optional[int] = Field(None, alias="tx-accounting-bytes")
    rx_accounting_bytes: Optional[int] = Field(None, alias="rx-accounting-bytes")

    tx_igmp: Optional[int] = Field(None, alias="tx-igmp")
    rx_igmp: Optional[int] = Field(None, alias="rx-igmp")
    rx_igmp_wrong_state: Optional[int] = Field(None, alias="rx-igmp-wrong-state")

    tx_icmp: Optional[int] = Field(None, alias="tx-icmp")
    rx_icmp: Optional[int] = Field(None, alias="rx-icmp")

    tx_icmpv6: Optional[int] = Field(None, alias="tx-icmpv6")
    rx_icmpv6: Optional[int] = Field(None, alias="rx-icmpv6")

    session_traffic: Optional[SessionTraffic] = Field(None, alias="session-traffic")

    a10nsp: Optional[A10NSPStats] = None