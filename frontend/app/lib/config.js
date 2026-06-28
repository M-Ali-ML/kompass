// Single source of truth for the CopilotKit endpoint and the API origin.
// Default to a SAME-ORIGIN relative path so the browser hits whatever host
// served the page (localhost, a LAN IP like 192.168.x.x, etc.) and Next's
// `/api/:path*` rewrite proxies it to the backend server-side. This keeps the
// app reachable from other devices on the network without CORS headaches.
// Override with NEXT_PUBLIC_COPILOTKIT_ENDPOINT for a custom backend origin.
export const COPILOTKIT_ENDPOINT =
  process.env.NEXT_PUBLIC_COPILOTKIT_ENDPOINT || "/api/copilotkit";

export const API_BASE = COPILOTKIT_ENDPOINT.replace(/\/api\/copilotkit\/?$/, "");
