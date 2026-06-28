"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Group, Panel } from "react-resizable-panels";
import { CopilotChat } from "@copilotkit/react-core/v2";
import { AlertTriangle, X } from "lucide-react";
import { AppHeader } from "./components/app-header";
import { TripSidebar } from "./components/trip-sidebar";
import { ResizeHandle } from "./components/resize-handle";
import { ChatStatus } from "./components/chat-status";
import { MapStateProvider, useMapState } from "./components/map/map-context";
import { TripPanel } from "./components/map/trip-panel";
import { useActiveTrip } from "./hooks/use-active-trip";
import { useTripTools } from "./hooks/use-trip-tools";
import { useMediaQuery } from "./hooks/use-media-query";

// Whether the active route actually has something to draw on the map. The map
// panel stays hidden until there's real data (a plotted route or a hovered
// stay), so a fresh trip starts as a focused, full-width chat.
function routeHasData(route) {
  return Boolean(
    route && ((route.legs || []).length > 0 || (route.accommodations || []).length > 0)
  );
}

// Custom slots for the chat's message view:
// - `reasoningMessage`: candy styling for the agent's built-in reasoning
//   ("thinking") bubble (AG-UI REASONING_* events render via
//   CopilotChatReasoningMessage) — dressed in the pink, rounded chat look.
// - `cursor`: replaces the default bare loading dot with `ChatStatus`, a live
//   "what's happening" indicator (current tool / generic thinking) inline at
//   the tail of the conversation.
const CHAT_VIEW_SLOTS = {
  messageView: {
    reasoningMessage: {
      className:
        "!my-2 !rounded-2xl !border !border-pink-100 !bg-pink-50/50 !px-3.5 !py-2.5 !text-foreground/80",
    },
    cursor: ChatStatus,
  },
};

export default function Home() {
  const trip = useActiveTrip();

  return (
    <MapStateProvider>
      <Workspace {...trip} />
    </MapStateProvider>
  );
}

