// Single source of truth for the CopilotKit endpoint and the API origin.
// The API base is derived by stripping the CopilotKit path so trip endpoints
// (e.g. /api/trips) hit the same backend origin.
export const COPILOTKIT_ENDPOINT =
  process.env.NEXT_PUBLIC_COPILOTKIT_ENDPOINT || "http://localhost:8000/api/copilotkit";

export const API_BASE = COPILOTKIT_ENDPOINT.replace(/\/api\/copilotkit\/?$/, "");
