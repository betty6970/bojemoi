#!/bin/bash
# Setup Docker on various distributions
# Usage: curl this script | bash

set -e

echo "Installing Docker..."

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS"
    exit 1
fi

case $OS in
    ubuntu|debian)
        # Install prerequisites
        apt-get update
        apt-get install -y ca-certificates curl gnupg lsb-release

        # Add Docker GPG key
        mkdir -p /etc/apt/keyrings
        curl -fsSL "https://download.docker.com/linux/${OS}/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

        # Add Docker repository
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${OS} $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

        # Install Docker
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        ;;

    alpine)
        # Install Docker on Alpine
        apk add --no-cache docker docker-compose
        rc-update add docker default
        service docker start
        ;;

    centos|rocky|rhel)
        # Install Docker on RHEL-based
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        systemctl enable docker
        systemctl start docker
        ;;

    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

# Add admin user to docker group if exists
if id "admin" &>/dev/null; then
    usermod -aG docker admin
fi

echo "Docker installed successfully"
docker --version
