"use client";

import { MapPin } from "lucide-react";
import { useMapState } from "./map-context";
import { TripMap } from "./trip-map";
import { formatPrice } from "../../lib/format";
import { modeGlyph } from "../../lib/transport";

const fmtDay = (iso) => {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
};

function RouteSummary({ route }) {
  const legs = route.legs || [];
  return (
    <div className="px-4 py-3 border-b border-pink-100 bg-surface shrink-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-extrabold text-foreground truncate">
            {route.destination || route.label || "Your trip"}
          </h2>
          <p className="text-xs font-medium text-foreground/60 mt-0.5">
            {route.label && route.label !== route.destination ? `${route.label} · ` : ""}
            {fmtDay(route.startDate)}
            {route.endDate ? ` – ${fmtDay(route.endDate)}` : ""}
          </p>
        </div>
        {route.grandTotal != null && (
          <span className="shrink-0 text-base font-extrabold text-primary">
            {formatPrice(route.grandTotal, route.currency)}
          </span>
        )}
      </div>

      {legs.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-foreground">
          {legs.map((leg, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-foreground/40">→</span>}
              <span aria-hidden>{modeGlyph(leg.mode)}</span>
              <span className="font-semibold">{leg.origin}</span>
              {i === legs.length - 1 && (
                <>
                  <span className="text-foreground/40">→</span>
                  <span className="font-semibold">{leg.destination}</span>
                </>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// The right-hand panel: a compact itinerary summary above the interactive map.
// Reads the active route from the shared MapState store.
export function TripPanel() {
  const { activeRoute } = useMapState();

  return (
    <aside className="flex flex-col w-full h-full border-l border-pink-100 bg-background">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-pink-100 bg-surface shrink-0">
        <MapPin className="w-4 h-4 text-primary" />
        <span className="text-xs font-bold uppercase tracking-wider text-primary">Trip Map</span>
      </div>

      {activeRoute && <RouteSummary route={activeRoute} />}

      <div className="flex-1 min-h-0">
        <TripMap route={activeRoute} />
      </div>
    </aside>
  );
}
