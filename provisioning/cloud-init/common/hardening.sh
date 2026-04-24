#!/bin/bash
# Basic security hardening script
# Usage: curl this script | bash

set -e

echo "Applying security hardening..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

# SSH hardening
if [ -f /etc/ssh/sshd_config ]; then
    echo "Hardening SSH configuration..."

    # Backup original config
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

    # Apply secure settings
    sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
    sed -i 's/#MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
    sed -i 's/#LoginGraceTime.*/LoginGraceTime 60/' /etc/ssh/sshd_config

    # Restart SSH service
    case $OS in
        alpine)
            rc-service sshd restart
            ;;
        *)
            systemctl restart sshd || systemctl restart ssh
            ;;
    esac
fi

# Kernel hardening (sysctl)
echo "Applying kernel hardening..."
cat > /etc/sysctl.d/99-hardening.conf << 'EOF'
# Disable IP forwarding (unless needed for routing)
net.ipv4.ip_forward = 0

# Disable source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Enable TCP SYN cookies
net.ipv4.tcp_syncookies = 1

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0

# Log suspicious packets
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Ignore ICMP broadcasts
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Protect against SYN flood attacks
net.ipv4.tcp_max_syn_backlog = 2048

# Disable IPv6 if not needed (comment out if IPv6 is required)
# net.ipv6.conf.all.disable_ipv6 = 1
EOF

sysctl -p /etc/sysctl.d/99-hardening.conf

# File permissions
echo "Setting secure file permissions..."
chmod 600 /etc/shadow 2>/dev/null || true
chmod 644 /etc/passwd
chmod 600 /etc/gshadow 2>/dev/null || true
chmod 644 /etc/group

# Remove unnecessary services
echo "Disabling unnecessary services..."
case $OS in
    ubuntu|debian)
        systemctl disable avahi-daemon 2>/dev/null || true
        systemctl disable cups 2>/dev/null || true
        ;;
esac

echo "Security hardening completed"
