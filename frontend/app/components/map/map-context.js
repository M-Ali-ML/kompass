"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

// Shared "active route" store that decouples the chat-side scenario cards (which
// know the itinerary) from the right-panel map (which renders it). A scenario
// card calls setActiveRoute(...) when it streams in or when the user clicks
// "View on map"; the TripMap reads activeRoute and plots it.
const MapStateContext = createContext(null);

// Normalize a Scenario into the minimal shape the map + summary panel need.
export function routeFromScenario(scenario, { destination, currency } = {}) {
  if (!scenario) return null;
  const it = scenario.itinerary || {};
  return {
    destination: destination || scenario.destination || "",
    label: scenario.comparison_label || scenario.label || "",
    currency: currency || "EUR",
    startDate: scenario.start_date || null,
    endDate: scenario.end_date || null,
    grandTotal: scenario.cost_breakdown?.grand_total ?? null,
    legs: it.legs || [],
    accommodations: it.accommodations || [],
  };
}

export function MapStateProvider({ children }) {
  const [activeRoute, setActiveRoute] = useState(null);

  const setRouteFromScenario = useCallback((scenario, opts) => {
    setActiveRoute(routeFromScenario(scenario, opts));
  }, []);

  const value = useMemo(
    () => ({ activeRoute, setActiveRoute, setRouteFromScenario }),
    [activeRoute, setRouteFromScenario]
  );

  return <MapStateContext.Provider value={value}>{children}</MapStateContext.Provider>;
}

export function useMapState() {
  const ctx = useContext(MapStateContext);
  if (!ctx) {
    // Tolerate use outside the provider (e.g. a card rendered before mount) so
    // a missing provider degrades to a no-op rather than crashing the chat.
    return { activeRoute: null, setActiveRoute: () => {}, setRouteFromScenario: () => {} };
  }
  return ctx;
}
