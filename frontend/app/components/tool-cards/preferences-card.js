import { CheckCircle2, Loader2 } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";

export const preferencesParameters = z.object({
  direct_flights_only: z.boolean().optional(),
  preferred_transit_modes: z.array(z.string()).optional(),
  hotel_class: z.string().nullable().optional(),
  vibe_tags: z.array(z.string()).optional(),
  currency: z.string().optional(),
});

const TRANSIT_EMOJI = {
  flight: "✈️",
  train: "🚆",
  bus: "🚌",
  ferry: "🚢",
};

// Inline card for gather_preferences calls — shows the extracted trip prefs as chips.
export function PreferencesCard({ status, parameters: prefs }) {
  if (!prefs) return null;

  const isComplete = status === "complete";
  const showCurrency = prefs.currency && prefs.currency !== "EUR";
  const hasPrefs =
    prefs.direct_flights_only ||
    (prefs.preferred_transit_modes && prefs.preferred_transit_modes.length > 0) ||
    prefs.hotel_class ||
    (prefs.vibe_tags && prefs.vibe_tags.length > 0) ||
    showCurrency;

  if (!hasPrefs) return null;

  return (
    <ToolCard
      icon={isComplete ? CheckCircle2 : Loader2}
      spin={!isComplete}
      loading={!isComplete}
      label={isComplete ? "Preferences Extracted" : "Extracting Preferences..."}
    >
      <div className="flex flex-wrap gap-1.5">
        {prefs.direct_flights_only && (
          <span className="px-2.5 py-1 bg-pink-50 text-pink-700 border border-pink-100 rounded-full text-xs font-semibold">
            ✈️ Direct Flights Only
          </span>
        )}
        {prefs.hotel_class && (
          <span className="px-2.5 py-1 bg-purple-50 text-purple-800 border border-purple-100 rounded-full text-xs font-semibold">
            🏨 {prefs.hotel_class}
          </span>
        )}
        {prefs.preferred_transit_modes?.map((mode) => (
          <span
            key={mode}
            className="px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded-full text-xs font-semibold capitalize"
          >
            {TRANSIT_EMOJI[mode] || "🚗"} {mode}
          </span>
        ))}
        {prefs.vibe_tags?.map((vibe) => (
          <span
            key={vibe}
            className="px-2.5 py-1 bg-yellow-50 text-amber-800 border border-yellow-100 rounded-full text-xs font-semibold"
          >
            ✨ {vibe}
          </span>
        ))}
        {showCurrency && (
          <span className="px-2.5 py-1 bg-green-50 text-green-700 border border-green-100 rounded-full text-xs font-semibold">
            💱 Prices in {prefs.currency}
          </span>
        )}
      </div>
    </ToolCard>
  );
}
