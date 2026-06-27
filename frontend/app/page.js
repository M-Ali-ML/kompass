"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Group, Panel } from "react-resizable-panels";
import { CopilotChat } from "@copilotkit/react-core/v2";
import { AlertTriangle, X } from "lucide-react";
import { AppHeader } from "./components/app-header";
import { TripSidebar } from "./components/trip-sidebar";
import { ResizeHandle } from "./components/resize-handle";
import { MapStateProvider } from "./components/map/map-context";
import { TripPanel } from "./components/map/trip-panel";
import { useActiveTrip } from "./hooks/use-active-trip";
import { useTripTools } from "./hooks/use-trip-tools";
import { useMediaQuery } from "./hooks/use-media-query";

// Candy styling for the agent's built-in reasoning ("thinking") bubble. The
// AG-UI REASONING_* events already render collapsibly via CopilotKit's
// CopilotChatReasoningMessage — these classes just dress it in the pink,
// rounded look of the rest of the chat. Passed through the nested chatView →
// messageView → reasoningMessage slot.
const CHAT_VIEW_SLOTS = {
  messageView: {
    reasoningMessage: {
      className:
        "!my-2 !rounded-2xl !border !border-pink-100 !bg-pink-50/50 !px-3.5 !py-2.5 !text-foreground/80",
    },
  },
};

export default function Home() {
  const { activeThreadId, reloadKey, handleNewTrip, handleSelectTrip } = useActiveTrip();

  // Surface run-level failures (e.g. an MCP server / model error mid-run) as a
  // dismissible toast over the chat, then auto-clear. Tool-level "no live data"
  // cases are handled gracefully inside the individual tool cards.
  const [chatError, setChatError] = useState(null);
  const handleChatError = useCallback(({ error }) => {
    setChatError(error?.message || "Something went wrong while planning. Please try again.");
  }, []);
  useEffect(() => {
    if (!chatError) return;
    const t = setTimeout(() => setChatError(null), 8000);
    return () => clearTimeout(t);
  }, [chatError]);

  // The map panel only shows on wide screens; below that the chat-side scenario
  // cards are the experience. We conditionally render the panel (rather than
  // CSS-hide it) so react-resizable-panels doesn't reserve space for it.
  const showMap = useMediaQuery("(min-width: 1024px)");

  // Persist the user's drag-resized layout per variant (with/without map).
  const groupRef = useRef(null);
  const storageKey = showMap ? "kompass-layout-map:v2" : "kompass-layout:v2";

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw && groupRef.current?.setLayout) {
        groupRef.current.setLayout(JSON.parse(raw));
      }
    } catch {
      // Ignore malformed/missing saved layouts — defaults apply.
    }
  }, [storageKey]);

  const handleLayoutChanged = useCallback(
    (layout) => {
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(layout));
      } catch {
        // Persistence is best-effort.
      }
    },
    [storageKey]
  );

  // Register the generative-UI renderers for each agent tool.
  useTripTools();

  return (
    <MapStateProvider>
      <div className="flex flex-col h-screen overflow-hidden bg-background">
        <AppHeader />

        {/* Three resizable panes (history | chat | map) with draggable
            dividers. Sizes persist per-layout in localStorage. */}
        <Group
          key={storageKey}
          groupRef={groupRef}
          orientation="horizontal"
          onLayoutChanged={handleLayoutChanged}
          className="flex-1 overflow-hidden"
        >
          <Panel id="sidebar" defaultSize="18%" minSize="12%" maxSize="32%">
            <TripSidebar
              activeThreadId={activeThreadId}
              onNewTrip={handleNewTrip}
              onSelectTrip={handleSelectTrip}
              reloadKey={reloadKey}
            />
          </Panel>

          <ResizeHandle />

          {/* V2 CopilotChat — native reasoning support via AG-UI protocol.
              Messages are driven by the shared agent instance; resuming a trip
              calls agent.setMessages(...) and the chat re-renders in place. */}
          <Panel id="chat" minSize="25%" className="min-w-0">
            <div className="relative h-full">
              {chatError && (
                <div className="absolute inset-x-3 top-3 z-10 flex items-start gap-2 rounded-2xl bg-rose-50 border border-rose-200 px-3.5 py-2.5 pink-shadow">
                  <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <p className="flex-1 text-xs text-rose-700/90 leading-relaxed">{chatError}</p>
                  <button
                    type="button"
                    onClick={() => setChatError(null)}
                    aria-label="Dismiss"
                    className="text-rose-400 hover:text-rose-600 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
              <CopilotChat
                className="h-full"
                onError={handleChatError}
                chatView={CHAT_VIEW_SLOTS}
                labels={{
                  title: "Kompass Travel Assistant",
                  placeholder: "Where do you want to go?",
                }}
              />
            </div>
          </Panel>

          {showMap && (
            <>
              <ResizeHandle />
              {/* Right split-panel: itinerary summary + interactive trip map. */}
              <Panel id="map" defaultSize="34%" minSize="20%" maxSize="55%">
                <TripPanel />
              </Panel>
            </>
          )}
        </Group>
      </div>
    </MapStateProvider>
  );
}
