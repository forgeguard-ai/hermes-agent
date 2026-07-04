# Runtime Images, Desktop Client Mode & Fork Publishing Plan (2026-07-03)

Fork-scoped work plan for `ForgeGuard/hermes-agent`. Branch:
`claude/hermes-deployment-actions-optimization-37xs93` (from `origin/main` @ `cd969db`).
Checkboxes are the resumable state — update in place as items complete.

## Goals

1. **Desktop client (priority #1):** Client Mode (connect to a remote/local
   Hermes dashboard endpoint) becomes the default experience; local mode stays
   fully supported but de-emphasized. Initial connection and reconnection get
   real resilience (retry/backoff, heartbeat, saved endpoints).
2. **Runtime images:** split the single published image into two publicly
   usable variants — a full supervised server image (`runtime-*`) and a lean
   CLI/distrobox image (`cli-*`) — from one multi-stage Dockerfile.
3. **Fork publishing:** consolidate fork-specific docs under
   `docs/forgeguard-fork/`, add a fork section near the top of the README, and
   move to neutral, self-describing artifact names (tags, workflow names,
   labels).
4. **Actions hygiene:** remove duplicate builds, gate release-on-merge, stop
   fork-irrelevant scheduled jobs, add PR CI concurrency. Keep all
   correctness CI (tests/lint/typecheck) untouched.

## Step 0

- [x] Branch created from `origin/main`; this plan saved before implementation.

## Phase 1 — Desktop: client-mode default + connection resiliency

Files: `apps/desktop/electron/main.cjs`, `electron/first-run-choice.cjs`,
`src/components/connection-mode-dialog.tsx`, `src/store/connection-mode.ts`,
`src/app/gateway/hooks/use-gateway-boot.ts`,
`apps/shared/src/json-rpc-gateway.ts`, `src/i18n/en.ts`,
`src/components/boot-failure-overlay.tsx`.

- [ ] First-run chooser: Client Mode card primary/preselected; Local card
      secondary ("Advanced"); invert `i18n/en.ts` framing (client
      "recommended"; local no longer "the default"). Keep `firstRunChoiceRequired`
      bypasses (existing local installs boot straight to local). Keep the
      persisted parse-fallback `'local'` in `main.cjs` (corrupt/absent config on
      an existing install must not flip a local user to remote).
      `resolveRemoteBackend` precedence unchanged.
- [ ] Initial-connect retry: wrap `boot()`'s single `gateway.connect()` in
      bounded backoff (~4 attempts, 1→2→4→8s), re-minting the WS URL each
      attempt (OAuth tickets are single-use); CONNECTING overlay stays up during
      retries; `FIRST_RUN_CHOICE_REQUIRED` sentinel path unchanged.
- [ ] Heartbeat: periodic lightweight RPC (~30s, booted/visible only; pick a
      cheap method from `tui_gateway/server.py`); missed deadline → force-close
      → existing reconnect path.
- [ ] Saved endpoints: `connection.json` `remote{}` → `remotes[]` +
      `activeRemote` (old shape read compatibly); minimal picker in the
      connection dialog.
- [ ] Tests gate: run `apps/desktop/electron/**/*.test.cjs` (node:test) as a
      blocking CI step in `build-desktop-client.yml`; extend
      `connection-mode-dialog.test.tsx`, `use-gateway-boot.test.tsx`,
      `first-run-choice.test.cjs` for the new default + initial retry.
- [ ] Update `website/docs/user-guide/desktop.md`.

## Phase 2 — Runtime image split (one Dockerfile, two targets)

- [ ] Restructure `Dockerfile` into named stages: `base` (debian 13 + uv/node +
      runtime system deps) → `venv-builder` (gcc/g++/cmake + `uv sync`; venv
      copied out — compilers reach neither final image) → final targets:
- [ ] **`runtime` target** (tags `runtime-<sha>` / `runtime-latest` /
      `runtime-<ver>`): current full behavior (s6-overlay + services, dashboard
      /gateway supervision, web + ui-tui builds, Playwright/Chromium, `/init`
      entrypoint, `VOLUME /opt/data`) minus in-image compilers. Bake in the
      dashboard login-route fix (install tree is sealed read-only — runtime
      patching is impossible by design). Verify `plugins.dashboard_auth.basic`
      importable + dashboard honors `dashboard.basic_auth` from config.yaml.
      Add `HEALTHCHECK` (status probe honoring `HERMES_DASHBOARD`, graceful
      when disabled).
- [ ] **`cli` target** (tags `cli-<sha>` / `cli-latest` / `cli-<ver>`): no
      s6-overlay, no `web/` dashboard frontend build, no `--extra matrix`
      (drops the libolm compile chain); keeps ui-tui + Playwright/Chromium;
      plain login-shell-friendly entrypoint; distrobox host-integration
      packages pre-baked (verify list against distrobox docs/`distrobox-init`).
      Contract: working `apt` + `ca-certificates`; plain non-s6 `hermes` shim
      in `/usr/local/bin` usable by any uid; `PLAYWRIGHT_BROWSERS_PATH`,
      `HERMES_LAZY_INSTALL_TARGET=$HOME/.hermes/lazy-packages`, PATH exported
      via `/etc/profile.d/hermes.sh`; `/opt/hermes` world-readable root-owned;
      no desktop stack.
