---
title: "Training a ML Model on Real Exploitation Data — and Avoiding the accuracy=1.0 Trap"
date: 2026-07-08T00:01:00+00:00
draft: false
tags: ["machine-learning", "threat-intelligence", "cybersecurity", "infosec", "homelab", "docker-swarm", "docker", "devops", "selfhosted", "opensource", "build-in-public"]
summary: "I plugged my RandomForest model into 6 million real Metasploit hosts and got accuracy=1.0. Here's why that was a bug, not a success, and how I actually fixed it."
description: "Lessons from training ML on real offensive pipeline data: circular feature/label dependency, extreme class imbalance, and oversampling pwned hosts to get a model that actually learns something."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

When you train a machine learning model on synthetic data, you know you're working with clean, structured noise. But when you plug it into real production data — 6.15 million hosts, 33.7 million services, years of exploitation results — and get `train_accuracy=1.0`, you want to celebrate.

It's a trap. I fell into it twice before understanding what was happening.

Here's what I learned.

## Context: ML Threat Intel on an Offensive Pipeline

My homelab runs on Docker Swarm with a continuous scan pipeline: `bm12` does mass fingerprinting, `uzi` attempts exploits on detected services, `nuclei` hunts CVEs, and everything lands in a Metasploit PostgreSQL database that's grown to ~9 GB.

Alongside this, I run an `ml-threat-intel-api` service that classifies IPs as `benign / suspicious / malicious` and computes a reputation score. Until now it ran on **synthetic data** — random distributions I generated myself. Obviously the model learned perfectly the patterns I had invented.

The goal: plug it into real MSF data.

## Version 1: accuracy=1.0 (First Trap)

The first implementation was straightforward. For each host in MSF, I computed:

```python
features = [
    reputation_score,   # min(100, port_scan_count*3 + malware_hits*15)
    age_days,
    0.0,                # report_count (unavailable)
    70.0,               # country_risk (fixed)
    50.0,               # asn_reputation (neutral)
    port_scan_count,
    malware_hits,       # ← COUNT(vulns) from MSF
    ...
]

# Labels
if malware_hits >= 3 or port_scan_count >= 10:
    label = 2  # malicious
elif port_scan_count >= 3 or malware_hits >= 1:
    label = 1  # suspicious
else:
    label = 0  # benign
```

Result after training: `train_accuracy=1.0`, `test_accuracy=1.0`.

The problem? **The labels are a deterministic function of the features.** The model reads `malware_hits` at index 6, applies the threshold I hardcoded in the labels, and gets perfect accuracy — not because it learned anything, but because it *re-learns the if/else rule I wrote myself*.

That's tautology, not machine learning.

## Version 2: accuracy=0.9999 (Second Trap)

I fixed the circular dependency by separating sources: `confirmed_vulns` (COUNT of MSF vulns) for labels only, and `filtered_port_count` replacing it at index 6 in features.

```python
# confirmed_vulns → labels only, never in X
if confirmed_vulns >= 3:
    label = 2
elif confirmed_vulns >= 1:
    label = 1
else:
    label = 0

# feature[6] = filtered_port_count (independent of labels)
features = [..., port_scan_count, filtered_port_count, ...]
```

Result: `train_accuracy=0.9999`.

Still too good? Yes. This time the problem was different: out of 50,000 randomly sampled hosts, only **5 had confirmed vulns**. That's 0.01% of the dataset.

Real distribution: `benign=49995, suspicious=3, malicious=2`.

The model predicts "benign" for everything and is right 99.99% of the time. Accuracy is a useless metric when classes are this imbalanced.

## Version 3: Oversampling Pwned Hosts (The Real Fix)

The issue isn't the natural proportion — it's realistic, most scanned hosts aren't exploited. The problem is that with 5 positive examples, the model has nothing to learn from.

The solution: **exhaustively fetch all pwned hosts, then sample benign ones**.

