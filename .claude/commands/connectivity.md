# External Connectivity Check

Test connectivity to all external APIs and feeds used by injector services.

## Arguments

- (none) - Run all connectivity checks
- `apis` - Test only authenticated API endpoints (VirusTotal, Shodan, AbuseIPDB, OTX, Anthropic)
- `feeds` - Test only public feeds (CERT-FR, FireHOL, abuse.ch)
- `telegram` - Test only Telegram Bot API connectivity

## Important: Worker Node Access

Services with secrets (ml-threat-intel, telegram-bot, vigie, etc.) run on **worker nodes**, not the manager.
To read secrets, SSH into the worker node where the container runs.

### Worker Node IPs (from `docker node inspect`):
```bash
# Get current IPs dynamically
for node in meta-68 meta-69 meta-70; do
  IP=$(docker node inspect $node --format '{{.Status.Addr}}' 2>/dev/null)
  echo "$node=$IP"
done
```

### SSH to workers:
```bash
ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=5 docker@<WORKER_IP> "<command>"
```

## Instructions

### Step 1: Read secrets from worker nodes via SSH

Find which worker runs ml-threat-intel and telegram-bot, then read their secrets.

```bash
# Find worker nodes for services with secrets
ML_NODE=$(docker service ps ml-threat_ml-threat-intel-api --format "{{.Node}}" --filter "desired-state=running" | head -1)
TG_NODE=$(docker service ps telegram_telegram-bot --format "{{.Node}}" --filter "desired-state=running" | head -1)

echo "ml-threat-intel runs on: $ML_NODE"
echo "telegram-bot runs on: $TG_NODE"

# Get IPs
ML_IP=$(docker node inspect $ML_NODE --format '{{.Status.Addr}}' 2>/dev/null)
TG_IP=$(docker node inspect $TG_NODE --format '{{.Status.Addr}}' 2>/dev/null)

SSH_OPTS="-p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=5"

# Read API keys from ml-threat-intel container
ssh $SSH_OPTS docker@$ML_IP \
  "ML=\$(docker ps -q -f name=ml-threat_ml-threat-intel-api | head -1) && \
   echo VT=\$(docker exec \$ML cat /run/secrets/vt_api_key 2>/dev/null || echo MISSING) && \
   echo SHODAN=\$(docker exec \$ML cat /run/secrets/shodan_api_key 2>/dev/null || echo MISSING) && \
   echo ABUSE=\$(docker exec \$ML cat /run/secrets/abuseipdb_api_key 2>/dev/null || echo MISSING) && \
   echo OTX=\$(docker exec \$ML cat /run/secrets/otx_api_key 2>/dev/null || echo MISSING) && \
   echo ANTHROPIC=\$(docker exec \$ML cat /run/secrets/anthropic_api_key 2>/dev/null || echo MISSING)" 2>/dev/null > /tmp/_ck_secrets

# Read Telegram token
ssh $SSH_OPTS docker@$TG_IP \
  "TG=\$(docker ps -q -f name=telegram_telegram-bot | head -1) && \
   echo TG_TOKEN=\$(docker exec \$TG cat /run/secrets/telegram_bot_token 2>/dev/null || echo MISSING)" 2>/dev/null >> /tmp/_ck_secrets

cat /tmp/_ck_secrets
```

Parse the secrets from the output file. **Detect placeholder keys** — if a value starts with `your_` or `CHANGE_ME` or is shorter than 10 chars, treat it as NOT CONFIGURED.

### Step 2: Test public feeds (no auth required)

```bash
echo "==============================="
echo "  PUBLIC FEEDS"
echo "==============================="

echo -n "[CERT-FR alerte]  "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://cert.ssi.gouv.fr/alerte/feed/"; echo
echo -n "[CERT-FR avis]    "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://cert.ssi.gouv.fr/avis/feed/"; echo
echo -n "[CERT-FR ioc]     "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://cert.ssi.gouv.fr/ioc/feed/"; echo
echo -n "[FireHOL L1]      "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"; echo
echo -n "[FireHOL L2]      "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level2.netset"; echo
echo -n "[ThreatFox]       "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://threatfox.abuse.ch/export/csv/ip-port/recent/"; echo
echo -n "[URLhaus]         "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://urlhaus.abuse.ch/downloads/text_online/"; echo
echo -n "[Feodo Tracker]   "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.txt"; echo
echo -n "[IP-API]          "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "http://ip-api.com/json/8.8.8.8"; echo
echo -n "[IPInfo]          "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://ipinfo.io/8.8.8.8/json"; echo
echo -n "[IPWhois]         "; curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" --max-time 10 "https://ipwhois.app/json/8.8.8.8"; echo
```

