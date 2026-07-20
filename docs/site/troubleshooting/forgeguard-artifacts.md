---
title: Troubleshooting ForgeGuard artifacts
description: Fixes for common issues with ForgeGuard Hermes runtime images, the CLI image, and desktop installers.
order: 50
status: stable
---

# Troubleshooting ForgeGuard artifacts

Fixes for issues specific to the ForgeGuard artifacts. For problems in Hermes
itself, see the upstream [documentation](https://hermes-agent.nousresearch.com/docs/).

## The dashboard refuses to bind and the container exits

**Symptom.** A `runtime-*` container exits immediately after start; the log
contains `Refusing to bind dashboard to 0.0.0.0`.

**Cause.** The dashboard is bound to a non-loopback address and no
authentication provider is registered. The auth gate fails closed on non-loopback
binds (upstream behaviour since `v2026.7.1`); `--insecure` does not bypass it.

**Fix.** Configure an auth provider and recreate the container — see
[Dashboard authentication](../operations/dashboard-authentication.md). Confirm
with:

```bash
docker logs hermes | grep -i "Refusing to bind dashboard"
```

## Permission errors on the state volume

**Symptom.** The agent cannot write to `/opt/data`, or files on the host
`~/.hermes` are owned by an unexpected user.

**Cause.** The in-container user's UID/GID does not match the owner of the bind
mount.

**Fix.** Pass `HERMES_UID` / `HERMES_GID` (or the `PUID` / `PGID` aliases) set to
your host user, instead of `docker run --user`:

```bash
-e HERMES_UID="$(id -u)" -e HERMES_GID="$(id -g)"
```

The image boots as root to `chown` the volume, then drops to that user.

## The container reports unhealthy

**Symptom.** `docker inspect` shows the container as `unhealthy`.

**Cause / fix.** The `HEALTHCHECK` probes the dashboard's `/api/status` endpoint
on port `9119`. If `HERMES_DASHBOARD` is unset, the check is a healthy no-op — so
an unhealthy status means the dashboard was expected but is not responding.
Check the logs and confirm the auth provider is configured:

```bash
curl --fail http://localhost:9119/api/status
docker logs hermes
```

## A messaging adapter isn't installed in the CLI image

**Symptom.** Running a gateway for a platform (e.g. Telegram) in the `cli-*`
image fails to import an adapter.

**Cause.** The CLI image does not bake in messaging adapters. Hermes
lazy-installs them into `~/.hermes/lazy-packages` on first use.

**Fix.** Run the gateway once and let it fetch the adapter, or use the
[runtime image](../deployment/runtime-images.md), which bakes messaging and
Matrix adapters in.

## macOS: "Hermes is damaged and can't be opened"

**Symptom.** macOS refuses to open the installed app, reporting it as damaged.

**Cause.** The macOS build is ad-hoc signed and not notarized (no Apple
Developer credentials on this fork), so Gatekeeper quarantines the downloaded
`.dmg`.

**Fix.** After copying `Hermes.app` to `/Applications`, clear the quarantine
attribute once:

```bash
xattr -cr /Applications/Hermes.app
```

Downloading the `.zip` with `curl -L` avoids the quarantine attribute entirely.
See [Desktop artifacts](../deployment/desktop-artifacts.md).

## Related

- [Runtime images](../deployment/runtime-images.md)
- [Dashboard authentication](../operations/dashboard-authentication.md)
- [Desktop artifacts](../deployment/desktop-artifacts.md)
