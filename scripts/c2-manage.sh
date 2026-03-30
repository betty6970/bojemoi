#!/bin/bash
# c2-manage.sh — Borodino stack + C2 redirector management
#
# Usage:
#   ./c2-manage.sh all start                   # Check + start VPN server, VPN client, borodino stack
#   ./c2-manage.sh all stop                    # Stop borodino stack + VPN client (VPN server left up)
#   ./c2-manage.sh borodino start              # Deploy stack, wait until all services up
#   ./c2-manage.sh borodino stop               # Remove stack, wait until all services gone
#   ./c2-manage.sh redirector delete <name>    # Revoke cert, delete files

set -euo pipefail

STACK_FILE="/opt/bojemoi/stack/40-service-borodino.yml"
STACK_NAME="borodino"
PKI_DIR="/opt/bojemoi/volumes/c2-vpn"
EASYRSA_PKI="$PKI_DIR/pki"
CLOUD_INIT_DIR="/opt/bojemoi/cloud-init"

POLL_INTERVAL=3
TIMEOUT=300

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[-]${NC} $*" >&2; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

# ── Helpers ───────────────────────────────────────────────────────────────────

# Print a live-updating status line (overwrites previous)
status_line() { printf "\r\033[K  ${CYAN}→${NC} %s" "$*"; }

# Wait for all borodino services to reach desired replica count
wait_for_stack_up() {
    local deadline=$(( $(date +%s) + TIMEOUT ))
    info "Waiting for all services to reach desired replicas (timeout ${TIMEOUT}s)..."
    while true; do
        local total=0 ready=0 not_ready=""
        while IFS= read -r line; do
            local name replicas
            name=$(echo "$line" | awk '{print $1}')
            replicas=$(echo "$line" | awk '{print $2}')
            # replicas format: "5/5" or "0/0" or "5/5 (max 5 per node)"
            local running desired
            running=$(echo "$replicas" | cut -d/ -f1)
            desired=$(echo "$replicas" | cut -d/ -f2 | cut -d' ' -f1)
            total=$(( total + 1 ))
            if [ "$running" = "$desired" ]; then
                ready=$(( ready + 1 ))
            else
                not_ready="$not_ready $name($running/$desired)"
            fi
        done < <(docker stack services "$STACK_NAME" --format "{{.Name}} {{.Replicas}}" 2>/dev/null)

        status_line "$ready/$total services ready${not_ready:+ | pending:$not_ready}"

        if [ "$ready" -eq "$total" ] && [ "$total" -gt 0 ]; then
            echo ""
            log "All $total services up."
            return 0
        fi
        if [ "$(date +%s)" -ge "$deadline" ]; then
            echo ""
            err "Timeout after ${TIMEOUT}s. Remaining:$not_ready"
            return 1
        fi
        sleep "$POLL_INTERVAL"
    done
}

# Wait until docker stack rm completes (all services gone)
wait_for_stack_down() {
    local deadline=$(( $(date +%s) + TIMEOUT ))
    info "Waiting for all services to stop (timeout ${TIMEOUT}s)..."
    while true; do
        local count
        count=$(docker stack services "$STACK_NAME" --format "{{.Name}}" 2>/dev/null | wc -l)
        status_line "$count services still running..."
        if [ "$count" -eq 0 ]; then
            echo ""
            log "Stack $STACK_NAME fully stopped."
            return 0
        fi
        if [ "$(date +%s)" -ge "$deadline" ]; then
            echo ""
            err "Timeout after ${TIMEOUT}s — some services may still be stopping."
            return 1
        fi
        sleep "$POLL_INTERVAL"
    done
}

# ── Component checks ─────────────────────────────────────────────────────────

SSH_KEY="/home/docker/LightsailDefaultKey-eu-central-1.pem"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=10"
VPN_OVPN="/opt/bojemoi/volumes/c2-vpn/clients/lab-manager.ovpn"

check_openvpn_server() {
    ssh $SSH_OPTS ec2-user@bojemoi.me \
        "sudo docker inspect openvpn-c2 --format '{{.State.Running}}' 2>/dev/null" 2>/dev/null \
        | grep -q "true"
}

