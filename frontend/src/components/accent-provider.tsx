"use client";

// ponytail: ported from apps/web's useAccountPrefs accent state + SettingsModal
// swatches — same 7 hex values, same localStorage + data-attribute pattern,
// just renamed to deer-flow's own storage key and exposed via context instead
// of a page-local hook since both the settings page and the dot-grid mount
// need to read it.
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export const ACCENT_KEYS = [
  "purple",
  "green",
  "blue",
  "pink",
  "orange",
  "cyan",
  "red",
] as const;

export type AccentKey = (typeof ACCENT_KEYS)[number];

export const ACCENT_HEX: Record<AccentKey, string> = {
  purple: "#6c5ce7",
  green: "#00d2a0",
  blue: "#0081f2",
  pink: "#fd79a8",
  orange: "#ffa726",
  cyan: "#00cec9",
  red: "#ff6b6b",
};

// Approximate hex for deer-flow's default --primary (oklch teal, hue 205),
// used as the dot-grid's default color when no accent override is active.
export const DEFAULT_ACCENT_HEX = "#00cec9";

export const BG_HEX: Record<"dark" | "light", string> = {
  dark: "#0d0e10",
  light: "#f7f7f9",
};

export function mixHex(hex: string, bgHex: string, ratio: number): string {
  const a = hex.replace("#", "");
  const b = bgHex.replace("#", "");
  const ar = parseInt(a.slice(0, 2), 16);
  const ag = parseInt(a.slice(2, 4), 16);
  const ab = parseInt(a.slice(4, 6), 16);
  const br = parseInt(b.slice(0, 2), 16);
  const bg = parseInt(b.slice(2, 4), 16);
  const bb = parseInt(b.slice(4, 6), 16);
  const r = Math.round(ar * ratio + br * (1 - ratio));
  const g = Math.round(ag * ratio + bg * (1 - ratio));
  const bl = Math.round(ab * ratio + bb * (1 - ratio));
  return `#${[r, g, bl].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

type AccentContextValue = {
  accent: AccentKey | null;
  setAccent: (accent: AccentKey | null) => void;
};

const AccentContext = createContext<AccentContextValue | null>(null);

export function useAccent() {
  const ctx = useContext(AccentContext);
  if (!ctx) throw new Error("useAccent must be used within AccentProvider");
  return ctx;
}

const STORAGE_KEY = "deerflow-accent";

export function AccentProvider({ children }: { children: ReactNode }) {
  const [accent, setAccent] = useState<AccentKey | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as AccentKey | null;
    if (stored && (ACCENT_KEYS as readonly string[]).includes(stored)) {
      setAccent(stored);
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (accent) {
      document.documentElement.dataset.accent = accent;
      localStorage.setItem(STORAGE_KEY, accent);
    } else {
      delete document.documentElement.dataset.accent;
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [accent, hydrated]);

  return (
    <AccentContext.Provider value={{ accent, setAccent }}>
      {children}
    </AccentContext.Provider>
  );
}
