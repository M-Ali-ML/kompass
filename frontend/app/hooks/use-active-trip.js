import { useCallback, useEffect, useRef, useState } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import { getTrip, saveTripMessages } from "../lib/trips-api";

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

  // When a run finishes, persist the full AG-UI message history (text turns plus
  // tool calls and their results) so the generative-UI cards rehydrate on
  // reload, then refresh the trip list (new trip persisted, title derived).
  useEffect(() => {
    if (!agent) return;
    const sub = agent.subscribe({
      onRunFinalized: async () => {
        try {
          const tripId = agent.threadId;
          const messages = agent.messages || [];
          if (tripId && messages.length > 0) {
            await saveTripMessages(tripId, messages);
          }
        } catch (err) {
          console.error("Failed to persist trip messages", err);
        }
        reloadTrips();
      },
    });
    return () => sub?.unsubscribe?.();
  }, [agent, reloadTrips]);

  // Monotonic guard so rapid trip switches can't race: only the most recent
  // selection is allowed to apply its fetched messages. A slower, earlier
  // getTrip() resolving last would otherwise overwrite the newer trip's chat.
  const selectSeqRef = useRef(0);

  const handleNewTrip = useCallback(() => {
    selectSeqRef.current += 1; // invalidate any in-flight trip selection
    agent?.setMessages([]);
    setActiveThreadId(newThreadId());
  }, [agent]);

  const handleSelectTrip = useCallback(
    async (tripId) => {
      if (!agent || tripId === activeThreadId) return;
      const seq = ++selectSeqRef.current;
      try {
        const messages = await getTrip(tripId);
        if (seq !== selectSeqRef.current) return; // superseded by a newer selection
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
