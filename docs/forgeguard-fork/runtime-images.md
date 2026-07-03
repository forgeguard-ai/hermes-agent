# ForgeGuard runtime images

The fork publishes two image variants to GitHub Container Registry from one
multi-target `Dockerfile`. Anyone can pull and run them — no relationship to
any other ForgeGuard tooling required.

| Variant | Tags | What it is |
| --- | --- | --- |
| **runtime** | `ghcr.io/forgeguard/hermes-agent:runtime-latest` (rolling), `runtime-<git-sha>` (immutable), `runtime-<release>` (e.g. `runtime-v2026.7.1-forgeuard.4`) | The full supervised server image: s6-overlay supervises the dashboard and per-profile gateways (they restart on crash and come back after `docker restart` / host reboot), web dashboard UI, Playwright/Chromium browser tools, messaging + Matrix adapters baked in. Identical layout to upstream's Docker image (`/opt/hermes` immutable install tree, `/opt/data` state volume). |
| **cli** | `cli-latest`, `cli-<git-sha>`, `cli-<release>` | A lean interactive image for **distrobox** (or plain `docker run -it`) use: CLI + TUI + browser tools, no dashboard/gateway server stack, no supervisor. Distrobox's host-integration packages are pre-baked so the first `distrobox enter` is instant. Messaging adapters are not baked in; Hermes lazy-installs them into your `~/.hermes/lazy-packages` on first use. |

Prefer immutable tags (`runtime-<release>`) for deployments you care about;
the `-latest` tags are convenient for testing but drift forward on every fork
release. Both images carry the `com.forgeguard.hermes.prebaked=1` OCI label.

## Persistent server install (`runtime-*`)

```bash
docker pull ghcr.io/forgeguard/hermes-agent:runtime-latest
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
  ghcr.io/forgeguard/hermes-agent:runtime-latest gateway run
```

What each piece buys you:

- **`--restart unless-stopped`** restarts the container after crashes and
  host reboots; **inside** the container s6-overlay independently supervises
  the dashboard and per-profile gateway processes, and a boot reconciler
  restores every gateway that was running before the restart. A container
  `HEALTHCHECK` tracks the dashboard's public `/api/status` endpoint (it
  reports healthy-no-op when `HERMES_DASHBOARD` is unset, so one-shot/CLI
  containers never flap).
- **`-v ~/.hermes:/opt/data`** is ALL of your durable state — config,
  sessions, memory, skills, profiles, logs. The image itself is immutable;
  upgrading = pull a newer tag and recreate the container, state survives.
- **Auth is mandatory** on the container's non-loopback dashboard bind (as of
  upstream `v2026.7.1` a 0.0.0.0-bound dashboard refuses to start without a
  provider). Set the basic-auth pair above (the `_SECRET` keeps sessions
  valid across restarts) or `HERMES_DASHBOARD_OAUTH_CLIENT_ID`. If the
  container exits immediately, check `docker logs hermes` for
  `Refusing to bind dashboard to 0.0.0.0`.
- **`HERMES_UID`/`HERMES_GID`** remap the in-container user to the owner of
  your bind mount — use these instead of `docker run --user` (the image boots
  as root so its setup hook can chown the volume, then drops privileges).
- **Port 9119** is the dashboard/gateway backend — the same endpoint the
  Hermes Desktop app's **Client Mode** connects to (enter
  `http(s)://<host>:9119` in the connection dialog and sign in with the
  provider you configured). The OpenAI-compatible API server on `8642` is
  separate and optional.

First-time setup: `docker exec -it hermes hermes setup` (the image's exec
shim drops root to the runtime user automatically), or drive everything from
the web dashboard / Desktop Client Mode.

Everything else — compose examples, profiles, log routing, resource limits,
audio — behaves exactly like upstream's image:
[Docker user guide](../../website/docs/user-guide/docker.md). Substitute
`ghcr.io/forgeguard/hermes-agent:runtime-latest` for
`nousresearch/hermes-agent:latest` in any command there.

## Distrobox install (`cli-*`)

```bash
distrobox create --image ghcr.io/forgeguard/hermes-agent:cli-latest --name hermes
distrobox enter hermes
hermes            # first run walks you through `hermes setup`
```

Notes:

- Your home directory is shared with the container (distrobox's default), so
  Hermes state lands in your own `~/.hermes` and survives container
  recreation and image upgrades. Upgrade = `distrobox rm hermes` +
  re-create from a newer `cli-*` tag.
- The image pre-bakes distrobox's Debian host-integration package set and a
  pre-generated `en_US.UTF-8` locale, so the first `distrobox enter` skips
  distrobox-init's usual multi-minute dependency install.
- `hermes` is on `PATH` via a plain launcher shim; `/etc/profile.d/hermes.sh`
  exports the Playwright browser path and the lazy-install target for login
  shells.
- The install tree (`/opt/hermes`) is root-owned and read-only. Optional
  backends (messaging platforms, opt-in tool SDKs) lazy-install into
  `~/.hermes/lazy-packages` on first use — so `hermes gateway run` for e.g.
  Telegram works, it just fetches that adapter once.
- The image also works with plain Docker for one-off CLI use:
  `docker run -it --rm -v ~/.hermes:/root/.hermes ghcr.io/forgeguard/hermes-agent:cli-latest`.

## Which variant do I want?

- Running a **persistent agent a client connects to** (Desktop Client Mode,
  web dashboard, messaging platforms, scheduled jobs)? → `runtime-*`.
- Working **interactively in a terminal** on a Linux box/workstation and
  wanting host integration without installing the full dependency stack on
  the host? → `cli-*` via distrobox.
