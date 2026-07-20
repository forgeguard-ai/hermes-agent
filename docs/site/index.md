---
title: ForgeGuard Hermes Agent
description: The ForgeGuard maintained distribution of Hermes Agent — versioned runtime and CLI container images and desktop installers, with durable state and dashboard authentication.
order: 0
status: stable
---

# ForgeGuard Hermes Agent

ForgeGuard maintains a distribution of [Hermes Agent](https://hermes-agent.nousresearch.com/docs/),
the self-improving AI agent built by [Nous Research](https://nousresearch.com).
The upstream product — the agent runtime, its providers, tools, messaging
gateway, and desktop app — is owned and documented by Nous Research. ForgeGuard
adds a packaging and release overlay on top of tagged upstream releases:
versioned runtime and CLI container images on GHCR and desktop installers
attached to each fork release.

This documentation covers **only the ForgeGuard distribution artifacts**. For
how Hermes itself works — configuration, providers, skills, memory, the
messaging gateway, security model — follow the links to the upstream product
documentation.

> This is a maintained fork. ForgeGuard tracks upstream tagged releases and
> publishes its own artifacts; it does not change how the Hermes agent behaves.
> Core Hermes behaviour and product documentation remain upstream-owned. See
> [How ForgeGuard relates to upstream](./fork/upstream.md).

## Choose a task

- **Choose an artifact** — decide between the runtime image, the CLI image, and
  the desktop app: [Choose a ForgeGuard artifact](./getting-started/choose-a-forgeguard-artifact.md).
- **Run a persistent agent** — a supervised server with a web dashboard and
  durable state: [Runtime images](./deployment/runtime-images.md).
- **Use the CLI image** — an interactive terminal install via distrobox:
  [Distrobox / CLI image](./deployment/distrobox-cli.md).
- **Install desktop artifacts** — Linux and macOS builds of Hermes Desktop:
  [Desktop artifacts](./deployment/desktop-artifacts.md).
- **Upgrade safely** — understand tags and roll back cleanly:
  [Releases and upgrades](./operations/releases-and-upgrades.md).
- **Understand the fork** — what ForgeGuard adds and how versions map:
  [ForgeGuard changes](./fork/forgeguard-changes.md) ·
  [Compatibility](./fork/compatibility.md).

## Sections

| Section | Contents |
|---|---|
| [Getting started](./getting-started/choose-a-forgeguard-artifact.md) | Pick the right ForgeGuard artifact for your use case. |
| [Deployment](./deployment/runtime-images.md) | Runtime images, the distrobox CLI image, and desktop installers. |
| [Operations](./operations/dashboard-authentication.md) | Dashboard authentication, persistence and backups, releases and upgrades. |
| [Reference](./reference/image-tags.md) | Image tag families and platform/version compatibility. |
| [Troubleshooting](./troubleshooting/forgeguard-artifacts.md) | Fixing common issues with ForgeGuard artifacts. |
| [Fork](./fork/forgeguard-changes.md) | What ForgeGuard changes, compatibility, upstream relationship, and migration. |

## Where to file issues

Report problems with **ForgeGuard artifacts** (the GHCR images, the desktop
installers, the release/versioning scheme, or ForgeGuard-only container
behaviour) to [`forgeguard-ai/hermes-agent`](https://github.com/forgeguard-ai/hermes-agent/issues).
Report bugs in **Hermes itself** — behaviour reproducible on an upstream install —
to [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent/issues).
See [How ForgeGuard relates to upstream](./fork/upstream.md) for the full
boundary and the reproduce-on-upstream-first guidance.
