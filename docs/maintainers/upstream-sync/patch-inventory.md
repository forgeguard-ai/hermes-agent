# Fork patch inventory (ForgeGuard fork)

The fork-patch re-verification checklist for [step 4 of the sync runbook](./sync-policy.md#4-resolve-conflicts-then-re-verify-the-fork-patch-checklist).
After merging an upstream tag, **explicitly re-verify every item below** is still
present and correct on the merged branch — a clean auto-merge can silently keep
the wrong side, and these are exactly the places most likely to matter to the
fork's own CI/release behaviour.

This inventory is deliberately specific: concise enough to maintain, detailed
enough to catch silent merge damage. Keep it current as the fork's patch set
evolves.

## CI / workflow guards

- [ ] **`contributor-check` upstream-only guard** — since the v2026.8.16 sync
      upstream ships the check as an *unguarded* reusable workflow
      (`.github/workflows/contributor-check.yml`, `workflow_call`-only); the
      fork guard lives at the **`ci.yml` call site**: the `contributor-check`
      job's `if:` includes `github.repository == 'NousResearch/hermes-agent'`.
      Verify no other workflow calls `contributor-check.yml` without a guard.
- [ ] **`docker-lint.yml` direct linter invocation** — the forgeguard-ai org's
      actions policy only allows GitHub-authored / org-owned /
      Marketplace-verified actions, and `ci.yml` calls this file as a reusable
      workflow, so a disallowed action here fails the ENTIRE CI run at startup
      (nothing ran on the fork until this was fixed, 2026-08-12). The fork
      runs hadolint (digest-pinned 2.12.0 container) and shellcheck (apt) as
      plain commands with behaviour held equivalent to upstream's
      `hadolint/hadolint-action` + `ludeeus/action-shellcheck` (same
      `.hadolint.yaml`, same severity threshold, extension + shebang file
      discovery). An upstream sync touching this file conflicts here; keep the
      direct invocations and port upstream's substantive changes (versions,
      configs, new lint targets) into them.
- [ ] **`build-runtime-images.yml`** exists at
      `.github/workflows/build-runtime-images.yml`, still matrixes over
      `target: [runtime, cli]`, and pushes both `runtime-*` and `cli-*` tags to
      `ghcr.io/forgeguard-ai/hermes-agent`. It must have **no `push:` trigger** —
      `release-on-merge.yml` is the single merge-time builder (a push trigger
      here re-introduces double builds on qualifying merges).
- [ ] **`build-desktop-client.yml`** exists at
      `.github/workflows/build-desktop-client.yml` with both Linux and macOS
      jobs, and **no `push:` trigger** (same single-builder rule as above).
- [ ] **`release-on-merge.yml`** exists at
      `.github/workflows/release-on-merge.yml`, calls `build-runtime-images.yml`
      with `version:` (not the retired `extra_tag`), still carries its
      release gating (`no-release` label + release-relevant-paths check in
      `compute-version`), and still names releases after the `pyproject.toml`
      product semver (`v<hermes-version>`, `-forgeguard.<n>` suffix only on
      re-cuts of an already-released version; scheme since Hermes 0.19.0) —
      `FORK_UPSTREAM_BASE` feeds only the release-notes "Upstream release"
      line, not the tag.
- [ ] ~~**`upload_to_pypi.yml` guards (all three jobs)**~~ — **retired at the
      v2026.8.16 sync.** Upstream retired the brew + pip/PyPI wheel channels in
      0.20.0 and deleted the workflow; the fork accepted the deletion. (Its
      `sign`-job lesson — an explicit `if:` bypasses `needs:`
      success-skip-propagation, so every job needs its own guard — lives on in
      the entries below.)
