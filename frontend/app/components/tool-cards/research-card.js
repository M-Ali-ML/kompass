import { useState } from "react";
import { Globe, ChevronDown } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { Markdown } from "../markdown";
import { isPreparing } from "../../lib/format";

export const researchParameters = z.object({
  query: z.string().optional(),
});

// Coerce the search_web result (a markdown string, occasionally wrapped in an
// object by the transport) into plain text.
const toText = (result) => {
  if (result == null) return "";
  if (typeof result === "string") return result;
  if (typeof result === "object") return result.text || result.content || "";
  return String(result);
};

// Generative UI for search_web — collapses the grounded research answer into a
// tidy, expandable card instead of dumping the raw markdown into the chat.
export function ResearchCard({ status, parameters, result }) {
  const [open, setOpen] = useState(false);
  const query = parameters?.query || "";

  if (status !== "complete") {
    return (
      <ToolCard
        icon={Globe}
        loading
        label={isPreparing(status) ? "Preparing web research…" : `Researching the web${query ? ` · ${query}` : ""}`}
      />
    );
  }

  const text = toText(result).trim();
  if (!text) return null;

  // The research sub-agent reports failures inline as "(Live web search was
  // unavailable: …)" — render that as a graceful error rather than passing it
  // off as a real finding.
  if (text.startsWith("(Live web search was unavailable")) {
    return (
      <ToolCard
        icon={Globe}
        label="Web research"
        error="Live web search was temporarily unavailable. I'll try again or flag anything that couldn't be verified."
      />
    );
  }

  return (
    <ToolCard icon={Globe} label="Web research">
      {query && (
        <p className="text-xs font-medium text-foreground/70 mb-2 line-clamp-2">“{query}”</p>
      )}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 text-left text-xs font-semibold text-primary hover:opacity-80"
      >
        {open ? "Hide details" : "Show what I found"}
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
