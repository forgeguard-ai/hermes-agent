# Upstream sync: merge NousResearch/hermes-agent v2026.7.20 into the fork (2026-07-22)

Checkbox-tracked working copy of the approved sync plan, per the fork's
plan-saving rule (`AGENTS.md` → "Plan-Saving Rule"). Update checkboxes **in
place** as work completes — this file is the resumable state for any agent or
human picking the sync up mid-flight, and the handoff record for local
validation before the final dev → main merge.

## Context

- Fork base: **v2026.7.1** (`FORK_UPSTREAM_BASE`). Target: **v2026.7.20**
  ("Quicksilver", product version 0.19.0, ~2,245 commits, ~2,465 files changed,
  +300k/−36k). Upstream cut intermediate tags v2026.7.7 / v2026.7.7.2; per
  [sync policy](../maintainers/upstream-sync/sync-policy.md) we merge the
  **newest tag in ONE real merge** (never squash/rebase, never stepwise).
- Work happens on `dev` (user-directed deviation from the runbook's
  `sync/upstream-<TAG>` branch; cloud session branch
  `claude/fork-sync-upstream-release-41pg7g` publishes to `dev` via
  `git push origin HEAD:dev`). Final landing is a **real merge** dev → main
  after local validation; that merge triggers `release-on-merge.yml`
  (→ `v2026.7.20-forgeguard.1`, ghcr runtime/cli images, 5 desktop installers)
  and the external docs publish off `.forgeguard/docs.yml`.
- State discovered at planning time: fork `main` = `1d7b372`, `dev` = `5d5874f`
  (main + docs-validate-on-dev commit); local clone shallow, no upstream
  remote; upstream `v2026.7.20^{commit}` = `3ef6bbd201263d354fd83ec55b3c306ded2eb72a`,
  `v2026.7.1^{commit}` = `7c1a029553d87c43ecff8a3821336bc95872213b`.
- Governing docs: `docs/maintainers/upstream-sync/{sync-policy,patch-inventory,conflict-resolution}.md`,
  `docs/maintainers/release/release-process.md`.

## Phase 0 — Plan capture

- [x] Save this plan to `docs/agent-plans/2026-07-22-upstream-sync-v2026.7.20-plan.md`,
      commit, push to `dev`.

## Phase 1 — Environment prep (cloud)

- [x] `git fetch origin --unshallow --tags` (full fork history; monitor disk).
- [x] `git remote add upstream https://github.com/NousResearch/hermes-agent.git`
      (read-only; TLS via `/root/.ccr/ca-bundle.crt` if needed — never disable
      verification).
- [x] `git fetch upstream tag v2026.7.20 tag v2026.7.1 --no-tags` (only the two
      needed tags — disk-conscious deviation from the runbook's blanket
      `--tags`).
- [x] Verify `git rev-parse 'v2026.7.20^{commit}'` == `3ef6bbd2...` and
      `git log -1 v2026.7.20` looks like Quicksilver.
- [x] **GATE:** `git merge-base HEAD 'v2026.7.20^{commit}'` ==
      `7c1a029...` (the v2026.7.1 commit). If not → STOP, investigate.
- [x] Confirm repo allows merge commits (`allow_merge_commit`) so the final
      dev→main PR can land as a real merge.

## Phase 2 — The merge

- [x] `git merge v2026.7.20 --no-edit -m "Merge upstream v2026.7.20 into fork dev"`
      → single real merge commit M (parents: dev tip + `3ef6bbd`). Resolve all
      conflicts inside M (Phase 3) before committing.
- [x] Lineage invariants honored: no squash/rebase/amend of M ever; final
      dev→main is a real merge.

## Phase 3 — Conflict resolution (keep upstream substance, re-apply fork delta)

- [x] Fork-only workflows kept verbatim: `build-runtime-images.yml`,
      `build-desktop-client.yml`, `release-on-merge.yml`, `docs-validate.yml`
      (confirm upstream added no same-named files).
