#!/usr/bin/env python3
"""Poste ARCHITECTURE.md dans #architecture en plusieurs messages Discord."""
import os, time, requests
from pathlib import Path

TOKEN    = Path("/run/secrets/discord_bot_token").read_text().strip()
GUILD_ID = os.environ["GUILD_ID"]
BASE     = "https://discord.com/api/v10"
HDR      = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

def api(method, path, retries=3, **kw):
    for attempt in range(retries):
        try:
            r = requests.request(method, f"{BASE}{path}", headers=HDR, timeout=15, **kw)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1)
                print(f"  [rate-limit] {wait}s...")
                time.sleep(wait + 0.2)
                continue
            if r.status_code == 204:
                return {}
            r.raise_for_status()
            return r.json() if r.content else {}
        except requests.exceptions.ConnectionError as e:
            print(f"  [retry {attempt+1}/{retries}] {e}")
            time.sleep(2 ** attempt)
    return {}

def post(channel_id, content):
    api("POST", f"/channels/{channel_id}/messages", json={"content": content})
    time.sleep(0.8)

def delete_all(channel_id):
    """Supprime tous les messages existants du salon."""
    while True:
        msgs = api("GET", f"/channels/{channel_id}/messages", params={"limit": 100})
        if not msgs:
            break
        for m in msgs:
            api("DELETE", f"/channels/{channel_id}/messages/{m['id']}")
            time.sleep(0.4)
        if len(msgs) < 100:
            break

# Trouve le channel #architecture
channels = api("GET", f"/guilds/{GUILD_ID}/channels")
ch = {c["name"]: c["id"] for c in channels if c["type"] == 0}
arch_id = ch.get("architecture")
if not arch_id:
    print("Channel #architecture introuvable")
    exit(1)

print("Nettoyage des messages existants...")
delete_all(arch_id)

# Découpe le texte en blocs ≤ 1900 chars en respectant les lignes
def split_blocks(text, maxlen=1900):
    blocks, current = [], []
    length = 0
    for line in text.splitlines(keepends=True):
        if length + len(line) > maxlen and current:
            blocks.append("".join(current))
            current, length = [], 0
        current.append(line)
        length += len(line)
    if current:
        blocks.append("".join(current))
    return blocks

content = Path("/app/ARCHITECTURE.md").read_text()

# Sépare par sections (## )
import re
sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)

print(f"Envoi de {len(sections)} sections...")
for section in sections:
    section = section.strip()
    if not section:
        continue
    for block in split_blocks(section):
        block = block.strip()
        if not block:
            continue
        print(f"  → {block[:60].strip()!r}...")
        post(arch_id, block)

print("\n✅ Done.")
