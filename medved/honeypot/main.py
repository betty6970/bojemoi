import asyncio
import logging
import signal

from .config import settings
from .db import init_db, close_db
from .metrics import start_metrics_server
from .faraday_reporter import faraday_reporter_loop
from .protocols.ssh_handler import start_ssh_server
from .protocols.http_handler import start_http_server
from .protocols.rdp_handler import start_rdp_server
from .protocols.smb_handler import start_smb_server
from .protocols.ftp_handler import start_ftp_server
from .protocols.telnet_handler import start_telnet_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("medved")


async def main():
    logger.info("Medved honeypot starting...")

    # Init database
    await init_db()
    logger.info("Database ready")

    # Start Prometheus metrics
    start_metrics_server()
    logger.info("Metrics server on port %d", settings.metrics_port)

    # Start all protocol handlers
    servers = []
    for name, starter in [
        ("SSH", start_ssh_server),
        ("HTTP", start_http_server),
        ("RDP", start_rdp_server),
        ("SMB", start_smb_server),
        ("FTP", start_ftp_server),
        ("Telnet", start_telnet_server),
    ]:
        try:
            result = await starter()
            if result is not None:
                servers.append(result)
            logger.info("%s handler started", name)
        except Exception:
            logger.exception("Failed to start %s handler", name)

    # Start Faraday reporter
    reporter_task = asyncio.create_task(faraday_reporter_loop())

    logger.info("Medved honeypot ready - all protocols listening")

    # Wait for shutdown signal
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    await stop.wait()
    logger.info("Shutting down...")

    reporter_task.cancel()
    for server in servers:
        server.close()
    await close_db()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
