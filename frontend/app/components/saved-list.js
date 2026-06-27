"use client";

import { useCallback, useEffect, useState } from "react";
import { Bookmark, Trash2, Loader2 } from "lucide-react";
import { listSavedScenarios, deleteSavedScenario } from "../lib/trips-api";
import { formatPrice } from "../lib/format";
import { fmtDay } from "../lib/itinerary";
import { ScenarioDetailModal } from "./tool-cards/scenario-detail-modal";

const stressDot = (score) =>
  score <= 2 ? "bg-emerald-400" : score === 3 ? "bg-amber-400" : "bg-rose-400";

const fmtRange = (start, end) => {
  const a = fmtDay(start);
  const b = fmtDay(end);
  return a && b ? `${a} – ${b}` : a || b || "";
};

// Lists all saved scenarios (newest first). Click to open the detail popup;
// trash to delete. `reloadKey` forces a refetch when bumped by the parent.
export function SavedList({ reloadKey }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openItem, setOpenItem] = useState(null);

  const load = useCallback(async () => {
    try {
      setItems(await listSavedScenarios());
    } catch (err) {
      console.error("Failed to load saved scenarios", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load, reloadKey]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await deleteSavedScenario(id);
    } catch (err) {
      console.error("Failed to delete saved scenario", err);
    }
    await load();
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading…
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="px-2 py-3 text-sm text-muted">
        No saved trips yet. Open a scenario and hit “Save this trip”.
      </div>
    );
  }

  return (
    <>
      <ul className="flex flex-col gap-1.5">
        {items.map((it) => {
          const title = it.destination || it.label || "Saved trip";
          return (
            <li key={it.id}>
              <div
                onClick={() => setOpenItem(it)}
                className="group flex flex-col gap-1 px-3 py-2.5 rounded-2xl cursor-pointer border border-transparent hover:bg-pink-50/60"
              >
                <div className="flex items-center gap-2">
                  <Bookmark className="w-4 h-4 shrink-0 text-primary" />
                  <span className="flex-1 truncate text-sm font-semibold text-foreground">
                    {title}
                  </span>
                  <button
                    onClick={(e) => handleDelete(e, it.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-pink-100 text-muted hover:text-primary transition-opacity"
                    aria-label="Delete saved trip"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="flex items-center justify-between pl-6 text-xs">
                  <span className="truncate text-foreground/60">
                    {it.comparison_label ? `${it.comparison_label} · ` : ""}
                    {fmtRange(it.start_date, it.end_date)}
                  </span>
                  <span className="flex items-center gap-2 shrink-0">
                    {it.stress_score != null && (
                      <span
                        className={`w-2 h-2 rounded-full ${stressDot(it.stress_score)}`}
                        title={`Stress ${it.stress_score}/5`}
                      />
                    )}
                    {it.grand_total != null && (
                      <span className="font-bold text-primary">
                        {formatPrice(it.grand_total, it.currency)}
                      </span>
                    )}
                  </span>
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      {openItem && (
        <ScenarioDetailModal
          scenario={openItem.scenario || {}}
          currency={openItem.currency}
          destination={openItem.destination}
          savedId={openItem.id}
          tripId={openItem.trip_id}
          onRemoved={() => load()}
          onClose={() => setOpenItem(null)}
        />
      )}
    </>
  );
}
