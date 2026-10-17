"""Tests for .github/scripts/audit_fork_workflows.py.

The audit guards the fork against upstream workflow changes that misbehave
outside upstream's GitHub organisation: larger-runner labels that never
resolve, scheduled and tag-push triggers, and actions or reusable workflows
the org policy blocks. The repository's own workflows must always pass; each
rule is also exercised against small synthetic workflows.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PATH = _REPO / ".github" / "scripts" / "audit_fork_workflows.py"
_spec = importlib.util.spec_from_file_location("audit_fork_workflows", _PATH)
if _spec is None or _spec.loader is None:
    raise ImportError("Failed to load audit_fork_workflows.py")
audit_mod = importlib.util.module_from_spec(_spec)
# Registered before exec: dataclasses resolve string annotations through
# sys.modules[cls.__module__].
sys.modules[_spec.name] = audit_mod
_spec.loader.exec_module(audit_mod)


def _write(root: Path, name: str, body: str) -> Path:
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    path = wf_dir / name
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return path


def _rules(root: Path) -> list[str]:
    return [v.rule for v in audit_mod.audit(root)]


CLEAN = """
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/retry
      - run: echo ok
"""


# ---------------------------------------------------------------------------
# The real workflows
# ---------------------------------------------------------------------------


def test_repository_workflows_pass_the_audit(capsys):
    assert audit_mod.workflow_files(_REPO), "no workflows found to audit"
    violations = audit_mod.audit(_REPO)
    assert violations == [], "\n".join(str(v) for v in violations)
    assert audit_mod.main(["--root", str(_REPO)]) == 0
    assert "no violations" in capsys.readouterr().out


def test_allowlist_entries_all_have_reasons():
    for pattern, entry in audit_mod.ACTION_ALLOWLIST.items():
        assert entry.reason.strip(), pattern
    for name, reason in audit_mod.SCHEDULE_ALLOWLIST.items():
        assert reason.strip(), name


# ---------------------------------------------------------------------------
# Baseline and CLI
# ---------------------------------------------------------------------------


def test_clean_workflow_passes(tmp_path):
    _write(tmp_path, "clean.yml", CLEAN)
    assert _rules(tmp_path) == []
    assert audit_mod.main(["--root", str(tmp_path)]) == 0


def test_main_reports_per_file_and_fails(tmp_path, capsys):
    _write(tmp_path, "clean.yml", CLEAN)
    _write(
        tmp_path,
        "bad.yaml",
        """
        on:
          schedule:
            - cron: "0 0 * * *"
        jobs:
          a:
            runs-on: ubuntu-latest-32-core
            steps: []
        """,
    )
    assert audit_mod.main(["--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "bad.yaml:" in out
    assert "clean.yml" not in out
    assert "schedule" in out and "ubuntu-latest-32-core" in out
    assert "FAILED: 2 violation(s)" in out


def test_main_errors_when_there_are_no_workflows(tmp_path):
    assert audit_mod.main(["--root", str(tmp_path)]) == 2


def test_unparseable_workflow_is_a_violation(tmp_path):
    _write(tmp_path, "broken.yml", "on: [push\njobs: {\n")
    assert _rules(tmp_path) == ["parse-error"]


# ---------------------------------------------------------------------------
# Rule 1: *-core runner labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "runs_on",
    [
        "ubuntu-latest-32-core",
        "[self-hosted, windows-latest-32-arm-core]",
        "${{ inputs.arch == 'arm64' && 'windows-latest-32-arm-core' || 'windows-latest-32-core' }}",
    ],
)
def test_core_runner_literal_is_flagged(tmp_path, runs_on):
    _write(
        tmp_path,
        "w.yml",
        f"""
        on: workflow_dispatch
        jobs:
          a:
            runs-on: {runs_on}
            steps: []
        """,
    )
    assert set(_rules(tmp_path)) == {"runner-core"}


def test_core_runner_in_matrix_is_flagged(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        on: workflow_dispatch
        jobs:
          a:
            strategy:
              matrix:
                include:
                  - platform: linux/amd64
                    runner: ubuntu-latest
                  - platform: linux/arm64
                    runner: ubuntu-latest-32-arm-core
            runs-on: ${{ matrix.runner }}
            steps: []
          b:
            strategy:
              matrix:
                target:
                  - {arch: x64, runner: windows-latest-32-core}
            runs-on: ${{ matrix.target.runner }}
            steps: []
        """,
    )
    violations = audit_mod.audit(tmp_path)
    assert [(v.rule, v.where) for v in violations] == [
        ("runner-core", "jobs.a"),
        ("runner-core", "jobs.b"),
    ]


