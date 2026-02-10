import logging
import time
import uuid

from aiohttp import web

from ..config import settings
from ..db import log_event
from ..metrics import connections_total, auth_attempts_total, events_total, connection_duration

logger = logging.getLogger("medved.http")

LOGIN_PAGE = """<!DOCTYPE html>
<html><head><title>Admin Panel - Login</title>
<style>
body{font-family:Arial;background:#1a1a2e;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.login{background:#16213e;padding:40px;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,.3);width:350px}
h2{color:#e94560;text-align:center;margin-bottom:30px}
input{width:100%;padding:12px;margin:8px 0;border:1px solid #0f3460;border-radius:4px;background:#1a1a2e;color:#eee;box-sizing:border-box}
button{width:100%;padding:12px;background:#e94560;border:none;border-radius:4px;color:#fff;cursor:pointer;font-size:16px;margin-top:15px}
.msg{color:#e94560;text-align:center;font-size:14px;margin-top:10px}
</style></head>
<body><div class="login"><h2>Admin Panel</h2>
<form method="POST" action="/login">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button type="submit">Sign In</button>
<div class="msg" id="msg"></div>
</form></div></body></html>"""

LOGIN_FAIL = LOGIN_PAGE.replace(
    '<div class="msg" id="msg"></div>',
    '<div class="msg">Invalid credentials. This attempt has been logged.</div>',
)


async def handle_index(request: web.Request) -> web.Response:
    ip = request.remote
    session_id = str(uuid.uuid4())[:12]
    connections_total.labels(protocol="http").inc()
    events_total.labels(protocol="http", event_type="connection").inc()
    ua = request.headers.get("User-Agent", "")
    logger.info("HTTP GET / from %s (UA: %s)", ip, ua)
    await log_event(
        source_ip=ip,
        source_port=0,
        dest_port=settings.http_port,
        protocol="http",
        event_type="connection",
        user_agent=ua,
        session_id=session_id,
        raw_data={"method": "GET", "path": "/", "headers": dict(request.headers)},
    )
    return web.Response(text=LOGIN_PAGE, content_type="text/html")


async def handle_login(request: web.Request) -> web.Response:
    ip = request.remote
    session_id = str(uuid.uuid4())[:12]
    ua = request.headers.get("User-Agent", "")
    try:
        data = await request.post()
        username = data.get("username", "")
        password = data.get("password", "")
    except Exception:
        username = password = ""

    auth_attempts_total.labels(protocol="http").inc()
    events_total.labels(protocol="http", event_type="auth_attempt").inc()
    logger.info("HTTP login: %s:%s from %s", username, password, ip)
    await log_event(
        source_ip=ip,
        source_port=0,
        dest_port=settings.http_port,
        protocol="http",
        event_type="auth_attempt",
        username=username,
        password=password,
        user_agent=ua,
        session_id=session_id,
        raw_data={"method": "POST", "path": "/login"},
    )
    return web.Response(text=LOGIN_FAIL, content_type="text/html")


async def handle_any(request: web.Request) -> web.Response:
    ip = request.remote
    ua = request.headers.get("User-Agent", "")
    events_total.labels(protocol="http", event_type="probe").inc()
    await log_event(
        source_ip=ip,
        source_port=0,
        dest_port=settings.http_port,
        protocol="http",
        event_type="probe",
        user_agent=ua,
        payload=f"{request.method} {request.path}",
        raw_data={"method": request.method, "path": request.path, "headers": dict(request.headers)},
    )
    return web.Response(status=404, text="Not Found")


def create_http_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/admin", handle_index)
    app.router.add_get("/login", handle_index)
    app.router.add_post("/login", handle_login)
    app.router.add_route("*", "/{path:.*}", handle_any)
    return app


async def start_http_server():
    app = create_http_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.http_port)
    await site.start()
    logger.info("HTTP honeypot listening on port %d", settings.http_port)
