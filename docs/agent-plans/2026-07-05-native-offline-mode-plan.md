# Native Offline-Mode Gate — Code-Review Fixes (2026-07-05)

Branch: `claude/multi-repo-code-review-9g12lw`

Approved code-review fixes making the native offline/privacy gate
(`hermes_cli/offline.py`) cover the same six network call sites the legacy
reversible source patch (`agent-deployment-manager/scripts/hermes-offline-patch.sh`)
covers, plus correctness/test/doc follow-ups. When offline mode is OFF, all
existing behavior is preserved.

## Context / key decisions

- The `HERMES_OFFLINE_*` env vars are a deliberate cross-repo interface with the
  ForgeGuard deployment manager's `write_env_file` — KEEP the env-var contract,
  DOCUMENT the exception rather than migrating to `config.yaml` (H4).
- Native gate must match the patch's truthiness default: when offline mode is on,
  an UNSET `DISABLE_*` flag defaults to disabled (H2).

## Work items

- [x] H1 — Wire the gate into the remaining 5 call sites the patch covers:
  - [x] `hermes_cli/nous_account.py` — `get_nous_portal_account_info` +
    `_fetch_nous_account_info` (portal account-info) → `portal_checks_disabled()`.
  - [x] `agent/account_usage.py` — `nous_credits_lines` (portal usage) → `[]`.
  - [x] `hermes_cli/nous_billing.py` — `_request` (billing) → raise BillingError
    `error="offline_mode"`.
  - [x] `agent/model_metadata.py` — `fetch_model_metadata` (OpenRouter) →
    `remote_metadata_disabled()`, cache/disk fallback.
  - [x] `hermes_cli/model_catalog.py` — `_fetch_provider_override` →
    `remote_catalog_disabled()`, return None.
- [x] H2 — Fix truthiness default divergence: `_disable_flag()` helper, unset
  `DISABLE_*` defaults to disabled when offline on. Master switch keeps
  explicit-truthy semantics. Docstring accuracy updated.
- [x] H5 — `agent/models_dev.py` offline path back-dates cache time (grace window)
  instead of stamping stale data fresh; one-time `logger.info` on suppressed
  force_refresh.
- [x] H6 — `hermes_cli/model_catalog.py` offline log downgraded to once-only info.
- [x] H7 — Delete dead `status()` (camelCase) from offline.py; keep
  `portal_checks_disabled()` (now wired). Update tests.
- [x] H3 — Rewrite `tests/hermes_cli/test_offline_mode.py` to assert network layer
  is never called (assert_not_called spies); cover the new sites + H2 default.
- [x] H9 — `tests/conftest.py` blanks `HERMES_OFFLINE_MODE` + 4 `DISABLE_*` vars.
- [x] H4 — Document env-var contract exception in offline.py docstring + AGENTS.md.
- [x] H10 — Fix `docs/forgeguard-fork/graphify-refresh-skill.md` inaccuracies
  (real ~287 KB size; real completion markers; achievable Built-from-commit check).
- [x] H8 — This plan file.

## Validation

- `scripts/run_tests.sh tests/hermes_cli/test_offline_mode.py`
- `ruff check .` / `ty check` where available.
