# ForgeGuard README + documentation-layer migration

**Branch:** `claude/forgeguard-docs-migration-l6qfhi`
**Date:** 2026-07-20
**Baseline:** fork `main` @ `caae80d`, `FORK_UPSTREAM_BASE=v2026.7.1`, Hermes `v0.18.0`.

## Context

The root `README.md` opens with a long ForgeGuard fork alert that reads like a
manual and buries the upstream value proposition. Fork docs live flat under
`docs/forgeguard-fork/` with no publication boundary, front matter, or user vs
maintainer separation. This change implements the org-wide ForgeGuard README/docs
standard (from the build kit): a concise branded README, a website-publishable
`docs/site/` overlay, maintainer docs under `docs/maintainers/`, a
`.forgeguard/docs.yml` manifest, and CI validation — leaving the upstream
`website/docs/` Docusaurus tree untouched.

**Out of scope:** upstream sync, runtime-behavior changes, deleting/reorganizing
`website/docs/`, publishing images/installers/releases, rebranding the app.

## Approved decisions

- CI: **standalone** `.github/workflows/docs-validate.yml` (own triggers, fork-owned,
  no changes to upstream `ci.yml`/`detect-changes`).
- Old paths: **single redirect stub** at `docs/forgeguard-fork/README.md`; remove
  per-page files + the `docs/fork-maintenance/` stub; update all internal refs.

## Verified facts (from live checkout)

- Ports 9119 (dashboard/gateway, `/api/status`), 8642 (OpenAI-compat API, optional).
- Install `/opt/hermes`; state `/opt/data` (VOLUME); CLI/distrobox uses `~/.hermes`.
- Dockerfile stages `base→toolchain→venv-runtime→venv-cli→cli→runtime`; runtime LAST.
  Labels `com.forgeguard.hermes.prebaked=1` + `.variant`. s6 in runtime only.
- Auth mandatory on non-loopback bind since v2026.7.1; `--insecure` no longer bypasses.
  basic-auth `_USERNAME`/`_PASSWORD_HASH`(pref)/`_PASSWORD`/`_SECRET` or OAuth `_CLIENT_ID`.
- `HERMES_UID`/`HERMES_GID` (aliases PUID/PGID), default UID 10000.
- Tags: `{runtime,cli}-<version>` + `-<sha>` immutable, `-latest` rolling; registry
  `ghcr.io/forgeguard-ai/hermes-agent`.
- Desktop Linux `.AppImage/.deb/.rpm` + macOS `.dmg/.zip`, ad-hoc signed NOT notarized;
  Windows deferred. `xattr -cr /Applications/Hermes.app`.
- Banner 2172×724. Stale fixes: `forgeuard` typo; `--insecure` no-bypass; `_PASSWORD_HASH`.

## Work items

- [x] Save this plan to `docs/agent-plans/`.
- [x] Install assets → `docs/site/assets/{repository,logos,screenshots}/`.
- [x] Install `.forgeguard/docs.yml`.
- [x] Write `docs/site/` pages (index, getting-started, deployment ×3, operations ×3,
      reference ×2, troubleshooting, fork ×4) with front matter.
- [x] Write `docs/maintainers/` pages (development/review, development/graphify-refresh,
      release/release-process, release/artifact-verification, upstream-sync ×3).
- [x] Rewrite root `README.md` per kit §7.
- [x] Collapse `docs/forgeguard-fork/` to stub; remove `docs/fork-maintenance/` stub;
      update refs in AGENTS.md, CLAUDE.md, copilot-instructions.md, README,
      release-on-merge.yml, website/docs/user-guide/docker.md.
- [x] Root policies: SECURITY.md note, new SUPPORT.md, CONTRIBUTING.md overlay path.
- [x] `scripts/docs/validate_docs.py` + `.github/workflows/docs-validate.yml`.
- [x] Verify: validator (pass), `git diff --check` (clean), grep sweeps (clean),
      documented facts asserted against live source (pass). Python pytest harness
      not installed in this env and docker suite needs a daemon — not run.
- [ ] Commit + push to `claude/forgeguard-docs-migration-l6qfhi`.

## Verification

`python scripts/docs/validate_docs.py`; `git diff --check`;
`grep -rn 'docs/forgeguard-fork/' --include=*.md --include=*.yml .` → stub only;
`grep -rn forgeuard` → 0; targeted `scripts/run_tests.sh` for docker/dashboard/version.
