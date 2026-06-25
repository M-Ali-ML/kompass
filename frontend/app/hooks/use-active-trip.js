import { useCallback, useEffect, useState } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import { getTrip } from "../lib/trips-api";

const newThreadId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `trip-${Date.now()}-${Math.random().toString(36).slice(2)}`;

// Owns the active trip/thread state and keeps the shared agent in sync with it.
// `reloadKey` bumps whenever the trip list should refresh (e.g. after a run).
export function useActiveTrip() {
  const { agent } = useAgent();
  const [activeThreadId, setActiveThreadId] = useState(() => newThreadId());
  const [reloadKey, setReloadKey] = useState(0);
  const reloadTrips = useCallback(() => setReloadKey((k) => k + 1), []);

  // Keep the agent's thread id in sync with the active trip. This parent effect
  // runs after CopilotChat's own mount effect (which would otherwise assign a
  // random thread id), so the backend persists messages under the trip we show
  // as active. We intentionally do NOT pass `threadId`/`key` to CopilotChat —
  // remounting it triggers the cloud-thread `connectAgent` bootstrap which
  // races with the messages we load on resume.
  useEffect(() => {
    // The agent instance is intentionally mutable shared state (CopilotChat
    // mutates agent.threadId the same way internally).
    // eslint-disable-next-line react-hooks/immutability
    if (agent) agent.threadId = activeThreadId;
  }, [agent, activeThreadId]);

  // Refresh the trip list whenever an agent run finishes (new trip persisted,
  // title derived, latest assistant turn stored).
  useEffect(() => {
    if (!agent) return;
    const sub = agent.subscribe({
      onRunFinalized: () => reloadTrips(),
    });
    return () => sub?.unsubscribe?.();
  }, [agent, reloadTrips]);

  const handleNewTrip = useCallback(() => {
    agent?.setMessages([]);
    setActiveThreadId(newThreadId());
  }, [agent]);

  const handleSelectTrip = useCallback(
    async (tripId) => {
      if (!agent || tripId === activeThreadId) return;
      try {
        const messages = await getTrip(tripId);
        agent.setMessages(messages);
        setActiveThreadId(tripId);
      } catch (err) {
        console.error("Failed to resume trip", err);
      }
    },
    [agent, activeThreadId]
  );

  return { activeThreadId, reloadKey, handleNewTrip, handleSelectTrip };
}
