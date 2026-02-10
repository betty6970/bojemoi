import asyncio
import logging
import time
import uuid

from ..config import settings
from ..db import log_event
from ..metrics import connections_total, auth_attempts_total, events_total, connection_duration

logger = logging.getLogger("medved.ftp")

FTP_BANNER = "220 ProFTPD 1.3.5e Server (Welcome) [{}]\r\n"
FTP_USER_OK = "331 Password required for {}\r\n"
FTP_LOGIN_FAIL = "530 Login incorrect.\r\n"
FTP_UNKNOWN = "500 Unknown command.\r\n"
FTP_GOODBYE = "221 Goodbye.\r\n"


class FTPHandler:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.peer = writer.get_extra_info("peername")
        self.ip = self.peer[0] if self.peer else "unknown"
        self.port = self.peer[1] if self.peer else 0
        self.session_id = str(uuid.uuid4())[:12]
        self.start = time.monotonic()
        self.current_user = None

    async def handle(self):
        try:
            connections_total.labels(protocol="ftp").inc()
            events_total.labels(protocol="ftp", event_type="connection").inc()
            logger.info("FTP connection from %s:%d", self.ip, self.port)
            await log_event(
                source_ip=self.ip,
                source_port=self.port,
                dest_port=settings.ftp_port,
                protocol="ftp",
                event_type="connection",
                session_id=self.session_id,
            )

            # Send banner
            local = self.writer.get_extra_info("sockname")
            banner = FTP_BANNER.format(local[0] if local else "127.0.0.1")
            self.writer.write(banner.encode())
            await self.writer.drain()

            # Command loop
            for _ in range(20):  # max 20 commands
                try:
                    line = await asyncio.wait_for(self.reader.readline(), timeout=60)
                except asyncio.TimeoutError:
                    break
                if not line:
                    break

                cmd_line = line.decode("utf-8", errors="replace").strip()
                if not cmd_line:
                    continue

                parts = cmd_line.split(" ", 1)
                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "USER":
                    self.current_user = arg
                    self.writer.write(FTP_USER_OK.format(arg).encode())
                    await self.writer.drain()
                elif cmd == "PASS":
                    auth_attempts_total.labels(protocol="ftp").inc()
                    events_total.labels(protocol="ftp", event_type="auth_attempt").inc()
                    logger.info("FTP auth: %s:%s from %s", self.current_user, arg, self.ip)
                    await log_event(
                        source_ip=self.ip,
                        source_port=self.port,
                        dest_port=settings.ftp_port,
                        protocol="ftp",
                        event_type="auth_attempt",
                        username=self.current_user,
                        password=arg,
                        session_id=self.session_id,
                    )
                    self.writer.write(FTP_LOGIN_FAIL.encode())
                    await self.writer.drain()
                    self.current_user = None
                elif cmd == "QUIT":
                    self.writer.write(FTP_GOODBYE.encode())
                    await self.writer.drain()
                    break
                else:
                    events_total.labels(protocol="ftp", event_type="command").inc()
                    await log_event(
                        source_ip=self.ip,
                        source_port=self.port,
                        dest_port=settings.ftp_port,
                        protocol="ftp",
                        event_type="command",
                        payload=cmd_line,
                        session_id=self.session_id,
                    )
                    self.writer.write(FTP_UNKNOWN.encode())
                    await self.writer.drain()

        except asyncio.TimeoutError:
            pass
        except Exception:
            logger.exception("FTP handler error from %s", self.ip)
        finally:
            duration = time.monotonic() - self.start
            connection_duration.labels(protocol="ftp").observe(duration)
            self.writer.close()


async def handle_ftp_connection(reader, writer):
    handler = FTPHandler(reader, writer)
    await handler.handle()


async def start_ftp_server():
    server = await asyncio.start_server(
        handle_ftp_connection, "0.0.0.0", settings.ftp_port,
    )
    logger.info("FTP honeypot listening on port %d", settings.ftp_port)
    return server
