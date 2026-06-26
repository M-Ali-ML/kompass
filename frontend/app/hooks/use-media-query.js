"use client";

import { useEffect, useState } from "react";

// SSR-safe media-query hook. Returns false on the server / first paint, then
// syncs to the real match after mount and on subsequent changes.
export function useMediaQuery(query) {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
