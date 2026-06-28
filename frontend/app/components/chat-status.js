"use client";

import { useEffect, useRef, useState } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import { Loader2 } from "lucide-react";

// Friendly, human-readable status for each agent tool. Shown while the agent is
// working but hasn't produced visible content yet (the long "stuck on a dot"
// gaps: initial reasoning, tool execution, and the final itinerary synthesis).
const TOOL_LABELS = {
  gather_preferences: "Noting your preferences…",
  find_cheapest_dates: "Finding the cheapest dates…",
  search_flights: "Searching flights…",
  search_accommodations: "Finding places to stay…",
  search_web: "Researching the details…",
  search_ground_transport: "Checking trains, buses & ferries…",
  generate_scenarios: "Building your trip options…",
  set_background_image: "Painting your trip vibe…",
};

// Generic messages cycled while the model is "thinking" with no active tool.
const THINKING_BEFORE_TOOLS = "Thinking it through…";
const THINKING_AFTER_TOOLS = "Putting your itinerary together…";

// A live "what's happening" indicator driven by the AG-UI run lifecycle. It
// surfaces the current tool (or a generic thinking message) so the user never
// stares at a blank loading dot during long turns. Hidden once real text starts
// streaming (the answer itself is now visible) or the run ends.
//
// Wired in as CopilotChat's `messageView.cursor` slot, so it renders inline at
// the tail of the conversation (left-aligned, where assistant messages appear)
// in place of the default bare loading dot.
export function ChatStatus() {
  const { agent } = useAgent();
  const [phase, setPhase] = useState("idle"); // idle | thinking | tool | text
  const [toolName, setToolName] = useState(null);
  // Whether any tool has run this turn — switches the generic thinking copy from
  // "thinking it through" to "putting your itinerary together" for the final
  // synthesis step.
  const usedToolRef = useRef(false);

  useEffect(() => {
    if (!agent?.subscribe) return undefined;

    if (agent.isRunning) setPhase("thinking");

    const startTurn = () => {
      usedToolRef.current = false;
      setToolName(null);
      setPhase("thinking");
    };
    const endTurn = () => {
      setPhase("idle");
      setToolName(null);
    };

    const { unsubscribe } = agent.subscribe({
      onRunInitialized: startTurn,
      onRunStartedEvent: startTurn,
      onToolCallStartEvent: (params) => {
        const name = params?.event?.toolCallName ?? params?.toolCallName ?? null;
        usedToolRef.current = true;
        setToolName(name);
        setPhase("tool");
      },
      onToolCallResultEvent: () => setPhase("thinking"),
      onToolCallEndEvent: () => setPhase("thinking"),
      // Real assistant text is now streaming — the answer is visible, so step aside.
      onTextMessageStartEvent: () => setPhase("text"),
      onRunFinishedEvent: endTurn,
      onRunFinalized: endTurn,
      onRunFailed: endTurn,
      onRunErrorEvent: endTurn,
    });

    return () => unsubscribe?.();
  }, [agent]);

  if (phase !== "thinking" && phase !== "tool") return null;

  const label =
    phase === "tool"
      ? TOOL_LABELS[toolName] || "Working on it…"
      : usedToolRef.current
        ? THINKING_AFTER_TOOLS
        : THINKING_BEFORE_TOOLS;

  return (
    <div className="my-2 flex justify-start">
      <div className="inline-flex items-center gap-2 rounded-full border border-pink-200 bg-surface px-3.5 py-2 text-sm font-semibold text-foreground/80 pink-shadow">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <span>{label}</span>
      </div>
    </div>
  );
}
