---
title: "Building Your Own Falcon MCP: ThreatFox + Cross-Reference Against 6 Million Hosts"
date: 2026-08-06T23:30:00+00:00
draft: false
tags: ["threat-intelligence", "cybersecurity", "osint", "infosec", "homelab", "docker-swarm", "docker", "devops", "selfhosted", "opensource", "build-in-public", "cobalt-strike", "c2", "mcp", "red-team"]
summary: "I saw a post describing how Falcon MCP is used to track APT C2 infrastructure. Tonight I replicated it with free sources — and found an active Cobalt Strike C2 in my database."
description: "How to build an MCP server with ThreatFox (abuse.ch) to cross-reference C2 IOCs against a database of 6 million scanned hosts, starting from scratch with free tools."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Tonight I read a post describing something interesting: someone uses CrowdStrike Falcon via MCP to query their threat intelligence database in natural language — APT12, Calypso, Pegasus, DarkHotel — and get categorized C2 IOC lists by actor.

Falcon costs a fortune. But the concept is simple. And I already had the infrastructure to do the same thing.

This post covers how I built the equivalent in a few hours, using free sources, and what I found.

## What Is MCP?

MCP (Model Context Protocol) is a standard developed by Anthropic that allows an LLM to connect to external tools in real time. When I talk to Claude Code, it can call tools — launch an nmap scan, query my Metasploit database, search for CVEs — because my infrastructure exposes those capabilities through an MCP server.

That's exactly what CrowdStrike did: they plugged their Falcon platform into this protocol. The operator asks "show me active APT12 C2s from this week" and the LLM queries Falcon automatically.

The difference from a regular chatbot: the data is **fresh** and **contextualized to your own infrastructure**.

## My Starting Infrastructure

I have a Docker Swarm homelab with:
- A custom MCP server (`mcp-server`) exposing around thirty tools
- A Metasploit PostgreSQL database with **6.15 million scanned hosts** and their services
- An automated scanning pipeline (masscan → classification → exploit → nuclei)

The MCP server already had `lookup_ip` for querying OTX on a single IP. What was missing: the **feed dimension** — querying threat feeds to find known actors, known C2s, and most importantly cross-referencing that against my own database.

## Free Sources

Two abuse.ch sources, free and well-maintained:

**ThreatFox** — C2 IOC database with confidence scores, malware families, and campaign tags. Requires a free account for the API. Thousands of recent IOCs: Cobalt Strike, Sliver, Metasploit stagers, botnets.

**Feodo Tracker** — botnet C2 list (Emotet, QakBot, IcedID). Completely public, no authentication. Fewer entries but zero friction.

## What We Built

Three functions in a new `bojemoi/cti.py` module:

```python
threatfox_recent(days=7, ioc_type=None, malware=None)
# → Recent IOCs, filterable by type and malware family

threatfox_search(ioc)
# → Is this IP/domain/hash a known C2?

ioc_crossref(days=7, malware=None, min_confidence=50)
# → THE KILLER FEATURE
```

The killer feature is `ioc_crossref`. The logic:

1. Fetch recent `ip:port` IOCs from ThreatFox
2. Extract unique IPs
3. A single SQL query against the 6.15M hosts:

```sql
SELECT host(address::inet), os_name, scan_status, last_scanned
FROM hosts
WHERE host(address::inet) = ANY($1)
```

4. Return matches with context from both sides (what ThreatFox knows + what my scanner saw)

If a host I've already scanned matches a known C2 — I know immediately.

These three functions are also exposed as MCP tools, so Claude can call them directly in conversation:

```
ioc_crossref    → cross-reference ThreatFox IOCs vs MSF DB
threatfox_recent → browse recent C2 IOCs by family/type
threatfox_search → look up a specific IP/domain/hash
```

## The Result

First run with `ioc_crossref(days=2)`:

```
Source       : threatfox
Unique IOCs  : 267
MSF HITS     : 1

  45.8.159.205  |  Cobalt Strike  |  scan_status: None
```

One hit. `45.8.159.205`, Cobalt Strike C2, port 8596, reported the day before with 75% confidence and tag `drb-ra`.

The IP had been in my database since May 2026 — my masscan sweep had touched it — but with no in-depth scan (status null).

## Manual Confirmation

Nmap scan:

```
22/tcp    open   ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.7
8596/tcp  open   unknown
```

HTTP probe on port 8596:

```
GET /  →  HTTP/1.1 404 Not Found
         Content-Type: text/plain
         Content-Length: 0
         [no Server header]

OPTIONS /  →  HTTP/1.1 200 OK
              Content-Type: text/html
              Allow: OPTIONS,GET,HEAD,POST
```

This is the classic signature of a **Cobalt Strike Malleable C2 HTTP profile**:
- Silent 404 on GET (non-beacon requests silently rejected)
- 200 on OPTIONS (beacon heartbeat)
- No `Server` header (obfuscation)
- Port 50050 closed (teamserver UI not exposed — careful operator)

Ubuntu 18.04 EOL. ASN AS49392 LLC Baxet, Moscow. Tag `drb-ra` is a campaign marker identified in the CTI community.

Finding documented in DefectDojo.

## What This Changes

The cross-reference is the part that interests me most. I'm not trying to check whether an IP *exists* in ThreatFox — I can do that with `lookup_ip`. I want to know if among the millions of hosts I've already scanned, some of them are known C2 infrastructure.

That's a different question, and the answer changes what you do next. A host already in your database with known services is immediately explorable — you already know its open ports, OS, and context.

The natural next step: automate this daily and alert via Telegram when a new match appears. That's now running as a daily cron on the lab:

```bash
0 7 * * * docker exec <mcp-server> python cti_daily.py
```

The script calls `ioc_crossref(days=1)`, and sends a Telegram message — either "0 hits, all clear" or a detailed alert with IP, malware family, and confidence score.

## Reproduce This

Everything you need:

- A Python MCP server (code is on my Gitea)
- A free ThreatFox key (register at threatfox.abuse.ch)
- A database of scanned hosts (or Shodan/Censys if you don't have your own scanner)

The cross-reference logic works with any SQL database. If you have a list of IPs you know about, you can cross-reference it against ThreatFox in a few lines.

---

*Infrastructure: Docker Swarm, Python, PostgreSQL, ThreatFox API, abuse.ch Feodo Tracker*
