"use client";

import { useState } from "react";
import { z } from "zod";
import { HelpCircle, Check, Loader2, CheckCircle2, Send } from "lucide-react";
import { ToolCard } from "../tool-card";

export const clarifyParameters = z.object({
  question: z.string(),
  options: z.array(z.string()).optional(),
  allow_multiple: z.boolean().optional(),
});

// Human-in-the-loop card for `ask_clarifying_question`. The agent pauses its run
// and asks one focused question with a few concrete options; the traveler picks
// one (or several, when `allow_multiple`) or types their own answer in "Other".
// Calling `respond(answer)` resumes the agent run with the chosen text.
//
// Statuses (CopilotKit v2 HITL):
//   - inProgress → args still streaming; show a preparing state
//   - executing  → interactive; `respond` is available
//   - complete   → already answered (incl. on resume); `result` holds the answer
export function ClarifyCard({ status, args, result, respond }) {
  const question = args?.question || "";
  const options = args?.options || [];
  const allowMultiple = !!args?.allow_multiple;

  const [selected, setSelected] = useState([]);
  const [other, setOther] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (status === "inProgress") {
    return (
      <ToolCard icon={HelpCircle} label="Preparing a question…" loading spin />
    );
  }

  if (status === "complete") {
    return (
      <ToolCard icon={CheckCircle2} label="Answered">
        {question && <p className="text-sm font-semibold text-foreground mb-1.5">{question}</p>}
        {result && (
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-pink-50 text-pink-700 border border-pink-100 text-xs font-semibold">
            <Check className="w-3.5 h-3.5" /> {result}
          </div>
        )}
      </ToolCard>
    );
  }

  // executing — interactive
  const toggle = (opt) => {
    if (allowMultiple) {
      setSelected((s) => (s.includes(opt) ? s.filter((o) => o !== opt) : [...s, opt]));
    } else {
      setSelected([opt]);
    }
  };

  const composedAnswer = () => {
    const parts = [...selected];
    const typed = other.trim();
    if (typed) parts.push(typed);
    return parts.join(", ");
  };

  const canSubmit = (selected.length > 0 || other.trim().length > 0) && !submitting;

  const submit = async (directAnswer) => {
    const answer = directAnswer ?? composedAnswer();
    if (!answer || submitting) return;
    setSubmitting(true);
    try {
      await respond?.(answer);
    } catch (e) {
      console.error("Failed to submit answer", e);
      setSubmitting(false);
    }
  };

  // Single-choice with no free-text intent: clicking an option answers immediately.
  const handleOptionClick = (opt) => {
    if (allowMultiple) {
      toggle(opt);
    } else if (other.trim()) {
      // The traveler is also typing — treat the click as a selection, let them confirm.
      toggle(opt);
    } else {
      submit(opt);
    }
  };

  return (
    <ToolCard icon={HelpCircle} label="A quick question">
      <p className="text-sm font-semibold text-foreground mb-2.5">{question}</p>

      {options.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {options.map((opt) => {
            const active = selected.includes(opt);
            return (
              <button
                key={opt}
                type="button"
                aria-pressed={active}
                disabled={submitting}
                onClick={() => handleOptionClick(opt)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border bouncy-hover disabled:opacity-60 ${
                  active
                    ? "bg-primary text-white border-primary pink-shadow"
                    : "bg-surface text-foreground/80 border-pink-200 hover:bg-pink-50"
                }`}
              >
                {active && <Check className="w-3.5 h-3.5" />}
                {opt}
              </button>
            );
          })}
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={other}
          onChange={(e) => setOther(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (canSubmit) submit();
            }
          }}
          disabled={submitting}
          placeholder={options.length > 0 ? "Or type your own answer…" : "Type your answer…"}
          className="flex-1 min-w-0 px-3 py-2.5 rounded-xl border border-pink-200 bg-surface text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={() => submit()}
          disabled={!canSubmit}
          aria-label="Send answer"
          className="shrink-0 px-4 py-2.5 rounded-xl bg-primary text-white text-sm font-bold inline-flex items-center justify-center gap-1.5 bouncy-hover pink-shadow disabled:opacity-50"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </ToolCard>
  );
}
