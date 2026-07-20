"""In-run Energy credit enforcement (stop-loss, not a biller).

Structurally mirrors :class:`~deerflow.agents.middlewares.token_budget_middleware.TokenBudgetMiddleware`,
but the budget is the *user's remaining Energy balance* (in weighted
token-equivalents, plus a configurable overdraft) fetched once per run, and
accumulation converts each model call's tokens through the shared
:func:`~deerflow.runtime.usage.conversion.weighted_tokens` helper so the in-run
math and the post-run settlement math can never diverge.

Behaviour:
  - ``abefore_agent`` reads the remaining budget once (one DB read). ``None``
    (feature off, or an unmetered/exempt user with no balance row) disables
    enforcement for the whole run.
  - ``after_model`` accumulates weighted tokens from new ``AIMessage`` usage
    (diffing so retroactive subagent tokens count once). At ``warn_threshold``
    it queues an in-context warning; at 100% of budget it strips ``tool_calls``
    to force a graceful final answer — the same mechanism token_budget uses, so
    a run out of Energy lands its answer instead of being killed mid-sentence.
  - It never writes to the DB; the authoritative charge happens at settlement.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from deerflow.agents.middlewares.token_budget_middleware import BoundedDict
from deerflow.config.usage_limits_config import CreditsConfig
from deerflow.runtime.usage.conversion import weighted_tokens

logger = logging.getLogger(__name__)

_WARN_MSG = "[ENERGY LOW] You have used about {percent:.0f}% of the Energy available for this run. Wrap up and produce a final answer soon; avoid starting new tool calls unless necessary."
_EXCEEDED_MSG = "[ENERGY EXHAUSTED] This run has used all the Energy available to it. Producing a final answer with the results collected so far."

# Sentinel stored when the run is not enforced (no budget / feature off) so we
# distinguish "not enforced" from "budget of 0".
_UNENFORCED = object()


class CreditBudgetMiddleware(AgentMiddleware[AgentState]):
    """Hard-stop a run that would overrun the user's remaining Energy balance."""

    def __init__(self, config: CreditsConfig) -> None:
        super().__init__()
        self._config = config
        self._lock = threading.Lock()
        self._budget: BoundedDict[str, Any] = BoundedDict(1000)
        self._warned: BoundedDict[str, bool] = BoundedDict(1000)
        self._pending_warnings: BoundedDict[str, list[str]] = BoundedDict(1000)
        self._seen_messages: BoundedDict[str, dict[str, tuple[int, int]]] = BoundedDict(1000)
        self._spent: BoundedDict[str, float] = BoundedDict(1000)

    @classmethod
    def from_config(cls, config: CreditsConfig) -> CreditBudgetMiddleware:
        return cls(config=config)

    def reset(self) -> None:
        with self._lock:
            self._budget.clear()
            self._warned.clear()
            self._pending_warnings.clear()
            self._seen_messages.clear()
            self._spent.clear()

    @staticmethod
    def _get_run_id(runtime: Runtime) -> str:
        ctx = getattr(runtime, "context", None)
        if isinstance(ctx, dict) and "run_id" in ctx:
            return ctx["run_id"]
        return str(id(runtime))

    @staticmethod
    def _resolve_user_id(runtime: Runtime) -> str | None:
        ctx = getattr(runtime, "context", None)
        if isinstance(ctx, dict):
            uid = ctx.get("user_id")
            if uid:
                return str(uid)
        from deerflow.runtime.user_context import get_effective_user_id

        return get_effective_user_id()

    @staticmethod
    def _service():
        """Lazily build a UsageService from the shared session factory (or None)."""
        from deerflow.persistence.engine import get_session_factory

        sf = get_session_factory()
        if sf is None:
            return None
        from deerflow.runtime.usage.service import UsageService

        return UsageService(sf)

    def _clear_run_state(self, run_id: str) -> None:
        with self._lock:
            self._budget.pop(run_id, None)
            self._warned.pop(run_id, None)
            self._pending_warnings.pop(run_id, None)
            self._seen_messages.pop(run_id, None)
            self._spent.pop(run_id, None)

    def _seed_seen(self, state: AgentState, run_id: str) -> None:
        """Mark pre-existing messages as seen so prior runs don't count here."""
        with self._lock:
            seen = self._seen_messages.setdefault(run_id, {})
            self._spent.setdefault(run_id, 0.0)
            for msg in state.get("messages", []):
                if isinstance(msg, AIMessage) and msg.id and hasattr(msg, "usage_metadata"):
                    usage = msg.usage_metadata or {}
                    seen[msg.id] = (usage.get("input_tokens", 0), usage.get("output_tokens", 0))

    @override
    async def abefore_agent(self, state: AgentState, runtime: Runtime) -> None:
        if not self._config.enabled:
            return
        run_id = self._get_run_id(runtime)
        self._seed_seen(state, run_id)
        budget: Any = _UNENFORCED
        service = self._service()
        if service is not None:
            try:
                remaining = await service.remaining_run_budget_tokens(self._resolve_user_id(runtime))
                if remaining is not None:
                    budget = remaining
            except Exception:  # noqa: BLE001 — enforcement must never break a run
                logger.warning("credit budget: failed to read remaining budget for run %s", run_id, exc_info=True)
        with self._lock:
            self._budget[run_id] = budget

    @override
    def before_agent(self, state: AgentState, runtime: Runtime) -> None:
        # Sync graph path: seed message bookkeeping only; without an async DB
        # read we cannot fetch a budget, so this run is left unenforced.
        if not self._config.enabled:
            return
        self._seed_seen(state, self._get_run_id(runtime))

    @override
    def after_agent(self, state: AgentState, runtime: Runtime) -> None:
        if not self._config.enabled:
            return
        self._clear_run_state(self._get_run_id(runtime))

    @override
    async def aafter_agent(self, state: AgentState, runtime: Runtime) -> None:
        self.after_agent(state, runtime)

    def _apply(self, state: AgentState, runtime: Runtime) -> dict | None:
        if not self._config.enabled:
            return None
        messages = state.get("messages", [])
        if not messages:
            return None
        last_msg = messages[-1]
        if not isinstance(last_msg, AIMessage):
            return None

        run_id = self._get_run_id(runtime)
        with self._lock:
            budget = self._budget.get(run_id, _UNENFORCED)
            if budget is _UNENFORCED or not isinstance(budget, (int, float)):
                return None

            seen = self._seen_messages.setdefault(run_id, {})
            spent = self._spent.setdefault(run_id, 0.0)
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.id and hasattr(msg, "usage_metadata"):
                    usage = msg.usage_metadata or {}
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    prev_input, prev_output = seen.get(msg.id, (0, 0))
                    diff_input = max(0, input_tokens - prev_input)
                    diff_output = max(0, output_tokens - prev_output)
                    if diff_input > 0 or diff_output > 0:
                        model_name = (getattr(msg, "response_metadata", {}) or {}).get("model_name")
                        spent += weighted_tokens(diff_input, diff_output, credits=self._config, model_name=model_name)
                        seen[msg.id] = (input_tokens, output_tokens)
            self._spent[run_id] = spent

            if budget <= 0 or spent <= 0:
                if budget <= 0 and spent > 0:
                    # Already overdrawn before the run produced tokens: stop now.
                    return self._build_hard_stop_update(last_msg, _EXCEEDED_MSG)
                return None

            fraction = spent / budget
            if fraction >= 1.0:
                logger.warning("credit budget hard stop for run %s (spent=%.0f budget=%.0f)", run_id, spent, budget)
                return self._build_hard_stop_update(last_msg, _EXCEEDED_MSG)
            if fraction >= self._config.warn_threshold and not self._warned.get(run_id, False):
                self._warned[run_id] = True
                self._pending_warnings.setdefault(run_id, []).append(_WARN_MSG.format(percent=fraction * 100))
            return None

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)

    @staticmethod
    def _append_text(content: str | list | None, stop_msg: str) -> str | list:
        if content is None:
            return stop_msg
        if isinstance(content, str):
            return f"{content}\n\n{stop_msg}" if content else f"\n\n{stop_msg}"
        if isinstance(content, list):
            return list(content) + [{"type": "text", "text": f"\n\n{stop_msg}"}]
        return f"{content}\n\n{stop_msg}"

    def _build_hard_stop_update(self, msg: AIMessage, stop_msg: str) -> dict[str, Any]:
        updated_content = self._append_text(msg.content, stop_msg)
        kwargs = dict(msg.additional_kwargs) if msg.additional_kwargs else {}
        kwargs.pop("tool_calls", None)
        kwargs.pop("function_call", None)
        response_metadata = dict(getattr(msg, "response_metadata", {}) or {})
        if response_metadata.get("finish_reason") == "tool_calls":
            response_metadata["finish_reason"] = "stop"
        stopped = msg.model_copy(update={"content": updated_content, "tool_calls": [], "additional_kwargs": kwargs, "response_metadata": response_metadata})
        return {"messages": [stopped]}

    def _drain_pending_warnings(self, runtime: Runtime) -> list[str]:
        if not self._config.enabled:
            return []
        with self._lock:
            return self._pending_warnings.pop(self._get_run_id(runtime), None) or []

    def _inject_warnings(self, request: ModelRequest, warnings: list[str]) -> ModelRequest:
        if not warnings:
            return request
        warning_msg = HumanMessage(content="\n\n".join(warnings), name="energy_warning")
        new_messages = list(getattr(request, "messages", [])) + [warning_msg]
        return request.override(messages=new_messages)

    @override
    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelCallResult:
        return handler(self._inject_warnings(request, self._drain_pending_warnings(request.runtime)))

    @override
    async def awrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[ModelResponse]]) -> ModelCallResult:
        return await handler(self._inject_warnings(request, self._drain_pending_warnings(request.runtime)))
