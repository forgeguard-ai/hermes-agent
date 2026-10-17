#!/usr/bin/env python3
"""Audit GitHub Actions workflows for things that break or misbehave on the fork.

Upstream's workflows assume upstream's GitHub organisation: paid larger
runners, scheduled jobs, tag-push releases and third-party actions the
forgeguard-ai org policy does not allow. On the fork each of those fails
silently (a job queued forever on a runner label that never resolves), fails
the whole CI run at startup (a blocked action or external reusable workflow),
or does something the fork never wants (a cron job that tags and drafts
releases). An upstream merge can re-introduce any of them, so this audit runs
on every sync and in the test suite.

Workflow files are named by file name (``tests.yml``); composite actions by
their path under ``.github/`` (``actions/nix-setup/action.yml``). Both forms
are what ``only_in`` and the allowlists match against.

Rules (each violation is reported per file and job; any violation exits 1):

  runner-core        a ``runs-on`` that names a ``*-core`` runner label. Literal
                     labels, lists, and expressions are scanned; when
                     ``runs-on`` reads ``matrix.<key>`` or ``inputs.<key>``, the
                     matrix values / input default and options for that key are
                     scanned too, as are ``runner``-like ``with:`` values passed
                     to a reusable workflow.
  schedule           an ``on: schedule`` trigger outside SCHEDULE_ALLOWLIST.
  push-tags          an ``on: push`` that fires on tag pushes: ``tags`` /
                     ``tags-ignore`` filters, or a bare ``push`` with no branch
                     or tag filter (GitHub runs that on every tag push too).
                     The fork cuts releases from its own pipeline, and its
                     release tags would match upstream's tag patterns.
  release-trigger    an ``on: release`` trigger outside RELEASE_TRIGGER_ALLOWLIST.
                     It would fire on the fork's own GitHub Releases.
  action-not-allowed a step ``uses:`` of an action outside ACTION_ALLOWLIST, in
                     a workflow or in a local composite action
                     (``.github/actions/**/action.yml``). Local actions
                     (``./...``) are always allowed.
  external-reusable  a job-level ``uses:`` of a reusable workflow that is not
                     ``./.github/workflows/...`` in this repository.

Usage:
  python .github/scripts/audit_fork_workflows.py            # this checkout
  python .github/scripts/audit_fork_workflows.py --root DIR # another tree

Only the standard library and PyYAML (already a project dependency) are used.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

# ---------------------------------------------------------------------------
# Policy data. Edit these, not the rule code.
# ---------------------------------------------------------------------------

# Workflow file names allowed to keep an ``on: schedule`` trigger.
SCHEDULE_ALLOWLIST: dict[str, str] = {
    "osv-scanner.yml": "the fork's weekly dependency vulnerability scan",
}

# Workflow file names allowed to keep an ``on: release`` trigger. None today:
# the fork's release pipeline calls its build workflows with workflow_call.
RELEASE_TRIGGER_ALLOWLIST: dict[str, str] = {}


@dataclass(frozen=True)
class AllowedAction:
    reason: str
    only_in: frozenset[str] | None = None


# Step-level actions allowed, as fnmatch patterns over ``owner/repo[/path]``
# (the part before ``@``). Each entry maps to a one-line reason. An entry may
# be limited to specific workflow files with ``only_in``.
ACTION_ALLOWLIST: dict[str, AllowedAction] = {
    # Defaults: GitHub-authored and Docker-authored actions.
    "actions/*": AllowedAction("GitHub-authored actions"),
    "github/*": AllowedAction("GitHub-authored actions (e.g. codeql-action)"),
    "docker/*": AllowedAction("Docker-authored, Marketplace-verified actions"),
    # Non-default entries: each one is a deliberate decision.
    "astral-sh/setup-uv": AllowedAction(
        "uv installer; verified creator, allowed by the org actions policy"
    ),
    "google/osv-scanner-action/osv-scanner-action": AllowedAction(
        "OSV scan run as a direct action (the external reusable workflow is blocked)"
    ),
    "google/osv-scanner-action/osv-reporter-action": AllowedAction(
        "OSV SARIF report step paired with the direct scan action"
    ),
    "cachix/install-nix-action": AllowedAction(
        "nix.yml only: kept to minimise upstream drift; the workflow is "
        "dispatch-only on the fork because the org policy blocks this action",
        only_in=frozenset({"nix.yml"}),
    ),
    "nix-community/cache-nix-action": AllowedAction(
        "nix.yml only: same as cachix/install-nix-action above",
        only_in=frozenset({"nix.yml"}),
    ),
    "DeterminateSystems/nix-installer-action": AllowedAction(
        "nix-setup composite only: inherited from upstream, referenced by no "
        "fork workflow; the org policy would block it if one did",
        only_in=frozenset({"actions/nix-setup/action.yml"}),
    ),
    "cachix/cachix-action": AllowedAction(
        "nix-setup composite only: same as DeterminateSystems/nix-installer-action",
        only_in=frozenset({"actions/nix-setup/action.yml"}),
    ),
}

# A runner label ending in "-core", e.g. ubuntu-latest-32-core,
# windows-latest-32-arm-core.
CORE_LABEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*-core(?![A-Za-z0-9_-])")

_EXPR_REF_RE = re.compile(r"\b(matrix|inputs)\.([A-Za-z0-9_-]+)")
_LOCAL_REUSABLE_PREFIX = "./.github/workflows/"


@dataclass(frozen=True)
class Violation:
    file: str
    rule: str
    where: str
    detail: str

    def __str__(self) -> str:
        loc = f"{self.file} [{self.where}]" if self.where else self.file
        return f"{loc}: {self.rule}: {self.detail}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _triggers(doc: dict[str, Any]) -> Any:
    """Return the ``on:`` value. PyYAML (YAML 1.1) parses a bare ``on`` key
    as boolean True, so look under both."""
    if "on" in doc:
        return doc["on"]
    return doc.get(True)


def _trigger_names(on: Any) -> list[str]:
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return [str(x) for x in on]
    if isinstance(on, dict):
        return [str(k) for k in on]
    return []


def _strings(value: Any) -> Iterator[str]:
    """Every string scalar inside a nested YAML value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _core_labels(value: Any) -> list[str]:
    found: list[str] = []
    for s in _strings(value):
        for m in CORE_LABEL_RE.findall(s):
            if m not in found:
                found.append(m)
    return found


