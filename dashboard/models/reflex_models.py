# dashboard/models/reflex_models.py
from __future__ import annotations
from pydantic.dataclasses import dataclass
from typing import Optional


@dataclass
class InstanceRow:
    name: str
    status: str

    # Display strings for the table
    session_text: str = "-"
    streams_text: str = "-"

