"""Fork-owned identity rules for the dashboard Models page analytics.

The Models page shows one card per (model, endpoint, auxiliary task). The
server half of that rule lives here so the analytics endpoint only carries
thin calls:

* :func:`fold_custom_provider_spellings` — one card per custom endpoint even
  when its usage was recorded under two provider spellings.
* :func:`count_shown_models` — the header's model count matches the cards.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

ANALYTICS_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "reasoning_tokens",
    "estimated_cost",
    "actual_cost",
    "sessions",
    "api_calls",
    "tool_calls",
)


def fold_custom_provider_spellings(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fold bare ``custom`` rows into the one named ``custom:<name>`` row.

    The same custom endpoint is recorded under two spellings: an agent built
    from config stores ``billing_provider="custom"`` (the runtime provider),
    while a mid-session model switch stores the picker's named slug
    (``custom:<name>``). Grouping by billing_provider then gives the Models
    page two cards for one model on one endpoint. Within one (model, task)
    group, bare ``custom`` rows merge into the named row when exactly one
    named ``custom:`` row exists; two or more named rows are different
    endpoints, so the bare rows are ambiguous and stay as they are.
    """
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in rows:
        key = (row.get("model") or "", row.get("aux_task") or "")
        groups.setdefault(key, []).append(row)

    out: List[Dict[str, Any]] = []
    for group in groups.values():
        named = [
            r for r in group
            if str(r.get("billing_provider") or "").startswith("custom:")
        ]
        if len(named) != 1:
            out.extend(group)
            continue
        target = named[0]
        for row in group:
            if row is target:
                continue
            if row.get("billing_provider") != "custom":
                out.append(row)
                continue
            for k in ANALYTICS_USAGE_KEYS:
                target[k] = (target.get(k) or 0) + (row.get(k) or 0)
            target["last_used_at"] = max(
                target.get("last_used_at") or 0, row.get("last_used_at") or 0
            )
        sessions = target.get("sessions") or 0
        total = (target.get("input_tokens") or 0) + (target.get("output_tokens") or 0)
        target["avg_tokens_per_session"] = total / sessions if sessions else 0
        out.append(target)
    return out


def count_shown_models(models: Iterable[Dict[str, Any]]) -> int:
    """Distinct model names across the cards the page shows.

    Main-loop and auxiliary-only models alike: a sessions-table count sees
    main-loop models only, so the header could read "3 models used" over
    cards naming more.
    """
    return len({m["model"] for m in models})
