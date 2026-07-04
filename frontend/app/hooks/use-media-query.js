"use client";

import { useCallback, useSyncExternalStore } from "react";

// SSR-safe media-query hook. Server render (and the hydration pass) report
// `false`; the client snapshot is read synchronously in the same flush right
// after hydration, so the real value lands before the first paint — no
// "mobile layout flashes on desktop" window, unlike a useEffect-based sync.
export function useMediaQuery(query) {
  const subscribe = useCallback(
    (onChange) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    [query]
  );

  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(query).matches,
    () => false
  );
}
