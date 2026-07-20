---
title: Runtime images
description: Deploy the ForgeGuard Hermes runtime image as a persistent, supervised server with durable state and an authenticated web dashboard.
order: 20
status: stable
---

# Runtime images

The `runtime-*` image is the full supervised Hermes server: an s6-overlay
supervisor keeps the web dashboard and per-profile gateways running (they
restart on crash and are restored after a container or host restart), with the
web dashboard UI, Playwright/Chromium browser tools, and messaging + Matrix
adapters baked in. Its on-disk layout matches upstream's Docker image — an
immutable `/opt/hermes` install tree and a `/opt/data` state volume.

Anyone can pull and run it; no other ForgeGuard tooling is required. Images are
published to `ghcr.io/forgeguard-ai/hermes-agent`.

> **Version-sensitive behaviour.** This page documents the fork tracking
> upstream `v2026.7.1` (Hermes `v0.18.0`). Dashboard authentication is
> mandatory on non-loopback binds from that release onward — see
> [Dashboard authentication](../operations/dashboard-authentication.md). Check
> [Compatibility](../fork/compatibility.md) for the current mapping.

## Prerequisites

- A container engine (Docker or Podman).
- A host directory for durable state (this guide uses `~/.hermes`).
- If the dashboard will listen on anything other than loopback, credentials for
  an [authentication provider](../operations/dashboard-authentication.md).

## Run a persistent server

Prefer an immutable tag for anything you care about. Replace
`runtime-v2026.7.1-forgeguard.5` with the tag of the [release](../operations/releases-and-upgrades.md)
you are pinning to:

```bash
docker pull ghcr.io/forgeguard-ai/hermes-agent:runtime-v2026.7.1-forgeguard.5
docker run -d \
  --name hermes \
  --restart unless-stopped \
  -v ~/.hermes:/opt/data \
  -p 9119:9119 \
  -e HERMES_DASHBOARD=1 \
  -e HERMES_DASHBOARD_BASIC_AUTH_USERNAME=admin \
  -e HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="$(openssl rand -hex 24)" \
  -e HERMES_DASHBOARD_BASIC_AUTH_SECRET="$(openssl rand -hex 32)" \
  -e HERMES_UID="$(id -u)" -e HERMES_GID="$(id -g)" \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-v2026.7.1-forgeguard.5 gateway run
```

The generated password is printed nowhere — set it to a value you control if you
need to log in interactively, or read it back from your own secret store. Never
commit a real password to a compose file or image.

What each piece does:

- **`--restart unless-stopped`** restarts the container after crashes and host
  reboots. Inside the container, s6-overlay independently supervises the
  dashboard and per-profile gateway processes, and a boot reconciler restores
  every gateway that was running before the restart.
- **`-v ~/.hermes:/opt/data`** is all of your durable state — config, sessions,
  memory, skills, profiles, logs. The image itself is immutable; upgrading means
  pulling a newer tag and recreating the container, and the state survives. See
  [Persistence and backups](../operations/persistence-and-backups.md).
- **`-p 9119:9119`** publishes the dashboard/gateway backend. This is the same
  endpoint the Hermes Desktop app's Client Mode connects to (enter
  `http(s)://<host>:9119` in its connection dialog). The OpenAI-compatible API
  server on `8642` is separate and optional; publish it only if you use it.
- **Authentication variables** are required on the non-loopback (`0.0.0.0`)
  dashboard bind. Set the basic-auth pair (the `_SECRET` keeps sessions valid
  across restarts) or an OAuth client ID. See
  [Dashboard authentication](../operations/dashboard-authentication.md).
- **`HERMES_UID` / `HERMES_GID`** remap the in-container user to the owner of
  your bind mount — use these instead of `docker run --user`. The image boots as
  root so its setup hook can `chown` the volume, then drops privileges. `PUID` /
  `PGID` are accepted as aliases.

## Verify

The container exposes an unauthenticated health endpoint used by its own
`HEALTHCHECK`:

```bash
curl --fail http://localhost:9119/api/status
docker inspect --format '{{.State.Health.Status}}' hermes
```

`docker inspect` should report `healthy` once the dashboard is up. The
`HEALTHCHECK` reports healthy-no-op when `HERMES_DASHBOARD` is unset, so
one-shot or CLI containers never flap.

If the container exits immediately, check the log for the auth gate:

```bash
docker logs hermes | grep -i "Refusing to bind dashboard"
```

## First-time setup

```bash
docker exec -it hermes hermes setup
```

The image's exec shim drops root to the runtime user automatically. You can also
drive everything from the web dashboard or Desktop Client Mode.

## Everything else behaves like upstream's image

Compose examples, profiles, log routing, resource limits, and audio all work
exactly as documented in the upstream
[Docker user guide](https://hermes-agent.nousresearch.com/docs/user-guide/docker) —
substitute `ghcr.io/forgeguard-ai/hermes-agent:runtime-<release>` for the
upstream image reference in any command there. This page does not restate that
material; it documents only what differs in the ForgeGuard image.

## Related

- [Distrobox / CLI image](./distrobox-cli.md) — the lean interactive variant.
- [Dashboard authentication](../operations/dashboard-authentication.md)
- [Persistence and backups](../operations/persistence-and-backups.md)
- [Image tag families](../reference/image-tags.md)
- [Troubleshooting ForgeGuard artifacts](../troubleshooting/forgeguard-artifacts.md)