### Step 3: Test authenticated APIs

Use the secrets from Step 1. For each key, first check if it's a placeholder (starts with `your_`, `CHANGE_ME`, or `MISSING`). Then make a lightweight validation call.

```bash
echo ""
echo "==============================="
echo "  AUTHENTICATED APIS"
echo "==============================="

# Helper: check if key is a placeholder
is_placeholder() {
  case "$1" in
    MISSING|your_*|CHANGE_ME*|changeme*|xxx*|TODO*) return 0 ;;
    *) return 1 ;;
  esac
}

echo -n "[VirusTotal]      "
if is_placeholder "$VT_KEY"; then echo "FAIL - placeholder key (not configured)"
else
  VT_HTTP=$(curl -s -o /tmp/vt_check.json -w "%{http_code}" --max-time 10 -H "x-apikey: $VT_KEY" "https://www.virustotal.com/api/v3/users/me")
  if [ "$VT_HTTP" = "200" ]; then echo "OK ($VT_HTTP)"; elif [ "$VT_HTTP" = "401" ]; then echo "FAIL - invalid key ($VT_HTTP)"; else echo "WARN ($VT_HTTP)"; fi
fi

echo -n "[Shodan]          "
if is_placeholder "$SHODAN_KEY"; then echo "FAIL - placeholder key (not configured)"
else
  SHODAN_HTTP=$(curl -s -o /tmp/shodan_check.json -w "%{http_code}" --max-time 10 "https://api.shodan.io/api-info?key=$SHODAN_KEY")
  if [ "$SHODAN_HTTP" = "200" ]; then
    SHODAN_CREDITS=$(python3 -c "import json; d=json.load(open('/tmp/shodan_check.json')); print(f'credits={d.get(\"query_credits\",\"?\")}')" 2>/dev/null)
    echo "OK ($SHODAN_HTTP, $SHODAN_CREDITS)"
  elif [ "$SHODAN_HTTP" = "401" ]; then echo "FAIL - invalid key ($SHODAN_HTTP)"; else echo "WARN ($SHODAN_HTTP)"; fi
fi

echo -n "[AbuseIPDB]       "
if is_placeholder "$ABUSEIPDB_KEY"; then echo "FAIL - placeholder key (not configured)"
else
  ABUSE_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "Key: $ABUSEIPDB_KEY" -H "Accept: application/json" "https://api.abuseipdb.com/api/v2/check?ipAddress=8.8.8.8&maxAgeInDays=1")
  if [ "$ABUSE_HTTP" = "200" ]; then echo "OK ($ABUSE_HTTP)"; elif [ "$ABUSE_HTTP" = "401" ] || [ "$ABUSE_HTTP" = "403" ]; then echo "FAIL - invalid/expired key ($ABUSE_HTTP)"; elif [ "$ABUSE_HTTP" = "429" ]; then echo "WARN - rate limited ($ABUSE_HTTP)"; else echo "WARN ($ABUSE_HTTP)"; fi
fi

echo -n "[AlienVault OTX]  "
if is_placeholder "$OTX_KEY"; then echo "FAIL - placeholder key (not configured)"
else
  OTX_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "X-OTX-API-KEY: $OTX_KEY" "https://otx.alienvault.com/api/v1/user/me")
  if [ "$OTX_HTTP" = "200" ]; then echo "OK ($OTX_HTTP)"; elif [ "$OTX_HTTP" = "403" ]; then echo "FAIL - invalid key ($OTX_HTTP)"; else echo "WARN ($OTX_HTTP)"; fi
fi

echo -n "[Anthropic]       "
if is_placeholder "$ANTHROPIC_KEY"; then echo "FAIL - placeholder key (not configured)"
else
  ANTH_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
    -H "x-api-key: $ANTHROPIC_KEY" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
    -d '{"model":"claude-haiku-4-5-20251001","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}' \
    "https://api.anthropic.com/v1/messages")
  if [ "$ANTH_HTTP" = "200" ]; then echo "OK ($ANTH_HTTP)"; elif [ "$ANTH_HTTP" = "401" ]; then echo "FAIL - invalid key ($ANTH_HTTP)"; elif [ "$ANTH_HTTP" = "429" ]; then echo "WARN - rate limited ($ANTH_HTTP)"; else echo "WARN ($ANTH_HTTP)"; fi
fi
```

