export interface PersonaTraits {
  formality: number;
  playfulness: number;
  verbosity: number;
  emojiUsage: number;
  nicknameForUser: string | null;
  customNotes: string;
  preset: string | null;
  onboardingCompleted: boolean;
}

export interface PersonaUpdateInput {
  formality?: number;
  playfulness?: number;
  verbosity?: number;
  emojiUsage?: number;
  nicknameForUser?: string | null;
  customNotes?: string;
  preset?: string | null;
  onboardingCompleted?: boolean;
}

export interface PersonaPreset {
  id: string;
  label: string;
  description: string;
  traits: PersonaTraits;
}
