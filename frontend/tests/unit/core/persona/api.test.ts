import { beforeEach, describe, expect, test, rs } from "@rstest/core";

rs.mock("@/core/api/fetcher", () => ({
  fetch: rs.fn(),
}));

rs.mock("@/core/config", () => ({
  getBackendBaseURL: () => "",
}));

import { fetch } from "@/core/api/fetcher";
import {
  loadPersona,
  updatePersona,
  resetPersona,
  loadPersonaPresets,
} from "@/core/persona/api";
import type { PersonaTraits } from "@/core/persona/types";

const mockedFetch = rs.mocked(fetch);

const samplePersona: PersonaTraits = {
  formality: 50,
  playfulness: 50,
  verbosity: 50,
  emojiUsage: 20,
  nicknameForUser: null,
  customNotes: "",
  preset: "default",
  onboardingCompleted: false,
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  mockedFetch.mockReset();
});

describe("persona api", () => {
  test("loadPersona fetches /api/persona", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, samplePersona));
    const result = await loadPersona();
    expect(result).toEqual(samplePersona);
    expect(mockedFetch).toHaveBeenCalledWith(expect.stringContaining("/api/persona"));
  });

  test("updatePersona PUTs the partial update", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, samplePersona));
    await updatePersona({ formality: 90 });
    const call = mockedFetch.mock.calls[0];
    expect(call).toBeDefined();
    const [, init] = call as [string, RequestInit];
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({ formality: 90 });
  });

  test("resetPersona POSTs to /api/persona/reset", async () => {
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, samplePersona));
    await resetPersona();
    const call = mockedFetch.mock.calls[0];
    expect(call).toBeDefined();
    const [url, init] = call as [string, RequestInit];
    expect(url).toContain("/api/persona/reset");
    expect(init.method).toBe("POST");
  });

  test("loadPersonaPresets fetches /api/persona/presets", async () => {
    const presets = [];
    mockedFetch.mockResolvedValueOnce(jsonResponse(200, presets));
    const result = await loadPersonaPresets();
    expect(result).toEqual(presets);
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/persona/presets"),
    );
  });
});
