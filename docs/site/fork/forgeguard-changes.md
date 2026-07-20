---
title: ForgeGuard changes
description: What the ForgeGuard fork adds on top of upstream Hermes Agent — runtime and CLI images, desktop installers, the release scheme, and CI guards.
order: 60
status: stable
---

# ForgeGuard changes

ForgeGuard maintains a distribution of upstream
[`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent). It
tracks upstream **tagged releases** and adds a packaging and release overlay. It
does not change how the Hermes agent behaves. This page summarises what the fork
adds.

## Runtime and CLI images

Two image variants are published to `ghcr.io/forgeguard-ai/hermes-agent` from one
multi-target `Dockerfile`:

- **`runtime-*`** — a full supervised server image. s6-overlay supervises the web
  dashboard and per-profile gateways; a boot reconciler restores gateways after a
  restart. Browser tools and messaging + Matrix adapters are baked in. Layout
  matches upstream's Docker image (`/opt/hermes` install, `/opt/data` state
  volume).
- **`cli-*`** — a lean interactive image for distrobox / one-off CLI use, with no
  dashboard/gateway stack and no supervisor. Distrobox host-integration packages
  and a locale are pre-baked; messaging adapters lazy-install on first use.

Both carry the OCI labels `com.forgeguard.hermes.prebaked=1` and
`com.forgeguard.hermes.variant=<runtime|cli>`. See
[Runtime images](../deployment/runtime-images.md) and
[Distrobox / CLI image](../deployment/distrobox-cli.md).

## Desktop installers

Prebuilt Hermes Desktop installers are attached to each fork release:

- **Linux:** `.AppImage`, `.deb`, `.rpm` (unsigned).
- **macOS:** `.dmg`, `.zip` (ad-hoc signed, **not notarized** — no Apple
  Developer credentials on this fork).
- **Windows:** not currently built.

See [Desktop artifacts](../deployment/desktop-artifacts.md).

## Release and version scheme

Releases are tagged `<upstream-base>-forgeguard.<n>` (e.g.
`v2026.7.1-forgeguard.5`). `<upstream-base>` is the upstream release tag the
fork's `main` is synced to (recorded in the `FORK_UPSTREAM_BASE` marker); `<n>`
increments per base tag. Image `-<version>` tags are immutable; `-latest` tags
roll. See [Releases and upgrades](../operations/releases-and-upgrades.md) and
[Image tag families](../reference/image-tags.md).

## Fork CI and workflow guards

The fork adds release automation (a release-on-merge orchestrator that calls
reusable image and desktop build workflows) and guards that prevent
upstream-only publishing, deploy, and scheduled workflows from running on the
fork. These are maintainer-facing and are documented under
[`docs/maintainers/`](https://github.com/forgeguard-ai/hermes-agent/tree/main/docs/maintainers);
they are not needed to consume the artifacts.

## ForgeGuard-only container behaviour

Beyond upstream's Docker image, the ForgeGuard images add: the multi-target
`Dockerfile` split (runtime vs CLI), the `com.forgeguard.hermes.*` labels,
pre-baked distrobox host-integration in the CLI image, and the
`HERMES_UID`/`HERMES_GID` (with `PUID`/`PGID` alias) volume-ownership remapping.
Dashboard authentication, persistence, ports, and health semantics otherwise
follow upstream.

## Supported platforms and signing state

- Images: `linux/amd64`.
- Desktop: Linux + macOS (ad-hoc signed, not notarized); Windows not built.

See [Platform compatibility](../reference/compatibility.md) for the full matrix
and [Compatibility](./compatibility.md) for the version mapping.

## Related

- [How ForgeGuard relates to upstream](./upstream.md)
- [Migrating from upstream](./migration-from-upstream.md)
- [Compatibility](./compatibility.md)
