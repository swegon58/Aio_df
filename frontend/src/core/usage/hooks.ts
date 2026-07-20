"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchUsage } from "./api";
import type { UsageState } from "./types";

export function usageQueryKey() {
  return ["usage"] as const;
}

/**
 * Poll the per-user Energy / rate-limit snapshot.
 *
 * Polls on a gentle interval (the balance regenerates continuously) and is
 * also invalidated after each run completes so the bar reflects a fresh
 * charge. Returns a disabled state until the backend reports the feature on.
 */
export function useUsage() {
  return useQuery<UsageState>({
    queryKey: usageQueryKey(),
    queryFn: fetchUsage,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    staleTime: 30_000,
    retry: false,
  });
}
