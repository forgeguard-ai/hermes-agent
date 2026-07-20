---
title: Platform compatibility
description: Supported platforms, container engines, and architectures for ForgeGuard Hermes runtime, CLI, and desktop artifacts.
order: 41
status: stable
---

# Platform compatibility

This page lists the platform and engine support for the **ForgeGuard artifacts**.
For the version mapping between the fork, upstream, and the Hermes product
version, see [Fork compatibility](../fork/compatibility.md).

## Container images

| Target | Status | Notes |
|---|---|---|
| `linux/amd64` | Supported | The published `runtime-*` and `cli-*` images are built for `linux/amd64`. |
| Other architectures | Not currently published | Build from the `Dockerfile` locally if you need a different architecture. |
| Docker | Supported | Primary tested engine. |
| Podman | Community-compatible | The images are OCI-standard; Podman generally works. Distrobox uses whichever engine you have configured. |

## Desktop installers

| Platform | Status | Formats |
|---|---|---|
| Linux | Supported | `.AppImage`, `.deb`, `.rpm` (unsigned). |
| macOS | Supported | `.dmg`, `.zip` (ad-hoc signed, **not notarized**). |
| Windows | Not currently built | — |

macOS builds require the Gatekeeper workaround on install — see
[Desktop artifacts](../deployment/desktop-artifacts.md).

## Ports

| Port | Service | Notes |
|---|---|---|
| `9119` | Dashboard / gateway backend | Published with `-p 9119:9119`; Desktop Client Mode connects here. |
| `8642` | OpenAI-compatible API server | Optional; publish only if used. |

## Hermes product compatibility

The agent runtime, providers, models, tools, and messaging platforms are the
upstream product's concern and are documented there. See the upstream
[Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
and [Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers)
pages. ForgeGuard does not independently support or extend the provider or
messaging catalogs.

## Related

- [Image tag families](./image-tags.md)
- [Fork compatibility](../fork/compatibility.md)
- [Desktop artifacts](../deployment/desktop-artifacts.md)