def test_matrix_core_string_unrelated_to_runner_is_ignored(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        on: workflow_dispatch
        jobs:
          a:
            strategy:
              matrix:
                suite: [e2e-desktop-core]
                runner: [ubuntu-latest]
            runs-on: ${{ matrix.runner }}
            steps: []
        """,
    )
    assert _rules(tmp_path) == []


def test_core_runner_in_input_default_is_flagged(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        on:
          workflow_call:
            inputs:
              runner:
                type: string
                default: windows-latest-32-core
        jobs:
          a:
            runs-on: ${{ inputs.runner }}
            steps: []
        """,
    )
    assert _rules(tmp_path) == ["runner-core"]


def test_core_runner_passed_to_reusable_workflow_is_flagged(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        on: workflow_dispatch
        jobs:
          a:
            uses: ./.github/workflows/run.yml
            with:
              runner: ubuntu-latest-96-core
              name: hermes-core
        """,
    )
    assert _rules(tmp_path) == ["runner-core"]


def test_standard_runners_pass(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        on: workflow_dispatch
        jobs:
          a:
            strategy:
              matrix:
                runner: [ubuntu-latest, ubuntu-24.04-arm, windows-latest, macos-latest]
            runs-on: ${{ matrix.runner }}
            steps: []
        """,
    )
    assert _rules(tmp_path) == []


# ---------------------------------------------------------------------------
# Rule 2: schedule triggers
# ---------------------------------------------------------------------------


def test_schedule_is_flagged(tmp_path):
    _write(
        tmp_path,
        "canary-release.yml",
        """
        on:
          schedule:
            - cron: "41 6 * * *"
          workflow_dispatch:
        jobs: {}
        """,
    )
    violations = audit_mod.audit(tmp_path)
    assert [v.rule for v in violations] == ["schedule"]
    assert "41 6 * * *" in violations[0].detail


def test_schedule_allowed_for_osv_scanner_only(tmp_path):
    body = """
    on:
      schedule:
        - cron: "0 3 * * 1"
      workflow_dispatch:
    jobs: {}
    """
    _write(tmp_path, "osv-scanner.yml", body)
    assert _rules(tmp_path) == []
    _write(tmp_path, "osv-scanner-weekly.yml", body)
    assert _rules(tmp_path) == ["schedule"]


def test_schedule_in_trigger_list_is_flagged(tmp_path):
    _write(tmp_path, "w.yml", "on: [schedule, workflow_dispatch]\njobs: {}\n")
    assert _rules(tmp_path) == ["schedule"]


# ---------------------------------------------------------------------------
# Rule 3: tag-push triggers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["tags", "tags-ignore"])
def test_push_tags_is_flagged(tmp_path, key):
    _write(
        tmp_path,
        "w.yml",
        f"""
        on:
          push:
            {key}:
              - "v*"
        jobs: {{}}
        """,
    )
    assert _rules(tmp_path) == ["push-tags"]


