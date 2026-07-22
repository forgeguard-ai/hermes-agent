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

- [ ] **`contributor-check` upstream-only guard** — `.github/workflows/ci.yml`,
      the `contributor-check` job's `if:` includes
      `github.repository == 'NousResearch/hermes-agent'`.
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
- [ ] **Upstream-only guards on the tag/schedule-triggered workflows** that would
      otherwise fire for real (or just burn scheduled runs) on the fork:
      `.github/workflows/upload_to_pypi.yml` (all three jobs: `build`, `publish`,
      `sign` — `sign` has its own explicit `if:` that bypasses the default
      `needs:` success-skip-propagation, so it needs its own guard, not just one
      on `build`), `.github/workflows/deploy-site.yml` (`deploy-vercel` job),
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
      guard) and `.github/workflows/osv-scanner.yml` (`scan` job, guarded only
      for `schedule` events — `github.event_name != 'schedule' || github.repository == 'NousResearch/hermes-agent'` —
      so the `workflow_call` from `ci.yml` and manual dispatch still run on the
      fork while the weekly cron stays upstream-only). `docker.yml` and
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
- [ ] **`apps/desktop/package.json`** has a top-level `"homepage"` field
      (`https://github.com/forgeguard-ai/hermes-agent#readme`) — required by
      electron-builder's Linux `deb` target; its absence fails `dist:linux` with
      `Please specify project homepage`.

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
