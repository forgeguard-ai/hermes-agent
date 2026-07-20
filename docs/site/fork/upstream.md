---
title: How ForgeGuard relates to upstream
description: The relationship between the ForgeGuard fork and upstream NousResearch/hermes-agent, and where to file issues.
order: 62
status: stable
---

# How ForgeGuard relates to upstream

Hermes Agent is built and maintained by [Nous Research](https://nousresearch.com).
ForgeGuard maintains a **distribution** of it. Understanding the split tells you
who owns what and where to send issues.

## Who owns what

| Area | Owner |
|---|---|
| The Hermes agent runtime, CLI, TUI, gateway, desktop app | Nous Research (upstream). |
| Providers, models, tools, skills, memory, messaging adapters | Nous Research (upstream). |
| Security and isolation model | Nous Research (upstream). |
| Product documentation at `hermes-agent.nousresearch.com` | Nous Research (upstream). |
| ForgeGuard runtime/CLI images, desktop installers, release/version scheme | ForgeGuard. |
| ForgeGuard container packaging and CI/release automation | ForgeGuard. |

## Licensing and attribution

Hermes Agent is MIT-licensed with copyright held by Nous Research. The fork
preserves that license and attribution. ForgeGuard-authored additions (the
packaging overlay, release automation, and this documentation) are identified in
the repository history. ForgeGuard does not claim upstream sponsorship,
endorsement, or support for its distribution-specific builds.

## What ForgeGuard does and does not do

- **Does:** track upstream tagged releases; build and publish versioned runtime
  and CLI images and desktop installers; document those artifacts.
- **Does not:** modify the agent's runtime behaviour, extend provider or
  messaging support, rebrand the application, or reorganise the upstream product
  documentation.

## Where to file issues

- **ForgeGuard artifacts** (GHCR images, desktop installers, release/versioning,
  ForgeGuard-only container behaviour) →
  [`forgeguard-ai/hermes-agent`](https://github.com/forgeguard-ai/hermes-agent/issues).
- **Hermes itself** (behaviour reproducible on an upstream install) →
  [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent/issues).

Reproduce on an upstream install first when it isn't obviously ForgeGuard-specific:
if it reproduces upstream, file it upstream. The repository's `SUPPORT.md` records
the full boundary.

## Related

- [ForgeGuard changes](./forgeguard-changes.md)
- [Compatibility](./compatibility.md)
- [Migrating from upstream](./migration-from-upstream.md)
