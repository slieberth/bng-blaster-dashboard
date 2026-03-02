# dashboard/models/instance.py
from __future__ import annotations
from pydantic.dataclasses import dataclass
from typing import Optional

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