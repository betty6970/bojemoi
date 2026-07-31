---
title: "Operation Talked: Russia-Nexus APT vs a Homelab Pentest Pipeline — Same Tools, Different Discipline"
date: 2026-07-31T20:00:00+00:00
draft: false
tags: ["threat-intelligence", "cybersecurity", "infosec", "homelab", "docker-swarm", "selfhosted", "build-in-public", "apprendre-la-cyber", "osint"]
summary: "SOCRadar exposed an active Russian espionage campaign targeting Ukraine's defense sector. Their C2 stack? Almost identical to my homelab. Here's the full comparison."
description: "Operation Talked used Sliver, WireGuard, 3x-ui and masscan — the same open-source stack as my automated pentest pipeline. The difference wasn't the tools, it was operational discipline."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

SOCRadar just published a detailed teardown of **Operation Talked**, a 14-month Russia-linked espionage campaign (attributed to UAC-0056/UAC-0114) that breached 9 Ukrainian defense and aerospace contractors, stealing full Git repository dumps. The campaign was still active at publication (July 29, 2026), with an interactive shell open on a Ukrainian railway logistics operator.

What caught my attention: their C2 stack is almost identical to what I run in my automated pentest pipeline.

---

## The Toolset Comparison

| Tool | Operation Talked | Bojemoi Lab |
|------|-----------------|-------------|
| C2 framework | Sliver mTLS + HTTP (v1.5.x) | Sliver mTLS + HTTP |
| VPN | WireGuard (port 44444/UDP) | WireGuard |
| VPN panel | 3x-ui MHSanaei fork (port 55555) | 3x-ui MHSanaei fork |
| Mass scanner | masscan + fscan | masscan (automated, 15 replicas) |
| Vuln scanner | nuclei | nuclei-worker (automated queue) |
| AI tooling | Kimi AI (kimi-cli) | Claude Haiku |
| Orchestration | manual (hands-on-keyboard) | fully automated pipeline |

These are literally the same open-source tools. The offensive ecosystem has completely democratized the toolset — a state-sponsored actor and a homelab run the same stack.

---

## Where They Win: Post-Exploitation Windows AD

Their real advantage is in the post-exploitation phase, specifically Active Directory:

- **mimikatz** — LSASS memory dump (T1003.001)
- **DonPAPI** — DPAPI credential harvest (T1555.003)
- **NetExec** — Pass-the-Hash via `nxc smb -H` (T1550.002)
- **Kerberos ticket theft** — Pass-the-Ticket (T1550.003)
- **evil-winrm** — WinRM lateral movement (T1021.006)
- **git-dumper** — bulk Git repository exfiltration (T1213)
- **proxychains-ng across 80+ proxies** — multi-hop exfil (T1090.003)

My pipeline is Linux/web focused. No AD lateral movement module. This is the genuine gap.

---

## Where I Win: OPSEC and Automation

### OPSEC

This is where the comparison becomes almost comical.

They ran everything on a bare Yandex Cloud IP (AS13238, Moscow) with zero reverse proxy. One service was a raw `python3 -m http.server` listener on port 8090 — serving 8,436 operational files with no authentication. Tools, stolen credentials, target lists, Sliver session logs, WireGuard private keys — all publicly accessible.

That single misconfiguration gave SOCRadar a 14-month case file built entirely from the attacker's own perspective.

My setup:
- Traefik reverse proxy in front of every service
- Fly.io redirectors — C2 traffic never hits the real server IP
- Docker secrets for all credentials
- Prometheus alerts on unexpected inbound connections

I would have detected an unauthorized reader on my infrastructure within minutes. They didn't notice for weeks.

The attribution tells the same story: their bash history contained commands mistyped with their Russian JCUKEN keyboard layout (`cd` typed as `св`, `ls` as `ды`). A VPN cannot mask muscle memory.

### Automation

They worked manually, hands-on-keyboard. My pipeline runs continuously without intervention:

```
AK47 (masscan) → BM12 (fingerprinting) → UZI (MSF exploitation)
    → Sliver implant deploy
    → ZAP (web scan)
    → nuclei (CVE detection)
    → DefectDojo (triage via Claude Haiku)
    → Telegram alerts
```

15 scanning replicas, automated exploit queues, AI-powered triage. They had an operator manually enumerating databases on a compromised server. I have a queue processor.

---

## Full MITRE ATT&CK Coverage

Their complete TTP map across the 14-month campaign:

| Tactic | Technique | Tool |
|--------|-----------|------|
| Reconnaissance | T1595.001 Active Scanning | masscan, fscan, nuclei, Netlas/Shodan/FOFA |
| Resource Dev | T1583.003 VPS | Yandex Cloud Moscow |
| Initial Access | T1190 Exploit Public-Facing App | 19 CVEs (Sophos XG, FortiOS, F5, SAP, WordPress...) |
| Initial Access | T1133 External Remote Services | FortiGate SSL-VPN credential reuse |
| Persistence | T1505.003 Web Shell | Godzilla ASPX, r57, suo5 |
| Persistence | T1133 Sliver beacon | 60-second mTLS check-in |
| Defense Evasion | T1573.001 Encrypted Channel | Sliver mTLS |
| Credential Access | T1003.001 LSASS | mimikatz |
| Credential Access | T1555.003 Web Credentials | DonPAPI |
| Discovery | T1087.002 Domain Account | powerview.py, LDAP |
| Lateral Movement | T1550.002 Pass the Hash | NetExec |
| Lateral Movement | T1550.003 Pass the Ticket | Kerberos |
| Lateral Movement | T1021.006 WinRM | evil-winrm |
| Collection | T1213 Information Repositories | git-dumper |
| Exfiltration | T1567.002 Cloud Storage | AWS S3 |
| C2 | T1090.003 Multi-hop Proxy | proxychains-ng, Chisel, Gost SOCKS5 |

My pipeline covers T1595 through T1573. Everything from T1003 onward is the gap.

---

## Key CVEs in Their Arsenal

- **CVE-2022-1040** — Sophos XG RCE (757,000 targets scanned)
- **CVE-2024-55591** — FortiOS auth bypass
- **CVE-2025-31324** — SAP NetWeaver deserialization RCE
- **CVE-2023-46747** — F5 BIG-IP unauth RCE
- **CVE-2026-63030** — WordPress wp2shell (very recent)
- **CVE-2025-49113 / CVE-2025-25257** — Roundcube RCE

All 6 have Nuclei templates in my pipeline's template library.

---

## The Takeaway

State-sponsored actors with significant resources are running the same open-source offensive toolstack as a homelab. The sophistication gap isn't in the tools — it's in operational discipline and automation.

They had better post-exploitation depth (Windows AD). I have better OPSEC and full automation. They got caught because of a `SimpleHTTP` server left running on their C2. 

The democratization of offensive tooling is real. What differentiates operators isn't access to exotic tools — it's how they run them.

---

*Source: [SOCRadar — Operation Talked, July 29 2026](https://socradar.io/blog/operation-talked-russia-ukraine-defense-industry/)*  
*MITRE ATT&CK Navigator layer available in the [bojemoi CTI repo](https://gitea.bojemoi.me/bojemoi/bojemoi)*
