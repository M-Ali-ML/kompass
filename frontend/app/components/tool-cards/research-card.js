import { useState } from "react";
import { Globe, ChevronDown } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";

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
    return <ToolCard icon={Globe} loading label={`Researching the web${query ? ` · ${query}` : ""}`} />;
  }

  const text = toText(result).trim();
  if (!text) return null;

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
      <p
        className={`mt-2 text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap break-words ${
          open ? "" : "line-clamp-3"
        }`}
      >
        {text}
      </p>
    </ToolCard>
  );
}
