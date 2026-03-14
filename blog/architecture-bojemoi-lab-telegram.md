# Telegram Post — Bojemoi Lab Architecture

---

🏗️ **Bojemoi Lab — Full Architecture**

4 Swarm nodes. 43 services. 12 stacks.

**What's running right now:**
🔫 ak47 (x15) → CIDR nmap scan
🎯 bm12 (x15) → NSE fingerprinting + ML classification
💀 uzi (x3) → Metasploit (waiting on msfrpc)
🕵️ razvedka → DDoS prediction on hacktivist channels
🚨 vigie → real-time CERT-FR bulletins
🛡️ dozor → dynamic Suricata rules from IoC feeds
🍯 medved → multi-protocol honeypot (SSH/RDP/SMB/HTTP...)
🤖 telegram-bot → command interface (you are here)
🧠 ml-threat → IoC scoring + MITRE ATT&CK mapping
🔌 mcp-server → Claude Code integration

**DB: 6.15M hosts • 33.7M services • 9 GB PostgreSQL**

Full writeup on the blog → https://blog.bojemoi.me
