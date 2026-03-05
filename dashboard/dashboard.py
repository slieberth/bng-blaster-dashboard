import logging
import reflex as rx

# from dashboard.pages.index import index
from dashboard.pages import index  # noqa: F401
from dashboard.pages import login  # noqa: F401

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = rx.App()