- [ ] **Upstream-only guards on the tag/schedule-triggered workflows** that would
      otherwise fire for real (or just burn scheduled runs) on the fork:
      `.github/workflows/deploy-site.yml` (`deploy-vercel` job),
      `.github/workflows/skills-index.yml` (BOTH the `build-index` job — guarded
      on `schedule` events so the twice-daily cron doesn't run on the fork — and
      the `trigger-deploy` job), and
      `.github/workflows/skills-index-freshness.yml` (its check job — the
      every-4h cron is upstream-infrastructure-only). Pattern:
      `if: github.repository == 'NousResearch/hermes-agent'` (combined with the
      job's own other conditions via `&&`). **Audit every job in a multi-job
      workflow file individually** — a guard on the first job in a dependency
      chain does not automatically protect a downstream job that has its own
      explicit `if:`. As of the v2026.7.20 sync the guarded set also includes:
      `.github/workflows/js-autofix.yml` (BOTH jobs, `generate-patch` and
      `apply-patch` — the autofix bot pushes with an upstream `AUTOFIX_BOT_PAT`
      and auto-squash-merges its PRs, neither of which exists nor is wanted on
      the fork; `apply-patch` has its own explicit `if:` so it needs its own
      guard) and `.github/workflows/osv-scanner.yml` (BOTH the `scan` job and
      its `emit-status` wrapper job, guarded only for `schedule` events —
      `github.event_name != 'schedule' || github.repository == 'NousResearch/hermes-agent'` —
      so the `workflow_call` from `ci.yml` and manual dispatch still run on the
      fork while the weekly cron stays upstream-only). As of the v2026.8.16
      sync the guarded set also includes: `.github/workflows/install-e2e.yml`
      (ALL THREE jobs — `pick-releases`, `update`, `installer`; the twice-daily
      cron and the version-tag trigger exercise upstream install/update
      channels, and the fork's own release tags match its `v*` tag patterns;
      `update`/`installer` carry explicit `if:` conditions and so need their
      own guards) and `.github/workflows/publish-e2e-evidence.yml` (`publish`
      job — publishes E2E evidence via the upstream-owned
      `GH_IMAGE_SESSION_TOKEN` PAT). `ci-review-comment.yml` and
      `label-rerun.yml` are `GITHUB_TOKEN`-only and deliberately left
      UNguarded — they enhance fork PRs. `docker.yml` and
      `deploy-site.yml`'s `deploy-docs` job carry upstream-side repository
      guards of their own; verify they remain guarded but do not re-add fork
      copies.
- [ ] **`ci.yml` PR concurrency** — the fork adds a `concurrency:` group with
      `cancel-in-progress` for pull-request refs (never cancelling `main` runs);
      keep it through the merge.
- [ ] **`workflow_call` upload/push gating** — in both
      `build-desktop-client.yml`'s "Upload Linux/macOS installers" steps and
      `build-runtime-images.yml`'s "Push image to GHCR" step, the `if:` must gate
      on `inputs.upload` / `inputs.push` directly. **Do not** reintroduce
      `github.event_name == 'workflow_call'` — `github.event_name` inside a
      reusable workflow is always the *caller's* triggering event (e.g.
      `pull_request` for `release-on-merge.yml`), never literally
      `"workflow_call"`. This exact regression silently skipped every installer
      upload and image push for two releases before it was caught (2026-07-02) —
      the jobs report "success" either way, so this only surfaces by checking the
      *individual step* conclusions, not the job conclusion.

## Docker / build structure

- [ ] **Dockerfile multi-target structure intact** — the fork's `Dockerfile`
      declares `base` / `toolchain` / `venv-runtime` / `venv-cli` / `cli` /
      `runtime` stages, with **`runtime` as the LAST stage** (a target-less
      `docker build .` — compose, tests/docker fixture — must keep producing the
      full supervised image), compilers confined to `toolchain`, the
      `com.forgeguard.hermes.prebaked=1` label on both published targets, and the
      `HEALTHCHECK` + `docker/healthcheck.sh`, `docker/cli/hermes-shim.sh` and
      `docker/cli/profile.sh` still present. If upstream restructures its
      single-stage Dockerfile, re-apply their substantive change inside the
      matching stage rather than reverting the split.

## Desktop app

- [ ] ~~**`apps/desktop/vite.config.ts`** test scope fix~~ — **retired at the
      v2026.7.20 sync.** Upstream's `apps/desktop/vitest.config.ts` now defines
      separate `react-ui` (`src/**/*.test.{ts,tsx}`) and `electron-native`
      projects, absorbing the fork's scoping fix, and the electron `.test.cjs`
      node:test suites were ts-ified into vitest suites. `vite.config.ts` is
      upstream-identical again; verify it has NOT re-grown a fork `test:` block.
- [ ] **`apps/desktop/package.json` `"version"`** tracks the Hermes product
      version (`pyproject.toml`), not upstream's stale desktop version — bump it
      (and the `"apps/desktop"` entry in the root `package-lock.json`) on every
      sync that changes the product version.
- [ ] **`apps/desktop/src/app/settings/gateway-settings.test.tsx`** carries the
      fork's `localDesc` wording ("… Works offline.", no "This is the default")
      in its two label assertions — the fork is client-mode-first, so upstream's
      wording (re-)appearing here means an auto-merge silently restored
      upstream's string; re-adapt the assertions, not the fork's i18n.
- [ ] **`apps/desktop/package.json`** has a top-level `"homepage"` field
      (`https://github.com/forgeguard-ai/hermes-agent#readme`) — required by
      electron-builder's Linux `deb` target; its absence fails `dist:linux` with
      `Please specify project homepage`.

