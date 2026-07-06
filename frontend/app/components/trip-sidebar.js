"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, MapPin, Trash2, Loader2 } from "lucide-react";
import { listTrips, deleteTrip } from "../lib/trips-api";
import { formatPrice } from "../lib/format";
import { SavedList } from "./saved-list";
import { TripBackdrop } from "./trip-backdrop";

// Inclusive day count for a trip (a Sep 4 → Sep 11 trip reads as 8 days), or
// null when either endpoint is missing/unparseable.
function tripDayCount(start, end) {
  if (!start || !end) return null;
  const s = new Date(start);
  const e = new Date(end);
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null;
  const days = Math.round((e - s) / 86400000) + 1;
  return days > 0 ? days : null;
}

// Derive the at-a-glance sidebar tags from a trip's denormalized scenario
// summary. Kept to a few short chips (destination, duration, budget) so a
// narrow sidebar row never gets crowded; each piece is omitted when absent.
function tripTags(trip) {
  const tags = [];
  if (trip.destination) {
    tags.push({ key: "dest", label: trip.destination, primary: true });
  }
  const days = tripDayCount(trip.start_date, trip.end_date);
  if (days) tags.push({ key: "days", label: `${days}d` });
  if (typeof trip.grand_total === "number" && trip.grand_total > 0) {
    tags.push({ key: "budget", label: `~${formatPrice(trip.grand_total, trip.currency)}` });
  }
  return tags;
}

export function TripSidebar({ activeThreadId, onNewTrip, onSelectTrip, reloadKey }) {
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("trips");

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
    <aside className="flex flex-col w-full h-full bg-surface border-r border-pink-100 pink-shadow">
      <div className="p-4 border-b border-pink-100">
        <button
          onClick={onNewTrip}
          className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-primary text-white font-bold rounded-2xl bouncy-hover pink-shadow"
        >
          <Plus className="w-4 h-4" />
          New Trip
        </button>
      </div>

      <div className="px-3 pt-3">
        <div className="flex gap-1 p-1 bg-pink-50/60 rounded-2xl">
          {[
            { id: "trips", label: "Trips" },
            { id: "saved", label: "Saved" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                tab === t.id
                  ? "bg-surface text-primary pink-shadow"
                  : "text-muted hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        {tab === "saved" ? (
          <SavedList reloadKey={reloadKey} />
        ) : loading ? (
          <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading…
          </div>
        ) : trips.length === 0 ? (
          <div className="px-2 py-3 text-sm text-muted">
            No trips yet. Start planning!
          </div>
        ) : (
          <ul className="flex flex-col gap-2.5">
            {trips.map((trip) => {
              const isActive = trip.id === activeThreadId;
              const tags = tripTags(trip);
              return (
                <li key={trip.id}>
                  <div
                    onClick={() => onSelectTrip(trip.id)}
                    className={`group relative overflow-hidden flex flex-col rounded-2xl cursor-pointer border transition-colors ${
                      isActive
                        ? "bg-pink-50 border-pink-200 pink-shadow"
                        : "bg-surface border-pink-100 hover:border-pink-200 hover:bg-pink-50/60"
                    }`}
                  >
                    {/* Image banner: the generated vibe image at full strength,
                        over a soft candy gradient that stands in before (or in
                        place of) the image. A shimmer covers the first load. */}
                    <div className="relative h-24 w-full bg-gradient-to-br from-pink-100 via-pink-50 to-pink-100">
                      <TripBackdrop
                        tripId={trip.id}
                        version={trip.updated_at}
                        fade="none"
                        intensity={100}
                        withShimmer
                      />
                      {/* Blend the bottom of the image into the text row's own
                          background so the banner reads as part of the card. */}
                      <div
                        className={`pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t to-transparent ${
                          isActive ? "from-pink-50" : "from-surface"
                        }`}
                      />
                      <button
                        onClick={(e) => handleDelete(e, trip.id)}
                        className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 p-1 rounded-lg bg-surface/80 text-muted hover:text-primary hover:bg-surface transition-opacity"
                        aria-label="Delete trip"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Title + at-a-glance tags. */}
                    <div className="px-3 pb-2.5 pt-1">
                      <div className="flex items-center gap-1.5">
                        <MapPin
                          className={`w-3.5 h-3.5 shrink-0 ${
                            isActive ? "text-primary" : "text-muted"
                          }`}
                        />
                        <span className="flex-1 truncate text-sm font-semibold text-foreground">
                          {trip.title || "New Trip"}
                        </span>
                      </div>
                      {tags.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap items-center gap-1">
                          {tags.map((tag) => (
                            <span
                              key={tag.key}
                              className={`max-w-[9rem] truncate rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                tag.primary
                                  ? "bg-pink-100 text-pink-700"
                                  : "bg-pink-50 text-foreground/60 border border-pink-100"
                              }`}
                            >
                              {tag.label}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
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
