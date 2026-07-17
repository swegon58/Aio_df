"use client";

import { BotIcon, Hash, MessagesSquare, SettingsIcon } from "lucide-react";
import { usePathname } from "next/navigation";
import { useMemo } from "react";

import { useI18n } from "@/core/i18n/hooks";

import type { IconRailItem } from "./icon-rail";

export type IconRailKey = "chats" | "agents" | "channels" | "settings";

export function useIconRailItems(openOverlayKey?: IconRailKey | null): IconRailItem[] {
  const { t } = useI18n();
  const pathname = usePathname();

  return useMemo(
    () => [
      {
        key: "chats",
        label: t.sidebar.chats,
        icon: MessagesSquare,
        active:
          pathname.startsWith("/workspace/chats") &&
          openOverlayKey !== "channels" &&
          openOverlayKey !== "settings",
      },
      {
        key: "agents",
        label: t.sidebar.agents,
        icon: BotIcon,
        active: pathname.startsWith("/workspace/agents"),
      },
      {
        key: "channels",
        label: t.sidebar.channels,
        icon: Hash,
        active: openOverlayKey === "channels",
      },
      {
        key: "settings",
        label: t.common.settings,
        icon: SettingsIcon,
        active: openOverlayKey === "settings",
      },
    ],
    [t, pathname, openOverlayKey],
  );
}