## Carried runtime patches (verify by running their test files)

These fork fixes live inside upstream-owned Python/TS files and are the most
likely to be silently dropped by a clean auto-merge. Each has a test file that
IS the verification hook — run it on the merged branch instead of eyeballing:

- [ ] **`hermes_cli/auth.py` — "no-key" deploy sentinel is a placeholder**
      (fork v0.19.2). `"no-key"` in the placeholder-secret set;
      `"no-key-required"` deliberately stays out. Verified NOT upstream as of
      v2026.8.16 (the fork test fails on a clean upstream checkout).
      Test: `tests/hermes_cli/test_auth_usable_secret.py`.
- [ ] **custom:`<name>` slug handling** (fork v0.19.3):
      `hermes_cli/providers.py::canonicalize_provider_slug`, the
      `custom:custom` bare-bucket collapse in `hermes_cli/web_server.py`'s
      `_normalize_main_model_assignment` (upstream preserves *named* unresolved
      slugs verbatim — keep both behaviors), `resolve_provider`'s bare-slug
      resolution in `auth.py`, and the `/api/providers/validate`
      custom-endpoint key probe. `canonicalize_provider_slug` does not exist
      upstream (the fork test file cannot even import there).
      Test: `tests/hermes_cli/test_custom_provider_slug_canonicalization.py`.
- [ ] **mem0 embedder-bearer scoping** (fork v0.19.1):
      `plugins/memory/mem0/_backend.py` (scoped Ollama-client Authorization
      patch), `_oss_providers.py`, `_setup.py`. Verified NOT upstream as of
      v2026.8.16. Tests: `tests/plugins/memory/test_mem0_backend.py` +
      `test_mem0_setup.py`.
- [ ] **Desktop connection cluster runtime patches** — TLS bypass threading
      (`probeConnectionConfig(url, allowInvalidCertificate)`, the
      `hostAllowsInvalidCertificate` fallback inside `fetchJson`/
      `fetchPublicJson`, `installCertificateBypass()`), saved-endpoint history
      (`savedRemotes`), first-run choice IPC + gates in
      `apps/desktop/electron/main.ts`, and the first-run gate + heartbeat
      liveness (`gateway.ping`, fork-added method in `tui_gateway/server.py`)
      + bounded initial-connect retries in
      `apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts`.
      Tests: `apps/desktop/src/app/gateway/hooks/use-gateway-boot.test.tsx`
      (fork cases), `apps/desktop/electron/first-run-choice.test.ts`,
      `apps/desktop/electron/connection-config.test.ts`,
      `tests/tui_gateway/test_gateway_ping.py`.
- [ ] ~~**Desktop voice mic re-arm** (`use-voice-conversation.ts`)~~ —
      **retired-superseded at the v2026.8.16 sync.** Upstream's live-speech
      rewrite (`settleAfterSpeech` → `pendingStartRef` → loop-effect
      `startListening`) fixes the dead-mic class structurally and absorbed the
      fork's no-early-return in the tool-only branch. The fork keeps its
      regression scenario as coverage upstream does not have:
      `apps/desktop/src/app/chat/composer/hooks/use-voice-conversation.rearm.test.tsx`
      (seams adapted to the new hook; verify it stays green).

## Docs / instructions

- [ ] **`README.md`** still surfaces the ForgeGuard fork identity below the
      title/badges block (the compact fork alert linking to `docs/site/` and the
      fork pages).
- [ ] **`docs/site/`** and **`docs/maintainers/`** still contain the ForgeGuard
      documentation overlay: the user-facing pages under `docs/site/` and this
      runbook (plus [sync policy](./sync-policy.md) and
      [conflict resolution](./conflict-resolution.md)),
      [release process](../release/release-process.md),
      [review](../development/review.md), and
      [graphify-refresh](../development/graphify-refresh.md) under
      `docs/maintainers/`.
- [ ] **`AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`** still have
      the "ForgeGuard Fork — Additions Below This Line" section / pointer content
      intact (`AGENTS.md` is the source of truth; the other two are thin pointers
      to it), and their runbook links point at
      `docs/maintainers/upstream-sync/sync-policy.md`.

## Marker

- [ ] **`FORK_UPSTREAM_BASE`** — not a merge-conflict risk (you rewrite it in
      step 6 of the [sync policy](./sync-policy.md#6-update-fork_upstream_base)),
      but don't forget it.

## Related

- [Sync policy](./sync-policy.md)
- [Conflict resolution](./conflict-resolution.md)
- [Release process](../release/release-process.md)