def _matrix_values(job: dict[str, Any], key: str) -> list[Any]:
    strategy = job.get("strategy")
    matrix = strategy.get("matrix") if isinstance(strategy, dict) else None
    if not isinstance(matrix, dict):
        # A matrix given as one expression (fromJSON(...)) can't be resolved
        # statically; the runs-on literal scan still applies.
        return []
    values: list[Any] = []
    if key in matrix:
        values.append(matrix[key])
    for section in ("include", "exclude"):
        entries = matrix.get(section)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and key in entry:
                    values.append(entry[key])
    return values


def _input_values(on: Any, key: str) -> list[Any]:
    if not isinstance(on, dict):
        return []
    values: list[Any] = []
    for trigger in ("workflow_call", "workflow_dispatch"):
        spec = on.get(trigger)
        inputs = spec.get("inputs") if isinstance(spec, dict) else None
        if isinstance(inputs, dict) and isinstance(inputs.get(key), dict):
            for field in ("default", "options"):
                if field in inputs[key]:
                    values.append(inputs[key][field])
    return values


def _action_name(ref: str) -> str:
    return ref.split("@", 1)[0].strip()


def _allowed_action(name: str, workflow: str) -> bool:
    for pattern, entry in ACTION_ALLOWLIST.items():
        if fnmatch.fnmatchcase(name, pattern):
            if entry.only_in is None or workflow in entry.only_in:
                return True
    return False


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def _check_triggers(name: str, on: Any) -> list[Violation]:
    out: list[Violation] = []
    triggers = _trigger_names(on)

    if "schedule" in triggers and name not in SCHEDULE_ALLOWLIST:
        crons = []
        if isinstance(on, dict) and isinstance(on.get("schedule"), list):
            crons = [
                str(e.get("cron"))
                for e in on["schedule"]
                if isinstance(e, dict) and "cron" in e
            ]
        detail = "schedule trigger"
        if crons:
            detail += f" ({', '.join(crons)})"
        detail += "; scheduled runs are not allowed on the fork"
        out.append(Violation(name, "schedule", "on", detail))

    if "release" in triggers and name not in RELEASE_TRIGGER_ALLOWLIST:
        types = []
        if isinstance(on, dict) and isinstance(on.get("release"), dict):
            types = [str(t) for t in (on["release"].get("types") or [])]
        detail = "release trigger"
        if types:
            detail += f" ({', '.join(types)})"
        detail += "; it would fire on the fork's own GitHub Releases"
        out.append(Violation(name, "release-trigger", "on.release", detail))

    if "push" in triggers:
        push = on.get("push") if isinstance(on, dict) else None
        if not isinstance(push, dict):
            push = {}
        tag_filters = [k for k in ("tags", "tags-ignore") if k in push]
        branch_filters = [k for k in ("branches", "branches-ignore") if k in push]
        if tag_filters:
            patterns = []
            for k in tag_filters:
                patterns.extend(str(p) for p in (push.get(k) or []))
            out.append(
                Violation(
                    name,
                    "push-tags",
                    "on.push",
                    f"push {'/'.join(tag_filters)} trigger "
                    f"({', '.join(patterns) or 'any'}); fork releases are cut by "
                    "its own pipeline, never by tag pushes",
                )
            )
        elif not branch_filters:
            out.append(
                Violation(
                    name,
                    "push-tags",
                    "on.push",
                    "push trigger without a branches filter also fires on every "
                    "tag push; add a branches filter",
                )
            )
    return out


