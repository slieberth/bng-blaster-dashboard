import logging
import reflex as rx

from dashboard.pages import index  # noqa: F401
from dashboard.pages import login  # noqa: F401
from dashboard.pages import instance_dashboard  # noqa: F401

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = rx.App()



