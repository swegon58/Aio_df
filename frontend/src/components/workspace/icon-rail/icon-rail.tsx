"use client";

import type { LucideIcon } from "lucide-react";

export interface IconRailItem {
  key: string;
  label: string;
  icon: LucideIcon;
  active: boolean;
}

type IconRailVariant = "compact" | "mobile";

interface IconRailProps {
  variant: IconRailVariant;
  items: IconRailItem[];
  onItemClick: (key: string) => void;
}

export function IconRail({ variant, items, onItemClick }: IconRailProps) {
  const isCompact = variant === "compact";

  return (
    <>
      {items.map(({ key, label, icon: Icon, active }) => (
        <button
          key={key}
          type="button"
          className={`icon-rail-item${isCompact ? " icon-rail-item--compact" : ""}${active ? " active" : ""}`}
          onClick={() => onItemClick(key)}
          aria-label={isCompact ? label : undefined}
          title={isCompact ? label : undefined}
        >
          <span className="icon-rail-item-highlight">
            <Icon className={isCompact ? "w-7 h-7" : "w-5.5 h-5.5"} />
            <span className="icon-rail-label icon-rail-label-inner">{label}</span>
          </span>
        </button>
      ))}
    </>
  );
}