def _check_runner(name: str, job_id: str, job: dict[str, Any], on: Any) -> list[Violation]:
    where = f"jobs.{job_id}"
    sources: list[tuple[str, Any]] = []
    runs_on = job.get("runs-on")
    if runs_on is not None:
        sources.append(("runs-on", runs_on))
        for s in _strings(runs_on):
            for kind, key in _EXPR_REF_RE.findall(s):
                if kind == "matrix":
                    for v in _matrix_values(job, key):
                        sources.append((f"strategy.matrix.{key}", v))
                else:
                    for v in _input_values(on, key):
                        sources.append((f"inputs.{key}", v))
    # Runner labels handed to a reusable workflow.
    if isinstance(job.get("uses"), str) and isinstance(job.get("with"), dict):
        for k, v in job["with"].items():
            if "runner" in str(k).lower() or str(k).lower() == "runs-on":
                sources.append((f"with.{k}", v))

    out: list[Violation] = []
    for source, value in sources:
        for label in _core_labels(value):
            out.append(
                Violation(
                    name,
                    "runner-core",
                    where,
                    f"{source} uses larger-runner label '{label}', which does "
                    "not exist on the fork (the job would queue forever)",
                )
            )
    return out


def _check_uses(name: str, job_id: str, job: dict[str, Any]) -> list[Violation]:
    where = f"jobs.{job_id}"
    out: list[Violation] = []

    job_uses = job.get("uses")
    if isinstance(job_uses, str) and not job_uses.strip().startswith(
        _LOCAL_REUSABLE_PREFIX
    ):
        out.append(
            Violation(
                name,
                "external-reusable",
                where,
                f"reusable workflow '{job_uses.strip()}' is outside this "
                "repository; the org policy fails the whole run at startup",
            )
        )

    out.extend(_check_steps(name, where, job.get("steps")))
    return out


