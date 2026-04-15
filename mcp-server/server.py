#!/usr/bin/env python3
"""
Bojemoi Lab MCP Server
Expose les outils du lab (DB msf, DefectDojo, nmap, OSINT) via le protocole MCP.
Transport : HTTP/SSE sur le port 8001.
"""

import json
import logging
import os
import sys

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from tools import database, defectdojo, nmap, osint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("bojemoi-mcp")

# ---------------------------------------------------------------------------
# Serveur MCP
# ---------------------------------------------------------------------------

server = Server("bojemoi-lab")

TOOLS = [
    types.Tool(
        name="query_hosts",
        description=(
            "Interroge la base Metasploit pour lister des hôtes scannés. "
            "Filtres optionnels : système d'exploitation, statut de scan, plage d'adresse, rôle."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "filter_os": {
                    "type": "string",
                    "description": "Filtre partiel sur le nom de l'OS (ex: 'linux', 'windows', 'cisco')",
                },
                "filter_status": {
                    "type": "string",
                    "description": "Statut de scan exact (ex: 'bm12_v2', 'scanned')",
                },
                "address_range": {
                    "type": "string",
                    "description": "Préfixe d'adresse IP (ex: '185.220.' ou '10.0.')",
                },
                "filter_purpose": {
                    "type": "string",
                    "description": "Rôle de l'hôte (ex: 'server', 'client', 'device')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de résultats (défaut 20, max 200)",
                    "default": 20,
                },
            },
        },
    ),
    types.Tool(
        name="query_services",
        description="Liste les services/ports connus pour une adresse IP donnée.",
        inputSchema={
            "type": "object",
            "properties": {
                "host_address": {
                    "type": "string",
                    "description": "Adresse IP de l'hôte (ex: '185.220.101.45')",
                }
            },
            "required": ["host_address"],
        },
    ),
    types.Tool(
        name="get_host_details",
        description=(
            "Détails complets d'un hôte : OS, classification bm12, services, "
            "scan_details JSON avec scores et preuves de classification."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Adresse IP de l'hôte",
                }
            },
            "required": ["address"],
        },
    ),
    types.Tool(
        name="get_scan_stats",
        description=(
            "Statistiques globales de la base : nombre d'hôtes, hôtes classifiés, "
            "services, top OS, top rôles, top types de serveurs."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="run_nmap",
        description=(
            "Lance un scan nmap sur une cible. "
            "scan_type: basic (sV), full (sV+sC+O), stealth (sS), udp, quick. "
            "La cible doit être une IP, un hostname, ou un CIDR /24 minimum."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "IP, hostname ou CIDR (min /24)",
                },
                "ports": {
                    "type": "string",
                    "description": "Ports à scanner, ex: '80,443,8080' ou '1-1000' (défaut: top 1000)",
                },
                "scan_type": {
                    "type": "string",
                    "enum": ["basic", "full", "stealth", "udp", "quick"],
                    "default": "basic",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout en secondes (défaut 120)",
                    "default": 120,
                },
            },
            "required": ["target"],
        },
    ),
    types.Tool(
        name="lookup_ip",
        description=(
            "OSINT enrichment d'une adresse IP publique : géolocalisation, "
            "détection proxy/VPN/hosting, score de menace (0-100), "
            "signalements abuse, malware OTX, VirusTotal (si clé configurée)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "Adresse IP publique à analyser",
                }
            },
            "required": ["ip"],
        },
    ),
    types.Tool(
        name="list_products",
        description="Liste les products DefectDojo avec leur nombre de findings.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_findings",
        description="Récupère les findings actifs dans DefectDojo. Filtres optionnels: product_id, severity.",
        inputSchema={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "integer",
                    "description": "ID du product DefectDojo (optionnel)",
                },
                "severity": {
                    "type": "string",
                    "enum": ["Critical", "High", "Medium", "Low", "Info"],
                    "description": "Filtrer par sévérité (optionnel)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de findings (défaut 50)",
                    "default": 50,
                },
            },
        },
    ),
    types.Tool(
        name="add_finding",
        description="Ajoute un finding dans DefectDojo. Crée le product/engagement/test si nécessaire.",
        inputSchema={
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Nom du product DefectDojo"},
                "host": {"type": "string", "description": "IP de l'hôte cible"},
                "port": {"type": "integer", "description": "Port concerné"},
                "name": {"type": "string", "description": "Titre du finding"},
                "description": {"type": "string", "description": "Description détaillée"},
                "severity": {
                    "type": "string",
                    "enum": ["Critical", "High", "Medium", "Low", "Info"],
                    "default": "Medium",
                },
            },
            "required": ["product_name", "host", "port", "name", "description"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    log.info("Tool called: %s args=%s", name, arguments)
    try:
        if name == "query_hosts":
            result = database.query_hosts(**arguments)
        elif name == "query_services":
            result = database.query_services(**arguments)
        elif name == "get_host_details":
            result = database.get_host_details(**arguments)
        elif name == "get_scan_stats":
            result = database.get_scan_stats()
        elif name == "run_nmap":
            result = await nmap.run_nmap(**arguments)
        elif name == "lookup_ip":
            result = await osint.lookup_ip(**arguments)
        elif name == "list_products":
            result = await defectdojo.list_products()
        elif name == "get_findings":
            result = await defectdojo.get_findings(**arguments)
        elif name == "add_finding":
            result = await defectdojo.add_finding(**arguments)
        else:
            result = {"error": f"Outil inconnu: {name}"}
    except Exception as e:
        log.exception("Error in tool %s", name)
        result = {"error": str(e), "tool": name}

    return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


# ---------------------------------------------------------------------------
# Starlette app avec SSE transport
# ---------------------------------------------------------------------------

sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options(),
        )


async def handle_messages(request: Request):
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


async def health(request: Request):
    return JSONResponse({"status": "ok", "server": "bojemoi-mcp"})


app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=handle_messages),
        Route("/health", endpoint=health),
    ]
)


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8001"))
    log.info("Bojemoi MCP Server starting on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
