# C2 VPN PKI — /opt/bojemoi/volumes/c2-vpn/

This directory holds the PKI and configs for the C2 redirector infrastructure.

## Directory Layout

```
c2-vpn/
├── pki/          — EasyRSA PKI (CA, issued certs, private keys)
├── server/       — Server bundle to copy to bojemoi.me
│   ├── ca.crt
│   ├── server.crt
│   ├── server.key
│   ├── dh.pem
│   ├── ta.key
│   └── openvpn.conf
├── clients/      — Per-client .ovpn files (lab-manager, redirector-*)
└── ccd/          — OpenVPN CCD entries (client-config-dir)
    └── lab-manager  — iroute 192.168.1.0/24
```

## Quick Start

```bash
# 1. Initialize PKI
/opt/bojemoi/scripts/c2-vpn-init-pki.sh

# 2. Copy server bundle to bojemoi.me and start OpenVPN container
# (see output of step 1 for exact commands)

# 3. Connect lab-manager to VPN
openvpn --config /opt/bojemoi/volumes/c2-vpn/clients/lab-manager.ovpn --daemon

# 4. Provision a redirector
/opt/bojemoi/scripts/provision-redirector.sh redirector-1 hetzner hel1

# 5. Deploy VPS with generated cloud-init
# (see output of step 4 for exact hcloud/doctl/vultr-cli command)
```

## Security Notes

- `pki/private/` contains unencrypted private keys — do NOT commit to git
- `clients/*.ovpn` contain embedded private keys — treat as secrets
- Rotate redirector certs every 365 days (EASYRSA_CERT_EXPIRE=365)
- To revoke a compromised redirector: `easyrsa revoke <name>` then `easyrsa gen-crl`
