import { fetch } from "../api/fetcher";
import { getBackendBaseURL } from "../config";

import type { UsageState } from "./types";

/** Fetch the current user's Energy + rate-limit snapshot. */
export async function fetchUsage(): Promise<UsageState> {
  const res = await fetch(`${getBackendBaseURL()}/api/usage`, {
    method: "GET",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch usage: ${res.status}`);
  }
  return res.json();
}

/** Human-readable "time until X" from an ISO timestamp, e.g. "1h 52m". */
export function formatTimeUntil(iso: string | null): string | null {
  if (!iso) {
    return null;
  }
  const ms = new Date(iso).getTime() - Date.now();
  if (!Number.isFinite(ms) || ms <= 0) {
    return null;
  }
  const totalMinutes = Math.ceil(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}
