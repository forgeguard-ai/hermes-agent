# Upstream sync: merge NousResearch/hermes-agent v2026.8.16 into the fork (2026-08-16)

Checkbox-tracked working copy of the approved sync plan, per the fork's
plan-saving rule (`AGENTS.md` → "Plan-Saving Rule"). Update checkboxes **in
place** as work completes — this file is the resumable state for any agent or
human picking the sync up mid-flight, and the handoff record for local
validation before the final dev → main merge.

## Context

- Fork base: **v2026.7.20** (`FORK_UPSTREAM_BASE`); fork product version
  **0.19.3** (fork-only re-cuts v0.19.1–v0.19.3 since the last sync). Target:
  **v2026.8.16** (product **0.20.2**). The window spans four upstream releases
  — v2026.7.30 (0.19.1), v2026.8.3 (0.20.0 "Herald"), v2026.8.13 (0.20.1),
  v2026.8.16 (0.20.2) — ~5,000+ commits. Per
  [sync policy](../maintainers/upstream-sync/sync-policy.md) we merge the
  **newest tag in ONE real merge** (never squash/rebase, never stepwise).
- **User decisions (2026-08-16):** (1) work happens on **`dev`** (recreated
  from `main` at `9f7ee31`; user-directed deviation from the runbook's
  `sync/upstream-<TAG>` naming — and the runbook is to be updated this sync to
  codify `dev` as the standard sync branch going forward). (2) This session
  **stops at an open, CI-green PR** dev → main; the user merges (real merge)
  after local validation. The merge into main triggers `release-on-merge.yml`
  → fork release **v0.20.2** (product semver from `pyproject.toml`; no fork
  `v0.20.*` tag exists, so plain tag, no `-forgeguard.<n>` suffix).
