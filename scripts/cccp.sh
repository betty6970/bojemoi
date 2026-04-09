#!/bin/sh
# cccp.sh — Build & push custom images vers la registry locale
# Balaie les stacks, identifie les images custom, build les manquantes
#
# Usage:
#   cccp.sh                  — build toutes les images custom manquantes
#   cccp.sh <image>          — build une image spécifique
#   cccp.sh --force          — rebuild tout même si déjà présent
#   cccp.sh --list           — lister les mappings connus
#   cccp.sh --missing        — lister les images manquantes sans builder

set -e

REGISTRY="${REGISTRY:-localhost:5000}"
BOJEMOI_ROOT="${BOJEMOI_ROOT:-/opt/bojemoi}"
STACK_DIRS="${STACK_DIRS:-$BOJEMOI_ROOT/stack /opt/bojemoi_boot/stack}"

# ─── Mapping image → dockerfile|contexte ─────────────────────────────────────
# Retourne "DOCKERFILE|CONTEXT_DIR" (chemins relatifs à BOJEMOI_ROOT)
# ou "EXTERNAL|<root>|<dockerfile>|<context>" pour les repos hors bojemoi
# Retourne "" si image inconnue (officielle ou non gérée)
get_build_info() {
    local image="$1"
    local base="${image%%:*}"   # strip tag

    case "$base" in
        # ── Borodino / C2 ────────────────────────────────────────────────────
        borodino)
            echo "borodino/Dockerfile.borodino|borodino" ;;
        borodino-msf)
            echo "borodino/Dockerfile.borodino-msf|borodino" ;;
        wg-gateway)
            echo "borodino/Dockerfile.wg-gateway|borodino" ;;

        # ── ZAP / Scanners web ───────────────────────────────────────────────
        oblast)
            echo "oblast/Dockerfile.oblast|oblast" ;;
        oblast-1)
            echo "oblast-1/Dockerfile.oblast-1|oblast-1" ;;

        # ── Nuclei / Samsonov ────────────────────────────────────────────────
        nuclei)
            echo "samsonov/Dockerfile.nuclei|samsonov" ;;
        nuclei-api)
            echo "samsonov/nuclei_api/Dockerfile|samsonov/nuclei_api" ;;
        pentest-orchestrator)
            echo "samsonov/pentest_orchestrator/Dockerfile|samsonov/pentest_orchestrator" ;;

        # ── Services de surveillance ─────────────────────────────────────────
        medved)
            echo "medved/Dockerfile.medved|medved" ;;
        dozor)
            echo "dozor/Dockerfile.dozor|dozor" ;;
        dvar)
            echo "dvar/Dockerfile.dvar|dvar" ;;
        vigie)
            echo "vigie/Dockerfile.vigie|vigie" ;;
        sentinel-collector)
            echo "sentinel/collector/Dockerfile|sentinel/collector" ;;

        # ── Blockchain / Misc ────────────────────────────────────────────────
        karacho)
            echo "karacho/Dockerfile.karacho|karacho" ;;
        koursk)
            echo "koursk/Dockerfile.koursk|koursk" ;;
        koursk-1)
            echo "koursk-1/Dockerfile.koursk-1|koursk-1" ;;
        koursk-2)
            echo "koursk-2/Dockerfile.koursk-2|koursk-2" ;;
        tsushima)
            echo "tsushima/Dockerfile.tsushima|tsushima" ;;
        razvedka)
            echo "razvedka/Dockerfile.razvedka|razvedka" ;;

        # ── MCP / Outils ─────────────────────────────────────────────────────
        bojemoi-mcp)
            echo "mcp-server/Dockerfile|mcp-server" ;;
        suricata-attack-enricher)
            echo "suricata-attack-enricher/Dockerfile|suricata-attack-enricher" ;;
        trivy-scanner)
            echo "trivy-scanner/Dockerfile|trivy-scanner" ;;
        protonmail-bridge)
            echo "Dockerfile.protonmail-bridge|." ;;
        provisioning)
            echo "provisioning/Dockerfile.provisioning|provisioning" ;;

        # ── Repos externes (hors /opt/bojemoi) ───────────────────────────────
        ml-threat-intel)
            echo "EXTERNAL|/opt/bojemoi-ml-threat|Dockerfile.ml-threat|." ;;
        telegram-bot)
            echo "EXTERNAL|/opt/bojemoi-telegram/telegram-bot|Dockerfile.telegram-bot|." ;;

        # ── Inconnue / officielle ─────────────────────────────────────────────
        *)
            echo "" ;;
    esac
}

# ─── Extraction des images custom depuis les stacks ───────────────────────────
get_custom_images_from_stacks() {
    for dir in $STACK_DIRS; do
        find "$dir" -name '*.yml' -type f 2>/dev/null
    done | xargs grep -h "image:" 2>/dev/null | \
        sed 's/.*image:[[:space:]]*//' | \
        sed 's/\${IMAGE_REGISTRY:-localhost:5000}/localhost:5000/g' | \
        sed 's/["'"'"']//g' | sed 's/#.*//' | tr -d ' ' | \
        grep "^localhost:5000/" | grep -v '\*' | grep -v '^\$' | \
        sed 's|^localhost:5000/||' | \
        sort -u | while read -r img; do
            info=$(get_build_info "$img")
            [ -n "$info" ] && echo "$img"
        done
}

