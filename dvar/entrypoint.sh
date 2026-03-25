#!/bin/bash
set -e

echo "[DVAR] Starting Damn Vulnerable ARM Router..."

# Auto-détection IP si non fournie
if [ -z "$DVAR_IP" ]; then
    DVAR_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo "[DVAR] IP auto-détectée: $DVAR_IP"
fi

# ---- Telnet (port 23) via busybox ARM ----
# busybox telnetd : authentification désactivée (accès direct root)
if [ -x /opt/dvar/busybox ]; then
    qemu-arm-static /opt/dvar/busybox telnetd -l /bin/sh -p 23 -F &
    echo "[DVAR] Telnet ARM (port 23) started"
else
    # Fallback: telnetd natif x86 avec compte root sans mot de passe
    if command -v telnetd >/dev/null 2>&1; then
        passwd -d root 2>/dev/null || true
        telnetd -l /bin/sh &
        echo "[DVAR] Telnet x86 fallback (port 23) started"
    fi
fi

# ---- HTTP vuln (port 80) via ARM binary ----
qemu-arm-static /opt/dvar/httpd &
echo "[DVAR] HTTP ARM (port 80) started"

# ---- FTP simple (port 21) ----
if command -v tcpsvd >/dev/null 2>&1; then
    tcpsvd -vE 0.0.0.0 21 ftpd -w / &
    echo "[DVAR] FTP (port 21) started"
fi

# ---- Enregistrement dans msf DB ----
if [ -n "$MSF_PG_HOST" ] && [ -n "$DVAR_IP" ]; then
    echo "[DVAR] Registering in MSF DB at $MSF_PG_HOST..."
    sleep 5
    PGPASSWORD="${MSF_PG_PASS:-bojemoi}" psql \
        -h "$MSF_PG_HOST" -U "${MSF_PG_USER:-postgres}" -d "${MSF_PG_DB:-msf}" \
        -c "INSERT INTO hosts (address, name, os_name, os_flavor, arch, purpose, comments, scan_status, created_at, updated_at)
            VALUES ('$DVAR_IP'::inet, 'dvar', 'Linux', 'BusyBox', 'armle', 'device',
                    'DVAR - Damn Vulnerable ARM Router (lab target)', 'bm12_v3', now(), now())
            ON CONFLICT (address) DO UPDATE
            SET name='dvar', arch='armle', purpose='device',
                comments='DVAR - Damn Vulnerable ARM Router (lab target)',
                scan_status='bm12_v3', updated_at=now();" 2>/dev/null \
    && echo "[DVAR] Registered in MSF DB" \
    || echo "[DVAR] MSF DB registration skipped (DB not ready)"

    # Enregistrer les services
    PGPASSWORD="${MSF_PG_PASS:-bojemoi}" psql \
        -h "$MSF_PG_HOST" -U "${MSF_PG_USER:-postgres}" -d "${MSF_PG_DB:-msf}" \
        -c "DO \$\$
            DECLARE hid INTEGER;
            BEGIN
                SELECT id INTO hid FROM hosts WHERE host(address::inet) = '$DVAR_IP' LIMIT 1;
                IF hid IS NOT NULL THEN
                    INSERT INTO services (host_id, port, proto, name, state, info, created_at, updated_at)
                    VALUES (hid, 80, 'tcp', 'http', 'open', 'DVAR vuln httpd ARM v1.0', now(), now())
                    ON CONFLICT (host_id, port, proto) DO UPDATE SET state='open', updated_at=now();
                    INSERT INTO services (host_id, port, proto, name, state, info, created_at, updated_at)
                    VALUES (hid, 23, 'tcp', 'telnet', 'open', 'BusyBox telnetd ARM', now(), now())
                    ON CONFLICT (host_id, port, proto) DO UPDATE SET state='open', updated_at=now();
                    INSERT INTO services (host_id, port, proto, name, state, info, created_at, updated_at)
                    VALUES (hid, 21, 'tcp', 'ftp', 'open', 'BusyBox ftpd ARM', now(), now())
                    ON CONFLICT (host_id, port, proto) DO UPDATE SET state='open', updated_at=now();
                END IF;
            END
            \$\$;" 2>/dev/null && echo "[DVAR] Services enregistrés" || true

    # Enregistrer les scan_details pour que uzi le traite comme iot_embedded
    PGPASSWORD="${MSF_PG_PASS:-bojemoi}" psql \
        -h "$MSF_PG_HOST" -U "${MSF_PG_USER:-postgres}" -d "${MSF_PG_DB:-msf}" \
        -c "UPDATE hosts SET scan_details = '{
                \"type\": \"iot_embedded\",
                \"confidence\": 95,
                \"products\": [{\"name\": \"dlink\"}, {\"name\": \"linksys\"}, {\"name\": \"http\"}, {\"name\": \"telnet\"}],
                \"server_type\": \"iot_embedded\",
                \"arch\": \"armle\"
            }'::jsonb
            WHERE host(address::inet) = '$DVAR_IP';" 2>/dev/null && echo "[DVAR] scan_details IoT enregistrés" || true
fi

echo "[DVAR] All services started. Waiting..."
wait
