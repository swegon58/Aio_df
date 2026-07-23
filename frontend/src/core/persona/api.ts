import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type { PersonaPreset, PersonaTraits, PersonaUpdateInput } from "./types";

async function readPersonaResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as {
      detail?: unknown;
    };
    const detailMessage =
      typeof errorData.detail === "string" ? errorData.detail : null;
    throw new Error(detailMessage ?? `${fallbackMessage}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function loadPersona(): Promise<PersonaTraits> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona`);
  return readPersonaResponse<PersonaTraits>(response, "Failed to fetch persona");
}

export async function updatePersona(
  input: PersonaUpdateInput,
): Promise<PersonaTraits> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return readPersonaResponse<PersonaTraits>(response, "Failed to update persona");
}

export async function resetPersona(): Promise<PersonaTraits> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona/reset`, {
    method: "POST",
  });
  return readPersonaResponse<PersonaTraits>(response, "Failed to reset persona");
}

export async function loadPersonaPresets(): Promise<PersonaPreset[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona/presets`);
  return readPersonaResponse<PersonaPreset[]>(response, "Failed to fetch persona presets");
}