# ─── Check si une image existe dans la registry ───────────────────────────────
image_in_registry() {
    local img="$1"
    local base="${img%%:*}"
    local tag="${img#*:}"
    [ "$tag" = "$base" ] && tag="latest"
    curl -4 -sf "http://$REGISTRY/v2/$base/manifests/$tag" \
        -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
        -o /dev/null 2>/dev/null
}

# ─── Build d'une image ────────────────────────────────────────────────────────
build_image() {
    local image="$1"   # ex: borodino:latest
    local info
    info=$(get_build_info "$image")

    if [ -z "$info" ]; then
        echo "  [SKIP] $image — pas de mapping Dockerfile"
        return 0
    fi

    local registry_tag="$REGISTRY/$image"
    local dockerfile context_dir build_root

    case "$info" in
        EXTERNAL|*)
            if echo "$info" | grep -q "^EXTERNAL|"; then
                build_root=$(echo "$info" | cut -d'|' -f2)
                dockerfile=$(echo "$info" | cut -d'|' -f3)
                context_dir=$(echo "$info" | cut -d'|' -f4)
                context_dir="$build_root/$context_dir"
            else
                dockerfile="$BOJEMOI_ROOT/$(echo "$info" | cut -d'|' -f1)"
                local rel_ctx
                rel_ctx=$(echo "$info" | cut -d'|' -f2)
                context_dir="$BOJEMOI_ROOT/$rel_ctx"
            fi
            ;;
    esac

    if [ ! -f "$dockerfile" ]; then
        echo "  [WARN] $image — Dockerfile introuvable: $dockerfile"
        return 0
    fi
    if [ ! -d "$context_dir" ]; then
        echo "  [WARN] $image — contexte introuvable: $context_dir"
        return 0
    fi

    echo "  [BUILD] $registry_tag"
    echo "          Dockerfile: $dockerfile"
    echo "          Contexte:   $context_dir"

    if docker build \
        -f "$dockerfile" \
        -t "$registry_tag" \
        "$context_dir"; then
        docker push "$registry_tag"
        echo "  [OK]   $registry_tag poussé"
    else
        echo "  [ERR]  Build échoué pour $image"
        return 1
    fi
}

# ─── Commande --list ──────────────────────────────────────────────────────────
cmd_list() {
    echo "=== Images custom connues ==="
    printf "%-35s %s\n" "IMAGE" "DOCKERFILE"
    printf "%-35s %s\n" "─────────────────────────────────" "──────────────────────────────"
    for img in \
        borodino borodino-msf wg-gateway \
        oblast oblast-1 \
        nuclei nuclei-api pentest-orchestrator \
        medved dozor dvar vigie sentinel-collector \
        karacho koursk koursk-1 koursk-2 tsushima razvedka \
        bojemoi-mcp suricata-attack-enricher trivy-scanner \
        protonmail-bridge provisioning \
        ml-threat-intel telegram-bot; do
        info=$(get_build_info "$img")
        if [ -n "$info" ]; then
            case "$info" in
                EXTERNAL*)
                    df=$(echo "$info" | cut -d'|' -f2,3 | tr '|' '/')
                    ;;
                *)
                    df=$(echo "$info" | cut -d'|' -f1)
                    ;;
            esac
            printf "%-35s %s\n" "$img" "$df"
        fi
    done
}

# ─── Commande --missing ───────────────────────────────────────────────────────
cmd_missing() {
    echo "=== Images custom manquantes dans la registry ==="
    local found=0
    get_custom_images_from_stacks | while read -r img; do
        if ! image_in_registry "$img"; then
            echo "  MISSING: localhost:5000/$img"
            found=1
        fi
    done
    [ $found -eq 0 ] && echo "  Toutes les images sont présentes"
}

# ─── Build principal ──────────────────────────────────────────────────────────
cmd_build() {
    local force="$1"
    local target="$2"
    local built=0 skipped=0 errors=0

    echo "=== Build images custom ==="
    echo "Registry: $REGISTRY"
    echo ""

    local images
    if [ -n "$target" ]; then
        images="$target"
    else
        images=$(get_custom_images_from_stacks)
    fi

    for img in $images; do
        info=$(get_build_info "$img")
        if [ -z "$info" ]; then
            echo "  [SKIP] $img — aucun mapping"
            skipped=$((skipped + 1))
            continue
        fi

        if [ "$force" != "yes" ] && image_in_registry "$img"; then
            echo "  [OK]   localhost:5000/$img — déjà dans la registry"
            skipped=$((skipped + 1))
            continue
        fi

        echo ""
        if build_image "$img"; then
            built=$((built + 1))
        else
            errors=$((errors + 1))
        fi
    done

    echo ""
    echo "=== Résumé ==="
    echo "  Built:   $built"
    echo "  Skipped: $skipped"
    echo "  Errors:  $errors"
    [ $errors -gt 0 ] && return 1
    return 0
}

# ─── Main ─────────────────────────────────────────────────────────────────────
case "${1:-}" in
    --list)
        cmd_list ;;
    --missing)
        cmd_missing ;;
    --force)
        cmd_build yes "${2:-}" ;;
    -h|--help)
        echo "Usage: $0 [--list|--missing|--force|<image>]"
        echo "  (sans args) — build les images custom manquantes depuis les stacks" ;;
    "")
        cmd_build no "" ;;
    *)
        # Image spécifique
        info=$(get_build_info "$1")
        if [ -z "$info" ]; then
            echo "Image inconnue: $1"
            echo "Utilisez --list pour voir les mappings disponibles"
            exit 1
        fi
        cmd_build no "$1" ;;
esac
