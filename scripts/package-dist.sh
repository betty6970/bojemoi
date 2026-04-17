#!/bin/ash
# =============================================================================
# Bojemoi Lab — Distribution Packager
# =============================================================================
# Génère une archive de distribution ne contenant :
#   - Stacks YAML défensifs uniquement (pas d'offensif)
#   - Code Python compilé en .pyc uniquement (pas de sources .py)
#   - Dockerfiles des services d'architecture
#   - Fichiers de config (volumes/, scripts/, docs/)
#   - BUILD_PROMPT.md, ARCHITECTURE.md, README.md
#
# Usage:
#   ./scripts/package-dist.sh [--version X.Y.Z] [--output /path/to/out]
# =============================================================================
set -eu

# ─── Paramètres ────────────────────────────────────────────────────────────

VERSION="${1:-}"
OUTPUT_DIR="${2:-/tmp}"
TIMESTAMP=$(date +%Y%m%d-%H%M)

if [ -z "$VERSION" ]; then
  VERSION=$(git -C "$(dirname "$0")/.." describe --tags --always 2>/dev/null || echo "dev-$TIMESTAMP")
fi

DIST_NAME="bojemoi-lab-${VERSION}"
DIST_DIR="/tmp/${DIST_NAME}"
ARCHIVE="${OUTPUT_DIR}/${DIST_NAME}.tar.gz"

REPO_MAIN="/opt/bojemoi"
REPO_BOOT="/opt/bojemoi_boot"
REPO_ML="/opt/bojemoi-ml-threat"
REPO_TG="/opt/bojemoi-telegram"

# ─── Couleurs ──────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo "${BLUE}[pack]${NC} $*"; }
success() { echo "${GREEN}[ok]${NC}   $*"; }
warn()    { echo "${YELLOW}[warn]${NC} $*"; }

# ─── Helpers ───────────────────────────────────────────────────────────────

copy() {
  src="$1"; dst="$2"
  mkdir -p "$(dirname "$dst")"
  cp -r "$src" "$dst"
}

compile_py() {
  # Compile tous les .py d'un répertoire source vers un répertoire dest (.pyc seulement)
  src="$1"; dst="$2"
  find "$src" -name "*.py" | while read f; do
    rel="${f#$src/}"
    dir="$dst/$(dirname "$rel")"
    mkdir -p "$dir"
    python3 -m py_compile "$f"
    # Récupérer le .pyc généré dans __pycache__
    base=$(basename "$f" .py)
    dirpath=$(dirname "$f")
    pyc=$(find "$dirpath/__pycache__" -name "${base}.cpython-*.pyc" 2>/dev/null | head -1)
    if [ -n "$pyc" ]; then
      cp "$pyc" "$dir/${base}.pyc"
    else
      warn "Pas de .pyc pour $f"
    fi
  done
  # Copier les fichiers non-Python utiles (requirements.txt, config, etc.)
  find "$src" -not -name "*.py" -not -path "*/__pycache__/*" -not -path "*/.git/*" -type f | while read f; do
    rel="${f#$src/}"
    dir="$dst/$(dirname "$rel")"
    mkdir -p "$dir"
    cp "$f" "$dir/"
  done
}

# ─── Init ──────────────────────────────────────────────────────────────────

info "Version : $VERSION"
info "Dest    : $ARCHIVE"
rm -rf "$DIST_DIR" && mkdir -p "$DIST_DIR"

# =============================================================================
# 1. STACKS — défensifs uniquement
# =============================================================================
info "Stacks YAML..."
mkdir -p "$DIST_DIR/stack"

STACKS="
01-service-hl.yml
02-service-maintenance.yml
45-service-ml-threat-intel.yml
46-service-razvedka.yml
47-service-vigie.yml
48-service-dozor.yml
49-service-mcp.yml
50-service-trivy.yml
51-service-ollama.yml
55-service-sentinel.yml
56-service-dvar.yml
60-service-telegram.yml
65-service-medved.yml
70-service-defectdojo.yml
"

for f in $STACKS; do
  if [ -f "$REPO_MAIN/stack/$f" ]; then
    cp "$REPO_MAIN/stack/$f" "$DIST_DIR/stack/$f"
  else
    warn "Stack introuvable : $f"
  fi
done

# Boot stack (dépôt séparé)
if [ -f "$REPO_BOOT/stack/01-boot-service.yml" ]; then
  cp "$REPO_BOOT/stack/01-boot-service.yml" "$DIST_DIR/stack/01-boot-service.yml"
  success "Stack boot inclus"
else
  warn "Stack boot introuvable ($REPO_BOOT/stack/01-boot-service.yml)"
fi

# Suricata host
if [ -f "$REPO_MAIN/stack/01-suricata-host.yml" ]; then
  cp "$REPO_MAIN/stack/01-suricata-host.yml" "$DIST_DIR/stack/01-suricata-host.yml"
fi

# =============================================================================
# 2. CODE PYTHON → .pyc
# =============================================================================
info "Compilation Python → .pyc..."

# Services dans bojemoi principal
for svc in vigie dozor sentinel razvedka medved mcp-server ptaas-init c2-monitor; do
  src="$REPO_MAIN/$svc"
  if [ -d "$src" ]; then
    info "  $svc"
    compile_py "$src" "$DIST_DIR/$svc"
  fi
done

# ML Threat Intel (dépôt séparé)
if [ -d "$REPO_ML" ]; then
  info "  ml-threat-intel"
  compile_py "$REPO_ML" "$DIST_DIR/ml-threat-intel"
fi