- [x] Guarded upstream workflows: take upstream structure, re-graft
      `if: github.repository == 'NousResearch/hermes-agent'` on **every job
      individually** — `upload_to_pypi.yml` (build/publish/**sign** — sign has
      its own `if:`), `deploy-site.yml` (deploy-vercel), `skills-index.yml`
      (build-index on schedule + trigger-deploy), `skills-index-freshness.yml`,
      `ci.yml` contributor-check.
- [x] `ci.yml` fork PR-concurrency block preserved.
- [x] **Audit ALL workflows in the merged tree (incl. brand-new upstream ones)
      for `push:`/`schedule:`/tag/registry triggers that would fire on the
      fork; guard before first push of the merged tree.** Record new guards in
      patch-inventory.md.
- [x] Dockerfile: fork 6-stage split kept (`base`/`toolchain`/`venv-runtime`/
      `venv-cli`/`cli`/`runtime`, runtime LAST, prebaked labels, HEALTHCHECK);
      upstream changes mapped into matching stages.
- [x] Semantic check: `hermes serve`-era changes vs `docker/healthcheck.sh` +
      `docker/cli/hermes-shim.sh` + `docker/cli/profile.sh`.
- [x] AGENTS.md: upstream body adopted; fork `HERMES_OFFLINE_*` exception
      re-grafted into upstream's env-var guidance (fork content INSIDE the
      inherited section — highest silent-loss risk); fork tail carried forward
      verbatim; `CLAUDE.md` + `.github/copilot-instructions.md` thin-pointer
      tails intact.
- [x] README.md: upstream README + ForgeGuard identity block re-inserted below
      title/badges (reference: commit `ed218a8`).
- [x] `pyproject.toml` + `uv.lock`: upstream wholesale (incl.
      `version = "0.19.0"`); `uv lock --check` passes.
- [x] `apps/desktop/vite.config.ts`: `test.include: ['src/**/*.test.{ts,tsx}']`
      re-applied on upstream's config shape.
- [x] `apps/desktop/package.json`: `"homepage"` field re-applied; upstream
      deps/lockfile taken.
- [x] i18n files resolved per Phase 4 Text Size verdict.
- [x] Any conflict far outside the patch-inventory surface → stopped and
      investigated before resolving.

## Phase 4 — Preserve vs supersede (fork features)

- [x] **Text Size vs upstream UI scale** analyzed
      (`git show 'v2026.7.20^{commit}':<path>`, `git log -p -S`). Verdict
      recorded here + `docs/site/fork/forgeguard-changes.md` +
      patch-inventory.md. Rule: upstream persisted-scale-with-Settings-UI ⇒
      supersede (adopt upstream, delete fork zoom store/IPC/keys/tests, port
      fork-only niceties as minimal delta); wheel-zoom-only ⇒ keep fork slider
      rewired onto upstream plumbing. ONE persistence source only.
      - Verdict: **superseded — upstream adopted.** Upstream v2026.7.20 ships
        the same feature evolved (same `hermes:desktop:zoomLevel` key, same
        1.2^level scale, `electron/zoom.ts` funnel, UI Scale presets row,
        resize re-assert hardening, half-step Ctrl/Cmd shortcuts). All fork
        Text Size code/i18n/tests removed; zero migration needed for users.
- [x] Banner version label: ForgeGuard identity re-applied to upstream's banner
      code path; fork banner tests green.
- [x] Offline gate: `hermes_cli/offline.py` present; call-site wiring verified
      against upstream startup/`serve` restructure; offline tests green.

## Phase 5 — Patch-inventory re-verification (grep, not eyeball)

- [ ] Every checkbox in `docs/maintainers/upstream-sync/patch-inventory.md`
      re-verified on the merged tree.
- [ ] Especially: `inputs.upload`/`inputs.push` gated **directly** in both build
      workflows — no `github.event_name == 'workflow_call'` regression.
- [ ] patch-inventory.md updated for anything this sync changed.

## Phase 6 — Validation (cloud)

- [x] Venv recreated (`uv sync` → `.venv`).
- [ ] `scripts/run_tests.sh` full suite; every failure triaged:
      upstream-debt (reproduces in clean `git worktree add ... v2026.7.20`)
      listed for the PR body vs merge regression (fixed before done).
      Worktree removed after.
      - Triage notes: _pending_
- [ ] `ui-tui`: npm test + typecheck.
- [ ] `apps/desktop`: vitest via repo-root vitest; repo typecheck.
- [ ] `uv lock --check`.
- [ ] `python scripts/docs/validate_docs.py` + Docusaurus website build
      (mirrors `docs-site-checks.yml`).
- [ ] hadolint (if available) / else defer.
- [ ] `scripts/graphify-refresh.sh` + commit refreshed
      `graphify-out/GRAPH_REPORT.md`.

Deferred to local (user): full Docker image builds + `tests/docker` fixture (if
no daemon in cloud), desktop packaging + interactive smoke (zoom/Text Size
outcome, Capabilities page, i18n), offline mode E2E against the ForgeGuard
deployment manager, macOS checks.

## Phase 7 — Docs updates

- [ ] `docs/site/fork/compatibility.md` version table → base `v2026.7.20`,
      release line `v2026.7.20-forgeguard.<n>`, product `0.18.0` → `0.19.0`.
- [ ] `docs/site/fork/forgeguard-changes.md` → Text Size verdict,
      absorbed/dropped patches, new guards.
- [ ] `docs/site/operations/releases-and-upgrades.md` + release-notes heredoc in
      `release-on-merge.yml`: v2026.7.1-era auth callout reviewed against
      0.19.0 (update BOTH places if stale).
- [ ] `docs/maintainers/development/review.md` refreshed for upstream's desktop
      restructure.

## Phase 8 — FORK_UPSTREAM_BASE + version

- [ ] `echo "v2026.7.20" > FORK_UPSTREAM_BASE`, committed as
      `chore: bump FORK_UPSTREAM_BASE to v2026.7.20`.
- [ ] `release-on-merge.yml`'s `grep -m1 '^version' pyproject.toml` verified to
      yield `0.19.0` on the merged tree.

## Phase 9 — Commit/push structure on shared dev

No amend/force-push after anything is pushed. Sequence:

- [x] 1. `docs:` this plan file (pushed immediately).
- [x] 2. Merge commit M (pushed only after the Phase 3 workflow-trigger audit).
- [ ] 3. `fix(sync): ...` single-topic fixups (inventory pass + test triage).
- [ ] 4. `chore: bump FORK_UPSTREAM_BASE to v2026.7.20`.
- [ ] 5. `docs(fork): update compatibility/changes/release docs for v2026.7.20`.
- [ ] 6. `chore: refresh Graphify report` (last).

## Phase 10 — Final phase (user-driven, local)

- [ ] User local validation: pull `dev`; rerun `scripts/run_tests.sh` (or
      targeted areas), desktop smoke, Docker builds, offline-mode E2E.
- [ ] PR dev→main: `gh pr create --repo forgeguard-ai/hermes-agent --base main
      --head dev --title "sync: merge upstream v2026.7.20 into fork main"` —
      body lists conflict decisions, Text Size verdict, triaged upstream-debt
      failures, patch-inventory confirmation. NO `no-release` label; never an
      upstream branch as head.
- [ ] Merge with a **real merge only**:
      `gh pr merge <N> --merge --delete-branch=false`.
- [ ] Release verification (check **step**-level conclusions):
      `release-on-merge.yml` green; version `v2026.7.20-forgeguard.1` (or next
      free `.N`); installer-upload + GHCR-push steps `success` (not `skipped`);
      all 5 assets (`.deb`, `.AppImage`, `.rpm`, `.dmg`, `.zip`); both
      `runtime-`/`cli-` tags pull from `ghcr.io/forgeguard-ai/hermes-agent`;
      release title shows Hermes v0.19.0.
- [ ] Docs publish verified: docs-validate green on main; published overlay at
      `/projects/hermes-agent/docs` shows the v2026.7.20 compatibility table.
- [ ] Cleanup: fast-forward `dev` to `main`; tick remaining checkboxes here in a
      final small commit.

## Decisions & findings log (2026-07-22, cloud session)

- 23 conflicted files, all inside the predicted surface (root docs + desktop).
- Connection-mode/onboarding cluster: fork's client-mode-first onboarding,
  connection-mode dialog, first-run local-vs-remote choice, TLS bypass for
  self-signed certs, saved-endpoint history, and on-demand URL probe were
  **preserved** on top of upstream's ts-ified electron layer and new
  "Hermes Cloud connection mode" (both coexist; cloud connections are not
  recorded in the endpoint history; a saved cloud connection bypasses the
  first-run chooser).
- `desktop-controller.tsx` retired upstream; fork's dialog mount + deep-link
  branch re-homed into `src/app/contrib/wiring.tsx` and
  `src/app/contrib/hooks/use-desktop-integrations.ts`.
- `electron/first-run-choice.cjs` (+test) converted to `.ts` (upstream's
  electron tree is now tsc-typechecked + vitest-run; `.cjs` would fail both).
- New upstream workflows guarded for the fork: `js-autofix.yml` (both jobs;
  upstream bot PAT + auto-squash-merge) and `osv-scanner.yml` weekly cron
  (schedule-only guard). Recorded in patch-inventory.md.
- Desktop package version bumped 0.18.0 → 0.19.0 (fork convention: track the
  Hermes product version; upstream leaves it at 0.17.0) in
  `apps/desktop/package.json` + root `package-lock.json`.
- after-pack ad-hoc signing + `codesign --verify` gate re-applied onto
  upstream's renamed `after-pack.mjs`; upstream's new `afterSign:
  scripts/notarize.mjs` no-ops without Apple creds (compatible).
- `pyproject.toml`/`uv.lock` = upstream byte-identical; version 0.19.0;
  `release-on-merge.yml` version grep verified.
- Offline-mode + banner identity test files pass on the merged tree.

## Key risks & mitigations

- New upstream workflow fires on first dev push → pre-push `on:` audit (Phase 3).
- Wrong merge-base after unshallow → hard gate (Phase 1).
- Dual zoom persistence flapping → single-source verdict (Phase 4).
- Silent healthcheck/shim breakage from `hermes serve` → explicit inspection.
- Squash-only repo setting → checked up front (Phase 1).
- `docs/plans/` (upstream) vs `docs/agent-plans/` (fork) → this file stays here.
- Disk allowance → fetch only needed tags; remove triage worktree; monitor `df`.