- State discovered at planning time: fork `main` = `9f7ee31`; last sync merge
  `fc8cbf5` with upstream parent `3ef6bbd201263d354fd83ec55b3c306ded2eb72a`
  (= the v2026.7.20 commit; present locally). Local clone shallow, no
  `upstream` remote. Container: Node 22.22.2 (upstream 0.20.x requires Node
  26), uv 0.8.17, Python 3.11.15 (satisfies upstream's new `>=3.11,<3.14`),
  ~30G free disk. No `gh` CLI — fork-side GitHub ops via the GitHub MCP
  server; upstream fetched via plain git HTTPS.
- Upstream 0.20.0 breaking/infra: **Node 26 required**; **brew + pip/PyPI
  channels retired** (upstream deleted `.github/workflows/upload_to_pypi.yml`);
  tool iteration limit 90→500; `compression.min_tail_user_messages`; major
  voice/TTS rework; desktop artifacts/plugin SDK/multi-window/SSH-remote; A2A
  protocol; iron-proxy egress firewall. Upstream `.github/workflows/` now has
  27 files (`contributor-check.yml` extracted as an *unguarded* reusable
  workflow — the fork guard lives at the `ci.yml` call-site `if:`; ~10
  workflows are brand-new and unaudited).
- Governing docs: `docs/maintainers/upstream-sync/{sync-policy,patch-inventory,conflict-resolution}.md`,
  `docs/maintainers/release/release-process.md`; structural template
  `docs/agent-plans/2026-07-22-upstream-sync-v2026.7.20-plan.md`.

## Supersession verdicts (probed upstream files at v2026.8.16 during planning)

| Fork patch | Upstream state | Verdict |
|---|---|---|
| `auth.py` "no-key" placeholder (0.19.2, `6e893d9`) | absent (placeholder set lacks `"no-key"`) | **Carry forward** onto upstream's restructured auth (profile-scoped `_scoped_key_env`) |
| custom:`<name>` slug fixes (0.19.3, `697c90e`+`20ac314`) | **partially converged** (`is_runtime_provider_routable` accepts `custom:*`) | Per-behavior truth-table classification (Phase 4b); carry only un-converged deltas |
| mem0 embedder-bearer scoping (0.19.1) | absent | **Carry forward** |
| Desktop voice mic re-arm (`use-voice-conversation.ts`, `1adf919`) | hook **rewritten** (`settleAfterSpeech` → `pendingStartRef` → loop-effect `startListening`) | **Likely superseded** — prove with the fork's regression test (Phase 4a) |
| `docker-lint.yml` direct hadolint/shellcheck (`788f161`) | upstream still uses org-policy-blocked actions | **Must preserve** fork rewrite; port upstream substantive changes into it; add missing patch-inventory entry |
| `upload_to_pypi.yml` guards | file deleted upstream | **Accept deletion**, retire inventory entry |

## Phase 0 — Plan capture

- [x] Save this plan to `docs/agent-plans/2026-08-16-upstream-sync-v2026.8.16-plan.md`,
      commit `docs:`, push to `dev` (docs-only; current tree's triggers known-safe).

## Phase 1 — Environment prep + gates (cloud)

- [x] `git fetch origin --unshallow` (full fork ancestry for a correct merge
      base; monitor disk).
- [x] `git remote add upstream https://github.com/NousResearch/hermes-agent.git`
      (read-only; TLS via the proxy CA bundle — never disable verification).
- [x] `git fetch upstream tag v2026.8.16 --no-tags` (only the target tag —
      disk-conscious deviation from the runbook's blanket `--tags`).
- [x] Verify tag: `git log -1 'v2026.8.16^{commit}'` looks like the 2026-08-16
      release; `git show 'v2026.8.16^{commit}':pyproject.toml | grep -m1 '^version'`
      → `0.20.2`.
- [x] **GATE (hard stop):** `git merge-base dev 'v2026.8.16^{commit}'` ==
      `3ef6bbd201263d354fd83ec55b3c306ded2eb72a`. Else STOP, investigate.
- [x] Confirm no pre-existing fork `v0.20.*` tag (expect plain `v0.20.2`).
- [x] Attempt Node 26 install (tarball → scratchpad, prepend PATH) for JS
      validation; on failure proceed on Node 22 and record the deviation
      (PR CI's JS jobs become the authoritative JS gate).
- [x] Snapshot ground-truth diffs per fork-patched cluster: fork delta
      `git diff fc8cbf5..dev -- <paths>`; upstream delta
      `git diff 3ef6bbd2..'v2026.8.16^{commit}' -- <paths>`.

## Phase 2 — The merge

- [x] `git merge v2026.8.16 --no-edit -m "Merge upstream v2026.8.16 into fork dev"`
      → single real merge commit M (parents: dev tip + tag commit). All
      Phase 3–5 resolution happens inside M **before its first push**.
- [x] Lineage invariants: never squash/rebase/amend M after push; final
      dev→main lands as a real merge.
- [x] Deviation note: at this window size the runbook's "small additive
      conflicts" expectation is void — the Phase 3 cluster list is the
      pre-authorized surface; conflicts outside it still stop the merge.

## Phase 3 — Conflict resolution (keep upstream substance, re-apply fork delta)

- [x] **`upload_to_pypi.yml`:** accept upstream deletion (modify/delete
      conflict) — channel retired in 0.20.0.
- [x] **Fork-only workflows kept verbatim:** `release-on-merge.yml`,
      `build-runtime-images.yml`, `build-desktop-client.yml`,
      `docs-validate.yml`; confirm upstream added no same-named files.
- [x] **`ci.yml`:** upstream structure + re-graft fork PR-concurrency block +
      contributor-check call-site guard
      (`github.repository == 'NousResearch/hermes-agent'`; the extracted
      `contributor-check.yml` itself is unguarded by design — verify no other
      caller).
- [x] **`docker-lint.yml`:** keep fork direct-invocation shape (digest-pinned
      hadolint 2.12.0, shebang-aware shellcheck discovery); port upstream
      substantive changes into it.
- [x] **Guarded upstream workflows re-grafted per job:** `deploy-site.yml`
      (deploy-vercel), `skills-index.yml` (build-index schedule guard +
      trigger-deploy), `skills-index-freshness.yml`, `js-autofix.yml` (both
      jobs), `osv-scanner.yml` (schedule-only pattern); verify upstream's own
      guards on `docker.yml` / `deploy-docs` survived — don't duplicate.
- [x] **Dockerfile:** fork 6-stage split kept (`base`/`toolchain`/
      `venv-runtime`/`venv-cli`/`cli`/`runtime`, runtime LAST, prebaked
      labels, HEALTHCHECK); upstream changes (expect Node 26 bump, possible
      iron-proxy packages) mapped into matching stages.
- [x] Semantic re-check: `docker/healthcheck.sh`, `docker/cli/hermes-shim.sh`,
      `docker/cli/profile.sh` vs upstream 0.20.x serve/CLI restructuring.
- [x] **Auth/providers/web_server:** re-apply "no-key" placeholder onto
      upstream's restructured auth; reconcile custom-slug deltas per Phase 4b.
      Gates: `tests/hermes_cli/test_auth_usable_secret.py` +
      `test_custom_provider_slug_canonicalization.py` green (adapt seams only,
      never behavioral assertions).
- [x] **mem0:** carry `_backend.py`/`_oss_providers.py`/`_setup.py` deltas.
      Gates: `test_mem0_backend.py` + `test_mem0_setup.py` green.
- [x] **Desktop cluster:** client-mode-first onboarding preserved
      (`electron/main.ts` first-run choice/TLS bypass/saved endpoints,
      `src/app/contrib/wiring.tsx`, `use-desktop-integrations.ts`,
      `electron/first-run-choice.ts` + tests) — re-home mounts if upstream
      moved them. Voice hook: take upstream provisionally (Phase 4a verdict).
      `after-pack.mjs` ad-hoc signing + `codesign --verify` +
      `CSC_FOR_PULL_REQUEST` re-applied.
- [x] **`apps/desktop/package.json`:** upstream deps + fork `homepage` +
      `"version": "0.20.2"` (fork convention; upstream leaves it stale). Root
      `package-lock.json`: upstream wholesale + surgical `apps/desktop`
      version-entry edit (no full regeneration). `vite.config.ts` stays
      upstream-identical.
- [x] **AGENTS.md:** upstream body adopted; `HERMES_OFFLINE_*` exception
      re-grafted INSIDE the inherited env-var section (highest silent-loss
      risk); fork tail carried verbatim; `CLAUDE.md` +
      `.github/copilot-instructions.md` thin pointers intact.
- [x] **README.md:** upstream body + ForgeGuard fork alert below title/badges;
      keep `install.ps1` mention (upstream test asserts it); scrub retired
      brew/pip channel wording.
- [x] **Fork docs overlay** (`docs/site/`, `docs/maintainers/`) preserved;
      `docs/agent-plans/` (fork) distinct from upstream `docs/plans/`.
- [x] **Banner ForgeGuard identity** re-applied onto upstream's banner path;
      fork banner tests green.
- [x] **`hermes_cli/offline.py`:** call-site wiring re-verified against
      upstream's iron-proxy egress restructure; offline tests green.
- [x] **`pyproject.toml` + `uv.lock`:** upstream byte-identical (0.20.2);
      `uv lock --check` passes. `hermes_cli/__init__.py`,
      `acp_registry/agent.json`, `SUPPORT.md`: upstream side (verify 0.20.2).
- [x] **`graphify-out/GRAPH_REPORT.md`:** clear conflict either side;
      regenerate at the end (Phase 7).
- [x] Any conflict far outside this surface → stopped and investigated before
      resolving.

## Phase 4 — Supersession proofs (evidence, not eyeball)

- [ ] **4a voice hook:** run fork's `use-voice-conversation.test.tsx`
      unmodified on the merged tree. Pass → superseded (drop fork patch;
      keep/retire test per upstream's own coverage). Seam-only failures →
      rewrite test seams, re-run. Behavioral failure → re-apply minimal fork
      delta onto upstream's new hook shape. Verdict recorded here +
      `forgeguard-changes.md` + patch inventory. Real-mic smoke deferred to
      user local.
- [ ] **4b custom-slug + no-key truth table:** copy
      `test_custom_provider_slug_canonicalization.py` +
      `test_auth_usable_secret.py` into the clean upstream worktree and run
      against pristine v2026.8.16 — each passing test = behavior converged
      upstream (drop that fork delta); each failure = still fork-required
      (carry). Per-behavior verdicts recorded here + PR body.

## Phase 5 — Workflow trigger + actions-policy audit (HARD GATE before first push of M)

- [x] Dump `on:` blocks of ALL merged workflow files (27 upstream + fork-only);
      classify and guard `push:`/`schedule:` triggers and upstream-bot
      workflows (`pull_request_target`/`issue_comment`/`workflow_run` with
      PATs/auto-merge/label writes).
- [x] Specific suspects: `publish-e2e-evidence.yml`, `e2e-desktop.yml`,
      `install-e2e.yml`/`install-e2e-run.yml`/`installer-tests.yml`,
      `ci-review-comment.yml`/`review-labels.yml`/`label-rerun.yml`,
      `tests-os.yml`.
- [x] Actions-policy sweep: `grep -h 'uses:' .github/workflows/*.yml | sort -u`;
      any non-(GitHub-authored / forgeguard-org-owned / Marketplace-verified)
      action reachable on fork PRs → rewrite to direct invocation
      (docker-lint precedent) or guard off the fork.
- [ ] Branch-protection reconciliation: fork `main` required checks vs new
      upstream job names — unguardable-new checks must skip, not block.
- [ ] Record every new/changed guard in `patch-inventory.md` (Phase 6). Only
      after this audit may M be pushed.

## Phase 6 — Patch-inventory re-verification + updates

- [ ] Every checkbox in `docs/maintainers/upstream-sync/patch-inventory.md`
      re-verified on the merged tree, by grep, not memory.
- [ ] Especially: `inputs.upload`/`inputs.push` gated **directly** in both
      build workflows (2026-07-02 silent-skip class); no `push:` trigger on
      either build workflow; release-on-merge gating intact.
- [ ] Inventory edits: retire `upload_to_pypi.yml` entry (strike-through,
      dated); reword contributor-check (guard at ci.yml call site); **add**
      missing `docker-lint.yml` direct-invocation entry (org actions-policy
      rationale); add all new Phase 5 guards; add carried-runtime-patch
      entries with their test files as verification hooks (no-key →
      `test_auth_usable_secret.py`; custom-slug →
      `test_custom_provider_slug_canonicalization.py`; mem0 →
      `test_mem0_backend.py`/`test_mem0_setup.py`); record voice-hook verdict.

## Phase 7 — Validation (cloud)

- [ ] `uv sync` → `.venv`; `uv lock --check` clean.
- [ ] `scripts/run_tests.sh` full suite (~17k tests; never bare pytest);
      triage every failure vs a clean upstream worktree
      (`git worktree add <scratchpad>/upstream-clean 'v2026.8.16^{commit}'`,
      `uv sync`, same wrapper): failure-set difference = merge regressions
      (fix before PR) vs upstream debt (list in PR body). Also run Phase 4b
      here. Remove worktree after; monitor disk.
- [ ] Targeted fork suites explicitly green: custom-slug, auth-usable-secret,
      mem0 ×2, offline, banner, first-run/connection-config,
      `tests/tools/test_windows_native_support.py` (README install.ps1).
- [ ] JS (Node 26 if installed, else Node 22 + recorded deviation): root
      `npm install`; `ui-tui` — `npm run build:ink`, typecheck, vitest;
      `apps/desktop` — both tsconfigs typecheck, vitest `ui` + `electron`
      projects (voice-hook focus).
- [ ] `python scripts/docs/validate_docs.py`.
- [ ] hadolint: deferred to PR CI (fork's `docker-lint.yml` runs it).
- [ ] `scripts/graphify-refresh.sh` → commit refreshed
      `graphify-out/GRAPH_REPORT.md` (final content commit).

Deferred to local (user): full Docker builds of both targets + `tests/docker`
fixture, desktop packaging + codesign verify + real-mic voice smoke, offline
E2E against the ForgeGuard deployment manager, GHCR image pull checks.

## Phase 8 — Docs updates

- [ ] `docs/site/fork/compatibility.md`: base `v2026.8.16`, release `v0.20.2`,
      product 0.19.3 → 0.20.2.
- [ ] `docs/site/fork/forgeguard-changes.md`: voice-hook verdict, per-behavior
      custom-slug outcome, upload_to_pypi retirement, docker-lint rewrite,
      new workflow guards.
- [ ] `docs/site/operations/releases-and-upgrades.md` **and** the
      release-notes heredoc in `release-on-merge.yml`: Node 26 requirement +
      brew/pip retirement; scrub stale install-channel references across
      `docs/site/` (incl. `migration-from-upstream.md`, `upstream.md`).
- [ ] `docs/maintainers/development/review.md`: refresh for upstream 0.20
      structure (voice/TTS, A2A, iron-proxy, desktop artifacts/plugin SDK).
- [ ] **Codify `dev` as the standard sync branch** in
      `docs/maintainers/upstream-sync/sync-policy.md` (user decision #1);
      keep "never PR from an upstream head"; update cross-references naming
      the old `sync/upstream-<TAG>` convention.

## Phase 9 — FORK_UPSTREAM_BASE + version

- [ ] `echo "v2026.8.16" > FORK_UPSTREAM_BASE`, committed as
      `chore: bump FORK_UPSTREAM_BASE to v2026.8.16`.
- [ ] `grep -m1 '^version' pyproject.toml` → `0.20.2` on the merged tree;
      desktop package.json/package-lock at 0.20.2.

## Phase 10 — Commit/push sequencing on dev

No amend/force-push after anything is pushed. Sequence:

- [ ] 1. `docs:` this plan file (pushed immediately).
- [ ] 2. Merge commit M (pushed only after the Phase 5 audit).
- [ ] 3. `fix(sync): ...` single-topic fixups (inventory pass, test triage,
      supersession adaptations).
- [ ] 4. `chore: bump FORK_UPSTREAM_BASE to v2026.8.16`.
- [ ] 5. `docs(fork): update compatibility/changes/release docs for v2026.8.16`.
- [ ] 6. `chore: refresh Graphify report` (last).

## Phase 11 — PR + CI green, then stop (user decision #2)

- [ ] PR via GitHub MCP: base `main`, head `dev`, title
      `sync: merge upstream v2026.8.16 into fork main`. Body: upstream window
      summary + breaking changes (Node 26, brew/pip retirement, iteration
      90→500, py <3.14); per-cluster conflict decisions; supersession verdict
      table; new/retired workflow guards; patch-inventory confirmation;
      triaged upstream-debt failures; validation results (+ any Node-22
      deviation); deferred-to-local checklist; expected release `v0.20.2`.
      NO `no-release` label; never an upstream branch as head.
- [ ] Watch PR CI; fix forward with new commits only. Stop once green.
- [ ] User merges with a **real merge only** after local validation.
- [ ] Post-merge (offered): `release-on-merge.yml` fully green with
      **step-level** installer-upload + GHCR-push success (not skipped);
      release `v0.20.2` with all 5 installers (`.deb`, `.AppImage`, `.rpm`,
      `.dmg`, `.zip`) + "Upstream release: v2026.8.16" notes line; both
      `runtime-`/`cli-` image tag families on ghcr.
- [ ] Cleanup: tick remaining checkboxes here in a final small commit.

## Key risks & mitigations

- **R1** Node 22 container vs Node 26 requirement → tarball install or defer
  JS authority to PR CI; verify Dockerfile/installer Node bump lands in fork
  stages.
- **R2** Branch-protection required checks naming new upstream jobs that can't
  pass on the fork → audit before opening the PR.
- **R3** package-lock regeneration churn → surgical version edit only.
- **R4** Actions-policy startup failures beyond docker-lint → Phase 5 sweep is
  load-bearing.
- **R5** `pull_request_target`/`issue_comment` workflows run from main's copy
  — inert on the PR, live right after merge; audit correctness pre-merge.
- **R6** Iron-proxy egress vs fork `HERMES_OFFLINE_*` gate + desktop TLS
  bypass → explicit call-site inspection + offline tests.
- **R7** Disk: unshallow + tag fetch + worktree + venvs + node_modules on ~30G
  → single-tag fetch, shared uv cache, prompt worktree removal, monitor `df`.
- **R8** Stop-rule calibration: Phase 3 list is the pre-authorized conflict
  surface; anything outside it stops the merge for investigation.

## Decisions & findings log (2026-08-16, cloud session)

(Appended as work proceeds.)
