"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";
import { AppHeader } from "./components/app-header";
import { TripSidebar } from "./components/trip-sidebar";
import { useActiveTrip } from "./hooks/use-active-trip";
import { useTripTools } from "./hooks/use-trip-tools";

export default function Home() {
  const { activeThreadId, reloadKey, handleNewTrip, handleSelectTrip } = useActiveTrip();

  // Register the generative-UI renderers for each agent tool.
  useTripTools();

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <AppHeader />

      <div className="flex flex-1 overflow-hidden">
        <TripSidebar
          activeThreadId={activeThreadId}
          onNewTrip={handleNewTrip}
          onSelectTrip={handleSelectTrip}
          reloadKey={reloadKey}
        />

        {/* V2 CopilotChat — native reasoning support via AG-UI protocol.
            Messages are driven by the shared agent instance; resuming a trip
            calls agent.setMessages(...) and the chat re-renders in place. */}
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
    </div>
  );
}
