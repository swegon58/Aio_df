/** @rstest-environment happy-dom */
import { describe, expect, test, rs } from "@rstest/core";
import { render, screen } from "@testing-library/react";

import { PersonalityWizard } from "@/components/workspace/onboarding/personality-wizard";
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
      onboardingCompleted: false,
    },
    isLoading: false,
    error: null,
  }),
  usePersonaPresets: () => ({
    presets: [
      {
        id: "default",
        label: "Balanced Aio",
        description: "...",
        traits: { formality: 50, playfulness: 50, verbosity: 50, emojiUsage: 20 },
      },
    ],
    isLoading: false,
    error: null,
  }),
  useUpdatePersona: () => ({ mutate: rs.fn(), isPending: false }),
}));

describe("PersonalityWizard", () => {
  test("shows the wizard when onboarding is not yet completed", () => {
    render(
      <I18nProvider initialLocale="en-US">
        <PersonalityWizard />
      </I18nProvider>,
    );
    expect(screen.getByText("Balanced Aio")).toBeTruthy();
  });
});
