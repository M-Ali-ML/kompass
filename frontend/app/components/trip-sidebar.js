"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, MapPin, Trash2, Loader2 } from "lucide-react";
import { listTrips, deleteTrip } from "../lib/trips-api";

export function TripSidebar({ activeThreadId, onNewTrip, onSelectTrip, reloadKey }) {
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setTrips(await listTrips());
    } catch (err) {
      console.error("Failed to load trips", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Fetch-on-mount/refresh: setState runs only after the awaited fetch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load, reloadKey]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await deleteTrip(id);
    } catch (err) {
      console.error("Failed to delete trip", err);
    }
    await load();
    if (id === activeThreadId) onNewTrip();
  };

  return (
    <aside className="flex flex-col w-72 shrink-0 h-full bg-surface border-r border-pink-100 pink-shadow">
      <div className="p-4 border-b border-pink-100">
        <button
          onClick={onNewTrip}
          className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-primary text-white font-bold rounded-2xl bouncy-hover pink-shadow"
        >
          <Plus className="w-4 h-4" />
          New Trip
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="px-2 mb-2 text-xs font-bold uppercase tracking-wider text-muted">
          Your Trips
        </div>

        {loading ? (
          <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading…
          </div>
        ) : trips.length === 0 ? (
          <div className="px-2 py-3 text-sm text-muted">
            No trips yet. Start planning!
          </div>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {trips.map((trip) => {
              const isActive = trip.id === activeThreadId;
              return (
                <li key={trip.id}>
                  <div
                    onClick={() => onSelectTrip(trip.id)}
                    className={`group flex items-center gap-2.5 px-3 py-2.5 rounded-2xl cursor-pointer transition-colors ${
                      isActive
                        ? "bg-pink-50 border border-pink-200"
                        : "border border-transparent hover:bg-pink-50/60"
                    }`}
                  >
                    <MapPin
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? "text-primary" : "text-muted"
                      }`}
                    />
                    <span className="flex-1 truncate text-sm font-medium text-foreground">
                      {trip.title || "New Trip"}
                    </span>
                    <button
                      onClick={(e) => handleDelete(e, trip.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-pink-100 text-muted hover:text-primary transition-opacity"
                      aria-label="Delete trip"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
