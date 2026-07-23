/** @rstest-environment happy-dom */
import { describe, expect, test, rs } from "@rstest/core";
import { render, screen } from "@testing-library/react";

import { PersonalitySettingsPage } from "@/components/workspace/settings/personality-settings-page";
import { I18nProvider } from "@/core/i18n/context";

rs.mock("@/core/persona/hooks", () => ({
  usePersona: () => ({
    persona: {
      formality: 50,
      playfulness: 50,
      verbosity: 50,
      emojiUsage: 20,
      nicknameForUser: null,
      customNotes: "",
      preset: "default",
      onboardingCompleted: true,
    },
    isLoading: false,
    error: null,
  }),
  useUpdatePersona: () => ({ mutate: rs.fn(), isPending: false }),
  useResetPersona: () => ({ mutate: rs.fn(), isPending: false }),
  usePersonaPresets: () => ({
    presets: [
      { id: "default", label: "Balanced Aio", description: "...", traits: {} },
      {
        id: "warm_companion",
        label: "Warm Companion",
        description: "...",
        traits: {},
      },
    ],
    isLoading: false,
    error: null,
  }),
}));

describe("PersonalitySettingsPage", () => {
  test("renders every preset card and all four tone sliders", () => {
    render(
      <I18nProvider initialLocale="en-US">
        <PersonalitySettingsPage />
      </I18nProvider>,
    );
    // ponytail: getByText/getByLabelText already throw if no match is found,
    // so .toBeTruthy() (a core matcher) is enough — avoids pulling in
    // @testing-library/jest-dom just for .toBeInTheDocument().
    expect(screen.getByText("Balanced Aio")).toBeTruthy();
    expect(screen.getByText("Warm Companion")).toBeTruthy();
    expect(screen.getByLabelText(/formality/i)).toBeTruthy();
    expect(screen.getByLabelText(/playfulness/i)).toBeTruthy();
    expect(screen.getByLabelText(/verbosity/i)).toBeTruthy();
    expect(screen.getByLabelText(/emoji/i)).toBeTruthy();
  });
});
