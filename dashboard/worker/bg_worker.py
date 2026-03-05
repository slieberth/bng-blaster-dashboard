from __future__ import annotations

import asyncio
import logging
import os
import signal


#
# demo only
#

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("dashboard.bg_worker")


async def worker_loop(stop_event: asyncio.Event) -> None:
    """Main worker loop."""
    logger.info("Background worker started")

    while not stop_event.is_set():
        logger.info("Background worker tick")
        await asyncio.sleep(5)

    logger.info("Background worker stopping")


def main() -> None:
    """Entry point for the background worker process."""
    stop_event = asyncio.Event()

    def _signal_handler(*_):
        logger.info("Shutdown signal received")
        stop_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    asyncio.run(worker_loop(stop_event))


if __name__ == "__main__":
    main()