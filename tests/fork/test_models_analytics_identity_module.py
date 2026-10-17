"""Fork-owned tests: ``hermes_cli/models_analytics_identity.py``.

The end-to-end Models-page cases live in
``tests/hermes_cli/test_models_analytics_identity.py``; these pin the module
and the hook the analytics endpoint uses.
"""

import pytest

from hermes_cli import models_analytics_identity as mai


def _row(model, provider, task="", **usage):
    row = {"model": model, "billing_provider": provider}
    if task:
        row["aux_task"] = task
    row.update(usage)
    return row


def test_bare_custom_folds_into_single_named_row():
    rows = mai.fold_custom_provider_spellings([
        _row("m", "custom", input_tokens=10, output_tokens=5, sessions=1, tool_calls=2, last_used_at=7),
        _row("m", "custom:box", input_tokens=1, output_tokens=1, sessions=1, last_used_at=3),
    ])
    assert len(rows) == 1
    r = rows[0]
    assert r["billing_provider"] == "custom:box"
    assert (r["input_tokens"], r["output_tokens"], r["sessions"], r["tool_calls"]) == (11, 6, 2, 2)
    assert r["last_used_at"] == 7
    assert r["avg_tokens_per_session"] == pytest.approx(17 / 2)


def test_tasks_and_ambiguous_endpoints_stay_separate():
    rows = mai.fold_custom_provider_spellings([
        _row("m", "custom", sessions=1),
        _row("m", "custom:a", sessions=1),
        _row("m", "custom:b", sessions=1),
        _row("m", "custom", task="compression", sessions=1),
        _row("m", "openrouter", sessions=1),
    ])
    assert sorted((r["billing_provider"], r.get("aux_task", "")) for r in rows) == [
        ("custom", ""), ("custom", "compression"), ("custom:a", ""), ("custom:b", ""), ("openrouter", ""),
    ]


def test_non_custom_rows_in_a_folded_group_are_kept():
    rows = mai.fold_custom_provider_spellings([
        _row("m", "custom:box", sessions=1),
        _row("m", "openrouter", sessions=1),
    ])
    assert {r["billing_provider"] for r in rows} == {"custom:box", "openrouter"}


def test_count_shown_models_counts_distinct_names():
    assert mai.count_shown_models([{"model": "a"}, {"model": "a"}, {"model": "b"}]) == 2
    assert mai.count_shown_models([]) == 0


def test_web_server_keeps_the_legacy_name():
    from hermes_cli import web_server

    assert web_server._fold_custom_provider_spellings is mai.fold_custom_provider_spellings