def test_push_tags_alongside_branches_is_flagged(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        on:
          push:
            branches: [main]
            tags: ["v*"]
        jobs: {}
        """,
    )
    assert _rules(tmp_path) == ["push-tags"]


@pytest.mark.parametrize("on", ["push", "[push, pull_request]", "\n  push:\n"])
def test_bare_push_is_flagged_because_it_fires_on_tags(tmp_path, on):
    _write(tmp_path, "w.yml", f"on: {on}\njobs: {{}}\n")
    assert _rules(tmp_path) == ["push-tags"]


def test_push_with_branch_filter_passes(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        on:
          push:
            branches-ignore: [gh-pages]
        jobs: {}
        """,
    )
    assert _rules(tmp_path) == []


# ---------------------------------------------------------------------------
# PyYAML parses a bare `on` key as boolean True
# ---------------------------------------------------------------------------


def test_on_key_parsed_as_true_is_still_checked(tmp_path):
    path = _write(
        tmp_path,
        "w.yml",
        """
        on:
          schedule:
            - cron: "0 0 * * *"
          push:
            tags: ["v*"]
        jobs: {}
        """,
    )
    import yaml

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert True in doc and "on" not in doc  # the quirk this test relies on
    assert sorted(_rules(tmp_path)) == ["push-tags", "schedule"]


def test_quoted_on_key_is_checked(tmp_path):
    _write(
        tmp_path,
        "w.yml",
        """
        "on":
          schedule:
            - cron: "0 0 * * *"
        jobs: {}
        """,
    )
    assert _rules(tmp_path) == ["schedule"]


# ---------------------------------------------------------------------------
# Rule 4: action allowlist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "action",
    [
        "actions/checkout@v4",
        "actions/cache/restore@0123456789abcdef0123456789abcdef01234567",
        "github/codeql-action/upload-sarif@v3",
        "docker/build-push-action@v6",
        "astral-sh/setup-uv@v6",
        "./.github/actions/retry",
    ],
)
def test_allowed_actions_pass(tmp_path, action):
    _write(
        tmp_path,
        "w.yml",
        f"""
        on: workflow_dispatch
        jobs:
          a:
            runs-on: ubuntu-latest
            steps:
              - uses: {action}
        """,
    )
    assert _rules(tmp_path) == []


@pytest.mark.parametrize(
    "action",
    [
        "hadolint/hadolint-action@v3",
        "ludeeus/action-shellcheck@master",
        "azure/login@v2",
        "actions-rs/toolchain@v1",  # owner prefix lookalike, not actions/*
        "docker://alpine:3.20",
    ],
)
def test_unlisted_actions_are_flagged(tmp_path, action):
    _write(
        tmp_path,
        "w.yml",
        f"""
        on: workflow_dispatch
        jobs:
          a:
            runs-on: ubuntu-latest
            steps:
              - name: Lint
                uses: {action}
        """,
    )
    violations = audit_mod.audit(tmp_path)
    assert [v.rule for v in violations] == ["action-not-allowed"]
    assert "step 'Lint'" in violations[0].where


def test_file_scoped_allowlist_entry(tmp_path):
    body = """
    on: workflow_dispatch
    jobs:
      a:
        runs-on: ubuntu-latest
        steps:
          - uses: cachix/install-nix-action@v31
    """
    _write(tmp_path, "nix.yml", body)
    assert _rules(tmp_path) == []
    _write(tmp_path, "other.yml", body)
    assert _rules(tmp_path) == ["action-not-allowed"]


# ---------------------------------------------------------------------------
# Rule 5: external reusable workflows
# ---------------------------------------------------------------------------


def test_external_reusable_workflow_is_flagged(tmp_path):
    _write(
        tmp_path,
        "osv-scanner.yml",
        """
        on: workflow_call
        jobs:
          scan:
            uses: google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@v2
        """,
    )
    violations = audit_mod.audit(tmp_path)
    assert [v.rule for v in violations] == ["external-reusable"]
    assert violations[0].where == "jobs.scan"


def test_local_reusable_workflow_passes(tmp_path):
    _write(
        tmp_path,
        "ci.yaml",
        """
        on:
          pull_request:
        jobs:
          tests:
            uses: ./.github/workflows/tests.yml
            secrets: inherit
        """,
    )
    assert _rules(tmp_path) == []
