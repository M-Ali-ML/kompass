"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";
import { useRenderTool } from "@copilotkit/react-core/v2";
import { Compass, Loader2, CheckCircle2 } from "lucide-react";
import { z } from "zod";

export default function Home() {
  // Tool execution UI — renders inline cards for gather_preferences calls
  useRenderTool({
    name: "gather_preferences",
    parameters: z.object({
      direct_flights_only: z.boolean().optional(),
      preferred_transit_modes: z.array(z.string()).optional(),
      hotel_class: z.string().nullable().optional(),
      vibe_tags: z.array(z.string()).optional(),
    }),
    render: ({ status, parameters }) => {
      const isComplete = status === "complete";
      const prefs = parameters;

      if (!prefs) return null;

      const hasPrefs = 
        prefs.direct_flights_only ||
        (prefs.preferred_transit_modes && prefs.preferred_transit_modes.length > 0) ||
        prefs.hotel_class ||
        (prefs.vibe_tags && prefs.vibe_tags.length > 0);

      if (!hasPrefs) return null;

      return (
        <div className={`p-4 my-2.5 rounded-2xl bg-surface border border-pink-100 bouncy-hover pink-shadow max-w-md ${!isComplete ? 'animate-pulse' : ''}`}>
          <div className="flex items-center gap-2 mb-2">
            {isComplete ? (
              <CheckCircle2 className="w-4 h-4 text-primary" />
            ) : (
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
            )}
            <span className="text-xs font-bold uppercase tracking-wider text-primary">
              {isComplete ? "Preferences Extracted" : "Extracting Preferences..."}
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-2">
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
              <span key={mode} className="px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded-full text-xs font-semibold capitalize">
                {mode === "flight" ? "✈️" : mode === "train" ? "🚆" : mode === "bus" ? "🚌" : mode === "ferry" ? "🚢" : "🚗"} {mode}
              </span>
            ))}
            {prefs.vibe_tags?.map((vibe) => (
              <span key={vibe} className="px-2.5 py-1 bg-yellow-50 text-amber-800 border border-yellow-100 rounded-full text-xs font-semibold">
                ✨ {vibe}
              </span>
            ))}
          </div>
        </div>
      );
    },
  });

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-surface border-b border-pink-100 pink-shadow shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary text-white rounded-2xl bouncy-hover pink-shadow">
            <Compass className="w-6 h-6 animate-spin-slow" />
          </div>
          <span className="text-xl font-extrabold tracking-tight text-foreground">
            Kompass
          </span>
        </div>
      </header>

      {/* V2 CopilotChat — native reasoning message support via AG-UI protocol */}
      <div className="flex-1 overflow-hidden">
        <CopilotChat
          className="h-full"
          labels={{
            title: "Kompass Travel Assistant",
            placeholder: "Where do you want to go?",
          }}
        />
      </div>
    </div>
  );

}
