"""Models dashboard: one card per model and endpoint, labelled aux cards,
and a model count that matches the cards.

An agent built from config records a custom endpoint's usage under the
runtime provider ``custom``; a mid-session model switch records the picker's
named slug ``custom:<name>``. Grouping by billing_provider used to give the
Models page two cards for the same model on the same endpoint.
"""
import pytest

from hermes_state import SessionDB


@pytest.fixture
def db(tmp_path):
    return SessionDB(tmp_path / "state.db")


def _row(model, provider, task="", **usage):
    base = {
        "model": model,
        "billing_provider": provider,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "reasoning_tokens": 0,
        "estimated_cost": 0,
        "actual_cost": 0,
        "sessions": 0,
        "api_calls": 0,
        "tool_calls": 0,
        "last_used_at": 0,
        "avg_tokens_per_session": 0,
    }
    if task:
        base["aux_task"] = task
    base.update(usage)
    return base


class TestFoldCustomProviderSpellings:
    def test_bare_custom_folds_into_the_one_named_row(self):
        from hermes_cli.web_server import _fold_custom_provider_spellings

        rows = _fold_custom_provider_spellings([
            _row("m", "custom", input_tokens=100, output_tokens=10, sessions=2, api_calls=3, last_used_at=50),
            _row("m", "custom:gw.example.lan", input_tokens=40, output_tokens=4, sessions=1, api_calls=1, last_used_at=90),
        ])
        assert len(rows) == 1
        r = rows[0]
        assert r["billing_provider"] == "custom:gw.example.lan"
        assert (r["input_tokens"], r["output_tokens"], r["sessions"], r["api_calls"]) == (140, 14, 3, 4)
        assert r["last_used_at"] == 90
        assert r["avg_tokens_per_session"] == pytest.approx(154 / 3)

    def test_two_named_endpoints_leave_bare_custom_alone(self):
        from hermes_cli.web_server import _fold_custom_provider_spellings

        rows = _fold_custom_provider_spellings([
            _row("m", "custom", sessions=1),
            _row("m", "custom:a", sessions=1),
            _row("m", "custom:b", sessions=1),
        ])
        assert sorted(r["billing_provider"] for r in rows) == ["custom", "custom:a", "custom:b"]

    def test_other_models_tasks_and_providers_are_untouched(self):
        from hermes_cli.web_server import _fold_custom_provider_spellings

        rows = _fold_custom_provider_spellings([
            _row("m", "custom", sessions=1),
            _row("other", "custom:gw", sessions=1),  # different model
            _row("m", "openrouter", sessions=1),  # not a custom spelling
            _row("m", "custom", task="compression", sessions=1),  # different task
        ])
        assert len(rows) == 4

    def test_aux_rows_fold_within_their_task(self):
        from hermes_cli.web_server import _fold_custom_provider_spellings

        rows = _fold_custom_provider_spellings([
            _row("m", "custom", task="compression", input_tokens=5, sessions=1),
            _row("m", "custom:gw", task="compression", input_tokens=7, sessions=1),
            _row("m", "custom:gw", input_tokens=1, sessions=1),
        ])
        by_task = {r.get("aux_task", ""): r for r in rows}
        assert set(by_task) == {"", "compression"}
        assert by_task["compression"]["input_tokens"] == 12
        assert by_task["compression"]["billing_provider"] == "custom:gw"


class TestModelsAnalyticsEndpoint:
    def test_one_card_per_endpoint_labelled_aux_and_matching_count(self, db, monkeypatch):
        import hermes_cli.web_server as ws

        db.create_session("built", source="cli")
        db.update_token_counts(
            "built", input_tokens=1000, output_tokens=100,
            model="driver", billing_provider="custom", api_call_count=2,
        )
        db.create_session("switched", source="cli")
        db.update_token_counts(
            "switched", input_tokens=500, output_tokens=50,
            model="driver", billing_provider="custom:gw.example.lan", api_call_count=1,
        )
        db.record_auxiliary_usage(
            "built", "compression", model="driver",
            billing_provider="custom", input_tokens=300, output_tokens=30,
        )
        db.record_auxiliary_usage(
            "built", "vision", model="vision-only",
            billing_provider="custom:gw.example.lan", input_tokens=20, output_tokens=2,
        )

        monkeypatch.setattr(ws, "_open_session_db_for_profile", lambda profile, read_only: db)
        monkeypatch.setattr(db, "close", lambda: None)
        out = ws._get_models_analytics(days=30)

        main = [m for m in out["models"] if not m["aux_task"]]
        assert [(m["model"], m["provider"]) for m in main] == [("driver", "custom:gw.example.lan")]
        assert main[0]["input_tokens"] == 1500
        assert main[0]["sessions"] == 2

        aux = {(m["model"], m["aux_task"]) for m in out["models"] if m["aux_task"]}
        assert aux == {("driver", "compression"), ("vision-only", "vision")}

        # The header counts the models the cards name, aux-only ones included.
        assert out["totals"]["distinct_models"] == 2
