import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  loadPersona,
  loadPersonaPresets,
  resetPersona,
  updatePersona,
} from "./api";
import type { PersonaTraits, PersonaUpdateInput } from "./types";

export function usePersona() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["persona"],
    queryFn: () => loadPersona(),
  });
  return { persona: data ?? null, isLoading, error };
}

export function useUpdatePersona() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: PersonaUpdateInput) => updatePersona(input),
    onSuccess: (persona) => {
      queryClient.setQueryData<PersonaTraits>(["persona"], persona);
    },
  });
}

export function useResetPersona() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => resetPersona(),
    onSuccess: (persona) => {
      queryClient.setQueryData<PersonaTraits>(["persona"], persona);
    },
  });
}

export function usePersonaPresets() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["persona-presets"],
    queryFn: () => loadPersonaPresets(),
  });
  return { presets: data ?? [], isLoading, error };
}
