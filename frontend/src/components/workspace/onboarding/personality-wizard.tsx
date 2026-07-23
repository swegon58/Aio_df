"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/core/i18n/hooks";
import { usePersona, usePersonaPresets, useUpdatePersona } from "@/core/persona/hooks";
import { cn } from "@/lib/utils";

type Step = "preset" | "nickname";

export function PersonalityWizard() {
  const { t } = useI18n();
  const { persona } = usePersona();
  const { presets } = usePersonaPresets();
  const updatePersona = useUpdatePersona();
  const [step, setStep] = useState<Step>("preset");
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");

  if (!persona || persona.onboardingCompleted) {
    return null;
  }

  function handleFinish() {
    updatePersona.mutate({
      nicknameForUser: nickname || null,
      onboardingCompleted: true,
    });
  }

  return (
    // ponytail: onOpenChange is a deliberate no-op — the wizard is not
    // dismissible via escape/outside-click; it only closes once
    // handleFinish flips onboardingCompleted and the component unmounts.
    <Dialog open onOpenChange={() => undefined}>
      <DialogContent aria-describedby={undefined} className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t.settings.personality.wizardTitle}</DialogTitle>
        </DialogHeader>

        {step === "preset" && (
          <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
              {t.settings.personality.wizardPresetPrompt}
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => {
                    setSelectedPreset(preset.id);
                    updatePersona.mutate({ ...preset.traits, preset: preset.id });
                  }}
                  className={cn(
                    "hover:bg-muted rounded-lg border p-4 text-left transition-colors",
                    selectedPreset === preset.id && "border-primary bg-muted",
                  )}
                >
                  <div className="font-medium">{preset.label}</div>
                  <div className="text-muted-foreground text-sm">{preset.description}</div>
                </button>
              ))}
            </div>
            <div className="flex justify-end">
              <Button onClick={() => setStep("nickname")} disabled={!selectedPreset}>
                {t.settings.personality.wizardNext}
              </Button>
            </div>
          </div>
        )}

        {step === "nickname" && (
          <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
              {t.settings.personality.wizardNicknamePrompt}
            </p>
            <Input
              value={nickname}
              placeholder={t.settings.personality.nicknamePlaceholder}
              onChange={(e) => setNickname(e.target.value)}
            />
            <p className="text-muted-foreground text-xs">
              {t.settings.personality.wizardSettingsHint}
            </p>
            <div className="flex justify-end">
              <Button onClick={handleFinish}>{t.settings.personality.wizardFinish}</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
