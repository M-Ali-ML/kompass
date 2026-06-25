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
  return (data.messages || []).map((m) => ({
    id: String(m.id),
    role: m.role,
    content: m.content,
  }));
}

export async function deleteTrip(tripId) {
  const res = await fetch(`${API_BASE}/api/trips/${tripId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}
