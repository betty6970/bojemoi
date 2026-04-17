#!/usr/bin/env python3
"""
Import RIPE NCC delegated stats for Russia into ip2location DB.
Injects missing CIDRs directly into ip2location_db1 (IPv4) and
ip2location_db1_v6 (IPv6) — no changes to ak47 needed.

Usage:
    PG_HOST=postgres PG_PASSWORD=secret python3 import_ripe_cidrs.py
"""

import ipaddress
import os
import sys
import urllib.request

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("[ERROR] psycopg2 not found. Install with: pip install psycopg2-binary")
    sys.exit(1)

RIPE_URL = "https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest"

PG_HOST     = os.environ.get("PG_HOST", "localhost")
PG_PORT     = int(os.environ.get("PG_PORT", "5432"))
PG_USER     = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", ""))
IP2LOC_DB   = os.environ.get("IP2LOC_DBNAME", "ip2location")

if not PG_PASSWORD and os.path.exists("/run/secrets/postgres_password"):
    with open("/run/secrets/postgres_password") as f:
        PG_PASSWORD = f.read().strip()



def fetch_ripe_cidrs(local_file: str = None) -> tuple[list, list]:
    ipv4, ipv6 = [], []
    if local_file and os.path.exists(local_file):
        print(f"[INFO] Using local file {local_file} ...")
        fh = open(local_file, "rb")
    else:
        print(f"[INFO] Downloading {RIPE_URL} ...")
        req = urllib.request.Request(RIPE_URL, headers={"User-Agent": "Mozilla/5.0"})
        fh = urllib.request.urlopen(req, timeout=60)
    with fh as f:
        for raw in f:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) < 6 or parts[1] != "RU":
                continue
            try:
                if parts[2] == "ipv4":
                    start = ipaddress.IPv4Address(parts[3])
                    end = ipaddress.IPv4Address(int(start) + int(parts[4]) - 1)
                    for net in ipaddress.summarize_address_range(start, end):
                        ipv4.append(str(net))
                elif parts[2] == "ipv6":
                    ipv6.append(f"{parts[3]}/{parts[4]}")
            except (ValueError, ZeroDivisionError):
                continue

    print(f"[INFO] Found {len(ipv4)} IPv4 CIDRs, {len(ipv6)} IPv6 CIDRs")
    return ipv4, ipv6


def import_to_db(ipv4: list, ipv6: list) -> None:
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER,
        password=PG_PASSWORD, dbname=IP2LOC_DB
    )
    cur = conn.cursor()

    if ipv4:
        rows = []
        for c in ipv4:
            net = ipaddress.IPv4Network(c, strict=False)
            rows.append((int(net.network_address), int(net.broadcast_address), c, "RU", "Russian Federation", "0"))
        execute_values(
            cur,
            """INSERT INTO ip2location_db1 (ip_from, ip_to, cidr_z, country_code, country_name, nmap)
               VALUES %s ON CONFLICT DO NOTHING""",
            rows,
            page_size=500,
        )
        cur.execute("SELECT COUNT(*) FROM ip2location_db1 WHERE country_code = 'RU'")
        total = cur.fetchone()[0]
        print(f"[INFO] ip2location_db1 RU total: {total} CIDRs")

    if ipv6:
        execute_values(
            cur,
            """INSERT INTO ip2location_db1_v6 (cidr_z, country_code, country_name, nmap)
               VALUES %s ON CONFLICT DO NOTHING""",
            [(c, "RU", "Russian Federation", "0") for c in ipv6],
            page_size=500,
        )
        cur.execute("SELECT COUNT(*) FROM ip2location_db1_v6 WHERE country_code = 'RU'")
        total = cur.fetchone()[0]
        print(f"[INFO] ip2location_db1_v6 RU total: {total} CIDRs")

    conn.commit()
    cur.close()
    conn.close()
    print("[INFO] Import done.")


if __name__ == "__main__":
    local = sys.argv[1] if len(sys.argv) > 1 else None
    ipv4, ipv6 = fetch_ripe_cidrs(local)
    import_to_db(ipv4, ipv6)
