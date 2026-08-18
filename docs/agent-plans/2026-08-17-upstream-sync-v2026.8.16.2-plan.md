# 2026-08-17 — Upstream sync v2026.8.16 → v2026.8.16.2, fork release v0.20.4

Status: implemented on `dev` (PR dev → main pending) · Procedure: `docs/maintainers/upstream-sync/sync-policy.md`
· Previous worked example: `2026-08-16-upstream-sync-v2026.8.16-plan.md`

## Gate (Phase 1)
- [x] `dev` = `main` (db40be650, fork v0.20.3 + PR #23 compressor reservation fix)
- [x] `git fetch upstream tag v2026.8.16.2 --no-tags`
- [x] `git merge-base dev v2026.8.16.2^{commit}` == `df4b65147` (recorded upstream parent)
- [x] Tag is product 0.20.3, `__release_date__ 2026.8.16.2`; no v2026.8.16.1 exists

## Delta
258 commits / ~461 files. Themes: Bot Mode desktop plugin (built-in), computer-use
Cua 0.20, MCP 2.x SDK, cron hardening, CommandCode provider, tool interruptibility,
empty-response guard settings → config.yaml, login-shell PATH for GUI desktop, remote
gateway headers, desktop `repository`/publish-path fixes. **Zero `.github/**` changes.**

## Pre-authorized conflict cluster (keep upstream substance, re-apply fork delta)
HIGH: `agent/agent_init.py`, `agent/agent_runtime_helpers.py` (fork = output-reservation
wiring; gate `tests/agent/test_output_reservation.py`), `hermes_cli/web_server.py`
(custom-provider slug fixes; re-run supersession truth table), `apps/desktop/electron/main.ts`
(fork client-mode/TLS bypass vs upstream startHermes/runPrimaryBackendStartup),
`apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts`.
MEDIUM: `agent/model_metadata.py`, `electron/connection-config.ts(+test)`, `preload.ts`,
`gateway-menu-panel.tsx`, `store/boot.ts`, `tui_gateway/server.py`, `tests/conftest.py`.
LOW: `global.d.ts`, i18n `{en,ja,zh,zh-hant,types}.ts`, `apps/shared/src/index.ts`,
`apps/desktop/README.md`, `.gitignore`.
CERTAIN-trivial: `apps/desktop/package.json` (keep upstream `repository`/publish keys; version
fork), `pyproject.toml`, `hermes_cli/__init__.py`, `uv.lock` (upstream, then set 0.20.4).
Anything outside this list stops the merge.

## After the merge, on dev (single-topic commits)
- [x] fix(desktop): reauth after container recreate — statusCode on fetchJson/fetchPublicJson,
      clear native tokens on 401/403 in mintGatewayWsTicket (credential only, never prefs),
      Sign-in action on the remoteFailure boot dialog, wider isRemoteReauthError; tests
- [x] fix(desktop): context meter shown by default (drop 'context-usage' from hidden defaults)
- [x] feat(desktop): update checks hard-off (fork constant): no poller, no toast, pills without
      "(+N)", user-hideable; `offline._disable_flag` honours an explicit truthy value without
      offline mode; Dockerfile `HERMES_OFFLINE_DISABLE_UPDATE_CHECKS=1`
- [x] feat(desktop): Windows nsis + portable artifacts (package.json targets/artifactNames,
      build-windows job, release download step, docs)
- [x] Version 0.20.4 (fork line is its own line — release-process.md convention updated),
      `FORK_UPSTREAM_BASE` = v2026.8.16.2, compatibility.md
- [x] Validation (this container: fork suites 187+82+44 green, desktop electron 1329, targeted ui suites, all four tsconfigs; the full ui suite and scripts/run_tests.sh run in CI — the 3 GB container times out on them; graphify refresh deferred, tool not installed here): uv sync/lock --check, scripts/run_tests.sh (diff vs clean worktree), fork
      suites, JS gates, validate_docs.py, graphify
- [ ] PR dev → main "sync: merge upstream v2026.8.16.2 into fork main", real merge → v0.20.4

## Merge resolution record
9 conflicts, all inside the pre-authorized cluster: `hermes_cli/__init__.py`
(upstream), `apps/desktop/package.json` (upstream `repository` key kept, URL
pointed at the fork; upstream's new publish test adapted to assert `forgeguard-ai`),
`connection-config.ts(+test)` (headers + allowInvalidCertificate both kept),
`store/boot.ts` (both functions kept), `gateway-menu-panel.tsx` (both buttons;
upstream's new test mock gained the fork's `connectionMode` i18n key),
`use-gateway-boot.test.tsx` (imports), `use-gateway-boot.ts` (fork version taken,
upstream's 12 additions — bounded boot retry, registerGatewayReconnect,
onActiveConnectionInvalidated, refreshActiveProfile, primary-only publish —
re-applied by hand inside the fork's initGatewayBoot wrapper), `electron/main.ts`
(11 hunks: buildRemoteBlock/buildRemoteConnection carry both
allowInvalidCertificate and headers; test-connection keeps the self-signed WS skip
and passes headers). `agent/agent_init.py`, `agent_runtime_helpers.py`,
`hermes_cli/web_server.py` auto-merged; proven by the fork suites.
