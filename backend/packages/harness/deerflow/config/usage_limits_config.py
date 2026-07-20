"""Config for per-user usage limits: Energy credits + run rate limiting.

Admin-managed via ``config.yaml`` only (no admin API/UI this phase). The whole
subsystem is hot-reloadable because ``get_app_config()`` re-reads the file per
request; every gate/settlement call therefore observes the latest values.

Terminology:
- The **internal** accounting unit is *weighted token-equivalents* (integers).
- **Energy** is a presentation-only unit: ``energy = tokens / tokens_per_unit``.
  Changing ``tokens_per_unit`` rescales *displayed* Energy but never mutates any
  stored token balance, so the display unit can be renamed/rescaled freely.
"""

from pydantic import BaseModel, Field, model_validator


class RateLimitWindow(BaseModel):
    """A single sliding-window run cap (all configured windows must pass)."""

    seconds: int = Field(ge=1, description="Length of the sliding window in seconds.")
    max_runs: int = Field(ge=1, description="Maximum number of runs a user may start within the window.")


class RateLimitConfig(BaseModel):
    """Per-user run rate limiting, evaluated by COUNT over the runs table."""

    enabled: bool = Field(default=True, description="Whether run rate limiting is enforced (only when usage_limits.enabled).")
    windows: list[RateLimitWindow] = Field(
        default_factory=lambda: [
            RateLimitWindow(seconds=300, max_runs=10),
            RateLimitWindow(seconds=86400, max_runs=200),
        ],
        description="Sliding-window run caps. Every window must pass for a run to start.",
    )


class CreditsConfig(BaseModel):
    """Per-user Energy credit balance with continuous lazy regeneration.

    All numeric limits below (``max_balance``, ``initial_balance``,
    ``regen_per_hour``, ``min_start_balance``, ``overdraft_allowance``) are
    expressed in **Energy units**. Internally they are converted to weighted
    tokens via ``tokens_per_unit``.
    """

    enabled: bool = Field(default=True, description="Whether Energy credit enforcement is active (only when usage_limits.enabled).")
    unit_name: str = Field(default="Energy", description="Display-only name of the usage unit. Never affects stored data.")
    tokens_per_unit: int = Field(default=1000, ge=1, description="How many weighted tokens equal one Energy unit (display conversion). Changing this rescales displayed Energy only.")
    input_weight: float = Field(default=1.0, ge=0.0, description="Weighting applied to input tokens when computing weighted-token cost.")
    output_weight: float = Field(default=4.0, ge=0.0, description="Weighting applied to output tokens (output typically costs several times more than input).")
    model_multipliers: dict[str, float] = Field(default_factory=dict, description="Per-model cost multipliers, e.g. {gpt-5: 3.0, qwen3-local: 0.0}. A 0.0 multiplier makes a model free.")
    default_multiplier: float = Field(default=1.0, ge=0.0, description="Multiplier applied to models not present in model_multipliers.")
    max_balance: int = Field(default=500, ge=1, description="Maximum Energy balance (regeneration is capped here).")
    initial_balance: int = Field(default=500, ge=0, description="Energy granted to a first-seen user.")
    regen_per_hour: float = Field(default=25.0, ge=0.0, description="Continuous Energy regeneration per hour, computed lazily. Set to max_balance/24 for a daily-grant feel.")
    min_start_balance: int = Field(default=0, description="A run start is rejected when effective Energy balance is <= this value.")
    in_run_enforcement: bool = Field(default=True, description="Register the in-run CreditBudgetMiddleware that hard-stops a run overrunning the remaining balance.")
    warn_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Fraction of the per-run budget at which a soft warning is injected in-context.")
    overdraft_allowance: int = Field(default=20, ge=0, description="Extra Energy a running run may overshoot beyond the remaining balance before the in-run hard stop triggers.")

    @model_validator(mode="after")
    def _validate(self) -> "CreditsConfig":
        if self.initial_balance > self.max_balance:
            raise ValueError("initial_balance must be <= max_balance")
        return self


class UsageUserOverride(BaseModel):
    """Per-user overrides keyed by email in ``usage_limits.user_overrides``.

    Any field left unset falls back to the global value. ``exempt`` bypasses
    both credits and rate limiting for that user.
    """

    exempt: bool = Field(default=False, description="Exempt this user from both Energy credits and rate limiting.")
    max_balance: int | None = Field(default=None, ge=1, description="Override max Energy balance for this user.")
    initial_balance: int | None = Field(default=None, ge=0, description="Override initial Energy grant for this user.")
    regen_per_hour: float | None = Field(default=None, ge=0.0, description="Override Energy regeneration per hour for this user.")
    rate_limit_windows: list[RateLimitWindow] | None = Field(default=None, description="Override rate-limit windows for this user.")


class UsageLimitsConfig(BaseModel):
    """Top-level ``usage_limits`` section: Energy credits + run rate limiting."""

    enabled: bool = Field(default=False, description="Master switch for the whole usage-limits subsystem.")
    exempt_admins: bool = Field(default=True, description="Users with system_role=admin bypass both credits and rate limiting.")
    credits: CreditsConfig = Field(default_factory=CreditsConfig, description="Energy credit configuration.")
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig, description="Run rate-limit configuration.")
    user_overrides: dict[str, UsageUserOverride] = Field(default_factory=dict, description="Per-user overrides keyed by email address.")
