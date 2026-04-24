#!/usr/bin/env python3
"""Supprime les messages en double dans chaque salon — garde le dernier."""
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
            print(f"  [retry {attempt+1}/{retries}] connexion erreur: {e}")
            time.sleep(2 ** attempt)
    return {}

channels = api("GET", f"/guilds/{GUILD_ID}/channels")
text_channels = [c for c in channels if c["type"] == 0]

for ch in text_channels:
    name = ch["name"]
    cid  = ch["id"]
    msgs = api("GET", f"/channels/{cid}/messages", params={"limit": 50})
    if not msgs or len(msgs) <= 1:
        continue

    # Garde le plus récent (index 0), supprime les autres
    to_delete = msgs[1:]  # Discord renvoie du plus récent au plus ancien
    print(f"#{name} — {len(to_delete)} doublon(s) à supprimer")
    for m in to_delete:
        api("DELETE", f"/channels/{cid}/messages/{m['id']}")
        print(f"  supprimé {m['id']}")
        time.sleep(0.5)

print("\n✅ Nettoyage terminé.")
