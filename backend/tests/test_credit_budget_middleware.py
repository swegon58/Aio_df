"""Tests for CreditBudgetMiddleware (in-run Energy stop-loss).

Mirrors tests/test_token_budget_middleware.py. The per-run budget is normally
fetched from the DB in abefore_agent; here we seed ``mw._budget[run_id]``
directly so ``_apply`` can be exercised in isolation.
"""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage

from deerflow.agents.middlewares.credit_budget_middleware import CreditBudgetMiddleware
from deerflow.config.usage_limits_config import CreditsConfig


def _make_runtime(run_id="test-run"):
    runtime = MagicMock()
    runtime.context = {"thread_id": "t1", "run_id": run_id, "user_id": "u1"}
    return runtime


def _ai(id_, input_tk, output_tk, *, tool_calls=None, model="m"):
    return AIMessage(id=id_, content="", tool_calls=tool_calls or [], usage_metadata={"input_tokens": input_tk, "output_tokens": output_tk, "total_tokens": input_tk + output_tk}, response_metadata={"model_name": model})


def _mw(**kw):
    # weights 1/1 and default multiplier 1 unless overridden -> weighted == raw tokens
    cfg = CreditsConfig(input_weight=1.0, output_weight=1.0, warn_threshold=0.8, enabled=True, **kw)
    return CreditBudgetMiddleware.from_config(cfg)


def test_unenforced_run_returns_none():
    mw = _mw()
    # No budget seeded -> _UNENFORCED -> no enforcement.
    state = {"messages": [_ai("m1", 500, 0)]}
    assert mw._apply(state, _make_runtime()) is None


def test_below_threshold_returns_none():
    mw = _mw()
    mw._budget["test-run"] = 1000
    state = {"messages": [_ai("m1", 500, 0)]}
    assert mw._apply(state, _make_runtime()) is None


def test_warning_queued_at_threshold():
    mw = _mw()
    mw._budget["test-run"] = 1000
    # 850 weighted tokens = 85% of 1000 budget.
    state = {"messages": [_ai("m1", 850, 0)]}
    assert mw._apply(state, _make_runtime()) is None
    assert len(mw._pending_warnings["test-run"]) == 1
    assert "ENERGY LOW" in mw._pending_warnings["test-run"][0]


def test_hard_stop_strips_tool_calls_at_budget():
    mw = _mw()
    mw._budget["test-run"] = 1000
    msg = _ai("m1", 1000, 0, tool_calls=[{"name": "x", "args": {}, "id": "c1"}])
    result = mw._apply({"messages": [msg]}, _make_runtime())
    assert result is not None
    stopped = result["messages"][0]
    assert stopped.tool_calls == []
    assert "ENERGY EXHAUSTED" in stopped.content


def test_multiplier_scales_weighted_spend():
    mw = _mw(model_multipliers={"pricey": 3.0})
    mw._budget["test-run"] = 1000
    # 400 tokens * 3.0 = 1200 weighted >= budget -> hard stop.
    msg = _ai("m1", 400, 0, tool_calls=[{"name": "x", "args": {}, "id": "c1"}], model="pricey")
    result = mw._apply({"messages": [msg]}, _make_runtime())
    assert result is not None
    assert result["messages"][0].tool_calls == []


def test_retroactive_subagent_tokens_counted_once():
    mw = _mw()
    mw._budget["test-run"] = 1000
    runtime = _make_runtime()
    msg = _ai("m1", 300, 0)
    mw._apply({"messages": [msg]}, runtime)
    assert mw._spent["test-run"] == 300
    # Same message id re-seen with grown tokens (subagent tokens folded in).
    msg2 = _ai("m1", 500, 0)
    mw._apply({"messages": [msg2]}, runtime)
    assert mw._spent["test-run"] == 500  # counted the +200 diff once, not 300+500


def test_disabled_config_no_op():
    cfg = CreditsConfig(enabled=False)
    mw = CreditBudgetMiddleware.from_config(cfg)
    mw._budget["test-run"] = 10
    assert mw._apply({"messages": [_ai("m1", 999, 0)]}, _make_runtime()) is None


def test_tool_message_history_ignored():
    mw = _mw()
    mw._budget["test-run"] = 1000
    msgs = [_ai("m1", 400, 0), ToolMessage(content="ok", tool_call_id="c1"), _ai("m2", 700, 0)]
    # 400 + 700 = 1100 >= 1000 -> hard stop on the last AIMessage.
    result = mw._apply({"messages": msgs}, _make_runtime())
    assert result is not None
    assert "ENERGY EXHAUSTED" in result["messages"][0].content
