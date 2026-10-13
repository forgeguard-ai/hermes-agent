"""Tests for the ``gateway.ping`` liveness RPC.

Desktop clients probe the socket on an interval and treat any reply — even an
error — as proof the connection is alive; only silence (a request timeout)
marks the socket half-dead and forces a reconnect. That contract needs ping
to answer inline with no session/agent access, and it needs unknown methods
(older backends without ping) to still produce an error *reply* rather than
silence.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def server():
    with patch.dict("sys.modules", {
        "hermes_constants": MagicMock(get_hermes_home=MagicMock(return_value="/tmp/hermes_test")),
        "hermes_cli.env_loader": MagicMock(),
        "hermes_cli.banner": MagicMock(),
        "hermes_state": MagicMock(),
    }):
        import importlib
        mod = importlib.import_module("tui_gateway.server")
        yield mod


def test_gateway_ping_replies_ok(server):
    resp = server.handle_request(
        {"jsonrpc": "2.0", "id": 7, "method": "gateway.ping", "params": {}},
    )
    assert resp == {"jsonrpc": "2.0", "id": 7, "result": {"ok": True}}


def test_gateway_ping_is_inline_not_pool_routed(server):
    """Ping exists to prove the transport is alive NOW — routing it through
    the worker pool would let a saturated pool turn a healthy socket into a
    false-dead one."""
    assert "gateway.ping" not in server._LONG_HANDLERS


def test_unknown_method_still_produces_a_reply(server):
    """Older-backend compatibility: clients send gateway.ping regardless of
    server version and rely on the unknown-method ERROR REPLY (not silence)
    to prove liveness."""
    resp = server.handle_request(
        {"jsonrpc": "2.0", "id": 8, "method": "gateway.definitely-not-a-method", "params": {}},
    )
    assert resp["error"]["code"] == -32601
