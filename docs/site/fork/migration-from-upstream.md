---
title: Migrating from upstream
description: Move an existing upstream Hermes Agent install to the ForgeGuard runtime or CLI images while preserving state.
order: 63
status: stable
---

# Migrating from upstream

If you already run Hermes from an upstream native install or upstream Docker
image, moving to a ForgeGuard artifact is low-friction: the agent is the same,
and durable state lives in the same place. This page covers the mechanics.

## Prerequisites

- An existing Hermes state directory (typically `~/.hermes`).
- A [backup](../operations/persistence-and-backups.md) of it before you start.

## From an upstream native install

Your state already lives in `~/.hermes`. To run the same agent as a persistent
server, point a ForgeGuard [runtime image](../deployment/runtime-images.md) at
that directory:

```bash
docker run -d --name hermes --restart unless-stopped \
  -v ~/.hermes:/opt/data -p 9119:9119 \
  -e HERMES_DASHBOARD=1 \
  -e HERMES_DASHBOARD_BASIC_AUTH_USERNAME=admin \
  -e HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="<from your secret store>" \
  -e HERMES_DASHBOARD_BASIC_AUTH_SECRET="<stable secret>" \
  -e HERMES_UID="$(id -u)" -e HERMES_GID="$(id -g)" \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<release> gateway run
```

To keep working in a terminal instead, use the
[CLI image via distrobox](../deployment/distrobox-cli.md); it shares your home
directory, so `~/.hermes` is used directly.

## From the upstream Docker image

The ForgeGuard `runtime-*` image uses the same `/opt/data` state volume layout as
upstream's image. Point the ForgeGuard image at the same volume and recreate the
container:

```bash
docker rm -f <old-container>
docker run -d --name hermes --restart unless-stopped \
  -v ~/.hermes:/opt/data -p 9119:9119 \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<release> gateway run
```

Any command from the upstream
[Docker user guide](https://hermes-agent.nousresearch.com/docs/user-guide/docker)
works with the ForgeGuard image reference substituted in.

## Note the dashboard auth requirement

If you previously ran an unauthenticated dashboard on a non-loopback bind, the
ForgeGuard runtime image (following upstream `v2026.7.1`) will refuse to start
without an auth provider. Configure one before exposing the dashboard — see
[Dashboard authentication](../operations/dashboard-authentication.md).

## Verify

```bash
curl --fail http://localhost:9119/api/status
docker exec -it hermes hermes doctor
```

Your existing profiles, sessions, and configuration should appear unchanged.

## Migrating back

Because the state directory is unchanged, migrating back to an upstream install
or image is the reverse of the above — point the upstream install/image at the
same `~/.hermes`. Keep a [backup](../operations/persistence-and-backups.md) from
before any upstream-base upgrade in case state was migrated in place.

## Related

- [Runtime images](../deployment/runtime-images.md)
- [Persistence and backups](../operations/persistence-and-backups.md)
- [How ForgeGuard relates to upstream](./upstream.md)
