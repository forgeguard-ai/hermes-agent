---
title: Release / package / artifact cleanup — hermes-agent + agent-command
status: in-progress
date: 2026-08-17
type: plan
---

## Progress

- [x] Phase 0 — capture the pre-deletion record; probe delete capability
- [x] Phase 1 — retarget hermes-agent doc pins `v0.19.0` → `v0.20.3`; narrow the
      rollback and provenance contracts
- [x] Phase 2 — release prune **staged** in `artifact-retention.yml` (direct
      deletion returned 403 for this session type)
- [x] Phase 3 — artifact prune **staged** in `artifact-retention.yml`
- [x] Phase 4 — `artifact-retention.yml` + `prune_artifacts.py` written and
      dry-run verified in both repos
- [x] Phase 5 — voice fix rescued to PR #16 (agent-command); branch prune
      **staged** in `branch-cleanup.yml` (ref deletion returned 403)
- [x] Phase 6 — validation: docs gate, typecheck, lint, test:ts, build
- [x] Phase 7 (2026-08-18) — branch merged onto post-sync `main` (`v0.20.4`,
      upstream `v2026.8.16.2`) with adjustments: `keep_builds` default 1 → 2
      (roll-back promise), `hermes-desktop-windows` added to the retained
      artifacts, a 24 h `min_age_hours` floor so a mid-CI dispatch never races
      `workflow_run` consumers, the split History blockquote repaired, and
      every doc pin moved to `v0.20.4`.
- [ ] **Maintainer action** — dispatch both workflows dry-run, read the plans,
      then re-run with `dry_run` unchecked; delete the 6 backup tags by hand

> Deletion could not be performed by the authoring session. Everything
> destructive is staged as `workflow_dispatch` workflows that default to
> dry-run. See the "Capability boundary" section below, and
> `docs/maintainers/release/2026-08-17-cleanup-record.md` in hermes-agent for the
> pre-deletion snapshot.

---

# Release / package / artifact cleanup — hermes-agent + agent-command

## Context

Both repos have accumulated publishing debris with **zero retention automation** — no
`delete-package-versions`, no scheduled prune, nothing but `retention-days:` on
individual `upload-artifact` steps. Measured today:

| | hermes-agent | agent-command |
|---|---|---|
| GitHub Releases | **13** (7.45 GB of assets) | 0 |
| Git tags | **40** (6 are backup/junk) | 0 |
| Live workflow artifacts | **161** (3.72 GB) | unreadable from this session |
| Stale branches | 1 | 6 |

The bulk is desktop installers duplicated across every release: 11 of the 13 releases
carry ~620 MB each of `hermes-desktop-client-*` `.deb`/`.AppImage`/`.rpm`/`.dmg`/`.zip`,
almost all with **0 downloads**. Live workflow artifacts are the same binaries again
(`hermes-desktop-linux` 2.09 GB + `hermes-desktop-macos` 1.63 GB across 6 runs each).

Target: keep the **2 most recent releases** and the **most recent full package build**,
delete everything else, and delete every branch that is behind/merged/unused except
`dev` on hermes-agent. Roughly **~9.6 GB reclaimed** across the two repos.

The cleanup is destructive and touches documented contracts, so the plan front-loads
the doc fixes and records every deleted ref before deleting it.

### Decisions taken (confirmed with maintainer)

1. `fix/mem0-llm-key-and-vllm-tunables`' unmerged voice fix → cherry-pick to a new
   branch, open a PR, then delete the stale branch.
2. Tags: delete **junk/backup only**. Release tags and upstream `v2026.*` tags stay.
3. agent-command gets **no invented `dev` branch** — keep `main` only.
4. GHCR pruning ships as a **committed `workflow_dispatch` workflow** per repo.

### Capability boundary — probed, not assumed

Phase 0's capability probe ran and **release and artifact deletion are both blocked for
this session type.** The plan pre-authorized this fallback for releases; artifacts hit
the same wall, so the same fallback applies to them. Measured:

