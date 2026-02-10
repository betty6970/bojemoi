import asyncio
import logging
import struct
import time
import uuid

from ..config import settings
from ..db import log_event
from ..metrics import connections_total, auth_attempts_total, events_total, connection_duration

logger = logging.getLogger("medved.smb")

# SMB2 Negotiate Response (simplified)
SMB2_NEGOTIATE_RESP = (
    b"\x00"                     # NetBIOS session message
    b"\x00\x00\x82"             # length placeholder
    b"\xfeSMB"                  # SMB2 magic
    b"\x40\x00"                 # header length 64
    b"\x00\x00"                 # credit charge
    b"\x00\x00\x00\x00"        # status: SUCCESS
    b"\x00\x00"                 # command: NEGOTIATE
    b"\x01\x00"                 # credit granted
    b"\x01\x00\x00\x00"        # flags: response
    b"\x00\x00\x00\x00"        # next command
    b"\x00\x00\x00\x00\x00\x00\x00\x00"  # message id
    b"\x00\x00\x00\x00"        # reserved
    b"\x00\x00\x00\x00"        # tree id
    b"\x00\x00\x00\x00\x00\x00\x00\x00"  # session id
    b"\x00\x00\x00\x00\x00\x00\x00\x00"  # signature (16 bytes)
    b"\x00\x00\x00\x00\x00\x00\x00\x00"
    # Negotiate response body
    b"\x41\x00"                 # structure size
    b"\x01\x00"                 # security mode: signing enabled
    b"\x02\x02"                 # dialect: SMB 2.0.2
    b"\x00\x00"                 # negotiate context count
    b"\x00\x00\x00\x00\x00\x00\x00\x00"    # server GUID (16 bytes)
    b"\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x07\x00\x00\x00"        # capabilities
    b"\x00\x00\x10\x00"        # max transact size
    b"\x00\x00\x10\x00"        # max read size
    b"\x00\x00\x10\x00"        # max write size
    b"\x00\x00\x00\x00\x00\x00\x00\x00"  # system time
    b"\x00\x00\x00\x00\x00\x00\x00\x00"  # server start time
    b"\x00\x00"                 # security buffer offset
    b"\x00\x00"                 # security buffer length
    b"\x00\x00\x00\x00"        # negotiate context offset
)


class SMBHandler:
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
            connections_total.labels(protocol="smb").inc()
            events_total.labels(protocol="smb", event_type="connection").inc()
            logger.info("SMB connection from %s:%d", self.ip, self.port)
            await log_event(
                source_ip=self.ip,
                source_port=self.port,
                dest_port=settings.smb_port,
                protocol="smb",
                event_type="connection",
                session_id=self.session_id,
            )

            # Read initial data (NetBIOS + SMB negotiate)
            data = await asyncio.wait_for(self.reader.read(4096), timeout=30)
            if not data:
                return

            raw_data = {"initial_bytes": data[:128].hex()}

            # Check for SMB1 or SMB2 magic
            is_smb = False
            if b"\xffSMB" in data:
                raw_data["version"] = "SMB1"
                is_smb = True
            elif b"\xfeSMB" in data:
                raw_data["version"] = "SMB2"
                is_smb = True

            await log_event(
                source_ip=self.ip,
                source_port=self.port,
                dest_port=settings.smb_port,
                protocol="smb",
                event_type="negotiate",
                session_id=self.session_id,
                raw_data=raw_data,
            )

            if is_smb:
                # Send negotiate response
                self.writer.write(SMB2_NEGOTIATE_RESP)
                await self.writer.drain()

                # Wait for Session Setup (may contain NTLM)
                try:
                    auth_data = await asyncio.wait_for(self.reader.read(4096), timeout=15)
                    if auth_data:
                        self._extract_ntlm(auth_data)
                except asyncio.TimeoutError:
                    pass

        except asyncio.TimeoutError:
            pass
        except Exception:
            logger.exception("SMB handler error from %s", self.ip)
        finally:
            duration = time.monotonic() - self.start
            connection_duration.labels(protocol="smb").observe(duration)
            self.writer.close()

    def _extract_ntlm(self, data: bytes):
        raw = {"auth_bytes": data[:256].hex()}
        username = None

        # Look for NTLMSSP signature
        ntlm_offset = data.find(b"NTLMSSP\x00")
        if ntlm_offset >= 0:
            raw["ntlmssp_found"] = True
            msg_type_offset = ntlm_offset + 8
            if len(data) > msg_type_offset + 4:
                msg_type = struct.unpack_from("<I", data, msg_type_offset)[0]
                raw["ntlm_msg_type"] = msg_type

                # Type 3 = Authentication message
                if msg_type == 3 and len(data) > ntlm_offset + 36:
                    try:
                        # Domain name fields at offset 28
                        domain_len = struct.unpack_from("<H", data, ntlm_offset + 28)[0]
                        domain_off = struct.unpack_from("<I", data, ntlm_offset + 32)[0]
                        # User name fields at offset 36
                        user_len = struct.unpack_from("<H", data, ntlm_offset + 36)[0]
                        user_off = struct.unpack_from("<I", data, ntlm_offset + 40)[0]

                        if domain_len > 0 and domain_off + domain_len <= len(data):
                            domain = data[domain_off:domain_off + domain_len].decode("utf-16-le", errors="replace")
                            raw["domain"] = domain
                        if user_len > 0 and user_off + user_len <= len(data):
                            username = data[user_off:user_off + user_len].decode("utf-16-le", errors="replace")
                            raw["username"] = username
                    except (struct.error, IndexError):
                        pass

        if username:
            auth_attempts_total.labels(protocol="smb").inc()
            events_total.labels(protocol="smb", event_type="auth_attempt").inc()
            logger.info("SMB NTLM auth from %s: %s", self.ip, username)

        asyncio.ensure_future(log_event(
            source_ip=self.ip,
            source_port=self.port,
            dest_port=settings.smb_port,
            protocol="smb",
            event_type="auth_attempt" if username else "payload",
            username=username,
            session_id=self.session_id,
            raw_data=raw,
        ))


async def handle_smb_connection(reader, writer):
    handler = SMBHandler(reader, writer)
    await handler.handle()


async def start_smb_server():
    server = await asyncio.start_server(
        handle_smb_connection, "0.0.0.0", settings.smb_port,
    )
    logger.info("SMB honeypot listening on port %d", settings.smb_port)
    return server
