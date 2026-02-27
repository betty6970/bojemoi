"""
database.py — Requêtes vers la base Metasploit (PostgreSQL).
"""

import json
import os
import psycopg2
import psycopg2.extras

def _secret(name: str, env_var: str, default: str = "") -> str:
    path = f"/run/secrets/{name}"
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.getenv(env_var, default)


DB_CONFIG = {
    "dbname": os.getenv("PG_DATABASE", "msf"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": _secret("mcp_pg_password", "PG_PASSWORD"),
    "host": os.getenv("PG_HOST", "postgres"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "connect_timeout": 10,
}


def _connect():
    return psycopg2.connect(**DB_CONFIG)


def query_hosts(
    filter_os: str = None,
    filter_status: str = None,
    address_range: str = None,
    filter_purpose: str = None,
    limit: int = 20,
) -> list[dict]:
    """
    Interroge les hôtes msf avec filtres optionnels.
    filter_status: 'bm12_v2' | 'scanned' | etc.
    filter_purpose: 'server' | 'client' | 'device' | etc.
    address_range: ex. '192.168.1.' (LIKE prefix)
    """
    limit = min(limit, 200)
    conditions = ["host(address::inet) NOT LIKE 'fe80:%%'"]
    params = []

    if filter_os:
        conditions.append("LOWER(os_name) LIKE LOWER(%s)")
        params.append(f"%{filter_os}%")
    if filter_status:
        conditions.append("scan_status = %s")
        params.append(filter_status)
    if filter_purpose:
        conditions.append("purpose = %s")
        params.append(filter_purpose)
    if address_range:
        conditions.append("host(address::inet) LIKE %s")
        params.append(f"{address_range}%")

    where = " AND ".join(conditions)
    params.append(limit)

    sql = f"""
        SELECT
            host(address::inet) AS address,
            os_name,
            os_flavor,
            purpose,
            state,
            comments,
            scan_status,
            last_scanned::text
        FROM hosts
        WHERE {where}
        ORDER BY last_scanned DESC NULLS LAST
        LIMIT %s
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def query_services(host_address: str) -> list[dict]:
    """Services connus pour un hôte (par adresse IP)."""
    sql = """
        SELECT s.port, s.proto, s.name, s.state, s.info
        FROM services s
        JOIN hosts h ON h.id = s.host_id
        WHERE host(h.address::inet) = %s
        ORDER BY s.port
        LIMIT 500
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (host_address,))
            return [dict(r) for r in cur.fetchall()]


def get_host_details(address: str) -> dict:
    """Détails complets d'un hôte : infos + services + scan_details JSON."""
    sql = """
        SELECT
            host(h.address::inet) AS address,
            h.os_name, h.os_flavor, h.os_sp, h.arch,
            h.purpose, h.state, h.comments,
            h.scan_status, h.scan_details,
            h.last_scanned::text,
            h.created_at::text
        FROM hosts h
        WHERE host(h.address::inet) = %s
        LIMIT 1
    """
    with _connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (address,))
            row = cur.fetchone()
            if not row:
                return {}
            result = dict(row)
            # Parse scan_details JSON si c'est une string
            if isinstance(result.get("scan_details"), str):
                try:
                    result["scan_details"] = json.loads(result["scan_details"])
                except Exception:
                    pass
            # Services
            result["services"] = query_services(address)
            return result


def get_scan_stats() -> dict:
    """Statistiques globales sur la base msf."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM hosts WHERE host(address::inet) NOT LIKE 'fe80:%%'")
            total_hosts = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM hosts WHERE scan_status = 'bm12_v2'")
            classified = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM services")
            total_services = cur.fetchone()[0]

            cur.execute("""
                SELECT os_name, COUNT(*) AS cnt
                FROM hosts
                WHERE os_name IS NOT NULL AND os_name != ''
                GROUP BY os_name ORDER BY cnt DESC LIMIT 10
            """)
            top_os = [{"os": r[0], "count": r[1]} for r in cur.fetchall()]

            cur.execute("""
                SELECT purpose, COUNT(*) AS cnt
                FROM hosts
                WHERE purpose IS NOT NULL AND purpose != ''
                GROUP BY purpose ORDER BY cnt DESC
            """)
            top_purposes = [{"purpose": r[0], "count": r[1]} for r in cur.fetchall()]

            cur.execute("""
                SELECT comments, COUNT(*) AS cnt
                FROM hosts
                WHERE scan_status = 'bm12_v2'
                  AND comments LIKE 'bm12: %'
                GROUP BY comments ORDER BY cnt DESC LIMIT 10
            """)
            top_types = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]

    return {
        "total_hosts": total_hosts,
        "classified_hosts": classified,
        "total_services": total_services,
        "top_os": top_os,
        "top_purposes": top_purposes,
        "top_server_types": top_types,
    }
