"""Tests for .github/scripts/fork_release_version.py (fork release versioning)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "fork_release_version.py"
TEMPLATE = REPO_ROOT / ".github" / "release-notes-template.md"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-on-merge.yml"


def _load():
    spec = importlib.util.spec_from_file_location("fork_release_version", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


frv = _load()

UPSTREAM_COMMIT = "4ccc58062c" + "0" * 30


@pytest.fixture
def pyproject(tmp_path):
    def write(version: str) -> Path:
        path = tmp_path / "pyproject.toml"
        path.write_text(f'[project]\nname = "hermes-agent"\nversion = "{version}"\n', encoding="utf-8")
        return path

    return write


# --- upstream-release mode ---------------------------------------------------


def test_upstream_release_first_cut_is_forgeguard_1(pyproject):
    result = frv.compute(
        base_tag="v0.22.2",
        pyproject=pyproject("0.0.0"),
        remote_tags=["v0.21.1", "v0.21.1-forgeguard.2", "v2026.8.31"],
        release_tags=[],
    )
    assert result.mode == "upstream-release"
    assert result.version == "v0.22.2-forgeguard.1"
    assert result.hermes_version == "0.22.2"
    assert result.base_tag == "v0.22.2"


def test_upstream_release_counts_remote_tags_from_ls_remote_output(pyproject):
    ls_remote = [
        "aaaa\trefs/tags/v0.22.2-forgeguard.1",
        "bbbb\trefs/tags/v0.22.2-forgeguard.3",
        "cccc\trefs/tags/v0.22.2-forgeguard.3^{}",
        "dddd\trefs/tags/v0.22.2-forgeguard.9-hotfix1",
        "eeee\trefs/tags/v0.22.20-forgeguard.7",
        "ffff\trefs/tags/v0.22.2",
    ]
    result = frv.compute(
        base_tag="v0.22.2", pyproject=pyproject("0.0.0"), remote_tags=ls_remote, release_tags=[]
    )
    # Odd suffixes, other versions and the upstream's own plain tag don't count.
    assert result.version == "v0.22.2-forgeguard.4"


def test_upstream_release_ignores_release_list_and_version_files(pyproject):
    result = frv.compute(
        base_tag="v0.22.2",
        pyproject=pyproject("9.9.9"),
        remote_tags=[],
        release_tags=["v0.22.2-forgeguard.5"],
    )
    assert result.version == "v0.22.2-forgeguard.1"


def test_upstream_release_restarts_n_for_a_new_upstream_release(pyproject):
    result = frv.compute(
        base_tag="v0.23.0",
        pyproject=pyproject("0.0.0"),
        remote_tags=["v0.22.2-forgeguard.1", "v0.22.2-forgeguard.2"],
        release_tags=[],
    )
    assert result.version == "v0.23.0-forgeguard.1"


def test_upstream_release_carries_upstream_commit(pyproject):
    result = frv.compute(
        base_tag="v0.22.2",
        pyproject=pyproject("0.0.0"),
        remote_tags=[],
        release_tags=[],
        upstream_commit=UPSTREAM_COMMIT,
    )
    assert result.outputs()["upstream_commit"] == UPSTREAM_COMMIT


def test_upstream_release_refuses_zero(pyproject):
    with pytest.raises(frv.ReleaseVersionError, match="0.0.0"):
        frv.compute(base_tag="v0.0.0", pyproject=pyproject("0.0.0"), remote_tags=[], release_tags=[])


# --- legacy mode (today's behaviour, unchanged) -------------------------------


def test_legacy_calendar_base_uses_pyproject_plain_tag(pyproject):
    result = frv.compute(
        base_tag="v2026.8.31",
        pyproject=pyproject("0.21.1"),
        remote_tags=["v0.21.1"],  # remote tags are not consulted in legacy mode
        release_tags=["v0.21.0", "v0.20.9-forgeguard.2"],
    )
    assert result.mode == "legacy"
    assert result.version == "v0.21.1"
    assert result.hermes_version == "0.21.1"
    assert result.base_tag == "v2026.8.31"


def test_legacy_recut_counts_plain_tag_as_cut_one(pyproject):
    result = frv.compute(
        base_tag="v2026.8.31", pyproject=pyproject("0.21.1"), remote_tags=[], release_tags=["v0.21.1"]
    )
    assert result.version == "v0.21.1-forgeguard.2"


def test_legacy_recut_skips_odd_suffixes(pyproject):
    result = frv.compute(
        base_tag="v2026.8.31",
        pyproject=pyproject("0.21.1"),
        remote_tags=[],
        release_tags=["v0.21.1", "v0.21.1-forgeguard.3", "v0.21.1-forgeguard.5-hotfix1"],
    )
    assert result.version == "v0.21.1-forgeguard.4"


@pytest.mark.parametrize("base", ["v2026.8.31", "v2026.8.16.2", "v0.22.2-rc.1", "release-x"])
def test_non_release_bases_are_legacy(base, pyproject):
    result = frv.compute(base_tag=base, pyproject=pyproject("0.21.1"), remote_tags=[], release_tags=[])
    assert result.mode == "legacy"
    assert result.version == "v0.21.1"


@pytest.mark.parametrize("version", ["0.0.0", ""])
def test_legacy_refuses_zero_or_empty_version(version, pyproject):
    # The state right after the sync if FORK_UPSTREAM_BASE were left on a
    # calendar base: version files say 0.0.0 → refuse, don't release v0.0.0.
    with pytest.raises(frv.ReleaseVersionError, match="refusing to release"):
        frv.compute(base_tag="v2026.8.31", pyproject=pyproject(version), remote_tags=[], release_tags=[])


def test_empty_base_is_refused(pyproject):
    with pytest.raises(frv.ReleaseVersionError):
        frv.compute(base_tag="  ", pyproject=pyproject("0.21.1"), remote_tags=[], release_tags=[])


# --- FORK_UPSTREAM_COMMIT ------------------------------------------------------


def test_upstream_commit_file_optional(tmp_path):
    assert frv.read_upstream_commit(tmp_path / "FORK_UPSTREAM_COMMIT") == ""


def test_upstream_commit_file_read_and_normalised(tmp_path):
    path = tmp_path / "FORK_UPSTREAM_COMMIT"
    path.write_text(UPSTREAM_COMMIT.upper() + "\n", encoding="utf-8")
    assert frv.read_upstream_commit(path) == UPSTREAM_COMMIT


def test_upstream_commit_file_rejects_garbage(tmp_path):
    path = tmp_path / "FORK_UPSTREAM_COMMIT"
    path.write_text("v0.22.2\n", encoding="utf-8")
    with pytest.raises(frv.ReleaseVersionError):
        frv.read_upstream_commit(path)


# --- CLI -------------------------------------------------------------------------


def test_cli_writes_outputs(tmp_path, pyproject, capsys):
    tags = tmp_path / "remote-tags.txt"
    tags.write_text("x\trefs/tags/v0.22.2-forgeguard.1\n", encoding="utf-8")
    commit = tmp_path / "FORK_UPSTREAM_COMMIT"
    commit.write_text(UPSTREAM_COMMIT + "\n", encoding="utf-8")
    out = tmp_path / "github-output"
    rc = frv.main(
        [
            "version",
            "--base-tag", "v0.22.2",
            "--pyproject", str(pyproject("0.0.0")),
            "--upstream-commit-file", str(commit),
            "--remote-tags", str(tags),
            "--release-tags", str(tmp_path / "missing.txt"),
            "--output", str(out),
        ]
    )
    assert rc == 0
    outputs = dict(line.split("=", 1) for line in out.read_text(encoding="utf-8").splitlines())
    assert outputs == {
        "mode": "upstream-release",
        "version": "v0.22.2-forgeguard.2",
        "base_tag": "v0.22.2",
        "hermes_version": "0.22.2",
        "upstream_commit": UPSTREAM_COMMIT,
    }
    assert "::notice::Computed release version: v0.22.2-forgeguard.2" in capsys.readouterr().out


def test_cli_refusal_exits_nonzero_and_writes_nothing(tmp_path, pyproject, capsys):
    out = tmp_path / "github-output"
    rc = frv.main(
        [
            "version",
            "--base-tag", "v2026.8.31",
            "--pyproject", str(pyproject("0.0.0")),
            "--upstream-commit-file", str(tmp_path / "none"),
            "--output", str(out),
        ]
    )
    assert rc == 1
    assert not out.exists()
    assert "::error::" in capsys.readouterr().out


def test_repo_markers_compute_a_releasable_version():
    """Whatever mode the checked-in markers select, it must not refuse."""
    base = (REPO_ROOT / "FORK_UPSTREAM_BASE").read_text(encoding="utf-8").strip()
    result = frv.compute(
        base_tag=base,
        pyproject=REPO_ROOT / "pyproject.toml",
        remote_tags=[],
        release_tags=[],
        upstream_commit=frv.read_upstream_commit(REPO_ROOT / "FORK_UPSTREAM_COMMIT"),
    )
    assert result.version.startswith("v")


# --- release notes -----------------------------------------------------------------


def _notes(**overrides):
    kwargs = dict(
        version="v0.22.2-forgeguard.1",
        base_tag="v0.22.2",
        hermes_version="0.22.2",
        upstream_commit=UPSTREAM_COMMIT,
        pr_number="42",
        runtime_digest="sha256:" + "a" * 64,
    )
    kwargs.update(overrides)
    return frv.render_notes(TEMPLATE.read_text(encoding="utf-8"), **kwargs)


def test_notes_fill_every_token():
    notes = _notes()
    assert "__" not in notes.replace("__init__", "")
    assert "merge of #42 into `main`" in notes
    assert "**Upstream release:** [v0.22.2](" in notes
    assert "[`4ccc58062c`](https://github.com/NousResearch/hermes-agent/commit/" + UPSTREAM_COMMIT in notes
    assert "docker pull ghcr.io/forgeguard-ai/hermes-agent:runtime-v0.22.2-forgeguard.1" in notes
    assert "ghcr.io/forgeguard-ai/hermes-agent@sha256:" + "a" * 64 in notes


def test_notes_placeholders_when_commit_digest_and_pr_unknown():
    notes = _notes(upstream_commit="", runtime_digest="", pr_number="")
    assert "/commit/" not in notes
    assert frv.NOTES_PLACEHOLDER_DIGEST in notes
    assert "manual run of the release workflow" in notes


def test_workflow_uses_the_script_and_template():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert ".github/scripts/fork_release_version.py version" in text
    assert ".github/release-notes-template.md" in text
    assert "dry_run" in text
    # The old version-file read must not come back: after the sync it yields 0.0.0.
    assert "grep -m1 '^version' pyproject.toml" not in text
