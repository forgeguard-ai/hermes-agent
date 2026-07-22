---
title: Compatibility
description: How the ForgeGuard fork release, upstream base, and Hermes product version map to image tags and desktop artifacts.
order: 61
status: stable
---

# Compatibility

This page maps the ForgeGuard fork to the upstream product. For platform,
engine, and architecture support, see
[Platform compatibility](../reference/compatibility.md).

## Version mapping

| Field | Value | Source |
|---|---|---|
| Upstream base (`FORK_UPSTREAM_BASE`) | `v2026.7.20` | `FORK_UPSTREAM_BASE` marker at the repository root. |
| Fork release line | `v2026.7.20-forgeguard.<n>` | Latest [fork release](https://github.com/forgeguard-ai/hermes-agent/releases). |
| Hermes product version | `0.19.0` | `pyproject.toml` (surfaced in each release title/notes). |
| Runtime/CLI images | `runtime-<version>`, `cli-<version>` (+ `-<sha>`, `-latest`) | `ghcr.io/forgeguard-ai/hermes-agent`. |
| Desktop artifacts | `.AppImage`/`.deb`/`.rpm`, `.dmg`/`.zip` | Attached to the fork release (versioned by the Release tag). |

> **Version-sensitive.** These values describe the current fork state. Always
> confirm against the live `FORK_UPSTREAM_BASE` marker and the newest
> [release](https://github.com/forgeguard-ai/hermes-agent/releases) — this fork
> advances quickly. The fork tag names the upstream *release line* it tracks, not
> the product version it contains; read both from the release notes.

## What the fork tracks

ForgeGuard syncs to upstream **tagged releases**, not the moving `upstream/main`
tip, so each fork sync point is stable and reproducible. When upstream cuts a new
tagged release that ForgeGuard adopts, `FORK_UPSTREAM_BASE` advances and the next
fork release line starts from that base.

## Upstream features not independently supported by ForgeGuard

ForgeGuard packages and releases the upstream product; it does not independently
support, extend, or guarantee:

- the provider and model catalog;
- the messaging platform adapters;
- the security/isolation model;
- the native installer and non-container installation paths;
- product features and configuration.

For all of those, the upstream product documentation is authoritative:
[Hermes Agent docs](https://hermes-agent.nousresearch.com/docs/). Report bugs in
those areas upstream — see
[How ForgeGuard relates to upstream](./upstream.md#where-to-file-issues).

## Related

- [ForgeGuard changes](./forgeguard-changes.md)
- [How ForgeGuard relates to upstream](./upstream.md)
- [Platform compatibility](../reference/compatibility.md)
- [Releases and upgrades](../operations/releases-and-upgrades.md)
