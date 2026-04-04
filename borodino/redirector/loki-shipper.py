#!/usr/bin/env python3
"""
Tails nginx access.log and ships lines to Loki in batches via VPN.

Env vars:
  LOKI_URL        — Loki push endpoint (default: http://192.168.1.121:3100/loki/api/v1/push)
  REDIRECTOR_NAME — 'app' label value   (default: redirector-unknown)
  FLY_REGION      — 'region' label value (set automatically by Fly.io)
  LOG_FILE        — file to tail        (default: /var/log/nginx/access.log)
  BATCH_DELAY     — seconds between flushes (default: 5)
"""
import json
import os
import sys
import time
import urllib.request

LOKI_URL = os.getenv("LOKI_URL", "http://192.168.1.121:3100/loki/api/v1/push")
APP      = os.getenv("REDIRECTOR_NAME", "redirector-unknown")
REGION   = os.getenv("FLY_REGION", "unknown")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/nginx/access.log")
DELAY    = float(os.getenv("BATCH_DELAY", "5"))

LABELS = {"job": "nginx-redirector", "app": APP, "region": REGION}


def push(lines):
    if not lines:
        return
    payload = json.dumps({
        "streams": [{"stream": LABELS, "values": lines}]
    }).encode()
    try:
        req = urllib.request.Request(
            LOKI_URL, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as e:
        print(f"[loki-shipper] push failed: {e}", file=sys.stderr)


def tail_file(path):
    while not os.path.exists(path):
        time.sleep(1)
    with open(path) as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if line:
                yield line.rstrip('\n')
            else:
                time.sleep(0.1)


def main():
    print(f"[loki-shipper] {LOG_FILE} → {LOKI_URL}  app={APP} region={REGION}",
          flush=True)
    batch = []
    last_flush = time.time()

    for line in tail_file(LOG_FILE):
        batch.append((str(int(time.time() * 1e9)), line))
        if time.time() - last_flush >= DELAY or len(batch) >= 100:
            push(batch)
            batch = []
            last_flush = time.time()


if __name__ == "__main__":
    main()
