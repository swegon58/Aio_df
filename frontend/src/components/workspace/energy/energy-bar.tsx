"use client";

import { ZapIcon } from "lucide-react";

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useI18n } from "@/core/i18n/hooks";
import { formatTimeUntil } from "@/core/usage/api";
import type { UsageCredits, UsageRateLimit } from "@/core/usage/types";
import { cn } from "@/lib/utils";

const LOW_FRACTION = 0.2;

function interp(template: string, vars: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => vars[k] ?? `{${k}}`);
}

type Tone = "normal" | "low" | "empty";

// Accent-aware by default (follows the user's chosen accent via --primary);
// only shifts to amber (running low) or red (exhausted) as a warning.
const TONE_CLASSES: Record<Tone, { text: string; icon: string; fill: string }> =
  {
    normal: {
      text: "",
      icon: "text-primary",
      fill: "bg-primary",
    },
    low: {
      text: "text-amber-600 dark:text-amber-400",
      icon: "text-amber-500",
      fill: "bg-amber-500",
    },
    empty: {
      text: "text-destructive",
      icon: "text-destructive",
      fill: "bg-destructive",
    },
  };

/**
 * Energy meter: an accent-coloured bar + integer readout ("⚡ 312 / 500").
 * Follows the user's accent colour, shifting to amber when running low and red
 * when exhausted. Hovering reveals regeneration + rate-limit detail. Used in the
 * chat right-panel and the Settings → Plan tab; `compact` moves the hint below.
 */
export function EnergyBar({
  credits,
  unitName = "Energy",
  rateLimit,
  compact = false,
  showIcon = true,
  className,
}: {
  credits: UsageCredits;
  unitName?: string;
  rateLimit?: UsageRateLimit | null;
  compact?: boolean;
  showIcon?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  const max = Math.max(1, credits.max);
  const value = Math.max(0, credits.balance_display);
  const fraction = Math.min(1, value / max);
  const tone: Tone = credits.exhausted
    ? "empty"
    : fraction <= LOW_FRACTION
      ? "low"
      : "normal";
  const c = TONE_CLASSES[tone];

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

  const bar = (
    <div className={cn("flex w-full flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between text-sm">
        <span
          className={cn(
            "flex items-center gap-1 font-medium tabular-nums",
            c.text,
          )}
        >
          {showIcon && (
            <ZapIcon className={cn("size-3.5", c.icon)} aria-hidden />
          )}
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

      <div className="bg-primary/20 h-1.5 w-full overflow-hidden rounded-full">
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-500",
            c.fill,
          )}
          style={{ width: `${Math.max(2, fraction * 100)}%` }}
        />
      </div>

      {compact && (
        <span className="text-muted-foreground text-[11px]">{hint}</span>
      )}
    </div>
  );

  const windows = rateLimit?.enabled ? rateLimit.windows : [];

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="w-full cursor-default">{bar}</div>
      </TooltipTrigger>
      <TooltipContent className="max-w-56 space-y-1">
        <p>{hint}</p>
        {credits.regen_per_hour > 0 && (
          <p className="text-muted-foreground">
            {interp(t.settings.plan.energyRegen, {
              rate: String(Math.round(credits.regen_per_hour)),
            })}
          </p>
        )}
        {windows.map((w) => (
          <p key={w.seconds} className="text-muted-foreground tabular-nums">
            {interp(t.settings.plan.rateWindow, {
              used: String(w.used),
              limit: String(w.limit),
              minutes: String(Math.round(w.seconds / 60)),
            })}
          </p>
        ))}
      </TooltipContent>
    </Tooltip>
  );
}
