"use client";

import { ZapIcon } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { useUsage } from "@/core/usage/hooks";

import { EnergyBar } from "./energy-bar";

/**
 * Energy card for the chat right-panel. Mirrors the agent-status card
 * (glass-surface + round icon badge) so the two read as a set. Renders nothing
 * when the feature is off or the user is exempt, so exempt/admin views stay
 * clean instead of showing an empty placeholder.
 */
export function EnergyPanelCard() {
  const { data: usage, isLoading } = useUsage();

  if (isLoading && !usage) {
    return (
      <div className="glass-surface flex items-center gap-3 rounded-lg p-4">
        <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-1.5 w-full rounded-full" />
        </div>
      </div>
    );
  }

  if (!usage?.enabled || !usage.credits?.enabled) {
    return null;
  }

  return (
    <div className="glass-surface flex items-center gap-3 rounded-lg p-4">
      <div className="icon-badge-glass flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
        <ZapIcon className="text-primary size-5" />
      </div>
      <EnergyBar
        credits={usage.credits}
        unitName={usage.unit_name}
        rateLimit={usage.rate_limit}
        showIcon={false}
      />
    </div>
  );
}
