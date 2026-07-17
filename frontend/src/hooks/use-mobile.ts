import * as React from "react";

const MOBILE_BREAKPOINT = 768;

function subscribe(callback: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
  mql.addEventListener("change", callback);
  return () => mql.removeEventListener("change", callback);
}

function getSnapshot() {
  return window.innerWidth < MOBILE_BREAKPOINT;
}

function getServerSnapshot() {
  return false;
}

// ponytail: useSyncExternalStore's getServerSnapshot keeps the client's first
// (hydrating) render identical to SSR — a plain useState/useEffect read of
// window.innerWidth diverges from SSR on real mobile devices and throws a
// hydration mismatch, forcing React to discard and regenerate the subtree.
export function useIsMobile() {
  return React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
