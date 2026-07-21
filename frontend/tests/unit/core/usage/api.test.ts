/**
 * Tests for the usage API client (`GET /api/usage`) and the time-until helper
 * that drives the Energy bar's "Full in …" hint.
 */
import { describe, expect, test, rs } from "@rstest/core";

rs.mock("@/core/api/fetcher", () => ({
  fetch: rs.fn(),
}));

rs.mock("@/core/config", () => ({
  getBackendBaseURL: () => "",
}));

import { fetch as fetcher } from "@/core/api/fetcher";
import { fetchUsage, formatTimeUntil } from "@/core/usage/api";

const mockFetch = fetcher as unknown as ReturnType<typeof rs.fn>;

describe("fetchUsage", () => {
  test("returns the parsed usage snapshot", async () => {
    const payload = {
      enabled: true,
      unit_name: "Energy",
      credits: {
        enabled: true,
        balance: 312.5,
        balance_display: 312,
        max: 500,
        regen_per_hour: 25,
        next_full_at: null,
        exhausted: false,
      },
      rate_limit: null,
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => payload,
    });
    const result = await fetchUsage();
    expect(result.enabled).toBe(true);
    expect(result.credits?.balance_display).toBe(312);
    expect(mockFetch).toHaveBeenCalledWith("/api/usage", { method: "GET" });
  });

  test("throws on a non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
    });
    await expect(fetchUsage()).rejects.toThrow("Failed to fetch usage: 500");
  });
});

describe("formatTimeUntil", () => {
  test("null / past timestamps return null", () => {
    expect(formatTimeUntil(null)).toBeNull();
    expect(
      formatTimeUntil(new Date(Date.now() - 1000).toISOString()),
    ).toBeNull();
  });

  test("formats hours and minutes", () => {
    const future = new Date(Date.now() + (112 * 60 + 30) * 1000).toISOString();
    // ~112 minutes -> "1h 52m" (ceil to the minute)
    expect(formatTimeUntil(future)).toMatch(/^1h 5[23]m$/);
  });

  test("formats minutes only", () => {
    const future = new Date(Date.now() + 6 * 60 * 1000).toISOString();
    expect(formatTimeUntil(future)).toMatch(/^[67]m$/);
  });
});
