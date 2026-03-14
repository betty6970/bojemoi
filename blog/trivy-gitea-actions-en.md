---
title: "Physician, Heal Thyself: Scanning My Own Dockerfiles with Trivy in Gitea Actions"
date: 2026-03-03T20:01:00+00:00
draft: false
tags: ["cybersecurity", "devops", "docker", "gitops", "homelab", "selfhosted", "infosec", "opensource", "build-in-public", "blue-team", "soc", "devsecops"]
summary: "I integrated Trivy into my Gitea Actions pipeline to automatically scan 30+ Dockerfiles and Docker Swarm stacks on every push. First finding: my own infrastructure had obvious gaps."
description: "Hands-on integration of Trivy in Gitea Actions to scan IaC misconfigurations and exposed secrets — no vulnerability database download, running on a 916 MB RAM Lightsail runner."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Physician, heal thyself.

I run an offensive homelab — mass nmap scans, Metasploit exploitation, threat intelligence pipelines. But my own Dockerfiles and Docker Swarm stacks had zero automated security scanning. Not a great look for a security lab.

## Why Trivy?

Trivy is an open-source security scanner from Aqua Security covering multiple attack surfaces: image vulnerabilities, IaC misconfigurations, exposed secrets.

For my use case, two scanners are particularly relevant and require **no vulnerability database download** (~300 MB — too heavy for my 916 MB Lightsail runner):

- `trivy config` — misconfigurations in Dockerfiles and YAML stacks
- `trivy fs --scanners secret` — hardcoded secrets in the codebase

## The Gitea Actions Integration

The workflow follows the same pattern as my existing Hugo CI/CD: container image + manual `git clone` against the internal Gitea URL.

```yaml
name: Trivy Security Scan

on:
  push:
    branches: [main]
  pull_request:

jobs:
  trivy:
    runs-on: ubuntu-latest
    container:
      image: aquasec/trivy:latest

    steps:
      - name: Clone repo
        run: |
          git clone --depth 1 --branch "${GITHUB_REF_NAME:-main}" \
            "http://oauth2:${{ secrets.GITEA_TOKEN }}@gitea:3000/${GITHUB_REPOSITORY}.git" /repo

      - name: Scan — misconfigurations
        run: |
          trivy config \
            --severity HIGH,CRITICAL \
            --exit-code 0 \
            /repo
        continue-on-error: true

      - name: Scan — exposed secrets
        run: |
          trivy fs \
            --scanners secret \
            --exit-code 0 \
            /repo
        continue-on-error: true
```

`--exit-code 0` = advisory mode, no pipeline blocking. Inventory first, harden later.

## Two Bugs Fixed Along the Way

**Bug 1**: The Gitea Act runner automatically mounts a volume at `/workspace/owner/repo`. Cloning to `/workspace` → "not an empty directory". Fix: clone to `/repo` instead.

**Bug 2**: The repo is private. `git clone` without credentials → "could not read Username". Fix: embed `oauth2:${{ secrets.GITEA_TOKEN }}` in the URL — the token is automatically injected by Gitea Actions.

## What the First Scan Found

### Misconfigurations (trivy config)

**Running as root (DS-0002 — HIGH)**

Multiple images run as root without an explicit non-privileged user: `berezina`, `borodino`, `narva`, `karacho`... Classic attack surface — if the container is compromised, the attacker gets root directly.

**Secrets in build-args / ENV (CRITICAL)**

`karacho`, `oblast`, and `oblast-1` Dockerfiles pass secrets via environment variables or build-args. These secrets end up baked into image layers and visible in Docker history.

**`apt-get` without `--no-install-recommends` (DS-0029 — HIGH)**

ZAP Dockerfiles (`oblast/Dockerfile.zaproxy`) install packages without `--no-install-recommends`, unnecessarily inflating image size and attack surface.

### Exposed Secrets (trivy fs)

No hardcoded secrets detected. Good news.

## What's Next

The workflow is live. Next steps:

1. Fix critical Dockerfiles (secrets in ENV first)
2. Add non-root `USER` declarations where feasible
3. Flip `--exit-code 1` on the secret scanner once false positives are triaged
4. Extend to `trivy image` to scan built images (requires more RAM)

Security infrastructure starts with its own hygiene.
