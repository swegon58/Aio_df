"use client";

import { useTheme } from "next-themes";
import { Toaster } from "sonner";

import {
  ACCENT_HEX,
  BG_HEX,
  DEFAULT_ACCENT_HEX,
  mixHex,
  useAccent,
} from "@/components/accent-provider";
import { DotGrid } from "@/components/dot-grid";
import { QueryClientProvider } from "@/components/query-client-provider";
import { CommandPalette } from "@/components/workspace/command-palette";
import { GatewayOfflineBanner } from "@/components/workspace/gateway-offline-banner";
import { WorkspaceIconRail } from "@/components/workspace/icon-rail/workspace-icon-rail";
import { PersonalityWizard } from "@/components/workspace/onboarding/personality-wizard";

export function WorkspaceContent({
  children,
  gatewayUnavailable = false,
}: Readonly<{
  children: React.ReactNode;
  gatewayUnavailable?: boolean;
}>) {
  const { accent } = useAccent();
  const { resolvedTheme } = useTheme();
  const theme = resolvedTheme === "light" ? "light" : "dark";
  const accentHex = accent ? ACCENT_HEX[accent] : DEFAULT_ACCENT_HEX;

  return (
    <QueryClientProvider>
      <div className="flex h-screen w-full">
        <WorkspaceIconRail />
        <main className="relative min-w-0 flex-1 overflow-hidden">
          <DotGrid
            key={`${theme}-${accent ?? "default"}`}
            className="dot-grid-bg"
            dotSize={3}
            gap={28}
            baseColor={mixHex(accentHex, BG_HEX[theme], theme === "light" ? 0.4 : 0.3)}
            activeColor={mixHex(accentHex, BG_HEX[theme], 0.55)}
            proximity={0}
            shockRadius={0}
            shockStrength={0}
          />
          <GatewayOfflineBanner gatewayUnavailable={gatewayUnavailable} />
          {children}
        </main>
      </div>
      <CommandPalette />
      <PersonalityWizard />
      <Toaster position="top-center" />
    </QueryClientProvider>
  );
}