- [ ] Prebaked marker label on both targets: `com.forgeguard.hermes.prebaked=1`.
- [ ] Rename `.github/workflows/build-adm-runtime-image.yml` →
      `build-runtime-images.yml` ("Build Runtime Images (GHCR)"); matrix over
      `target: [runtime, cli]`, per-target tags, separate cache refs
      (`buildcache-runtime-amd64`, `buildcache-cli-amd64`).
      `release-on-merge.yml` passes per-target `extra_tag`
      (`runtime-<version>`, `cli-<version>`).
- [ ] Tag migration: stop pushing the legacy `adm-*` tags (existing GHCR tags
      remain but go stale); release-notes template updated to the new tags.
- [ ] Testing: `tests/docker/` runs against `runtime` (unchanged contract);
      minimal `cli` smoke (`hermes --version`, `hermes config check`,
      distrobox-package presence, shim on PATH). hadolint/docker-lint stay
      green.

## Phase 3 — Fork publishing: naming cleanup + README + docs/forgeguard-fork/

- [ ] Naming sweep: replace legacy tooling-specific names in current file
      contents with neutral, self-describing wording ("ForgeGuard runtime
      image", "remote/self-hosted deployments", "downstream deployment
      tooling") across: `build-desktop-client.yml` comments,
      `release-on-merge.yml` comments + release-notes template, the upstream
      sync runbook, `website/docs/user-guide/docker.md` + `desktop.md`, and
      the 2026-07-02 fork-consolidation plan doc. (Git history is immutable
      and out of scope.)
- [ ] README: new fork section directly below the Hermes title/logo — what the
      fork is (tracks upstream tagged releases, MIT, attribution), image
      quickstarts for both variants, desktop installers pointer, link to
      `docs/forgeguard-fork/`. Move the existing "Docker (ForgeGuard fork)"
      quickstart content into it and delete the old lower section.
- [ ] `docs/forgeguard-fork/README.md` — index of fork docs.
- [ ] `docs/forgeguard-fork/upstream-sync-skill.md` — moved from
      `docs/fork-maintenance/` (update references in `CLAUDE.md`, `AGENTS.md`
      fork section, `.github/copilot-instructions.md`, workflow comments;
      leave a one-line pointer at the old path).
- [ ] `docs/forgeguard-fork/runtime-images.md` — public usage guide:
      persistent server install from `runtime-*` (`-v ~/.hermes:/opt/data`,
      `--restart unless-stopped`, `-p 9119`, required auth
      `HERMES_DASHBOARD_BASIC_AUTH_*`/OAuth, `gateway run`, upgrades) and
      distrobox install from `cli-*` (`distrobox create --image …:cli-latest`,
      `distrobox enter`, `hermes setup`).
- [ ] `docs/forgeguard-fork/releases-and-versioning.md` —
      `<upstream-base>-forgeguard.<n>` scheme, tag families, what
      release-on-merge does.

## Phase 6 — Actions optimization

- [ ] Remove `push: main` triggers from `build-runtime-images.yml` +
      `build-desktop-client.yml` (keep `workflow_call` + `workflow_dispatch`);
      `release-on-merge.yml` is the single merge-time builder.
- [ ] Release gating: skip when the merged PR has a `no-release` label OR
      touches no release-relevant paths (`apps/**`, `Dockerfile`, `docker/**`,
      `pyproject.toml`, `uv.lock`, `package*.json`, `ui-tui/**`, `web/**`,
      core Python — via `gh pr view --json files` in `compute-version`).
- [ ] Job-level `if: github.repository == 'NousResearch/hermes-agent'` guards
      on the schedule-run jobs in `skills-index.yml` (build job) and
      `skills-index-freshness.yml` (probe job). Keep `osv-scanner.yml` cron.
- [ ] `concurrency` + `cancel-in-progress: true` on `ci.yml` for PR refs only.
- [ ] Add every change here to the sync checklist in
      `docs/forgeguard-fork/upstream-sync-skill.md`.

## Verification

- [ ] `scripts/run_tests.sh` for touched Python; `npm run typecheck` matrix
      dirs; desktop vitest + `node --test apps/desktop/electron/*.test.cjs`.
- [ ] `hadolint Dockerfile` + `shellcheck` over `docker/` scripts.
- [ ] Build both image targets via `workflow_dispatch` of
      `build-runtime-images.yml` on this branch with `push=false` (runs
      `tests/docker/` against the built bytes).
- [ ] Desktop sanity via `npm run dev`: unreachable endpoint → initial backoff
      then overlay; reachable dashboard → client-mode connect → kill/restart
      dashboard → auto-reconnect.
- [ ] Naming sweep check: repo grep for legacy tooling names returns only
      benign hits (history excluded).
- [ ] Push to `origin claude/hermes-deployment-actions-optimization-37xs93`.
      No PRs to `NousResearch/hermes-agent` (fork policy).
