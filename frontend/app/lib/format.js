export const formatPrice = (amount, currency) => {
  if (amount == null) return "";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "EUR",
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${Math.round(amount)} ${currency || "EUR"}`;
  }
};

export const formatClock = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Extract a YYYY-MM-DD date from an ISO timestamp (or pass through if already a date).
const toDateOnly = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (!Number.isNaN(d.getTime())) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }
  return String(iso).slice(0, 10);
};

// Build a Google Flights search deep link for a single leg. We use a one-way
// search link (rather than a per-fare or round-trip URL) so each leg points at
// exactly its own direction + date — a round-trip query would make Google guess
// a return date and show a misleading window. It's deterministic from the leg
// data and works for restored trips without any extra API calls.
export const googleFlightsUrl = (origin, destination, departureIso) => {
  if (!origin || !destination) return null;
  const date = toDateOnly(departureIso);
  const q = `One-way flights from ${origin} to ${destination}${date ? ` on ${date}` : ""}`;
  return `https://www.google.com/travel/flights?q=${encodeURIComponent(q)}`;
};

// Tool results may arrive as an object or a JSON string depending on transport.
export const parseResult = (result) => {
  if (!result) return null;
  if (typeof result === "string") {
    try {
      return JSON.parse(result);
    } catch {
      return null;
    }
  }
  return result;
};

// Backend data tools signal an unreachable/failed source with an `error` field
// (e.g. {"error": "Flight search is unavailable.", "options": []}). Surface a
// friendly message so the card can render a graceful fallback instead of
// silently vanishing.
export const resultError = (data) => {
  const msg = data?.error;
  return typeof msg === "string" && msg.trim() ? msg.trim() : null;
};

// While a tool call streams, CopilotKit reports `inProgress` (args still
// arriving) then `executing` (running). Pick the right verb so the loading
// label reads "Preparing …" before flipping to the active search copy.
export const isPreparing = (status) => status === "inProgress";
