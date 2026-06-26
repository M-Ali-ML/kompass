"use client";

import { useCallback, useEffect, useRef } from "react";
import { Group, Panel } from "react-resizable-panels";
import { CopilotChat } from "@copilotkit/react-core/v2";
import { AppHeader } from "./components/app-header";
import { TripSidebar } from "./components/trip-sidebar";
import { ResizeHandle } from "./components/resize-handle";
import { MapStateProvider } from "./components/map/map-context";
import { TripPanel } from "./components/map/trip-panel";
import { useActiveTrip } from "./hooks/use-active-trip";
import { useTripTools } from "./hooks/use-trip-tools";
import { useMediaQuery } from "./hooks/use-media-query";

export default function Home() {
  const { activeThreadId, reloadKey, handleNewTrip, handleSelectTrip } = useActiveTrip();

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
            <CopilotChat
              className="h-full"
              labels={{
                title: "Kompass Travel Assistant",
                placeholder: "Where do you want to go?",
              }}
            />
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
