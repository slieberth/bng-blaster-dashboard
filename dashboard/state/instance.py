import json
import os
from pathlib import Path
from enum import Enum

import reflex as rx

from dashboard.services.controller_client import BngBlasterControllerClient


class Instance(rx.State):
    # --- instance controls ---
    name: str = ""


