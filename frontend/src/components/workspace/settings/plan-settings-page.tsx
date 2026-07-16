"use client";

import { CheckIcon } from "lucide-react";

import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import { SettingsSection } from "./settings-section";

// ponytail: static placeholder tiers — no billing backend yet, so price/features
// are hardcoded here rather than piped through i18n like the section chrome.
const TIERS = [
  {
    key: "free",
    name: "Free",
    price: 0,
    features: ["Core chat & agents", "Community support", "Limited monthly credits"],
    featured: false,
  },
  {
    key: "pro",
    name: "Pro",
    price: 12,
    features: [
      "Everything in Free",
      "Higher credit allowance",
      "Priority response times",
      "Deep Research workflow",
    ],
    featured: true,
  },
  {
    key: "team",
    name: "Team",
    price: 29,
    features: [
      "Everything in Pro",
      "Shared team workspace",
      "Admin & usage controls",
    ],
    featured: false,
  },
];

export function PlanSettingsPage() {
  const { t } = useI18n();

  return (
    <SettingsSection title={t.settings.plan.title} description={t.settings.plan.description}>
      <div className="space-y-6">
        <div className="bg-muted/50 flex items-center justify-between rounded-lg border px-4 py-3">
          <span className="text-sm font-medium">{t.settings.plan.creditsLabel}</span>
          <span className="text-muted-foreground text-sm">
            {t.settings.plan.creditsPlaceholder}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {TIERS.map((tier) => (
            <div
              key={tier.key}
              className={cn("pricing-card", tier.featured && "pricing-card--featured")}
            >
              {tier.featured && (
                <span className="bg-primary text-primary-foreground absolute -top-2.5 right-4 rounded-full px-2 py-0.5 text-[11px] font-semibold">
                  {t.settings.plan.mostPopular}
                </span>
              )}
              <div>
                <div className="text-sm font-semibold">{tier.name}</div>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="text-2xl font-bold">${tier.price}</span>
                  <span className="text-muted-foreground text-xs">
                    {t.settings.plan.perMonth}
                  </span>
                </div>
              </div>

              <ul className="flex flex-col gap-2">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm">
                    <span className="pricing-check">
                      <CheckIcon />
                    </span>
                    {feature}
                  </li>
                ))}
              </ul>

              <button
                type="button"
                disabled={tier.key === "free"}
                className={cn(
                  "pricing-cta",
                  tier.key === "free" && "pricing-cta--outline",
                )}
              >
                {tier.key === "free"
                  ? t.settings.plan.currentButton
                  : t.settings.plan.upgradeButton}
              </button>
            </div>
          ))}
        </div>
      </div>
    </SettingsSection>
  );
}
