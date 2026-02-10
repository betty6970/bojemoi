import asyncio
import logging
import time
import uuid

from ..config import settings
from ..db import log_event
from ..metrics import connections_total, auth_attempts_total, events_total, connection_duration

logger = logging.getLogger("medved.telnet")

TELNET_BANNER = b"\r\nUbuntu 22.04.3 LTS\r\n\r\n"
TELNET_LOGIN = b"login: "
TELNET_PASS = b"Password: "
TELNET_FAIL = b"\r\nLogin incorrect\r\n\r\n"
# IAC WILL ECHO, IAC WILL SGA (suppress go ahead)
TELNET_OPTS = b"\xff\xfb\x01\xff\xfb\x03"


class TelnetHandler:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.peer = writer.get_extra_info("peername")
        self.ip = self.peer[0] if self.peer else "unknown"
        self.port = self.peer[1] if self.peer else 0
        self.session_id = str(uuid.uuid4())[:12]
        self.start = time.monotonic()

    async def handle(self):
        try:
            connections_total.labels(protocol="telnet").inc()
            events_total.labels(protocol="telnet", event_type="connection").inc()
            logger.info("Telnet connection from %s:%d", self.ip, self.port)
            await log_event(
                source_ip=self.ip,
                source_port=self.port,
                dest_port=settings.telnet_port,
                protocol="telnet",
                event_type="connection",
                session_id=self.session_id,
            )

            # Send telnet options + banner
            self.writer.write(TELNET_OPTS + TELNET_BANNER)
            await self.writer.drain()

            # Allow 3 login attempts
            for _ in range(3):
                username = await self._prompt(TELNET_LOGIN)
                if username is None:
                    return
                password = await self._prompt(TELNET_PASS)
                if password is None:
                    return

                auth_attempts_total.labels(protocol="telnet").inc()
                events_total.labels(protocol="telnet", event_type="auth_attempt").inc()
                logger.info("Telnet auth: %s:%s from %s", username, password, self.ip)
                await log_event(
                    source_ip=self.ip,
                    source_port=self.port,
                    dest_port=settings.telnet_port,
                    protocol="telnet",
                    event_type="auth_attempt",
                    username=username,
                    password=password,
                    session_id=self.session_id,
                )

                self.writer.write(TELNET_FAIL)
                await self.writer.drain()

        except asyncio.TimeoutError:
            pass
        except Exception:
            logger.exception("Telnet handler error from %s", self.ip)
        finally:
            duration = time.monotonic() - self.start
            connection_duration.labels(protocol="telnet").observe(duration)
            self.writer.close()

    async def _prompt(self, prompt: bytes) -> str | None:
        self.writer.write(prompt)
        await self.writer.drain()
        try:
            data = await asyncio.wait_for(self.reader.readline(), timeout=60)
        except asyncio.TimeoutError:
            return None
        if not data:
            return None
        # Strip telnet IAC sequences
        clean = bytearray()
        i = 0
        raw = bytes(data)
        while i < len(raw):
            if raw[i] == 0xFF and i + 1 < len(raw):
                if raw[i + 1] in (0xFB, 0xFC, 0xFD, 0xFE) and i + 2 < len(raw):
                    i += 3
                elif raw[i + 1] == 0xFF:
                    clean.append(0xFF)
                    i += 2
                else:
                    i += 2
            else:
                clean.append(raw[i])
                i += 1
        return clean.decode("utf-8", errors="replace").strip()


async def handle_telnet_connection(reader, writer):
    handler = TelnetHandler(reader, writer)
    await handler.handle()


async def start_telnet_server():
    server = await asyncio.start_server(
        handle_telnet_connection, "0.0.0.0", settings.telnet_port,
    )
    logger.info("Telnet honeypot listening on port %d", settings.telnet_port)
    return server
