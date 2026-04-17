#!/usr/bin/env python3
"""
PTaaS Init Service — 02-init-ptaas
-----------------------------------
One-shot container. Runs once at first deployment.

Flow:
  1. Wait for postgres
  2. Already initialized? → exit 0
  3. Read ptaas_telegram_key + ptaas_local_key (Docker secrets)
  4. Compute serial = "PTaaS-" + HMAC(local_key, telegram_key)[:8].upper()
  5. Create DefectDojo product
  6. Set Docker node label ptaas.serial=<serial>
  7. Register on blockchain (stub)
  8. Persist in postgres ptaas_identity table
"""

import hashlib
import hmac
import os
import sys
import time

import docker
import psycopg2
import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_secret(name: str) -> str:
    path = f"/run/secrets/{name}"
    if not os.path.exists(path):
        raise RuntimeError(f"Docker secret '{name}' not found at {path}")
    with open(path) as f:
        return f.read().strip()


def wait_for_postgres(dsn: str, retries: int = 30, delay: int = 5) -> None:
    for i in range(retries):
        try:
            conn = psycopg2.connect(dsn)
            conn.close()
            print("[postgres] ready")
            return
        except Exception as e:
            print(f"[postgres] waiting ({i+1}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("Postgres not available after retries")


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ptaas_identity (
                serial              VARCHAR(20)  PRIMARY KEY,
                telegram_key_hash   TEXT         NOT NULL,
                local_key_ref       TEXT         NOT NULL,
                dojo_product_id     INTEGER,
                blockchain_tx       TEXT,
                cidr                TEXT,
                created_at          TIMESTAMP    DEFAULT NOW()
            )
        """)
    conn.commit()


def is_initialized(conn) -> tuple:
    """Returns (bool, serial|None)"""
    with conn.cursor() as cur:
        cur.execute("SELECT serial FROM ptaas_identity LIMIT 1")
        row = cur.fetchone()
        return (True, row[0]) if row else (False, None)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_serial(telegram_key: str, local_key: str) -> str:
    digest = hmac.new(
        local_key.encode(),
        telegram_key.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"PTaaS-{digest[:8].upper()}"


def create_dojo_product(serial: str, dojo_url: str, dojo_token: str) -> int:
    headers = {
        "Authorization": f"Token {dojo_token}",
        "Content-Type": "application/json",
    }

    # Get or create "PTaaS" product type
    r = requests.get(
        f"{dojo_url}/api/v2/product_types/",
        headers=headers,
        params={"name": "PTaaS"},
        timeout=15,
    )
    r.raise_for_status()
    results = r.json()["results"]
    if results:
        product_type_id = results[0]["id"]
    else:
        r = requests.post(
            f"{dojo_url}/api/v2/product_types/",
            headers=headers,
            json={"name": "PTaaS"},
            timeout=15,
        )
        r.raise_for_status()
        product_type_id = r.json()["id"]

    print(f"[dojo] product_type_id={product_type_id}")

    # Create product
    r = requests.post(
        f"{dojo_url}/api/v2/products/",
        headers=headers,
        json={
            "name": serial,
            "description": f"PTaaS node {serial} — auto-registered",
            "prod_type": product_type_id,
        },
        timeout=15,
    )
    r.raise_for_status()
    product_id = r.json()["id"]
    print(f"[dojo] product created: id={product_id} name={serial}")
    return product_id


def set_node_label(serial: str) -> None:
    client = docker.from_env()
    managers = client.nodes.list(filters={"role": "manager"})
    if not managers:
        raise RuntimeError("No manager node found via Docker API")
    node = managers[0]
    spec = node.attrs["Spec"]
    spec.setdefault("Labels", {})["ptaas.serial"] = serial
    node.update(spec)
    print(f"[docker] label ptaas.serial={serial} set on node {node.id[:12]}")


def create_docker_config(serial: str) -> None:
    """Create (or replace) Docker config 'ptaas_serial' with the serial value."""
    client = docker.from_env()
    # Remove existing config if any (configs are immutable)
    for cfg in client.configs.list(filters={"name": "ptaas_serial"}):
        try:
            cfg.remove()
            print(f"[docker] removed old config ptaas_serial")
        except Exception:
            pass
    client.configs.create("ptaas_serial", serial.encode())
    print(f"[docker] config ptaas_serial={serial} created")


def blockchain_register(serial: str, cidr: str = None) -> str:
    """Stub — à remplacer par l'intégration blockchain réelle."""
    print(f"[blockchain] STUB — registering serial={serial} cidr={cidr}")
    fake_tx = hashlib.sha256(serial.encode()).hexdigest()
    print(f"[blockchain] tx={fake_tx[:16]}...")
    return fake_tx


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_db   = os.getenv("POSTGRES_DB",   "ptaas")
    postgres_user = os.getenv("POSTGRES_USER",  "postgres")
    dojo_url      = os.getenv("DEFECTDOJO_URL", "http://defectdojo-nginx:8080")

    postgres_password = read_secret("postgres_password")
    telegram_key      = read_secret("ptaas_telegram_key")
    local_key         = read_secret("ptaas_local_key")
    dojo_token        = read_secret("dojo_api_token")

    dsn = (
        f"postgresql://{postgres_user}:{postgres_password}"
        f"@{postgres_host}/{postgres_db}"
    )

    # 1. Wait for postgres
    wait_for_postgres(dsn)
    conn = psycopg2.connect(dsn)

    # 2. Ensure table exists, check idempotency
    ensure_table(conn)
    initialized, existing_serial = is_initialized(conn)
    if initialized:
        print(f"[init] Already registered as {existing_serial} — nothing to do")
        conn.close()
        sys.exit(0)

    # 3. Compute serial
    serial = compute_serial(telegram_key, local_key)
    print(f"[init] Serial: {serial}")

    # 4. Create DefectDojo product
    print(f"[init] Creating DefectDojo product...")
    dojo_product_id = create_dojo_product(serial, dojo_url, dojo_token)

    # 5. Set Docker node label + config
    print(f"[init] Setting node label and Docker config...")
    set_node_label(serial)
    create_docker_config(serial)

    # 6. Blockchain registration (stub)
    print(f"[init] Blockchain registration...")
    blockchain_tx = blockchain_register(serial)

    # 7. Persist
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO ptaas_identity
                (serial, telegram_key_hash, local_key_ref, dojo_product_id, blockchain_tx)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            serial,
            hashlib.sha256(telegram_key.encode()).hexdigest(),
            "docker_secret:ptaas_local_key",
            dojo_product_id,
            blockchain_tx,
        ))
    conn.commit()
    conn.close()

    print(f"[init] ✓ PTaaS node registered: {serial}")
    sys.exit(0)


if __name__ == "__main__":
    main()
