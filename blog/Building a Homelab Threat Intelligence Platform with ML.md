# Building a Homelab Threat Intelligence Platform with ML: A Beginner's Journey

Six months ago, I knew almost nothing about cybersecurity infrastructure. Today, I run a production-grade threat intelligence platform that predicts DDoS attacks by monitoring hacktivist Telegram channels. If you're reading this thinking "that sounds impossible for someone starting out" - I get it. I thought the same thing.

This post is for you: the curious beginner who wants to build real security tools but doesn't know where to start.

## What Actually Is This Thing?

Let me start with what my system does in plain English:

**The Problem**: Hacktivist groups announce their attack targets on Telegram before launching DDoS attacks. French organizations often become targets, but there's no automated way to detect these threats early.

**My Solution**: A system that:
1. Monitors Telegram channels where hacktivists hang out
2. Reads messages in multiple languages (because hacktivists don't all speak English)
3. Identifies when organizations are mentioned
4. Scores how "buzzy" or threatening the discussion is
5. Alerts me when a French organization might be under threat

Think of it like having a robot that reads threatening forums 24/7 and taps you on the shoulder when trouble's brewing.

## Why You Can Build This (Even as a Beginner)

Here's my controversial take: **you don't need to be a coding expert to build sophisticated security systems anymore**. 

My approach relies on three principles:

### 1. Let AI Write Your Code
I don't write much code by hand. Instead, I manage prompts and structures. I tell Claude (or similar AI) what I want to build, and it generates the implementation. My job is architecture and integration, not syntax.

**This means**: If you can describe what you want clearly, you can build it.

### 2. Open Source Everything
Every tool I use is free and open source:
- XenServer for virtualization
- Docker Swarm for container orchestration  
- PostgreSQL for databases
- Gitea for Git workflows
- Prometheus/Grafana for monitoring

**This means**: Zero licensing costs, full control, and a massive community for support.

### 3. Automate Everything
Manual processes don't scale and you'll forget them. My infrastructure uses:
- GitOps workflows (push config → automatic deployment)
- Cloud-init for VM provisioning
- Webhook automation for CI/CD
- Container orchestration for self-healing

**This means**: Once set up, the system runs itself. You maintain infrastructure as code, not by clicking through interfaces.

## The Journey: What I (and Claude) Actually Built

Let me walk you through the evolution, because it wasn't linear:

### Phase 1: The Foundation (Months 0-2)
**Started with**: Basic XenServer setup, learning virtualization concepts

**What I learned**: You need a solid base layer before anything fancy. I spent time understanding:
- Network bonding for high availability
- Storage management
- VM templates and provisioning

**Beginner trap I avoided**: Trying to do everything at once. Master one layer before adding the next.

### Phase 2: Container Orchestration (Months 2-3)
**Built**: Docker Swarm cluster with automatic deployment

**What this gives you**: Deploy new services in seconds, not hours. Services restart automatically if they crash.

**The "aha" moment**: When I pushed code to Git and watched it automatically deploy to production without touching a terminal. That's when it clicked.

### Phase 3: GitOps Workflow (Months 3-4)
**Built**: Gitea integration with custom cloud-init datasources that query PostgreSQL

**What this enables**: 
- Write a YAML config describing a VM
- Push it to Git
- VM automatically gets created and configured
- All infrastructure becomes reproducible

**Why this matters**: Your homelab becomes code. Disaster recovery is just re-running your Git repo.

### Phase 4: Threat Intelligence (Months 4-6)
**Built**: The actual threat intelligence platform with:
- Telegram bot monitoring with OSINT capabilities
- Multilingual Named Entity Recognition (NER)
- Entity extraction and relationship mapping
- Buzz scoring algorithms
- Integration with Maltego, TheHive, MISP
- MITRE ATT&CK framework mapping

**The breakthrough**: Realizing threat intelligence is pattern matching at scale. ML helps, but smart architecture and data streaming matter more.

## The Architecture (Simplified)

Here's how the pieces fit together without overwhelming you:

```
[Telegram Channels] 
    ↓ (messages stream in)
[Telegram Bot Infrastructure]
    ↓ (raw text + metadata)
[Multilingual NER Processing]
    ↓ (identified entities)
[Entity Extraction & Scoring]
    ↓ (threat scores)
[PostgreSQL Database]
    ↓ (queries for analysis)
[Alert System] → [Me!]
```

Each box is a microservice in Docker. They communicate through message queues and APIs. If one crashes, the others keep running.

## Key Technologies Explained (For Beginners)

**XenServer**: Think of it like having multiple computers inside one physical computer. Each "virtual machine" acts independently.

**Docker Swarm**: Manages containers (lightweight mini-environments). If you deploy 5 containers, Swarm spreads them across your servers and restarts them if they die.

**PostgreSQL**: A database. It stores all the structured data (entities, threat scores, relationships).

**Gitea**: Like GitHub, but you host it yourself. Your code and configs live here.

**Cloud-init**: Automates VM setup. Instead of clicking through installers, you describe what you want in a file.

**NER (Named Entity Recognition)**: ML that finds entities in text. It spots "Microsoft" in a message and knows it's an organization, not just a word.

## Practical Tips If You're Starting Out

### Start Small, Think Big
Don't try to build everything at once. I started with:
1. One VM running Docker
2. One simple service (a Telegram bot)
3. One database
4. Then gradually added orchestration, monitoring, automation

### Embrace Configuration Over Code
Write YAML configs that describe what you want. Let tools like Docker Compose and cloud-init handle the implementation.

### Build in Production from Day One
Don't have a "learning environment" and a "production environment." Build production-grade from the start:
- Use container orchestration
- Set up monitoring
- Implement logging
- Design for failure

You'll learn better practices and won't need to rebuild later.

### Use AI Assistants Aggressively
I use Claude to:
- Generate FastAPI applications
- Write Docker configs
- Create database schemas
- Debug issues
- Explain concepts I don't understand

This isn't cheating - it's working smart.

### Focus on Integration, Not Implementation
Your value isn't writing Python - it's designing systems that solve problems. Let AI handle syntax. You handle architecture.

## The Threat Intelligence Platform: Deeper Dive

Since this is the cool part, let me break down how the ML/intelligence piece works:

### 1. Data Ingestion
Telegram bots monitor channels and capture:
- Message text
- Timestamp
- Sender info
- Channel metadata

This streams into a message queue for processing.

### 2. Multilingual Processing
Messages might be in Russian, English, French, or mixed. The NER pipeline:
- Detects language
- Applies appropriate NER model
- Extracts entities (organizations, people, locations, IPs, domains)

**Why multilingual matters**: Hacktivists often operate in Russian or use mixed languages to avoid detection.

### 3. Entity Extraction & Scoring
For each entity (like "Company X"), the system:
- Checks if it's French (geolocation + domain analysis)
- Counts mentions across time windows
- Analyzes sentiment and threat keywords
- Computes a "buzz score"

High buzz score = something's happening.

### 4. Threat Correlation
The system maps entities to:
- Known infrastructure (via OSINT tools like Shodan, VirusTotal)
- Historical attack patterns
- MITRE ATT&CK techniques

This builds a threat graph showing relationships.

### 5. Alerting
When patterns indicate elevated risk:
- Score exceeds threshold
- Multiple channels mention the same target
- Threat keywords appear in context

→ Alert fires with supporting evidence.

## OSINT Integration: Making It Smarter

The Telegram bot has integrated OSINT capabilities:

**IP Analysis**: Query VirusTotal, AbuseIPDB, Shodan for reputation and historical data

**Domain Intelligence**: Passive DNS, WHOIS, certificate analysis

**Blockchain Enrollment**: User verification via blockchain-based systems (for access control)

**Framework Mapping**: Automatic MITRE ATT&CK technique identification

This turns raw data into actionable intelligence.

## What Would I Do Differently?

**Start with better monitoring**: I added Prometheus/Grafana late. Wish I'd built it from day one. You can't debug what you can't see.

**Document as you go**: I'm rebuilding some knowledge because I didn't document decisions. Write down WHY you chose something, not just WHAT.

**Network design upfront**: I've had to refactor networking multiple times. Plan your subnets, VLANs, and firewall rules before deploying services.

**Test disaster recovery early**: I built an amazing system... then realized I hadn't tested restoring from backups. Test your failure modes.

## Resources That Actually Helped

**For learning infrastructure**:
- The Phoenix Project (book) - changed how I think about systems
- XenServer documentation - surprisingly readable
- Docker Swarm docs - shorter than Kubernetes, easier to start

**For threat intelligence**:
- MITRE ATT&CK framework - free, comprehensive
- MISP Project documentation - open source threat sharing
- TheHive Project - incident response platform

**For practical skills**:
- Claude (obviously) - for code generation and explanation
- GitHub repos of similar projects - learn from real implementations
- YouTube channels on homelab setups

## The Cost Reality

**Hardware**: I started with older server hardware (~$500 used)
**Software**: $0 (all open source)
**Cloud**: I have some AWS infrastructure, but homelab is self-hosted
**Time**: Significant, but compressed by using AI assistance

You can start smaller - a decent desktop or used server is enough.

## Final Thoughts: You Can Do This

The cybersecurity field sometimes feels gatekept by complexity and jargon. But here's the truth: **if you can describe a problem clearly, you can build a solution**.

Six months ago:
- I didn't know what Docker Swarm was
- I'd never written a FastAPI app
- I couldn't explain what NER meant
- I'd never deployed a VM programmatically

Today I run a production-grade threat intelligence platform.

The difference isn't that I became a genius - it's that I:
1. Broke big problems into small steps
2. Used AI to handle implementation details
3. Focused on open source tools
4. Automated relentlessly
5. Built in public (even when it was messy)

Your threat intelligence platform might look different than mine. Maybe you care about different threats, use different data sources, or have different infrastructure. That's perfect - build what matters to you.

The tools are free. The knowledge is accessible. The AI assistants are ready to help.

Start with one VM. Deploy one service. Automate one thing.

Six months from now, you'll be writing your own "beginner's journey" post.

---

**Next in this series**: I'll break down the technical architecture with code examples, Docker configs, and the actual Telegram bot implementation. But first, I want to hear from you: what part of this interests you most?

*Hit me up on @Betty_Bombers_bot with questions, or follow along as I document the technical deep-dives.*

