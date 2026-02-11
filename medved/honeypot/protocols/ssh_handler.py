import asyncio
import asyncssh
import logging
import time
import uuid

from ..config import settings
from ..db import log_event
from ..metrics import connections_total, auth_attempts_total, events_total, connection_duration

logger = logging.getLogger("medved.ssh")

SSH_BANNER = "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"


class HoneypotSSHServer(asyncssh.SSHServer):
    def __init__(self):
        self._peer = None
        self._session_id = str(uuid.uuid4())[:12]
        self._start = time.monotonic()

    def connection_made(self, conn):
        self._peer = conn.get_extra_info("peername")
        ip = self._peer[0] if self._peer else "unknown"
        port = self._peer[1] if self._peer else 0
        connections_total.labels(protocol="ssh").inc()
        events_total.labels(protocol="ssh", event_type="connection").inc()
        logger.info("SSH connection from %s:%d", ip, port)
        asyncio.ensure_future(log_event(
            source_ip=ip,
            source_port=port,
            dest_port=settings.ssh_port,
            protocol="ssh",
            event_type="connection",
            session_id=self._session_id,
        ))

    def connection_lost(self, exc):
        duration = time.monotonic() - self._start
        connection_duration.labels(protocol="ssh").observe(duration)

    def begin_auth(self, username):
        return True  # require auth

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        ip = self._peer[0] if self._peer else "unknown"
        port = self._peer[1] if self._peer else 0
        auth_attempts_total.labels(protocol="ssh").inc()
        events_total.labels(protocol="ssh", event_type="auth_attempt").inc()
        logger.info("SSH auth: %s:%s from %s", username, password, ip)
        asyncio.ensure_future(log_event(
            source_ip=ip,
            source_port=port,
            dest_port=settings.ssh_port,
            protocol="ssh",
            event_type="auth_attempt",
            username=username,
            password=password,
            session_id=self._session_id,
        ))
        return False  # always reject


async def start_ssh_server(host_key_path: str = "/app/ssh_host_key"):
    import os
    if os.path.exists(host_key_path):
        host_key = asyncssh.read_private_key(host_key_path)
    else:
        host_key = asyncssh.generate_private_key("ssh-rsa", comment="medved-honeypot")
        host_key.write_private_key(host_key_path)
        logger.info("Generated new SSH host key")

    await asyncssh.create_server(
        HoneypotSSHServer,
        "",
        settings.ssh_port,
        server_host_keys=[host_key],
        server_version=SSH_BANNER,
        login_timeout=30,
    )
    logger.info("SSH honeypot listening on port %d", settings.ssh_port)