```python
# 1. All hosts with at least one confirmed vuln (exhaustive)
cur.execute("""
    SELECT h.id, h.address::text,
           EXTRACT(EPOCH FROM (NOW()-h.created_at))/86400 AS age_days,
           COUNT(DISTINCT CASE WHEN s.state='open'     THEN s.id END) AS port_scan_count,
           COUNT(DISTINCT CASE WHEN s.state='filtered' THEN s.id END) AS filtered_port_count,
           COUNT(DISTINCT v.id) AS confirmed_vulns
    FROM hosts h
    LEFT JOIN services s ON s.host_id = h.id
    LEFT JOIN vulns v    ON v.host_id = h.id
    WHERE h.id IN (SELECT DISTINCT host_id FROM vulns)
    GROUP BY h.id, h.address, h.created_at
""")
pwned_rows = cursor.fetchall()  # → 184 hosts

# 2. Random sample of benign hosts (5:1 ratio)
n_benign = max(len(pwned_rows) * 5, 1000)
cur.execute("""
    ... WHERE h.id NOT IN (SELECT DISTINCT host_id FROM vulns)
    LIMIT %s
""", (n_benign,))
benign_rows = cursor.fetchall()  # → 1000 hosts
```

Final distribution: `benign=1000, suspicious=119, malicious=65`.

Result: `train_acc=0.9727`, **`test_acc=0.9331`**.

That train/test gap (4 points) indicates the model is actually generalizing rather than memorizing. It's not perfect — 184 pwned hosts is still sparse for a RandomForest — but it's honest.

## What MSF Vulns Actually Represent

An important note on label quality: in Metasploit, the `vulns` table is populated by modules that *attempt* an exploit. Some records correspond to confirmed RCE (meterpreter sessions, shells), others to attempts that returned a false positive.

In my pipeline, `uzi` pushes results into MSF via RPC. Recorded vulns are exploits that returned `SESSION` — so real compromises in the vast majority of cases. It's usable ground truth, but not perfect.

To improve further, next steps would be:
- Cross-reference with active Sliver sessions (confirmed compromises with a live beacon)
- Enrich with DefectDojo findings validated by an analyst

## What the Model Actually Learns Now

With correct labels and independent features, the RandomForest can now learn real patterns:

- A host with 15 open ports and 8 filtered is more likely to be exploitable than one with 2 open ports
- Recently added hosts (low `age_days`) are often active pipeline targets
- The `port_scan_count + filtered_port_count` combination gives a network exposure fingerprint

These aren't hardcoded rules — they're what the model discovers from the data.

## Retrain Loop Architecture

Everything is integrated into the FastAPI service with an async retrain loop:

```python
async def _retrain_loop(interval_hours: float):
    await asyncio.sleep(interval_hours * 3600)  # first run after 24h
    while True:
        async with _retrain_lock:
            metrics = await loop.run_in_executor(pool, train_from_msf)
            ml_pipeline.load_models()  # hot reload
        await asyncio.sleep(interval_hours * 3600)
```

And an endpoint to trigger manually:

```bash
curl -X POST http://threat-intel.bojemoi.lab.local/models/retrain
# → {"status": "started", "last_retrain": null}
```

The model retrains automatically every 24h on fresh MSF data, no service restart required.

## Takeaways

**1. accuracy=1.0 is almost always a bug.**
Either labels are a function of features (circular dependency), or classes are so imbalanced that "predict the majority class always" is enough.

**2. With heavily imbalanced data, the right metric is recall on the minority class.**
93% accuracy that misses 40% of malicious hosts is less useful than 85% accuracy that catches them all.

**3. Strategic oversampling is more honest than random LIMIT.**
Fetching 50k random hosts from a database where 0.003% are pwned gives a useless dataset. Fetching all pwned + a benign sample gives a workable one.

**4. Synthetic data isn't useless — it stabilizes.**
Mixing 20% synthetic data with real data prevents the model from forgetting general patterns when real data is too concentrated on a narrow subset.

The code is in the repo, the service is running. Next step: plug in Sliver sessions for even cleaner ground truth.

---

*Building in public on [@bojemoi_ptaas](https://t.me/bojemoi_ptaas)*
