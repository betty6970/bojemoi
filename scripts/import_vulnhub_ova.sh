#!/bin/bash
# import_vulnhub_ova.sh — Import an OVA/OVF as a XenServer template
#
# Usage (on the XenServer host):
#   bash import_vulnhub_ova.sh <ova_file> <template_name> [sr_name]
#
# Example:
#   bash import_vulnhub_ova.sh Metasploitable2-Linux.vmdk.zip metasploitable2
#   bash import_vulnhub_ova.sh dvwa.ova dvwa "Local storage"
#
# After import the template can be cloned via the orchestrator:
#   POST /api/v1/vm/vulnhub/<template_name>
#
# Supported formats: .ova, .ovf (xe vm-import), .vmdk / .vmx (xe vm-import with extras)
# For compressed archives (.zip, .tar.gz) extract first.
#
# Requires: xe CLI (XenServer/XCP-ng), running as root or user with xe access.

set -euo pipefail

OVA_FILE="${1:-}"
TEMPLATE_NAME="${2:-}"
SR_NAME="${3:-}"

usage() {
    echo "Usage: $0 <ova_file> <template_name> [sr_name]"
    echo ""
    echo "VulnHub catalog template names:"
    echo "  metasploitable2         — Metasploitable 2 (Ubuntu 8.04, classic)"
    echo "  metasploitable3-ubuntu  — Metasploitable 3 (Ubuntu 14.04, modern)"
    echo "  dvwa                    — DVWA (PHP/MySQL, OWASP Top 10)"
    echo "  dc-1                    — DC: 1 (Drupal 7, Drupalgeddon)"
    echo "  kioptrix-1              — Kioptrix Level 1 (Apache mod_ssl)"
    echo "  basic-pentesting-1      — Basic Pentesting 1 (WordPress, FTP)"
    echo "  lampiao                 — Lampião (Drupal 7 + Dirty COW)"
    echo "  pwnlab-init             — PwnLab: init (LFI → RCE)"
    exit 1
}

[[ -z "$OVA_FILE" || -z "$TEMPLATE_NAME" ]] && usage

if [[ ! -f "$OVA_FILE" ]]; then
    echo "ERROR: File not found: $OVA_FILE"
    exit 1
fi

command -v xe &>/dev/null || { echo "ERROR: xe CLI not found. Run this on the XenServer host."; exit 1; }

# --- Resolve SR UUID ---
if [[ -n "$SR_NAME" ]]; then
    SR_UUID=$(xe sr-list name-label="$SR_NAME" --minimal 2>/dev/null | head -1)
    if [[ -z "$SR_UUID" ]]; then
        echo "ERROR: SR '$SR_NAME' not found."
        echo "Available SRs:"
        xe sr-list --minimal 2>/dev/null | tr ',' '\n' | while read u; do
            [[ -n "$u" ]] && xe sr-param-get uuid="$u" param-name=name-label 2>/dev/null && echo "  ($u)"
        done
        exit 1
    fi
    SR_ARG="sr-uuid=$SR_UUID"
    echo "Using SR: $SR_NAME ($SR_UUID)"
else
    # Find default SR (first local SR)
    SR_UUID=$(xe sr-list type=lvm --minimal 2>/dev/null | cut -d',' -f1)
    [[ -z "$SR_UUID" ]] && SR_UUID=$(xe sr-list type=ext --minimal 2>/dev/null | cut -d',' -f1)
    [[ -z "$SR_UUID" ]] && { echo "WARNING: No default SR found, letting xe pick."; SR_ARG=""; } || SR_ARG="sr-uuid=$SR_UUID"
    [[ -n "$SR_UUID" ]] && echo "Using SR: $SR_UUID (auto-detected)"
fi

# --- Check for existing template ---
EXISTING=$(xe template-list name-label="$TEMPLATE_NAME" --minimal 2>/dev/null)
if [[ -n "$EXISTING" ]]; then
    echo "WARNING: Template '$TEMPLATE_NAME' already exists (UUID: $EXISTING)"
    read -rp "Overwrite? [y/N] " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo "Deleting existing template..."
        xe template-uninstall template-uuid="$EXISTING" force=true
    else
        echo "Aborted."
        exit 0
    fi
fi

# --- Import ---
echo ""
echo "Importing: $OVA_FILE"
echo "Template name: $TEMPLATE_NAME"
echo ""

VM_UUID=$(xe vm-import \
    filename="$OVA_FILE" \
    ${SR_ARG} \
    preserve=false 2>&1 | grep -E '^[0-9a-f-]{36}$' | tail -1 || true)

# Fallback: xe vm-import prints UUID on last line
if [[ -z "$VM_UUID" ]]; then
    VM_UUID=$(xe vm-import filename="$OVA_FILE" ${SR_ARG} preserve=false 2>/dev/null)
fi

if [[ -z "$VM_UUID" ]]; then
    echo "ERROR: Import failed or UUID not captured."
    echo "Try running manually: xe vm-import filename=$OVA_FILE ${SR_ARG}"
    exit 1
fi

echo "Imported VM UUID: $VM_UUID"

# --- Rename + mark as template ---
echo "Renaming to '$TEMPLATE_NAME' and converting to template..."
xe vm-param-set uuid="$VM_UUID" name-label="$TEMPLATE_NAME"
xe vm-param-set uuid="$VM_UUID" is-a-template=true
xe vm-param-set uuid="$VM_UUID" name-description="VulnHub target — $TEMPLATE_NAME. Imported $(date -u +%Y-%m-%dT%H:%M:%SZ). Do not start directly — use orchestrator POST /api/v1/vm/vulnhub/$TEMPLATE_NAME"

echo ""
echo "Done! Template '$TEMPLATE_NAME' created (UUID: $VM_UUID)"
echo ""
echo "Verify with:"
echo "  xe template-list name-label=$TEMPLATE_NAME"
echo ""
echo "Deploy via orchestrator:"
echo "  curl -X POST http://<orchestrator>:28080/api/v1/vm/vulnhub/$TEMPLATE_NAME \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"network\": \"lab-internal\"}'"
