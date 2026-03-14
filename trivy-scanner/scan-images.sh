#!/bin/bash
set -euo pipefail

IMAGES=(
    bojemoi-mcp
    borodino
    dozor
    karacho
    koursk
    koursk-1
    koursk-2
    medved
    ml-threat-intel
    ml-threat
    oblast
    oblast-1
    pentest-orchestrator
    provisioning
    razvedka
    samsonov
    suricata-attack-enricher
    suricata_exporter
    telegram-bot
    tsushima
    vigie
)

REGISTRY="bettybombers696"
REPORT_DIR="/reports/$(date +%Y-%m-%d)"
mkdir -p "$REPORT_DIR"

TOTAL=${#IMAGES[@]}
CRITICAL_IMAGES=()
CLEAN_IMAGES=()
FAILED_IMAGES=()

echo "======================================================================"
echo "  Trivy Image Scan — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "  Scanning $TOTAL images from $REGISTRY"
echo "======================================================================"

for image in "${IMAGES[@]}"; do
    REF="$REGISTRY/$image:latest"
    OUT="$REPORT_DIR/$image.txt"
    echo ""
    echo "--- [$image] ---"

    if trivy image \
        --image-src remote \
        --severity HIGH,CRITICAL \
        --no-progress \
        --format table \
        --output "$OUT" \
        "$REF" 2>&1; then

        if grep -qE "HIGH|CRITICAL" "$OUT" 2>/dev/null; then
            CRITICAL_IMAGES+=("$image")
            echo "FINDINGS — HIGH/CRITICAL detected"
            cat "$OUT"
        else
            CLEAN_IMAGES+=("$image")
            echo "OK — no HIGH/CRITICAL"
        fi
    else
        FAILED_IMAGES+=("$image")
        echo "ERROR — trivy failed for $image (image not found or pull error?)"
    fi
done

echo ""
echo "======================================================================"
echo "  Summary — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "======================================================================"
echo "  Clean     : ${#CLEAN_IMAGES[@]}/$TOTAL"
echo "  With CVEs : ${#CRITICAL_IMAGES[@]}/$TOTAL  ${CRITICAL_IMAGES[*]:-}"
echo "  Failed    : ${#FAILED_IMAGES[@]}/$TOTAL  ${FAILED_IMAGES[*]:-}"
echo "  Reports   : $REPORT_DIR/"
echo "======================================================================"
