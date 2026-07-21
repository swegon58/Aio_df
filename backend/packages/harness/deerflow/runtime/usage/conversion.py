"""Pure token <-> Energy conversion math.

Shared by the in-run enforcement middleware and the post-run settlement path so
the "how much did this cost" calculation is defined exactly once.

The **internal accounting unit** is *weighted token-equivalents*:

    weighted = multiplier(model) * (input_tokens * input_weight
                                    + output_tokens * output_weight)

**Energy** is a presentation unit: ``energy = weighted_tokens / tokens_per_unit``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deerflow.config.usage_limits_config import CreditsConfig


def _multiplier(credits: CreditsConfig, model_name: str | None) -> float:
    if model_name and model_name in credits.model_multipliers:
        return credits.model_multipliers[model_name]
    return credits.default_multiplier


def weighted_tokens(input_tokens: int, output_tokens: int, *, credits: CreditsConfig, model_name: str | None) -> float:
    """Weighted token-equivalents for one (model, input, output) slice.

    Returns a float; callers accumulate and round once (see
    :func:`run_charge_tokens_from_completion`) so per-call rounding never
    compounds.
    """
    mult = _multiplier(credits, model_name)
    return mult * (max(0, input_tokens) * credits.input_weight + max(0, output_tokens) * credits.output_weight)


def run_charge_tokens_from_completion(completion: Mapping[str, object], credits: CreditsConfig) -> int:
    """Compute a run's total weighted-token charge from journal completion data.

    Prefers the per-model breakdown (``token_usage_by_model``) so each model's
    multiplier applies to its own tokens. Falls back to the headline
    ``total_input_tokens``/``total_output_tokens`` (with ``default_multiplier``)
    for older rows that predate the per-model column. Rounds up exactly once.
    """
    by_model = completion.get("token_usage_by_model") or {}
    total = 0.0
    if isinstance(by_model, Mapping) and by_model:
        for model, usage in by_model.items():
            if not isinstance(usage, Mapping):
                continue
            total += weighted_tokens(int(usage.get("input_tokens", 0) or 0), int(usage.get("output_tokens", 0) or 0), credits=credits, model_name=str(model))
    else:
        total += weighted_tokens(int(completion.get("total_input_tokens", 0) or 0), int(completion.get("total_output_tokens", 0) or 0), credits=credits, model_name=None)
    return math.ceil(total)


def energy_to_tokens(energy: float, tokens_per_unit: int) -> int:
    """Convert an Energy amount (config-facing) to weighted tokens (stored)."""
    return int(round(energy * tokens_per_unit))


def tokens_to_energy(tokens: float, tokens_per_unit: int) -> float:
    """Convert weighted tokens (stored) to Energy (display)."""
    if tokens_per_unit <= 0:
        return 0.0
    return tokens / tokens_per_unit


def accrued_tokens(regen_tokens_per_hour: float, last_regen_at: datetime, now: datetime) -> int:
    """Regeneration accrued (weighted tokens) between ``last_regen_at`` and ``now``.

    Clamped at zero so backwards clocks never subtract. Used on both the read
    path (effective-balance preview, no write) and the write path (settlement,
    inside the transaction) so the two can never disagree.
    """
    if regen_tokens_per_hour <= 0:
        return 0
    elapsed_seconds = (now - last_regen_at).total_seconds()
    if elapsed_seconds <= 0:
        return 0
    return int(regen_tokens_per_hour * (elapsed_seconds / 3600.0))
