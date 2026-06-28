// Single source of truth for the CopilotKit endpoint and the API origin.
// Default to a SAME-ORIGIN relative path so the browser hits whatever host
// served the page (localhost, a LAN IP like 192.168.x.x, etc.) and Next's
// `/api/:path*` rewrite proxies it to the backend server-side. This keeps the
// app reachable from other devices on the network without CORS headaches.
// Override with NEXT_PUBLIC_COPILOTKIT_ENDPOINT for a custom backend origin.
export const COPILOTKIT_ENDPOINT =
  process.env.NEXT_PUBLIC_COPILOTKIT_ENDPOINT || "/api/copilotkit";

export const API_BASE = COPILOTKIT_ENDPOINT.replace(/\/api\/copilotkit\/?$/, "");

// Port the FastAPI backend listens on (see scripts/dev.sh / next.config rewrite).
const BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT || "8000";

// The endpoint used for the streaming agent connection.
//
// Streaming SSE through Next's dev `rewrites()` proxy gets BUFFERED — the whole
// turn arrives in one batch at the end instead of token-by-token. To avoid that
// we connect the agent DIRECTLY to the FastAPI backend, skipping the proxy hop.
// We reuse the page's own hostname (+ the backend port) so LAN/mobile access
// keeps working — the backend's CORS allows any localhost/127.* origin. An
// explicit NEXT_PUBLIC_COPILOTKIT_ENDPOINT (e.g. in E2E) always wins.
export function resolveStreamingEndpoint() {
  const override = process.env.NEXT_PUBLIC_COPILOTKIT_ENDPOINT;
  if (override) return override;
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:${BACKEND_PORT}/api/copilotkit`;
  }
  // SSR fallback (the live stream only runs client-side).
  return "/api/copilotkit";
}
