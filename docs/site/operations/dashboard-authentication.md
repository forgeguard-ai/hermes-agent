---
title: Dashboard authentication
description: Configure a required authentication provider for the Hermes dashboard on non-loopback binds in ForgeGuard runtime deployments.
order: 30
status: stable
---

# Dashboard authentication

When the Hermes dashboard binds to anything other than loopback, an
authentication gate engages and the dashboard **refuses to start unless an
auth provider is registered**. This is upstream behaviour as of `v2026.7.1`;
it applies to the ForgeGuard runtime image because that image exposes the
dashboard for remote clients.

> **Network exposure.** Publishing the dashboard port (`-p 9119:9119`) makes it
> reachable on your host's network. Always configure an auth provider before
> exposing it, and terminate TLS in front of it (a reverse proxy) for anything
> beyond a trusted LAN. The `--insecure` flag does **not** bypass the auth gate.

## Prerequisites

- A [runtime deployment](../deployment/runtime-images.md) (the CLI image has no
  dashboard).
- One of the providers below.

## Option 1 — basic authentication

Set a username and a password. Prefer a pre-hashed password
(`..._PASSWORD_HASH`) so a plaintext secret never sits in your environment or
process list; a plaintext `..._PASSWORD` is accepted as a fallback. Set
`..._SECRET` so sessions stay valid across restarts.

| Variable | Purpose |
|---|---|
| `HERMES_DASHBOARD_BASIC_AUTH_USERNAME` | Login username. |
| `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH` | Preferred: a pre-hashed password. |
| `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` | Fallback: plaintext password. |
| `HERMES_DASHBOARD_BASIC_AUTH_SECRET` | Session-signing secret; keeps sessions valid across restarts. |

```bash
docker run -d --name hermes --restart unless-stopped \
  -v ~/.hermes:/opt/data -p 9119:9119 \
  -e HERMES_DASHBOARD=1 \
  -e HERMES_DASHBOARD_BASIC_AUTH_USERNAME=admin \
  -e HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="$(openssl rand -hex 24)" \
  -e HERMES_DASHBOARD_BASIC_AUTH_SECRET="$(openssl rand -hex 32)" \
  ghcr.io/forgeguard-ai/hermes-agent:runtime-<release> gateway run
```

Never commit a real password to a compose file or Dockerfile. Inject secrets at
runtime from your own secret store.

## Option 2 — OAuth

Set `HERMES_DASHBOARD_OAUTH_CLIENT_ID` to register the OAuth provider instead of
basic auth. The Hermes Desktop Client Mode dialog signs in against either
provider.

## Verify

The dashboard should start and serve the UI. The health endpoint stays
unauthenticated and is used by the container `HEALTHCHECK`:

```bash
curl --fail http://localhost:9119/api/status
```

If the container exits immediately after start, the auth gate refused the bind.
Check the log:

```bash
docker logs hermes | grep -i "Refusing to bind dashboard"
```

Add a provider (above) and recreate the container.

## Upstream security model

The dashboard auth gate is one part of Hermes's overall security posture. The
meaningful trust boundary for untrusted input is whole-process / OS isolation,
which is documented upstream:
[Security guide](https://hermes-agent.nousresearch.com/docs/user-guide/security).
ForgeGuard does not change that model.

## Related

- [Runtime images](../deployment/runtime-images.md)
- [Persistence and backups](./persistence-and-backups.md)
- [Troubleshooting: refusing to bind](../troubleshooting/forgeguard-artifacts.md#the-dashboard-refuses-to-bind-and-the-container-exits)