check_vpn_client() {
    docker inspect lab-manager-vpn --format '{{.State.Running}}' 2>/dev/null | grep -q "true" && \
    ip link show tun0 &>/dev/null
}

check_vpn_tunnel() {
    ping -c1 -W3 10.8.0.1 &>/dev/null
}

check_borodino_stack() {
    local count
    count=$(docker stack services "$STACK_NAME" --format "{{.Name}}" 2>/dev/null | wc -l)
    [ "$count" -gt 0 ]
}

start_openvpn_server() {
    log "Starting OpenVPN server on bojemoi.me..."
    ssh $SSH_OPTS ec2-user@bojemoi.me \
        "sudo docker start openvpn-c2 2>/dev/null || sudo docker run -d --name openvpn-c2 \
            --cap-add=NET_ADMIN --device=/dev/net/tun \
            -p 1194:1194/udp \
            -v /opt/openvpn/server:/etc/openvpn/server:ro \
            -v /opt/openvpn/ccd:/etc/openvpn/ccd:ro \
            -v openvpn-logs:/var/log/openvpn \
            --restart unless-stopped \
            --sysctl net.ipv4.ip_forward=1 \
            --sysctl net.ipv4.conf.all.accept_redirects=0 \
            --entrypoint openvpn \
            kylemanna/openvpn \
            --config /etc/openvpn/server/openvpn.conf \
            --client-config-dir /etc/openvpn/ccd \
            --log /var/log/openvpn/openvpn.log" 2>&1
    # Wait up to 15s for it to be running
    local i
    for i in $(seq 1 15); do
        check_openvpn_server && return 0
        sleep 1
    done
    err "OpenVPN server did not come up in time"
    return 1
}