| Operation | Result |
|---|---|
| `DELETE .../releases/357115577` | **403** — "Creating, editing, or deleting releases is not permitted for this session type" |
| `DELETE .../actions/artifacts/9269976427` | **403** — "Resource not accessible by integration" |
| Any org-scoped packages endpoint | **403** — "sessions are bound to their configured repositories" |
| agent-command `actions/*` (read) | **403** — no Actions permission on that repo |
| hermes-agent `actions/*` (read) | 200 — enumerable, not deletable |
| `git push origin --delete` (branch or tag) | **403** — `send-pack: unexpected disconnect`, 4 retries |
| `DELETE .../git/refs/heads/<branch>` | **403** — "Write access to this GitHub API path is not permitted through this proxy" |
| Push a *new* branch, create a PR | **accepted** (PR #16 opened this way) |

`git push --dry-run --delete` reported success and was a **false positive** — dry-run
never sends the ref update, so it does not exercise the permission check. Only the real
push does, and it fails.

**Consequence: every destructive operation moves into committed workflows.** This session
can create and push, but cannot delete anything. Phases 2, 3 and 4 go into
`artifact-retention.yml`; Phase 5's branch deletions go into a second workflow,
`branch-cleanup.yml`. Both run under the repo's own `GITHUB_TOKEN`, dry-run by default.
The workflows are the deliverable; the maintainer dispatches them.

**Ordering correction this forces.** The stray `2026.7.1` tag still has a live Release
attached (its deletion was the probe that failed). Deleting the tag now would leave a
release pointing at a missing tag. So the workflow deletes the 11 releases *and* the
`2026.7.1` tag in one run; the other 6 backup tags carry no release and are deleted from
here directly.

### Three traps a naive prune would hit

- **`buildcache-runtime-amd64` / `buildcache-cli-amd64`** are buildkit registry-cache
  indexes living as versions of `ghcr.io/forgeguard-ai/hermes-agent`
  (`build-runtime-images.yml:109-110`, `mode=max`). A "delete untagged versions" prune
  destroys the cache and can orphan layers its index references. The prune must work
  from an explicit **tag keep-list** and **skip any version with zero tags**.
- **Five packages in the same GHCR namespace are not built by either repo** and are
  pinned at runtime: `camofox-browser:1.11.21` (hard pin in
  `agent-command/src/shared/profileSchema.ts:161`), `kokoro-server`,
  `kokoro-server-jetson`, `faster-whisper-server`, `faster-whisper-server-jetson`
  (`serviceSchema.ts:768-791`). The workflow must use a **package allowlist**, never
  iterate the namespace.
- **`README.md:96` pins `runtime-v0.19.0`** as the copy-pasteable quickstart. Deleting
  that GHCR version breaks the front page. Docs get fixed *before* anything is deleted.

---

## Phase 0 — Governance + safety net

1. Persist this plan under `docs/agent-plans/2026-08-17-release-artifact-cleanup.md` in
   **both** repos, per `.github/skills/plan-persistence/SKILL.md` (agent-command's
   `scripts/validate-agent-edits.sh` gate requires it).
2. Write `docs/maintainers/release/2026-08-17-cleanup-record.md` in hermes-agent
   capturing, **before deletion**, every release id + tag + asset name and every
   deleted tag's SHA. The 6 backup tags point at commits **not in `main`'s history** —
   once the tag is gone those commits are unreachable and GC-eligible. The record file
   is the only way back.
3. **Verify delete capability first** using the safest possible target: release
   `2026.7.1` (id `357115577`) has **0 assets** and its tag is reachable from `main`.
   If `DELETE /repos/forgeguard-ai/hermes-agent/releases/357115577` is rejected, stop
   and fold release deletion into the committed workflow alongside the GHCR prune.

---

## Phase 1 — Fix the doc pins (must precede deletion)

hermes-agent still advertises `v0.19.0` while `pyproject.toml` is `0.20.3`. Retarget to
`v0.20.3`:

| File:line | Change |
|---|---|
| `README.md:96` | `runtime-v0.19.0` → `runtime-v0.20.3` |
| `README.md:180` | "ships Hermes **`0.19.0`**" → `0.20.3` |
| `docs/site/deployment/runtime-images.md:36,40,51` | `runtime-v0.19.0` → `runtime-v0.20.3` |
| `docs/site/deployment/runtime-images.md:21` | "upstream `v2026.7.20` (Hermes `v0.19.0`)" → `v2026.8.16` / `v0.20.3` |
| `docs/site/reference/image-tags.md:28,35` | example tag → `runtime-v0.20.3` |
| `docs/site/operations/releases-and-upgrades.md:18,23` | `v0.19.0` examples → `v0.20.3` |
| `docs/site/fork/compatibility.md:19-20` | fork release line + product version `v0.20.2` → `v0.20.3` |

`scripts/docs/validate_docs.py:43,402` fails the build unless `README.md` contains the
literal `ghcr.io/forgeguard-ai/hermes-agent`. These edits only change the tag suffix, so
the guard stays satisfied — do not touch the namespace string.

**Narrow two contracts the prune invalidates.** Both currently promise unbounded history:

- `docs/site/operations/releases-and-upgrades.md:87` — *"Because the previous immutable
  tag still exists…"*. Add the retention window: the last 2 releases and the newest
  `runtime-<version>`/`cli-<version>` pair are what's guaranteed pullable.
- `docs/maintainers/release/artifact-verification.md:15-18` — its provenance procedure
  needs `runtime-<sha>` pullable, and there is no cosign/attestation fallback anywhere
  in the fork. State that provenance verification only covers retained builds.

Also correct the stale claim in `docs/maintainers/release/release-process.md` and
`releases-and-upgrades.md` that the old date-shaped scheme stops at
`v2026.7.1-forgeguard.3` — `.4`, `.5`, `.6` all exist.

---

## Phase 2 — hermes-agent Releases (repo-scoped REST, doable here)

**Keep 2:** `v0.20.3` (id 371499913), `v0.20.2` (id 371438369) — 1.25 GB.

**Delete 11** (≈6.2 GB), via `DELETE /repos/forgeguard-ai/hermes-agent/releases/{id}`:

```
369240252  v0.19.3                    367711797  v0.19.2
367468358  v0.19.1                    357801025  v0.19.0
357115577  2026.7.1        (0 assets) 357018116  v2026.7.1-forgeguard.6
349170677  v2026.7.1-forgeguard.5     349143205  v2026.7.1-forgeguard.4
348866236  v2026.7.1-forgeguard.3     348327467  v2026.7.1-forgeguard.2
348180830  v2026.7.1-forgeguard.1
```

Deleting the Release leaves the git tag — intended, per decision 2. **Consequence to
verify after:** `release-on-merge.yml:125-134` computes the next version by parsing
`gh release list --limit 200` for `-forgeguard.<n>` suffixes. With those releases gone
the counter resets, so a future re-cut of `v0.19.x` or `v2026.7.1` would try to create a
tag that still exists and fail. Add a note to
`docs/maintainers/release/release-process.md` recording this; no code change needed
while the version line is `0.20.x` and moving forward.

### Tags to delete (7)

Record the SHA first — the first six are **not in `main`'s history**:

```
premerge-oh-god                        a08725e5  2026-05-28  NOT in main
merge-commit-backup                    48a7e137  2026-05-28  NOT in main
clean-before-remerge                   0fce8216  2026-05-29  NOT in main
desktop-pr20059-installers             bff052d6  2026-05-11  NOT in main
backup/precopystrip-20260616-2058      a348fc1c  2026-06-16  NOT in main
backup/opentui-prestrip-20260616-1950  9d05f372  2026-06-16  NOT in main
2026.7.1                               1d7b3721  2026-07-20  reachable from main
```

`2026.7.1` is a stray no-`v` duplicate of `v2026.7.1-forgeguard.6`'s commit; safe.
Delete with `git push origin --delete refs/tags/<tag>`.

**Do not touch** the 12 upstream `v2026.3.12`–`v2026.6.5` date tags: the sync policy
runs `git tag -l 'v20*'` and `git merge <TAG>`, and a workflow falls back to
`git describe --tags --abbrev=0` (`sync-policy.md:41-42,121`).

---

## Phase 3 — hermes-agent workflow artifacts (doable here)

525 total / 161 live / 3.72 GB. Keep only the newest full package build: the single
newest `hermes-desktop-linux` + `hermes-desktop-macos` pair (the v0.20.3 run). Delete
the other 159 live artifacts via
`DELETE /repos/forgeguard-ai/hermes-agent/actions/artifacts/{id}` — ≈3.4 GB.

The 12 desktop artifacts are the whole payload; everything else
(`review-status-*`, `test-durations-slice-*`, `ci-timings-report`, `OSV Scanner SARIF
file`) is sub-MB CI ephemera on 1–14 day retention that would expire anyway. Delete for
tidiness, but it frees nothing. Skip the 364 already-expired entries.

Note the retained pair duplicates v0.20.3's release assets exactly — they can go too if
you'd rather hold one copy; say so and I'll drop them.

---

## Phase 4 — GHCR prune workflow (committed, dispatchable)

New file in each repo, `workflow_dispatch` only, `dry_run: true` **by default**, with
`permissions: { packages: write, actions: write, contents: read }`. Runs under the
repo's own `GITHUB_TOKEN`, which does have packages access this session lacks.

### `hermes-agent/.github/workflows/artifact-retention.yml`

Package allowlist: `hermes-agent` **only**.

Keep-list (delete a version only if **every** tag it carries is outside this list, and
**never** a version with zero tags):

```
runtime-v0.20.3   cli-v0.20.3            # most recent full build
runtime-latest    cli-latest             # rolling; agent-command's default image
buildcache-runtime-amd64  buildcache-cli-amd64   # buildkit cache indexes
runtime-<sha of v0.20.3>  cli-<sha of v0.20.3>   # provenance for the retained build
```

Delete: all other `runtime-v*` / `cli-v*` and all other `runtime-<sha>` / `cli-<sha>`.

Also prunes workflow artifacts using the Phase 3 rule, so the whole policy is
re-runnable rather than a one-off.

### `agent-command/.github/workflows/artifact-retention.yml`

Package allowlist: `fgcommand-api`, `fgcommand-web`, `fgcommand-gateway` **only** — the
three built by `server-images.yml`. Keep `latest` plus the newest explicit tag per
package; delete older; skip untagged.

Explicitly excluded by the allowlist: `camofox-browser`, `kokoro-server`,
`kokoro-server-jetson`, `faster-whisper-server`, `faster-whisper-server-jetson`.

Also prunes this repo's workflow artifacts (the only route to them — 403 from here).

### Fork bookkeeping

hermes-agent's new workflow is a fork-only file. Add it to
`docs/maintainers/upstream-sync/patch-inventory.md`, which enumerates fork-only
workflows (see its lines 50, 56, 59) so upstream syncs preserve it. It has no `push:`
trigger, so `patch-inventory.md:52`'s assertion about `build-runtime-images.yml` is
unaffected.

---

## Phase 5 — Branches

No open PRs exist in either repo, so no deletion orphans one.

### hermes-agent

| Branch | State | Action |
|---|---|---|
| `main` | — | keep |
| `dev` | merged, 3 behind | **keep** — upstream-sync staging; PRs #17 and #22 merged from it |
| `claude/fork-sync-upstream-release-41pg7g` | merged, 69 behind, 0 ahead | delete |

### agent-command

| Branch | State | Action |
|---|---|---|
| `main` | — | keep |
| `claude/agent-command-review-commander-6jtqc0` | merged, 19 behind, 0 ahead | delete |
| `claude/notifications-approvals-improvements-4tkp07` | merged, 59 behind, 0 ahead | delete |
| `claude/remote-system-probe-design-0xghys` | merged, 69 behind, 0 ahead | delete |
| `claude/security-review-7vi2np` | merged, 56 behind, 0 ahead | delete |
| `claude/forgeguard-post-migration-plan-lrbdw2` | 82 behind, **2 ahead** | delete — both commits verified superseded |
| `fix/mem0-llm-key-and-vllm-tunables` | 1 behind, **1 ahead** | PR the commit, then delete |

**Why `claude/forgeguard-post-migration-plan-lrbdw2` is safe.** Its two commits both
landed by other routes: `a957190` ("rename Go module and GHCR namespace to
forgeguard-ai") is in `main` — `go.mod` reads `module
github.com/forgeguard-ai/agent-command`; `07575e2` ("Ollama embedding services and API
key configuration") landed via PR #14 — `memoryLlmProviderSchema`, `embedderServiceId`,
`llmProvider` and `ollamaBaseUrl` are all present in
`origin/main:src/shared/profileSchema.ts`. The branch also predates the 2026-07-27
desktop removal (its diff vs `main` is +77.5k/−122k across 458 files) and edits
`scripts/hermes-distrobox-manager.sh`, which no longer exists. Nothing to salvage.

**`fix/mem0-llm-key-and-vllm-tunables` carries real unmerged work.** Commit `2fbdab6`
("fix(voice): the TTS/STT helpers read `$HERMES_HOME/.env`, not `$HOME/.hermes/.env`")
was pushed *after* PR #14 merged, so the merge missed it. It is a genuine bug fix — the
`$HOME`-relative path doubles into `.hermes/home/.hermes/.env` and the helper died with
"No such file or directory" on **every TTS call** while the endpoint itself was healthy.
Confirmed absent from `main`. Sequence:

1. `git checkout -B fix/voice-env-path-hermes-home origin/main`
2. `git cherry-pick 2fbdab6` (31 lines in `scripts/hermes-deploy-manager.sh`)
3. Validate: `bash -n scripts/hermes-deploy-manager.sh`, `shellcheck -S error`
4. Open a PR for maintainer review
5. Delete `fix/mem0-llm-key-and-vllm-tunables` **only after that PR merges**

Delete branches with `git push origin --delete <branch>`. Keep
`claude/repo-cleanup-artifacts-c7oop6` in both repos — it carries this work.

---

## Phase 6 — Validation

agent-command (per `CLAUDE.md`, all must come back clean):

```
npm run typecheck && npm run lint && npm run test:ts && npm run build
```

Workflow/script changes additionally: `npm run build:backend`, `npm run test:backend`,
`npm run vet:backend`, `npm run lint:backend`, plus `bash -n` and
`shellcheck -S error` on any touched script.

hermes-agent: `python3 scripts/docs/validate_docs.py` (proves the Phase 1 doc edits keep
`docs-validate.yml` green), and lint the two new workflow YAMLs.

Finish with `.github/skills/post-change-validation/SKILL.md`; the gate is
`scripts/validate-agent-edits.sh`.

---

## Manual verification (maintainer, after execution)

Ordered so each step sets up the next.

1. **Releases** — open `github.com/forgeguard-ai/hermes-agent/releases`. Expect exactly
   `v0.20.3` and `v0.20.2`, each with its 5 desktop installers. Nothing older.
2. **Tags** — `git fetch --prune --prune-tags origin && git tag -l`. Expect the 7 junk
   tags gone; the 12 upstream `v2026.*` tags and all release tags still present.
3. **Quickstart still works** — copy the `docker run` line from the freshly edited
   `README.md:96` and run it. It should pull `runtime-v0.20.3` and start the gateway. If
   it 404s, the GHCR keep-list dropped a tag the docs reference.
4. **Docs gate** — `python3 scripts/docs/validate_docs.py` exits 0.
5. **GHCR dry run** — Actions → *artifact-retention* → Run workflow with `dry_run: true`
   in **hermes-agent first**. Read the planned-deletion list in the job log and confirm
   it contains **no** `buildcache-*` entry, **no** untagged version, and **no**
   `runtime-latest`/`cli-latest`. Only then re-run with `dry_run: false`.
6. **Repeat step 5 for agent-command.** Confirm the log names only
   `fgcommand-api`/`-web`/`-gateway` and never `camofox-browser`, `kokoro-server*`, or
   `faster-whisper-server*`.
7. **Default deployment still resolves** — in Command Center, create a deployment
   accepting the default image (`runtime-latest`, from
   `src/shared/defaults.ts:10-13`) and confirm the pull succeeds and the
   `com.forgeguard.hermes.prebaked=1` guard at
   `scripts/hermes-deploy-manager.sh:1337` passes.
8. **Camofox pin intact** — start a deployment with browser tooling; confirm
   `ghcr.io/forgeguard-ai/camofox-browser:1.11.21` still pulls.
9. **Voice fix** — after the Phase 5 PR merges, redeploy and trigger a TTS call.
   Expect audio, and no "No such file or directory" in Activity → Logs. Before the fix
   this failed on every call.
10. **Branches** — `git branch -r` on both. hermes-agent: `main`, `dev`,
    `claude/repo-cleanup-artifacts-c7oop6`. agent-command: `main`,
    `claude/repo-cleanup-artifacts-c7oop6`.
11. **Next release is unaffected** — merge a trivial release-relevant PR into
    hermes-agent `main` and confirm `release-on-merge.yml` cuts `v0.20.4` (not a
    resurrected `v0.19.x`) and that the tag does not collide.

## Out of scope

Latent bugs found while surveying, worth separate fixes — flagging, not fixing here:

- `agent-command/scripts/rebuild-images.sh:339` greps `ghcr.io/forgeguard/camofox-browser:`
  (missing `-ai`), so `--list-runtime`'s camofox lookup silently returns empty.
- `agent-command/docs/maintainers/index.md:30` and `docs/site/operations/upgrades.md:122`
  link to `docs/maintainers/release/release-process.md`, which does not exist in that repo.
- `agent-command/deploy/fgcommand/docker-compose.yml:26` and
  `deploy/fgcommand/README.md:46` use `FGCOMMAND_IMAGE_TAG=v1.4.0` as the example, but
  agent-command has 0 tags and 0 releases — the example is already fictional.
