import asyncio
import logging
import sys

import uvicorn

from .config import settings
from . import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("alert_agent")


async def main():
    await db.init_db()
    logger.info(
        "Alert-agent starting (dry_run=%s, model=%s, cooldown=%ds)",
        settings.dry_run,
        settings.ollama_model,
        settings.cooldown_seconds,
    )

    from .webhook import app

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        await db.close_db()
        logger.info("Shutdown complete")


asyncio.run(main())
