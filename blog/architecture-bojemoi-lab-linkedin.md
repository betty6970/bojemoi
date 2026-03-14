# LinkedIn Post — Bojemoi Lab Architecture

---

I spent the last few months building Bojemoi Lab from scratch.

Here's what it looks like today: a 4-node Docker Swarm cluster that continuously scans the internet, classifies servers with ML, predicts DDoS attacks, and runs automated pentests.

**What's running right now:**

→ **Scan pipeline**: 3 tools chained together (ak47 nmap → bm12 NSE fingerprinting → uzi Metasploit), 15 replicas each, 6.15M hosts in the database
→ **Threat intelligence**: hacktivist Telegram channel monitoring (razvedka), real-time CERT-FR bulletins (vigie), ML-based IoC scoring (ml-threat-intel)
→ **IDS/IPS**: Suricata in host mode + automatic alert enrichment + CrowdSec WAF
→ **Honeypot**: multi-protocol (SSH, RDP, SMB, HTTP, FTP, Telnet) — everything logs to PostgreSQL and feeds into Faraday
→ **Observability**: Prometheus + Grafana + Loki + Tempo — 9 exporters, full stack
→ **Orchestration**: FastAPI + XenServer + Docker Swarm, with blockchain audit trail

**The stack: 9 GB PostgreSQL, 43 services, 12 Docker stacks.**

Everything is open source, versioned in Gitea, and deployed via CI/CD.

Full architecture breakdown on my blog: blog.bojemoi.me

Building in public. Alone, at night, with a beer.

\#homelab \#cybersecurity \#threatintelligence \#docker \#dockerswarm \#devops \#selfhosted \#opensource \#infosec \#buildinpublic \#blueTeam \#soc \#osint
