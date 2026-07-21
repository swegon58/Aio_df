/** Response shape of `GET /api/usage` (per-user Energy + rate limit). */
export interface UsageCredits {
  enabled: boolean;
  /** Effective Energy balance (may be fractional; may be negative on overdraft). */
  balance: number;
  /** Floor of balance, clamped at 0 — the number to show as the headline. */
  balance_display: number;
  /** Maximum Energy (bar capacity). */
  max: number;
  /** Continuous regeneration per hour, in Energy. */
  regen_per_hour: number;
  /** ISO timestamp when the bar refills to max, or null if full / no regen. */
  next_full_at: string | null;
  /** True when the balance is at/under the minimum needed to start a run. */
  exhausted: boolean;
}

export interface UsageRateWindow {
  seconds: number;
  limit: number;
  used: number;
  resets_at: string | null;
}

export interface UsageRateLimit {
  enabled: boolean;
  windows: UsageRateWindow[];
}

export interface UsageState {
  enabled: boolean;
  /** Display name of the unit (default "Energy"). */
  unit_name: string;
  credits: UsageCredits | null;
  rate_limit: UsageRateLimit | null;
}
