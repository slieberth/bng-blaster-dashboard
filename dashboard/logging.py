# dashboard/dashboard.py
from dashboard.logging_setup import setup_logging
setup_logging()

import logging
import reflex as rx
from dashboard.services.instance_watcher import instance_watcher

from dashboard.pages import index  # noqa: F401
from dashboard.pages import login  # noqa: F401

logger = logging.getLogger(__name__)

app = rx.App()

@app._api.on_event("startup")
async def startup_event():
    logger.info("startup_event")
    await instance_watcher.start()

@app._api.on_event("shutdown")
async def shutdown_event():
    logger.info("shutdown_event")
    await instance_watcher.stop()