import asyncio
import logging
import struct
import time
import uuid

from ..config import settings
from ..db import log_event
from ..metrics import connections_total, events_total, connection_duration

logger = logging.getLogger("medved.rdp")

# RDP Connection Confirm (X.224)
RDP_NEG_RSP = (
    b"\x03\x00"          # TPKT header
    b"\x00\x13"          # length 19
    b"\x0e"              # X.224 length
    b"\xd0"              # Connection Confirm
    b"\x00\x00"          # dst-ref
    b"\x00\x00"          # src-ref
    b"\x00"              # class 0
    b"\x02"              # RDP Negotiation Response
    b"\x00"              # flags
    b"\x08\x00"          # length
    b"\x00\x00\x00\x00"  # selected protocol: PROTOCOL_RDP
)


class RDPHandler:
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
            connections_total.labels(protocol="rdp").inc()
            events_total.labels(protocol="rdp", event_type="connection").inc()
            logger.info("RDP connection from %s:%d", self.ip, self.port)
            await log_event(
                source_ip=self.ip,
                source_port=self.port,
                dest_port=settings.rdp_port,
                protocol="rdp",
                event_type="connection",
                session_id=self.session_id,
            )

            # Read X.224 Connection Request
            data = await asyncio.wait_for(self.reader.read(4096), timeout=30)
            if not data:
                return

            raw_data = {"initial_bytes": data[:64].hex()}

            # Extract cookie/username from RDP request if present
            username = None
            if b"Cookie:" in data:
                try:
                    cookie_start = data.index(b"Cookie:") + 7
                    cookie_end = data.index(b"\r\n", cookie_start)
                    cookie = data[cookie_start:cookie_end].decode("ascii", errors="replace").strip()
                    raw_data["cookie"] = cookie
                    if "mstshash=" in cookie:
                        username = cookie.split("mstshash=")[1].strip()
                except (ValueError, IndexError):
                    pass

            if username:
                events_total.labels(protocol="rdp", event_type="auth_attempt").inc()
                await log_event(
                    source_ip=self.ip,
                    source_port=self.port,
                    dest_port=settings.rdp_port,
                    protocol="rdp",
                    event_type="auth_attempt",
                    username=username,
                    session_id=self.session_id,
                    raw_data=raw_data,
                )
            else:
                await log_event(
                    source_ip=self.ip,
                    source_port=self.port,
                    dest_port=settings.rdp_port,
                    protocol="rdp",
                    event_type="handshake",
                    session_id=self.session_id,
                    raw_data=raw_data,
                )

            # Send Connection Confirm
            self.writer.write(RDP_NEG_RSP)
            await self.writer.drain()

            # Read more data (client will try TLS/CredSSP)
            try:
                more = await asyncio.wait_for(self.reader.read(4096), timeout=10)
                if more:
                    events_total.labels(protocol="rdp", event_type="payload").inc()
                    await log_event(
                        source_ip=self.ip,
                        source_port=self.port,
                        dest_port=settings.rdp_port,
                        protocol="rdp",
                        event_type="payload",
                        session_id=self.session_id,
                        raw_data={"follow_up_bytes": more[:128].hex()},
                    )
            except asyncio.TimeoutError:
                pass

        except asyncio.TimeoutError:
            pass
        except Exception:
            logger.exception("RDP handler error from %s", self.ip)
        finally:
            duration = time.monotonic() - self.start
            connection_duration.labels(protocol="rdp").observe(duration)
            self.writer.close()


async def handle_rdp_connection(reader, writer):
    handler = RDPHandler(reader, writer)
    await handler.handle()


async def start_rdp_server():
    server = await asyncio.start_server(
        handle_rdp_connection, "0.0.0.0", settings.rdp_port,
    )
    logger.info("RDP honeypot listening on port %d", settings.rdp_port)
    return server