start_vpn_client() {
    log "Starting lab-manager VPN client..."
    docker rm -f lab-manager-vpn 2>/dev/null || true
    docker run -d --name lab-manager-vpn \
        --privileged \
        --network host \
        --restart unless-stopped \
        -v "$VPN_OVPN:/etc/openvpn/client.ovpn:ro" \
        --entrypoint sh \
        kylemanna/openvpn \
        -c "mkdir -p /dev/net && mknod /dev/net/tun c 10 200 2>/dev/null || true && \
            chmod 666 /dev/net/tun && \
            openvpn --config /etc/openvpn/client.ovpn" 2>&1
    # Wait up to 30s for tun0 + tunnel
    log "Waiting for VPN tunnel (up to 30s)..."
    local i
    for i in $(seq 1 30); do
        status_line "waiting for tun0... ${i}s"
        if check_vpn_tunnel; then
            echo ""
            log "VPN tunnel up — lab-manager IP: $(ip addr show tun0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1)"
            return 0
        fi
        sleep 1
    done
    echo ""
    err "VPN tunnel did not establish in 30s"
    docker logs lab-manager-vpn 2>&1 | tail -10
    return 1
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_all_start() {
    echo ""
    info "=== Checking C2 infrastructure ==="
    echo ""

    # ── 1. OpenVPN server (bojemoi.me) ────────────────────────────────────────
    printf "  %-40s" "OpenVPN server (bojemoi.me)..."
    if check_openvpn_server; then
        echo -e "${GREEN}UP${NC}"
    else
        echo -e "${YELLOW}DOWN — starting${NC}"
        start_openvpn_server || { err "Failed to start OpenVPN server"; exit 1; }
        printf "  %-40s${GREEN}UP${NC}\n" "OpenVPN server (bojemoi.me)..."
    fi

    # ── 2. VPN client (lab-manager) ───────────────────────────────────────────
    printf "  %-40s" "VPN client (lab-manager-vpn)..."
    if check_vpn_client; then
        echo -e "${GREEN}UP${NC} ($(ip addr show tun0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1))"
    else
        echo -e "${YELLOW}DOWN — starting${NC}"
        start_vpn_client || { err "Failed to start VPN client"; exit 1; }
        printf "  %-40s${GREEN}UP${NC}\n" "VPN client (lab-manager-vpn)..."
    fi

    # ── 3. VPN tunnel reachability ────────────────────────────────────────────
    printf "  %-40s" "VPN tunnel (ping 10.8.0.1)..."
    if check_vpn_tunnel; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        err "VPN tunnel is not reachable — check openvpn-c2 logs on bojemoi.me"
        exit 1
    fi

    # ── 4. Borodino stack ─────────────────────────────────────────────────────
    printf "  %-40s" "Borodino stack..."
    if check_borodino_stack; then
        local count
        count=$(docker stack services "$STACK_NAME" --format "{{.Name}}" 2>/dev/null | wc -l)
        echo -e "${GREEN}UP${NC} ($count services)"
    else
        echo -e "${YELLOW}DOWN — deploying${NC}"
        echo ""
        cmd_borodino_start
    fi

    echo ""
    log "All components up."
}

cmd_all_stop() {
    echo ""
    info "=== Stopping C2 infrastructure ==="
    echo ""

    # ── 1. Borodino stack ─────────────────────────────────────────────────────
    printf "  %-40s" "Borodino stack..."
    if check_borodino_stack; then
        echo -e "${YELLOW}UP — stopping${NC}"
        docker stack rm "$STACK_NAME" 2>&1
        wait_for_stack_down
    else
        echo -e "${CYAN}already down${NC}"
    fi

    # ── 2. VPN client ─────────────────────────────────────────────────────────
    printf "  %-40s" "VPN client (lab-manager-vpn)..."
    if check_vpn_client; then
        echo -e "${YELLOW}UP — stopping${NC}"
        docker rm -f lab-manager-vpn 2>/dev/null || true
        log "VPN client stopped."
    else
        echo -e "${CYAN}already down${NC}"
    fi

    # ── 3. OpenVPN server — left running (needed to not drop other connections)
    printf "  %-40s${CYAN}left running${NC}\n" "OpenVPN server (bojemoi.me)..."

    echo ""
    log "Done. OpenVPN server on bojemoi.me is still up (use 'all stop --vpn' to also stop it)."
}

cmd_borodino_start() {
    log "Deploying stack $STACK_NAME from $STACK_FILE..."
    docker stack deploy \
        -c "$STACK_FILE" \
        "$STACK_NAME" \
        --prune \
        --resolve-image always \
        --detach=true 2>&1
    echo ""
    wait_for_stack_up
    echo ""
    docker stack services "$STACK_NAME" --format "  {{.Name}}\t{{.Replicas}}\t{{.Image}}"
}

cmd_borodino_stop() {
    # Confirm
    warn "This will remove the entire $STACK_NAME stack."
    printf "  Confirm? [y/N] "
    read -r confirm
    [ "${confirm:-n}" != "y" ] && { info "Aborted."; exit 0; }

    log "Removing stack $STACK_NAME..."
    docker stack rm "$STACK_NAME" 2>&1
    echo ""
    wait_for_stack_down
}

cmd_redirector_list() {
    local REGISTRY_DIR="$PKI_DIR/redirectors"
    mkdir -p "$REGISTRY_DIR"

    local entries=()
    while IFS= read -r f; do
        entries+=("$f")
    done < <(find "$REGISTRY_DIR" -name "*.json" 2>/dev/null | sort)

    echo ""
    printf "  ${CYAN}%-22s %-10s %-8s %-18s %-8s %s${NC}\n" \
        "NAME" "PROVIDER" "REGION" "IP" "HTTP" "CREATED"
    printf "  %s\n" "$(printf '─%.0s' {1..75})"

    if [ ${#entries[@]} -eq 0 ]; then
        echo "  (no redirectors provisioned)"
    else
        for f in "${entries[@]}"; do
            local name provider region ip created http_status
            name=$(     grep '"name"'     "$f" | cut -d'"' -f4)
            provider=$( grep '"provider"' "$f" | cut -d'"' -f4)
            region=$(   grep '"region"'   "$f" | cut -d'"' -f4)
            ip=$(       grep '"ip"'       "$f" | cut -d'"' -f4)
            created=$(  grep '"created"'  "$f" | cut -d'"' -f4 | cut -dT -f1)

            # Quick HTTP check if IP is known
            if [ -n "$ip" ]; then
                http_status=$(curl -4 -sk -o /dev/null -w "%{http_code}" \
                    --connect-timeout 3 "https://${ip}/" 2>/dev/null || echo "???")
                [ "$http_status" = "302" ] && http_status="${GREEN}302${NC}" \
                                           || http_status="${RED}${http_status}${NC}"
            else
                ip="-"
                http_status="${YELLOW}no ip${NC}"
            fi

            printf "  %-22s %-10s %-8s %-18s ${http_status} %s\n" \
                "$name" "$provider" "$region" "$ip" "$created"
        done
    fi
    echo ""
}

cmd_redirector_delete() {
    local NAME="${1:-}"
    [ -z "$NAME" ] && { err "Usage: $0 redirector delete <name>"; exit 1; }

    local REGISTRY_DIR="$PKI_DIR/redirectors"
    local REG_FILE="$REGISTRY_DIR/${NAME}.json"

    if [ ! -f "$REG_FILE" ] && [ ! -f "$CLOUD_INIT_DIR/${NAME}.yaml" ]; then
        err "Redirector '$NAME' not found (no registry entry or cloud-init file)"
        exit 1
    fi

    # Get provider from registry
    local provider="unknown" ip="-"
    if [ -f "$REG_FILE" ]; then
        provider=$(grep '"provider"' "$REG_FILE" | cut -d'"' -f4)
        ip=$(grep '"ip"' "$REG_FILE" | cut -d'"' -f4)
    fi

    warn "Deleting redirector: $NAME (provider: $provider, ip: ${ip:--})"
    printf "  Confirm? [y/N] "
    read -r confirm
    [ "${confirm:-n}" != "y" ] && { info "Aborted."; exit 0; }

    rm -f "$CLOUD_INIT_DIR/${NAME}.yaml" && log "Deleted cloud-init"
    rm -f "$REG_FILE"                    && log "Deleted registry entry"

    echo ""
    warn "Destroy the VPS to complete:"
    case "$provider" in
        hetzner) echo "  hcloud server delete $NAME" ;;
        vultr)   echo "  vultr-cli instance delete \$(vultr-cli instance list | grep $NAME | awk '{print \$1}')" ;;
        do)      echo "  doctl compute droplet delete \$(doctl compute droplet list | grep $NAME | awk '{print \$1}')" ;;
        *)       echo "  Destroy manually on $provider" ;;
    esac
}

