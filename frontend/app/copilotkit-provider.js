"use client";

import { useMemo } from "react";
import { CopilotKit, HttpAgent } from "@copilotkit/react-core/v2";
import { resolveStreamingEndpoint } from "./lib/config";

export function CopilotKitWrapper({ children }) {
  // Build the agent on the client so it resolves the host-aware DIRECT backend
  // URL (bypassing Next's SSE-buffering dev proxy). Memoized so the instance is
  // stable across re-renders for the lifetime of the provider.
  const agentInstance = useMemo(
    () => new HttpAgent({ url: resolveStreamingEndpoint() }),
    []
  );

  // `selfManagedAgents` registers a client-side agent that talks straight to
  // our own AG-UI backend (no CopilotKit runtime in between). Safe here: the
  // HttpAgent carries only a URL — no API keys ever reach the browser bundle.
  const agents = useMemo(() => ({ default: agentInstance }), [agentInstance]);

  return <CopilotKit selfManagedAgents={agents}>{children}</CopilotKit>;
}
