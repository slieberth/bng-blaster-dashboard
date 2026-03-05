import asyncio
import logging

logger = logging.getLogger("wui.instances_dashboard")

async def long_running_task(foo, bar):
    try:
        while True:
            logger.info(f"!!! Running long_running_task with foo={foo} and bar={bar}")
            await asyncio.sleep(
                5
            )  # add some polling delay to avoid running too often
    except asyncio.CancelledError:
        logger.info("Task was stopped")