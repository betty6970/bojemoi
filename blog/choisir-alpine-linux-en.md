---
title: "Why I Chose Alpine Linux — and How Claude Took Over"
date: 2026-03-04T10:00:00+00:00
draft: false
tags: ["homelab", "docker", "docker-swarm", "devops", "selfhosted", "build-in-public", "french-tech", "apprendre-la-cyber", "opensource", "alpine-linux"]
summary: "No Claude at the start. Just 20 Intel CPUs, a scalability requirement, and an OS to pick. Here's how Alpine Linux became the foundation of Bojemoi Lab — and how AI gradually took command of the project."
description: "A personal account of how Bojemoi Lab started: choosing Alpine Linux, adopting Docker Swarm, and the complete transformation of a development workflow with Claude."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

When this project started, I had no relationship with Claude whatsoever.

## The challenge: 20 CPUs, a scalable platform

I needed to build a scalable platform. I had 20 Intel CPUs at my disposal and needed to pick a lightweight, secure OS to host as many VMs as possible.

I chose **Alpine Linux**.

The reason was straightforward: no packages were needed beyond Python and a few imports. Alpine is ~5 MB installed, a stripped-down kernel, minimal attack surface. For an offensive lab that would generate massive network traffic, it was the obvious call.

## Docker moves in — with an AI co-pilot

Docker quickly became the obvious choice. And with it, Claude arrived through the GUI.

What happened next still surprises me: my development pace accelerated dramatically, even though I still knew nothing about Python. Not a single script. Not a `for` loop. Nothing.

But I had clear ideas about what I wanted to build, and Claude turned those ideas into working code.

## The first friction point: Docker Swarm vs. Docker Compose

There was one notable source of friction. Claude had a tendency to confuse **Docker Swarm** and **docker-compose**. The syntax differs, placement constraints differ too, and a misconfigured Swarm stack doesn't just crash cleanly — it fails quietly in ways that take time to diagnose.

I had to dig into Swarm on my own. Understand overlay networks, secrets, node constraints. And correct Claude's stubbornness on the tricky parts.

After some hard-fought debugging sessions, I upgraded to **Claude Pro**.

And that was it. Total satisfaction. The sheer power of it.

## The question that changed everything

I've always been a developer at heart. At first, I'd ask Claude to produce Python scripts based on my pentesting knowledge.

Then one day, I asked a question about the value of Git in the age of LLMs. Claude replied:

---

> *Hi Betty,*
>
> *That's an interesting reflection — you're touching on a debate that's very much alive in the dev community right now. But let me nuance it a bit.*
>
> **What's true in your observation:** for many use cases — utility scripts, prototypes, one-off tools — yes, Claude can generate a solution on demand, and the code becomes almost "throwaway." You describe a need, I produce the result. No need to version a script you can regenerate in 30 seconds with a well-crafted prompt.
>
> **Where it hits its limits:** as soon as you have a project with state, accumulated complexity, or dependencies between components (like Bojemoi Lab), a Git repo remains essential:
>
> - **Accumulated context:** Claude has no persistent memory of the full codebase between sessions. A repo is the source of truth.
> - **Consistency:** when your FastAPI orchestrator, cloud-init templates, Docker Swarm configs, and Gitea hooks need to work together, you need one place where everything coexists and changes are tracked.
> - **Auditability:** especially with your audit trail logic, Git history is complementary.
> - **Reproducibility:** "it worked yesterday" is only verifiable with a commit.
>
> **What genuinely changes** is the relationship with code. The model shifts toward something like: the repo remains the source of truth, but Claude becomes the "on-demand developer" who reads the repo, understands the context, and produces the changes. The prompt partially replaces documentation, and the code becomes more replaceable than maintainable.

---

That answer changed how I work.

## The new workflow: steering without touching code

Since that day, I've held myself to a strict rule: **no more asking for scripts, no more touching code directly**.

I only ask general questions or express needs.

I've completely "lost" control over the containers, images, and internal processes — but that was intentional. I've focused entirely on requirements and on steering my team of developers... somewhat autistic ones. I'll come back to that point in a future post.

One other key point: I ask Claude to memorize my directives in `memory.md`. That file is what provides continuity between sessions — not my own memory, not scattered notes. A versioned, living file that Claude consults and updates.

## Where things stand today

Bojemoi Lab is running in production:
- **4 Docker Swarm nodes** (Alpine Linux throughout)
- **6.2M scanned hosts** in the Metasploit database
- **30+ Docker services** deployed via GitOps
- CI/CD pipelines running in Gitea Actions
- A local MCP server to control everything in natural language

All of it, without having written a single line of Python by hand.

Alpine Linux was the right call. Not because it's trendy, but because the constraint was real: lightweight, secure, minimal surface. And that constraint shaped everything that followed.

---

*What about you — how did you choose the base OS for your homelab? Do you still write code directly when working with an AI?*
