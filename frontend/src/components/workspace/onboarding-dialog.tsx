"use client";

import {
  Briefcase,
  Code2,
  GraduationCap,
  Palette,
  PenLine,
  SearchIcon,
  Sparkles,
  Terminal,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfettiButton } from "@/components/ui/confetti-button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";

import { useThread } from "./messages/context";

const ONBOARDING_KEY = "deerflow.onboarding-completed";
const STEP_COUNT = 3;

const ROLE_OPTIONS = [
  { value: "developer", label: "Developer", icon: Code2 },
  { value: "designer", label: "Designer", icon: Palette },
  { value: "product manager", label: "PM", icon: Briefcase },
  { value: "student", label: "Student", icon: GraduationCap },
  { value: "something else", label: "Other", icon: Sparkles },
];

const GOAL_OPTIONS = [
  { value: "write code", label: "Code", icon: Terminal },
  { value: "write content", label: "Write", icon: PenLine },
  { value: "do research", label: "Research", icon: SearchIcon },
  { value: "automate tasks", label: "Automate", icon: Zap },
  { value: "something else", label: "Other", icon: Sparkles },
];

// Shown once on the very first new-thread visit. Answers are sent as a
// normal first chat message (via submitAnswer, same path ClarificationCard
// uses) so the existing memory/fact-extraction pipeline picks them up —
// no separate profile API.
export function OnboardingDialog({ isNewThread }: { isNewThread: boolean }) {
  const { submitAnswer } = useThread();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [goals, setGoals] = useState<string[]>([]);

  useEffect(() => {
    if (!isNewThread) return;
    if (localStorage.getItem(ONBOARDING_KEY)) return;
    setOpen(true);
  }, [isNewThread]);

  const finish = () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    setOpen(false);
  };

  const handleSubmit = () => {
    const parts: string[] = [];
    if (name.trim()) parts.push(`My name is ${name.trim()}.`);
    if (role) parts.push(`I'm a ${role}.`);
    if (goals.length > 0) parts.push(`I want to ${goals.join(", ")}.`);
    finish();
    if (parts.length > 0) {
      void submitAnswer?.(`Quick intro before we start: ${parts.join(" ")}`);
    }
  };

  const isLast = step === STEP_COUNT - 1;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) finish();
      }}
    >
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-xl">Welcome to Aio 👋</DialogTitle>
          <DialogDescription className="text-base">
            A couple of quick questions so Aio can help you better. Totally
            optional — skip anytime.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-center gap-1.5 py-1">
          {Array.from({ length: STEP_COUNT }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i === step ? "bg-primary w-6" : "bg-muted w-1.5",
              )}
            />
          ))}
        </div>

        {step === 0 && (
          <div className="flex flex-col gap-3 py-2">
            <p className="text-sm font-medium">What should Aio call you?</p>
            <Input
              autoFocus
              className="h-12 text-base"
              placeholder="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
        )}

        {step === 1 && (
          <div className="flex flex-col gap-3 py-2">
            <p className="text-sm font-medium">What best describes you?</p>
            <ToggleGroup
              className="grid w-full grid-cols-3 gap-2"
              onValueChange={(value) => setRole(value)}
              type="single"
              value={role}
              variant="outline"
            >
              {ROLE_OPTIONS.map(({ value, label, icon: Icon }) => (
                <ToggleGroupItem
                  className="h-auto flex-col gap-1.5 rounded-lg py-4 text-sm data-[state=on]:border-primary data-[state=on]:bg-primary/10"
                  key={value}
                  value={value}
                >
                  <Icon className="size-5" />
                  {label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-3 py-2">
            <p className="text-sm font-medium">
              What are you here to do? (pick any)
            </p>
            <ToggleGroup
              className="grid w-full grid-cols-3 gap-2"
              onValueChange={(value) => setGoals(value)}
              type="multiple"
              value={goals}
              variant="outline"
            >
              {GOAL_OPTIONS.map(({ value, label, icon: Icon }) => (
                <ToggleGroupItem
                  className="h-auto flex-col gap-1.5 rounded-lg py-4 text-sm data-[state=on]:border-primary data-[state=on]:bg-primary/10"
                  key={value}
                  value={value}
                >
                  <Icon className="size-5" />
                  {label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
        )}

        <DialogFooter className="flex flex-row items-center justify-between sm:justify-between">
          <Button
            className="text-muted-foreground h-auto px-0"
            onClick={finish}
            size="sm"
            type="button"
            variant="link"
          >
            Skip
          </Button>
          <div className="flex items-center gap-2">
            {step > 0 && (
              <Button
                onClick={() => setStep((s) => s - 1)}
                size="sm"
                type="button"
                variant="outline"
              >
                Back
              </Button>
            )}
            {isLast ? (
              <ConfettiButton onClick={handleSubmit} size="sm" type="button">
                Get started
              </ConfettiButton>
            ) : (
              <Button
                onClick={() => setStep((s) => s + 1)}
                size="sm"
                type="button"
              >
                Next
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
