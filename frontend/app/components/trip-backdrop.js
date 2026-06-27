"use client";

import { useState } from "react";
import { tripBackgroundImageUrl } from "../lib/trips-api";

// A reusable decorative backdrop for a trip's generated "vibe" image.
//
// It renders an absolutely-positioned <img> that starts hidden and fades in
// only once the image successfully loads, and stays hidden on error. That makes
// it self-healing for the common case where the image hasn't been generated yet
// (the endpoint 404s) — the surrounding UI simply shows no image, no polling and
// no broken-image icon.
//
// `fade` picks the mask direction so the same component serves both call sites:
//   - "bottom": image fades downward (banner behind a modal header)
//   - "left":   image sits on the right and fades INTO text on the left (sidebar).
//     The image stays full-strength on the right and is fully gone by ~58% from
//     the right edge, leaving the left ~40% (where the title starts) clear.
const FADE_MASKS = {
  bottom:
    "linear-gradient(to bottom, black 0%, black 60%, transparent 100%)",
  left: "linear-gradient(to left, black 0%, black 24%, transparent 62%)",
  none: undefined,
};

export function TripBackdrop({
  tripId,
  version,
  className = "",
  fade = "bottom",
  blur = false,
  // Loaded opacity (0-100). Applied inline so it composes cleanly with the
  // fade-in transition instead of fighting a Tailwind opacity utility.
  intensity = 100,
}) {
  const [loaded, setLoaded] = useState(false);
  const src = tripBackgroundImageUrl(tripId, version);
  if (!src) return null;

  const mask = FADE_MASKS[fade];

  return (
    // A raw <img> (not next/image) is intentional: it self-hides until the
    // backend image loads and degrades on 404, and the source is a dynamic API
    // route, so Next's optimizer brings no benefit here.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      aria-hidden="true"
      onLoad={() => setLoaded(true)}
      onError={() => setLoaded(false)}
      className={`pointer-events-none absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${
        blur ? "blur-[2px]" : ""
      } ${className}`}
      style={{
        opacity: loaded ? intensity / 100 : 0,
        ...(mask ? { maskImage: mask, WebkitMaskImage: mask } : {}),
      }}
    />
  );
}