function Workspace({ activeThreadId, reloadKey, handleNewTrip, handleSelectTrip }) {
  const { activeRoute, hoveredStay, setActiveRoute } = useMapState();

  // Show the map panel only when there's data to plot. A new/empty trip (or one
  // still gathering info) keeps the map hidden so the chat gets the full width.
  const showMap = routeHasData(activeRoute) || Boolean(hoveredStay);

  // Reset the plotted route whenever the active trip changes (new trip or
  // switching trips) so a stale route never lingers on the map. The relevant
  // scenario card re-plots its route once a resumed trip's messages render.
  useEffect(() => {
    setActiveRoute(null);
  }, [activeThreadId, setActiveRoute]);

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

  // Desktop (lg+) gets the full three-pane split. Below that, the chat is
  // full-width, the map is hidden (chat-side cards are the experience), and the
  // trip sidebar collapses into an off-canvas drawer reached via the header
  // hamburger. We conditionally render panels (rather than CSS-hide) so
  // react-resizable-panels doesn't reserve space for them.
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [drawerOpen, setDrawerOpen] = useState(false);
  // The desktop trips sidebar starts collapsed so the chat opens front-and-center;
  // the header menu button toggles it. On mobile the same button opens the drawer.
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const handleMenuClick = useCallback(() => {
    if (isDesktop) setSidebarCollapsed((c) => !c);
    else setDrawerOpen(true);
  }, [isDesktop]);

  // The drawer is only rendered while `!isDesktop`, so growing into the desktop
  // layout hides it automatically — no effect needed to force it closed.

  // On mobile, picking/creating a trip should close the drawer so the chat shows.
  const selectTrip = useCallback(
    (id) => {
      handleSelectTrip(id);
      setDrawerOpen(false);
    },
    [handleSelectTrip]
  );
  const newTrip = useCallback(() => {
    handleNewTrip();
    setDrawerOpen(false);
  }, [handleNewTrip]);

  // Persist the user's drag-resized desktop layout.
  const groupRef = useRef(null);
  const storageKey = "kompass-layout-map:v2";

  // Only restore (and persist) the saved layout while the map pane is mounted,
  // since the stored sizes describe the three-pane split. When the map is
  // hidden the two remaining panes fall back to their default sizing.
  useEffect(() => {
    if (!isDesktop || !showMap || sidebarCollapsed) return;
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw && groupRef.current?.setLayout) {
        groupRef.current.setLayout(JSON.parse(raw));
      }
    } catch {
      // Ignore malformed/missing saved layouts — defaults apply.
    }
  }, [storageKey, isDesktop, showMap, sidebarCollapsed]);

  const handleLayoutChanged = useCallback(
    (layout) => {
      // Only persist the full three-pane layout; partial layouts (a collapsed
      // sidebar or hidden map) would have a different shape on restore.
      if (!showMap || sidebarCollapsed) return;
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(layout));
      } catch {
        // Persistence is best-effort.
      }
    },
    [storageKey, showMap, sidebarCollapsed]
  );

  // Register the generative-UI renderers for each agent tool.
  useTripTools();

  const sidebar = (
    <TripSidebar
      activeThreadId={activeThreadId}
      onNewTrip={newTrip}
      onSelectTrip={selectTrip}
      reloadKey={reloadKey}
    />
  );

  // V2 CopilotChat — native reasoning support via AG-UI protocol. Messages are
  // driven by the shared agent instance; resuming a trip calls
  // agent.setMessages(...) and the chat re-renders in place.
  const chatPanel = (
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
  );

  return (
    <>
      <div className="flex flex-col h-screen overflow-hidden bg-background">
        <AppHeader showMenu onMenuClick={handleMenuClick} />

        {isDesktop ? (
          /* Three resizable panes (history | chat | map) with draggable
             dividers. Sizes persist in localStorage. */
          <Group
            key={storageKey}
            groupRef={groupRef}
            orientation="horizontal"
            onLayoutChanged={handleLayoutChanged}
            className="flex-1 overflow-hidden"
          >
            {/* Trips sidebar — collapsed by default; the header menu toggles it. */}
            {!sidebarCollapsed && (
              <>
                <Panel id="sidebar" defaultSize="18%" minSize="12%" maxSize="32%">
                  {sidebar}
                </Panel>
                <ResizeHandle />
              </>
            )}

            <Panel id="chat" minSize="25%" className="min-w-0">
              {chatPanel}
            </Panel>

            {/* Right split-panel: itinerary summary + interactive trip map.
                Mounted only once there's a route/stay to show, so a fresh trip
                opens as a focused, full-width chat. */}
            {showMap && (
              <>
                <ResizeHandle />
                <Panel id="map" defaultSize="34%" minSize="20%" maxSize="55%">
                  <TripPanel />
                </Panel>
              </>
            )}
          </Group>
        ) : (
          /* Mobile/tablet: full-width chat; trips live in an off-canvas drawer. */
          <div className="flex-1 min-h-0 overflow-hidden">{chatPanel}</div>
        )}

        {/* Off-canvas trip drawer (mobile only). Kept mounted so it can slide
            in/out; backdrop closes it. */}
        {!isDesktop && (
          <div
            className={`fixed inset-0 z-[1300] ${drawerOpen ? "" : "pointer-events-none"}`}
            aria-hidden={!drawerOpen}
          >
            <div
              onClick={() => setDrawerOpen(false)}
              className={`absolute inset-0 bg-foreground/40 backdrop-blur-sm transition-opacity duration-300 ${
                drawerOpen ? "opacity-100" : "opacity-0"
              }`}
            />
            <div
              className={`absolute inset-y-0 left-0 w-[82%] max-w-xs transition-transform duration-300 ease-out ${
                drawerOpen ? "translate-x-0" : "-translate-x-full"
              }`}
            >
              {sidebar}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
