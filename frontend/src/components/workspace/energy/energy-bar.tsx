"use client";

import { ZapIcon } from "lucide-react";

import { useI18n } from "@/core/i18n/hooks";
import { formatTimeUntil } from "@/core/usage/api";
import type { UsageCredits } from "@/core/usage/types";
import { cn } from "@/lib/utils";

const LOW_FRACTION = 0.2;

function interp(template: string, vars: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => vars[k] ?? `{${k}}`);
}

/**
 * Energy meter: a cyan bar + integer readout ("⚡ 312 / 500"). Turns amber
 * below 20% and reads "Out of Energy" when exhausted. Used both in the Plan
 * settings tab (full) and as a compact sidebar indicator.
 */
export function EnergyBar({
  credits,
  unitName = "Energy",
  compact = false,
  className,
}: {
  credits: UsageCredits;
  unitName?: string;
  compact?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  const max = Math.max(1, credits.max);
  const value = Math.max(0, credits.balance_display);
  const fraction = Math.min(1, value / max);
  const low = fraction <= LOW_FRACTION || credits.exhausted;

  const fullIn = formatTimeUntil(credits.next_full_at);
  let hint: string;
  if (credits.exhausted) {
    hint = t.settings.plan.energyExhausted;
  } else if (!credits.next_full_at || fraction >= 1) {
    hint = t.settings.plan.energyFull;
  } else if (fullIn) {
    hint = interp(t.settings.plan.energyFullIn, { time: fullIn });
  } else {
    hint = interp(t.settings.plan.energyRegen, {
      rate: String(Math.round(credits.regen_per_hour)),
    });
  }

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between text-sm">
        <span
          className={cn(
            "flex items-center gap-1 font-medium tabular-nums",
            low && "text-amber-600 dark:text-amber-400",
          )}
        >
          <ZapIcon
            className={cn("size-3.5", low ? "text-amber-500" : "text-cyan-500")}
            aria-hidden
          />
          {value}
          <span className="text-muted-foreground font-normal">
            {" "}
            {t.settings.plan.energyOf} {Math.round(max)} {unitName}
          </span>
        </span>
        {!compact && (
          <span className="text-muted-foreground text-xs">{hint}</span>
        )}
      </div>

      <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-500",
            low ? "bg-amber-500" : "bg-cyan-500",
          )}
          style={{ width: `${Math.max(2, fraction * 100)}%` }}
        />
      </div>

      {compact && (
        <span className="text-muted-foreground text-[11px]">{hint}</span>
      )}
    </div>
  );
}