def _check_steps(name: str, where: str, steps: Any) -> list[Violation]:
    out: list[Violation] = []
    if not isinstance(steps, list):
        return out
    for i, step in enumerate(steps):
        if not isinstance(step, dict) or not isinstance(step.get("uses"), str):
            continue
        ref = step["uses"].strip()
        if ref.startswith("./"):
            continue
        action = _action_name(ref)
        if not _allowed_action(action, name):
            label = step.get("name") or step.get("id") or f"steps[{i}]"
            out.append(
                Violation(
                    name,
                    "action-not-allowed",
                    f"{where} step '{label}'",
                    f"action '{action}' is not in ACTION_ALLOWLIST",
                )
            )
    return out


def _load(path: Path, name: str) -> tuple[dict[str, Any] | None, list[Violation]]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return None, [Violation(name, "parse-error", "", str(exc).splitlines()[0])]
    if not isinstance(doc, dict):
        return None, [Violation(name, "parse-error", "", "not a YAML mapping")]
    return doc, []


def audit_composite(path: Path, root: Path) -> list[Violation]:
    """Check a local composite action's ``runs.steps[].uses``."""
    name = path.relative_to(root / ".github").as_posix()
    doc, errors = _load(path, name)
    if doc is None:
        return errors
    runs = doc.get("runs")
    if not isinstance(runs, dict):
        return []
    return _check_steps(name, "runs", runs.get("steps"))


def audit_file(path: Path) -> list[Violation]:
    name = path.name
    doc, errors = _load(path, name)
    if doc is None:
        return errors

    on = _triggers(doc)
    out = _check_triggers(name, on)
    jobs = doc.get("jobs")
    if isinstance(jobs, dict):
        for job_id, job in jobs.items():
            if not isinstance(job, dict):
                continue
            out.extend(_check_runner(name, str(job_id), job, on))
            out.extend(_check_uses(name, str(job_id), job))
    return out


def workflow_files(root: Path) -> list[Path]:
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return []
    return sorted(
        p for p in wf_dir.iterdir() if p.is_file() and p.suffix in (".yml", ".yaml")
    )


def composite_action_files(root: Path) -> list[Path]:
    actions_dir = root / ".github" / "actions"
    if not actions_dir.is_dir():
        return []
    return sorted(
        p
        for p in actions_dir.rglob("action.y*ml")
        if p.is_file() and p.name in ("action.yml", "action.yaml")
    )


def audit(root: Path) -> list[Violation]:
    out: list[Violation] = []
    for path in workflow_files(root):
        out.extend(audit_file(path))
    for path in composite_action_files(root):
        out.extend(audit_composite(path, root))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root to audit (default: this checkout)",
    )
    args = parser.parse_args(argv)

    files = workflow_files(args.root)
    if not files:
        print(f"no workflow files under {args.root / '.github' / 'workflows'}", file=sys.stderr)
        return 2

    composites = composite_action_files(args.root)
    scanned = f"{len(files)} workflow files and {len(composites)} composite actions"
    violations = audit(args.root)
    if not violations:
        print(f"fork workflow audit: {scanned}, no violations")
        return 0

    by_file: dict[str, list[Violation]] = {}
    for v in violations:
        by_file.setdefault(v.file, []).append(v)
    for file, items in by_file.items():
        print(f"{file}:")
        for v in items:
            loc = f"[{v.where}] " if v.where else ""
            print(f"  {v.rule}: {loc}{v.detail}")

    counts: dict[str, int] = {}
    for v in violations:
        counts[v.rule] = counts.get(v.rule, 0) + 1
    summary = ", ".join(f"{rule}={n}" for rule, n in sorted(counts.items()))
    print(
        f"\nfork workflow audit FAILED: {len(violations)} violation(s) in "
        f"{len(by_file)} files; scanned {scanned} ({summary})"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
