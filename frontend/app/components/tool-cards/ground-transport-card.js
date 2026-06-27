import { useState } from "react";
import { TrainFront, ChevronDown } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { Markdown } from "../markdown";
import { isPreparing } from "../../lib/format";

export const groundTransportParameters = z.object({
  origin: z.string().optional(),
  destination: z.string().optional(),
  date: z.string().optional(),
  modes: z.string().nullable().optional(),
});

// search_ground_transport returns a grounded markdown string (trains / buses /
// ferries), same shape as search_web. Coerce object-wrapped results to text.
const toText = (result) => {
  if (result == null) return "";
  if (typeof result === "string") return result;
  if (typeof result === "object") return result.text || result.content || "";
  return String(result);
};

// Generative UI for search_ground_transport — a collapsible card so the route's
// rail/bus/ferry options don't dump raw markdown into the chat.
export function GroundTransportCard({ status, parameters, result }) {
  const [open, setOpen] = useState(false);
  const route = `${parameters?.origin || "?"} → ${parameters?.destination || "?"}`;
  const modes = parameters?.modes ? ` · ${parameters.modes}` : "";

  if (status !== "complete") {
    return (
      <ToolCard
        icon={TrainFront}
        loading
        label={isPreparing(status) ? "Preparing transit search…" : `Searching ground transport ${route}${modes}`}
      />
    );
  }

  const text = toText(result).trim();
  if (!text) return null;

  if (text.startsWith("(Live web search was unavailable")) {
    return (
      <ToolCard
        icon={TrainFront}
        label={`Ground transport · ${route}`}
        error="Live transit lookup was temporarily unavailable. I'll estimate from what I already know."
      />
    );
  }

  return (
    <ToolCard icon={TrainFront} label={`Ground transport · ${route}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 text-left text-xs font-semibold text-primary hover:opacity-80"
      >
        {open ? "Hide options" : "Show transit options"}
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      <div className={`relative mt-2 ${open ? "" : "max-h-20 overflow-hidden"}`}>
        <Markdown content={text} />
        {!open && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-surface to-transparent" />
        )}
      </div>
    </ToolCard>
  );
}
