#!/bin/bash
# orchestrator-zap-nuclei-faraday.sh

set -e

TARGET_URL="${1}"
WORKSPACE="${2:-default}"
FARADAY_URL="${FARADAY_URL:-http://faraday:5985}"
FARADAY_USER="${FARADAY_USER}"
FARADAY_PASS="${FARADAY_PASS}"

if [ -z "$TARGET_URL" ]; then
    echo "Usage: $0 <target_url> [workspace]"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="/tmp/reports_${TIMESTAMP}"
mkdir -p "${REPORT_DIR}"

echo "[+] Starting security scan pipeline for ${TARGET_URL}"
echo "[+] Workspace: ${WORKSPACE}"
echo "[+] Report directory: ${REPORT_DIR}"

# ============================================
# Phase 1: ZAP Scan
# ============================================
echo ""
echo "=========================================="
echo "Phase 1: OWASP ZAP Scan"
echo "=========================================="

ZAP_CONTAINER=$(docker ps --filter "label=com.bojemoi.service=zap" --format "{{.Names}}" | head -n1)

if [ -z "$ZAP_CONTAINER" ]; then
    echo "[-] ZAP container not found!"
    exit 1
fi

echo "[+] Found ZAP container: ${ZAP_CONTAINER}"
echo "[+] Launching ZAP baseline scan..."

docker exec ${ZAP_CONTAINER} zap-baseline.py \
    -t "${TARGET_URL}" \
    -r "zap_report_${TIMESTAMP}.html" \
    -J "zap_report_${TIMESTAMP}.json" \
    -x "zap_report_${TIMESTAMP}.xml" \
    || true

# Copy ZAP reports
docker cp ${ZAP_CONTAINER}:/zap/wrk/zap_report_${TIMESTAMP}.json ${REPORT_DIR}/
docker cp ${ZAP_CONTAINER}:/zap/wrk/zap_report_${TIMESTAMP}.xml ${REPORT_DIR}/
docker cp ${ZAP_CONTAINER}:/zap/wrk/zap_report_${TIMESTAMP}.html ${REPORT_DIR}/

echo "[+] ZAP scan completed"

# ============================================
# Phase 2: Nuclei Scan
# ============================================
echo ""
echo "=========================================="
echo "Phase 2: Nuclei Scan"
echo "=========================================="

NUCLEI_CONTAINER=$(docker ps --filter "label=com.bojemoi.service=nuclei" --format "{{.Names}}" | head -n1)

if [ -z "$NUCLEI_CONTAINER" ]; then
    echo "[-] Nuclei container not found!"
    exit 1
fi

echo "[+] Found Nuclei container: ${NUCLEI_CONTAINER}"
echo "[+] Updating Nuclei templates..."

docker exec ${NUCLEI_CONTAINER} nuclei -update-templates

echo "[+] Launching Nuclei scan..."

# Scan avec différents niveaux de sévérité
docker exec ${NUCLEI_CONTAINER} nuclei \
    -u "${TARGET_URL}" \
    -severity critical,high,medium \
    -json \
    -o "/output/nuclei_report_${TIMESTAMP}.json" \
    -stats \
    -silent

# Scan avec templates spécifiques (optionnel)
docker exec ${NUCLEI_CONTAINER} nuclei \
    -u "${TARGET_URL}" \
    -tags cve,exposure,misconfiguration \
    -json \
    -o "/output/nuclei_cve_${TIMESTAMP}.json" \
    -silent \
    || true

# Copy Nuclei reports
docker cp ${NUCLEI_CONTAINER}:/output/nuclei_report_${TIMESTAMP}.json ${REPORT_DIR}/
docker cp ${NUCLEI_CONTAINER}:/output/nuclei_cve_${TIMESTAMP}.json ${REPORT_DIR}/ || true

echo "[+] Nuclei scan completed"

# ============================================
# Phase 3: Upload to Faraday
# ============================================
echo ""
echo "=========================================="
echo "Phase 3: Upload to Faraday"
echo "=========================================="

# Create workspace if doesn't exist
curl -s -X POST "${FARADAY_URL}/api/v3/ws/${WORKSPACE}" \
    -H "Content-Type: application/json" \
    -u "${FARADAY_USER}:${FARADAY_PASS}" \
    -d '{"name":"'${WORKSPACE}'","description":"Automated scan workspace"}' \
    || echo "[*] Workspace may already exist"

# Upload ZAP report
echo "[+] Uploading ZAP report..."
curl -X POST "${FARADAY_URL}/api/v3/ws/${WORKSPACE}/upload_report" \
    -H "Content-Type: multipart/form-data" \
    -u "${FARADAY_USER}:${FARADAY_PASS}" \
    -F "file=@${REPORT_DIR}/zap_report_${TIMESTAMP}.xml" \
    -w "\nStatus: %{http_code}\n"

# Upload Nuclei report
echo "[+] Uploading Nuclei report..."
curl -X POST "${FARADAY_URL}/api/v3/ws/${WORKSPACE}/upload_report" \
    -H "Content-Type: multipart/form-data" \
    -u "${FARADAY_USER}:${FARADAY_PASS}" \
    -F "file=@${REPORT_DIR}/nuclei_report_${TIMESTAMP}.json" \
    -w "\nStatus: %{http_code}\n"

# Upload Nuclei CVE report if exists
if [ -f "${REPORT_DIR}/nuclei_cve_${TIMESTAMP}.json" ]; then
    echo "[+] Uploading Nuclei CVE report..."
    curl -X POST "${FARADAY_URL}/api/v3/ws/${WORKSPACE}/upload_report" \
        -H "Content-Type: multipart/form-data" \
        -u "${FARADAY_USER}:${FARADAY_PASS}" \
        -F "file=@${REPORT_DIR}/nuclei_cve_${TIMESTAMP}.json" \
        -w "\nStatus: %{http_code}\n"
fi

echo ""
echo "=========================================="
echo "Scan Pipeline Completed!"
echo "=========================================="
echo "Reports saved in: ${REPORT_DIR}"
echo "Faraday workspace: ${WORKSPACE}"
echo "Target: ${TARGET_URL}"
echo ""
echo "Summary:"
ls -lh ${REPORT_DIR}

