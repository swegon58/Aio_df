"use client";

import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";

import type { BashStep } from "./right-status-panel";

const DARK_THEME = {
  background: "transparent",
  foreground: "#e4e4e7",
  cursor: "#e4e4e7",
  selectionBackground: "#3f3f4680",
};

const LIGHT_THEME = {
  background: "transparent",
  foreground: "#202028",
  cursor: "#202028",
  selectionBackground: "#d4d4d880",
};

// ponytail: read-only playback terminal — writes the full bash log into one
// xterm buffer so ANSI colors/cursor codes from the sandbox render correctly
// instead of as raw escape junk in a plain <pre>. No stdin, no PTY.
export function SandboxTerminal({ steps }: { steps: BashStep[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const term = new Terminal({
      convertEol: true,
      disableStdin: true,
      cursorBlink: false,
      fontSize: 12,
      fontFamily: "var(--font-mono, monospace)",
      theme: resolvedTheme === "dark" ? DARK_THEME : LIGHT_THEME,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(container);
    fitAddon.fit();
    termRef.current = term;
    fitRef.current = fitAddon;

    const resizeObserver = new ResizeObserver(() => {
      fitAddon.fit();
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
    // Theme changes need a fresh instance since xterm can't hot-swap colors.
  }, [resolvedTheme]);

  useEffect(() => {
    const term = termRef.current;
    if (!term) return;
    term.clear();
    term.reset();
    for (const step of steps) {
      term.writeln(`\x1b[36m$ ${step.command ?? ""}\x1b[0m`);
      if (step.result) {
        term.write(step.result.replace(/\n/g, "\r\n"));
        term.writeln("");
      }
      if (step.running) {
        term.writeln("\x1b[2mrunning...\x1b[0m");
      }
    }
    term.scrollToBottom();
  }, [steps]);

  return <div ref={containerRef} className="size-full" />;
}
