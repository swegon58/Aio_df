"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";
import {
  usePersona,
  usePersonaPresets,
  useResetPersona,
  useUpdatePersona,
} from "@/core/persona/hooks";
import type { PersonaTraits } from "@/core/persona/types";
import { cn } from "@/lib/utils";

import { SettingsSection } from "./settings-section";

const SLIDER_FIELDS: Array<{
  key: keyof Pick<
    PersonaTraits,
    "formality" | "playfulness" | "verbosity" | "emojiUsage"
  >;
  labelKey: "formality" | "playfulness" | "verbosity" | "emojiUsage";
}> = [
  { key: "formality", labelKey: "formality" },
  { key: "playfulness", labelKey: "playfulness" },
  { key: "verbosity", labelKey: "verbosity" },
  { key: "emojiUsage", labelKey: "emojiUsage" },
];

export function PersonalitySettingsPage() {
  const { t } = useI18n();
  const { persona } = usePersona();
  const { presets } = usePersonaPresets();
  const updatePersona = useUpdatePersona();
  const resetPersona = useResetPersona();
  const [nickname, setNickname] = useState(persona?.nicknameForUser ?? "");
  const [notes, setNotes] = useState(persona?.customNotes ?? "");

  if (!persona) {
    return null;
  }

  function handleSliderChange(
    field: (typeof SLIDER_FIELDS)[number]["key"],
    value: number[],
  ) {
    updatePersona.mutate(
      { [field]: value[0] },
      {
        onError: () => toast.error(t.settings.personality.saveFailed),
      },
    );
  }

  function handlePresetSelect(presetId: string) {
    const preset = presets.find((p) => p.id === presetId);
    if (!preset) return;
    updatePersona.mutate(
      { ...preset.traits, preset: presetId },
      {
        onSuccess: () => toast.success(t.settings.personality.presetApplied),
        onError: () => toast.error(t.settings.personality.saveFailed),
      },
    );
  }

  function handleSaveTextFields() {
    updatePersona.mutate(
      { nicknameForUser: nickname || null, customNotes: notes },
      {
        onSuccess: () => toast.success(t.settings.personality.saved),
        onError: () => toast.error(t.settings.personality.saveFailed),
      },
    );
  }

  function handleReset() {
    resetPersona.mutate(undefined, {
      onSuccess: () => toast.success(t.settings.personality.resetDone),
      onError: () => toast.error(t.settings.personality.saveFailed),
    });
  }

  return (
    <SettingsSection
      title={t.settings.personality.title}
      description={t.settings.personality.description}
    >
      <div className="space-y-8">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {presets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => handlePresetSelect(preset.id)}
              className={cn(
                "hover:bg-muted rounded-lg border p-4 text-left transition-colors",
                persona.preset === preset.id && "border-primary bg-muted",
              )}
            >
              <div className="font-medium">{preset.label}</div>
              <div className="text-muted-foreground text-sm">
                {preset.description}
              </div>
            </button>
          ))}
        </div>

        <div className="space-y-6">
          {SLIDER_FIELDS.map(({ key, labelKey }) => (
            <div key={key} className="space-y-2">
              <label
                htmlFor={`persona-${key}`}
                className="text-sm font-medium"
              >
                {t.settings.personality[labelKey]}
              </label>
              <Slider
                id={`persona-${key}`}
                aria-label={t.settings.personality[labelKey]}
                min={0}
                max={100}
                step={5}
                value={[persona[key]]}
                onValueChange={(value) => handleSliderChange(key, value)}
              />
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <label htmlFor="persona-nickname" className="text-sm font-medium">
            {t.settings.personality.nicknameLabel}
          </label>
          <Input
            id="persona-nickname"
            value={nickname}
            placeholder={t.settings.personality.nicknamePlaceholder}
            onChange={(e) => setNickname(e.target.value)}
            onBlur={handleSaveTextFields}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="persona-notes" className="text-sm font-medium">
            {t.settings.personality.notesLabel}
          </label>
          <Textarea
            id="persona-notes"
            value={notes}
            placeholder={t.settings.personality.notesPlaceholder}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={handleSaveTextFields}
            rows={4}
          />
        </div>

        <Button
          variant="outline"
          onClick={handleReset}
          disabled={resetPersona.isPending}
        >
          {t.settings.personality.resetButton}
        </Button>
      </div>
    </SettingsSection>
  );
}