# Telegram Bot (dépôt séparé)
if [ -d "$REPO_TG/telegram-bot" ]; then
  info "  telegram-bot"
  compile_py "$REPO_TG/telegram-bot" "$DIST_DIR/telegram-bot"
fi

# =============================================================================
# 3. DOCKERFILES (services d'architecture)
# =============================================================================
info "Dockerfiles..."

# Chercher tous les Dockerfile* dans les répertoires défensifs
# Inclure les Dockerfiles des services sélectionnés, exclure offensif
DOCKERFILE_DIRS="vigie dozor sentinel razvedka medved mcp-server ptaas-init c2-monitor nym-proxy"

for svc in $DOCKERFILE_DIRS; do
  src="$REPO_MAIN/$svc"
  if [ -d "$src" ]; then
    for df in "$src"/Dockerfile*; do
      [ -f "$df" ] || continue
      name=$(basename "$df")
      mkdir -p "$DIST_DIR/$svc"
      cp "$df" "$DIST_DIR/$svc/$name"
    done
  fi
done

# Dockerfile ML et Telegram
if [ -f "$REPO_ML/Dockerfile.ml-threat" ]; then
  cp "$REPO_ML/Dockerfile.ml-threat" "$DIST_DIR/ml-threat-intel/"
fi
if [ -f "$REPO_TG/telegram-bot/Dockerfile.telegram-bot" ]; then
  cp "$REPO_TG/telegram-bot/Dockerfile.telegram-bot" "$DIST_DIR/telegram-bot/"
fi

# Dockerfile postgres-ssl (architecture DB)
if [ -f "$REPO_MAIN/borodino/Dockerfile.postgres-ssl" ]; then
  mkdir -p "$DIST_DIR/postgres"
  cp "$REPO_MAIN/borodino/Dockerfile.postgres-ssl" "$DIST_DIR/postgres/"
fi

# =============================================================================
# 4. CONFIGS — volumes/
# =============================================================================
info "Configs volumes/..."

VOLUME_DIRS="
grafana
prometheus
alertmanager
loki
alloy
postgres
"

for d in $VOLUME_DIRS; do
  src="$REPO_MAIN/volumes/$d"
  if [ -d "$src" ]; then
    # Exclure les certificats SSL et données sensibles
    mkdir -p "$DIST_DIR/volumes/$d"
    find "$src" -type f \
      -not -path "*/ssl/*.key" \
      -not -path "*/ssl/*.pem" \
      -not -path "*/certs/*" \
      | while read f; do
          rel="${f#$src/}"
          mkdir -p "$DIST_DIR/volumes/$d/$(dirname "$rel")"
          cp "$f" "$DIST_DIR/volumes/$d/$rel"
        done
  fi
done

# =============================================================================
# 5. SCRIPTS — non-offensifs
# =============================================================================
info "Scripts..."
mkdir -p "$DIST_DIR/scripts"

SCRIPTS="
create-secrets.sh
build_all.sh
cccp.sh
import_ripe_cidrs.py
download_ip.py
list_registry.sh
cleaning_registry.sh
"

for s in $SCRIPTS; do
  if [ -f "$REPO_MAIN/scripts/$s" ]; then
    cp "$REPO_MAIN/scripts/$s" "$DIST_DIR/scripts/$s"
  fi
done

# Boot scripts
if [ -f "$REPO_BOOT/scripts/create-secrets.sh" ]; then
  cp "$REPO_BOOT/scripts/create-secrets.sh" "$DIST_DIR/scripts/create-secrets-boot.sh"
fi

# =============================================================================
# 6. DOCS & CONFIGS RACINE
# =============================================================================
info "Docs et configs racine..."

for f in \
  BUILD_PROMPT.md \
  ARCHITECTURE.md \
  README.md \
  .env.example \
  install.sh \
  Makefile
do
  [ -f "$REPO_MAIN/$f" ] && cp "$REPO_MAIN/$f" "$DIST_DIR/$f"
done

# Runbooks
[ -d "$REPO_MAIN/docs" ] && cp -r "$REPO_MAIN/docs" "$DIST_DIR/docs"

# =============================================================================
# 7. INIT SQL
# =============================================================================
if [ -f "$REPO_MAIN/volumes/postgres/init/01-create-databases.sql" ]; then
  mkdir -p "$DIST_DIR/volumes/postgres/init"
  cp "$REPO_MAIN/volumes/postgres/init/01-create-databases.sql" \
     "$DIST_DIR/volumes/postgres/init/"
fi

# =============================================================================
# 8. ARCHIVE
# =============================================================================
info "Génération de l'archive..."
mkdir -p "$OUTPUT_DIR"

# Supprimer les __pycache__ résiduels
find "$DIST_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

cd /tmp
tar czf "$ARCHIVE" "$DIST_NAME/"
cd - >/dev/null

SIZE=$(du -sh "$ARCHIVE" | cut -f1)
success "Archive : $ARCHIVE ($SIZE)"

# Nettoyage
rm -rf "$DIST_DIR"

# =============================================================================
# Rapport
# =============================================================================
echo ""
echo "=== Contenu de la distribution ==="
tar tzf "$ARCHIVE" | grep -v "/$" | sed 's|[^/]*/||' | sort | \
  awk -F/ '{print $1}' | sort -u | while read d; do
    count=$(tar tzf "$ARCHIVE" | grep "^${DIST_NAME}/${d}" | wc -l)
    echo "  $d/ ($count fichiers)"
  done
echo ""
success "bojemoi-lab ${VERSION} — distribution prête."
