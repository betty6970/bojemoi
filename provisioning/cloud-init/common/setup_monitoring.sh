#!/bin/bash
# Setup Prometheus node exporter for monitoring
# Usage: curl this script | bash

set -e

NODE_EXPORTER_VERSION="1.7.0"
INSTALL_DIR="/usr/local/bin"

echo "Installing Prometheus Node Exporter v${NODE_EXPORTER_VERSION}..."

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64) ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    armv7l) ARCH="armv7" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Download and install
cd /tmp
wget -q "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz"
tar xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}.tar.gz"
mv "node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}/node_exporter" "${INSTALL_DIR}/"
rm -rf "node_exporter-${NODE_EXPORTER_VERSION}.linux-${ARCH}"*

# Create systemd service
cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
Type=simple
User=nobody
ExecStart=/usr/local/bin/node_exporter
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter

echo "Node Exporter installed and running on port 9100"
