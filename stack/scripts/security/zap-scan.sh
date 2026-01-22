#!/bin/bash
set -euo pipefail

TARGET_URL="https://${STACK_NAME}-staging.bojemoi.lab.local"

echo "🔍 Scan OWASP ZAP de ${TARGET_URL}"

docker run --rm \
    --network gitlab-backend \
    -v $(pwd):/zap/wrk:rw \
    owasp/zap2docker-stable \
    zap-baseline.py \
    -t ${TARGET_URL} \
    -r zap-report.html \
    -x zap-report.xml \
    -J zap-report.json

echo "✅ Scan terminé"