### Step 4: Test Telegram Bot

```bash
echo ""
echo "==============================="
echo "  TELEGRAM BOT"
echo "==============================="

echo -n "[Telegram getMe]  "
if is_placeholder "$TG_TOKEN"; then echo "SKIP (no token)"
else
  TG_RESP=$(curl -s --max-time 10 "https://api.telegram.org/bot${TG_TOKEN}/getMe")
  TG_OK=$(echo "$TG_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok',''))" 2>/dev/null)
  if [ "$TG_OK" = "True" ]; then
    TG_NAME=$(echo "$TG_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); print(f'{r.get(\"username\",\"?\")}', end='')" 2>/dev/null)
    echo "OK (bot: @$TG_NAME)"
  else
    echo "FAIL - $TG_RESP"
  fi
fi
```

### Step 5: Test outbound connectivity from worker nodes

SSH into a worker and run DNS + HTTPS test from inside a container.

```bash
echo ""
echo "==============================="
echo "  WORKER NODE EGRESS"
echo "==============================="

# Pick a worker with borodino containers
WORKER_NODE=$(docker service ps borodino_ak47-service --format "{{.Node}}" --filter "desired-state=running" | head -1)
WORKER_IP=$(docker node inspect $WORKER_NODE --format '{{.Status.Addr}}' 2>/dev/null)

if [ -n "$WORKER_IP" ]; then
  ssh $SSH_OPTS docker@$WORKER_IP \
    "W=\$(docker ps -q -f name=borodino_ak47 | head -1); \
     echo -n '[Worker DNS]      '; DNS=\$(docker exec \$W nslookup api.shodan.io 2>&1 | grep -c Address || true); \
     if [ \"\$DNS\" -ge 2 ]; then echo OK; else echo 'FAIL - DNS broken'; fi; \
     echo -n '[Worker HTTPS]    '; WGET=\$(docker exec \$W wget -q -O /dev/null --timeout=10 'https://cert.ssi.gouv.fr/alerte/feed/' 2>&1; echo \$?); \
     if [ \"\$WGET\" = '0' ]; then echo OK; else echo \"FAIL (exit \$WGET)\"; fi" 2>/dev/null
else
  echo "SKIP - cannot reach worker nodes"
fi
```

### Step 6: Present summary

Present a table with all results:
- **OK** = endpoint reachable and auth valid
- **FAIL** = endpoint unreachable or auth rejected (placeholder keys count as FAIL)
- **WARN** = rate limited or unexpected response
- **SKIP** = secret not available or container not running

Group by: Public Feeds, Authenticated APIs, Telegram, Worker Egress.

Highlight any FAIL results and suggest fixes:
- Placeholder keys → need real API keys via `docker secret rm <name> && echo "REAL_KEY" | docker secret create <name> -` then redeploy the service
- Invalid keys → key expired or revoked, get a new one
- Rate limited → wait or upgrade plan
- DNS/HTTPS fail → check worker network config

## Output Format

```
=== Connectivity Report ===

PUBLIC FEEDS (11 endpoints)
  [OK]   CERT-FR alerte, CERT-FR avis, CERT-FR ioc
  [OK]   FireHOL L1, FireHOL L2
  [OK]   ThreatFox, URLhaus, Feodo Tracker
  [OK]   IP-API, IPInfo, IPWhois

AUTHENTICATED APIS (5 endpoints)
  [OK]   VirusTotal
  [OK]   Shodan (credits=100)
  [FAIL] AbuseIPDB - placeholder key
  [OK]   AlienVault OTX
  [OK]   Anthropic

TELEGRAM
  [OK]   @mybotname

WORKER EGRESS
  [OK]   DNS resolution
  [OK]   HTTPS outbound

Summary: 17/18 OK, 1 FAIL
Action needed: Replace AbuseIPDB placeholder with real API key
```
