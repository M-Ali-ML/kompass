import { API_BASE } from "./config";

// Thin client for the backend trip endpoints. Keeps fetch URLs and the
// success/shape handling in one place so new endpoints are easy to add.

export async function listTrips() {
  const res = await fetch(`${API_BASE}/api/trips`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data.trips) ? data.trips : [];
}

export async function getTrip(tripId) {
  const res = await fetch(`${API_BASE}/api/trips/${tripId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();

  // Prefer the full AG-UI history (includes tool calls + results) so generative
  // UI cards rehydrate on resume; fall back to plain-text turns for old trips.
  if (Array.isArray(data.message_history) && data.message_history.length > 0) {
    return data.message_history;
  }
  return (data.messages || []).map((m) => ({
    id: String(m.id),
    role: m.role,
    content: m.content,
  }));
}

// Persist the full AG-UI message history so generative-UI cards survive a reload.
export async function saveTripMessages(tripId, messages, title) {
  const res = await fetch(`${API_BASE}/api/trips/${tripId}/messages`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, title: title ?? null }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteTrip(tripId) {
  const res = await fetch(`${API_BASE}/api/trips/${tripId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

// --- Saved scenarios ---------------------------------------------------------

export async function saveScenario({ scenario, tripId, destination, currency }) {
  const res = await fetch(`${API_BASE}/api/saved-scenarios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, trip_id: tripId ?? null, destination, currency }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function listSavedScenarios(tripId) {
  const url = tripId
    ? `${API_BASE}/api/saved-scenarios?trip_id=${encodeURIComponent(tripId)}`
    : `${API_BASE}/api/saved-scenarios`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return Array.isArray(data.saved) ? data.saved : [];
}

export async function deleteSavedScenario(savedId) {
  const res = await fetch(`${API_BASE}/api/saved-scenarios/${savedId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}