# ── Entrypoint ────────────────────────────────────────────────────────────────

COMMAND="${1:-}"
SUB="${2:-}"

case "$COMMAND" in
    all)
        case "$SUB" in
            start) cmd_all_start ;;
            stop)  cmd_all_stop ;;
            *)
                err "Unknown all command: $SUB"
                echo "Usage: $0 all start|stop"
                exit 1 ;;
        esac
        ;;
    borodino)
        case "$SUB" in
            start) cmd_borodino_start ;;
            stop)  cmd_borodino_stop ;;
            *)
                err "Unknown borodino command: $SUB"
                echo "Usage: $0 borodino start|stop"
                exit 1 ;;
        esac
        ;;
    redirector)
        case "$SUB" in
            list)   cmd_redirector_list ;;
            delete) cmd_redirector_delete "${3:-}" ;;
            *)
                err "Unknown redirector command: $SUB"
                echo "Usage: $0 redirector list|delete <name>"
                exit 1 ;;
        esac
        ;;
    *)
        echo "Usage:"
        echo "  $0 all start                   # Check + start VPN server, VPN client, borodino stack"
        echo "  $0 all stop                    # Stop borodino stack + VPN client"
        echo "  $0 borodino start              # Deploy borodino stack (wait until all up)"
        echo "  $0 borodino stop               # Remove borodino stack (wait until all gone)"
        echo "  $0 redirector list             # List redirectors + connection status
  $0 redirector delete <name>    # Revoke cert + delete redirector files"
        exit 1 ;;
esac
