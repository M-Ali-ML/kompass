"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useAgent } from "@copilotkit/react-core/v2";
import {
  Plane,
  BedDouble,
  X,
  Clock,
  Moon,
  Timer,
  Repeat,
  MapPin,
  Heart,
  Check,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { formatPrice, googleFlightsUrl } from "../../lib/format";
import { saveScenario, deleteSavedScenario } from "../../lib/trips-api";
import { useMapState, routeFromScenario } from "../map/map-context";
import { MODE_GLYPH } from "../../lib/transport";
import {
  STRESS_LABEL,
  TRIP_GAP_MINUTES,
  stressTone,
  fmtDay,
  fmtYear,
  fmtTime,
  fmtDuration,
  formatLegPrice,
  legMinutes,
  layoverMinutes,
  isTightConnection,
  isOvernightLeg,
  splitJourneys,
  journeyMinutes,
  cleanCarrier,
  nightsBetween,
  tripNights,
} from "../../lib/itinerary";
import { TripBackdrop } from "../trip-backdrop";
import { StressGauge, LegIcon, StatTile, CostBar, DayRow } from "./scenario-parts";

const SAVE_LABEL = {
  idle: "Save this trip",
  saving: "Saving…",
  saved: "Saved",
  error: "Couldn't save — retry",
};

// Centered popup with the full itinerary for one scenario (opened from "View details").
// When `savedId` is provided (opened from the Saved panel), the footer offers
// "Remove from saved" instead of the save action.
export function ScenarioDetailModal({ scenario, currency, destination, savedId, tripId, onRemoved, onClose }) {
  const { agent } = useAgent();
  const { setActiveRoute } = useMapState();
  // Resolve which trip's vibe image to show: an explicit tripId (saved entries
  // carry their own) wins, otherwise fall back to the live conversation thread.
  const backdropTripId = tripId || agent?.threadId;
  const [saveState, setSaveState] = useState("idle");
  const [removeState, setRemoveState] = useState("idle");
  // Track which day rows are expanded. Day 1 starts open; "Expand all" opens the rest.
  const [openDays, setOpenDays] = useState(() => new Set([0]));

  const toggleDay = (i) =>
    setOpenDays((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });

  const handleViewOnMap = () => {
    setActiveRoute(routeFromScenario(scenario, { destination, currency }));
    onClose();
  };

  const handleSave = async () => {
    if (saveState === "saving" || saveState === "saved") return;
    setSaveState("saving");
    try {
      await saveScenario({
        scenario,
        tripId: agent?.threadId,
        destination,
        currency,
      });
      setSaveState("saved");
    } catch (e) {
      console.error("Failed to save scenario", e);
      setSaveState("error");
    }
  };

  const handleRemove = async () => {
    if (removeState === "removing") return;
    setRemoveState("removing");
    try {
      await deleteSavedScenario(savedId);
      onRemoved?.(savedId);
      onClose();
    } catch (e) {
      console.error("Failed to remove saved scenario", e);
      setRemoveState("error");
    }
  };

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  if (typeof document === "undefined") return null;

  const cb = scenario.cost_breakdown || {};
  const sf = scenario.stress_factors || {};
  const it = scenario.itinerary || {};
  const legs = it.legs || [];
  const stays = it.accommodations || [];
  const days = it.days || [];
  const allDaysOpen = days.length > 0 && openDays.size >= days.length;
  const highlights = scenario.highlights || [];
  const tone = stressTone(scenario.stress_score);
  const total = cb.grand_total || 0;
  const nights = tripNights(scenario.start_date, scenario.end_date);
  const travelers = Math.max(1, Math.round(scenario.travelers || 1));

  // Split the legs into outbound/return journeys so travel time reflects BOTH
  // directions rather than a single conflated number.
  const journeys = splitJourneys(legs);
  const outboundMin = journeyMinutes(journeys[0]);
  const returnMin = journeys.length > 1 ? journeyMinutes(journeys[journeys.length - 1]) : 0;

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-foreground/40 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-[640px] max-h-[92vh] sm:max-h-[88vh] flex flex-col rounded-t-3xl sm:rounded-3xl bg-surface pink-shadow-deep overflow-hidden">
        {/* Header */}
        <div className="relative overflow-hidden px-5 pt-5 pb-3 min-h-[104px] flex flex-col justify-end border-b border-pink-100">
          <TripBackdrop tripId={backdropTripId} fade="bottom" />
          {/* Scrim: kept light so the image stays vivid, with a horizontal
              gradient that only protects the left edge where the title sits and
              a soft bottom wash so the heading/dates stay legible. */}
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-surface via-surface/55 to-transparent" />
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-surface/85 to-transparent" />
          <div className="relative z-10 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-lg font-extrabold text-foreground leading-tight [text-shadow:0_1px_3px_rgba(255,255,255,0.7)]">{scenario.label}</h2>
              <div className="flex items-center flex-wrap gap-2 mt-1">
                {scenario.comparison_label && (
                  <span className="px-2.5 py-0.5 bg-secondary/15 text-secondary rounded-full text-[11px] font-bold uppercase tracking-wide">
                    {scenario.comparison_label}
                  </span>
                )}
                <span className="text-xs font-medium text-foreground/70">
                  {fmtDay(scenario.start_date)} – {fmtDay(scenario.end_date)}
                  {fmtYear(scenario.end_date) ? `, ${fmtYear(scenario.end_date)}` : ""}
                  {nights ? ` · ${nights} nights` : ""}
                  {travelers > 1 ? ` · ${travelers} travelers` : ""}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full text-foreground/60 hover:bg-pink-50 hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-5">
          {/* Price + stress */}
          <div className="flex items-end justify-between gap-4">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-foreground/60">Total price</div>
              <div className="text-3xl font-extrabold text-primary">{formatPrice(total, currency)}</div>
            </div>
            <div className="text-right">
              <div className={`text-[11px] font-bold uppercase tracking-wider ${tone.text}`}>
                {STRESS_LABEL[scenario.stress_score] || ""} · {scenario.stress_score}/5
              </div>
              <div className="mt-1 w-32 ml-auto">
                <StressGauge score={scenario.stress_score} />
              </div>
            </div>
          </div>

          {/* Highlights */}
          {highlights.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {highlights.map((h, i) => (
                <span
                  key={i}
                  className="px-2.5 py-0.5 bg-pink-50 text-pink-700 border border-pink-100 rounded-full text-[11px] font-medium"
                >
                  {h}
                </span>
              ))}
            </div>
          )}

          {/* Cost breakdown */}
          <section>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">Cost breakdown</h3>
            <div className="flex flex-col gap-3">
              <CostBar icon={Plane} label="Transport" amount={cb.transportation} total={total} currency={currency} barClass="bg-primary" />
              <CostBar icon={BedDouble} label="Stay" amount={cb.accommodation} total={total} currency={currency} barClass="bg-secondary" />
            </div>
          </section>

          {/* Stress factors */}
          <section>
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">Stress factors</h3>
            <div className="flex flex-wrap gap-2">
              <StatTile icon={Repeat} label="Layovers" value={sf.layover_count ?? "—"} />
              <StatTile icon={Moon} label="Overnight" value={sf.overnight_travel ? "Yes" : "No"} />
              <StatTile icon={Timer} label="Tight conn." value={sf.tight_connection ? "Yes" : "No"} />
              <StatTile
                icon={Clock}
                label="Travel time"
                value={
                  outboundMin && returnMin ? (
                    <span className="flex flex-col leading-tight">
                      <span>
                        {fmtDuration(outboundMin)}{" "}
                        <span className="text-[11px] font-semibold text-foreground/55">out</span>
                      </span>
                      <span>
                        {fmtDuration(returnMin)}{" "}
                        <span className="text-[11px] font-semibold text-foreground/55">back</span>
                      </span>
                    </span>
                  ) : outboundMin ? (
                    fmtDuration(outboundMin)
                  ) : sf.total_travel_hours != null ? (
                    `${sf.total_travel_hours}h`
                  ) : (
                    "—"
                  )
                }
              />
            </div>
          </section>

          {/* Travel timeline */}
          {legs.length > 0 && (
            <section>
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">Travel timeline</h3>
              <ol className="flex flex-col">
                {legs.map((leg, i) => {
                  const mins = legMinutes(leg);
                  const layover = i < legs.length - 1 ? layoverMinutes(leg, legs[i + 1]) : 0;
                  const flightHref =
                    leg.mode === "flight"
                      ? leg.booking_link ||
                        googleFlightsUrl(leg.origin, leg.destination, leg.departure_time)
                      : null;
                  const carrier = cleanCarrier(leg.carrier);
                  const isStay = layover > TRIP_GAP_MINUTES;
                  const tight = !isStay && isTightConnection(layover, legs[i + 1]);
                  const overnight = isOvernightLeg(leg);
                  return (
                    <li key={i} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <LegIcon mode={leg.mode} className="mt-0.5" />
                        {i < legs.length - 1 && <span className="flex-1 w-px bg-pink-200 my-1" />}
                      </div>
                      <div className="flex-1 pb-3">
                        <div className="flex items-center justify-between gap-2">
                          {flightHref ? (
                            <a
                              href={flightHref}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="View this flight on Google Flights"
                              className="group inline-flex items-center gap-1 text-sm font-bold text-foreground hover:text-primary"
                            >
                              {leg.origin} → {leg.destination}
                              <ExternalLink className="w-3 h-3 text-secondary opacity-60 group-hover:opacity-100" />
                            </a>
                          ) : (
                            <span className="text-sm font-bold text-foreground">
                              {leg.origin} → {leg.destination}
                            </span>
                          )}
                          <span className="text-xs font-semibold text-foreground/70">
                            {formatLegPrice(leg, travelers, currency)}
                          </span>
                        </div>
                        <div className="text-xs text-foreground/70 mt-0.5">
                          {fmtTime(leg.departure_time)}
                          {fmtTime(leg.arrival_time) ? ` – ${fmtTime(leg.arrival_time)}` : ""}
                          {mins ? ` · ${fmtDuration(mins)}` : ""}
                        </div>
                        {carrier && (
                          <div className="flex items-center gap-1 text-xs font-medium text-foreground/80 mt-0.5">
                            {leg.mode === "flight" ? (
                              <Plane className="w-3 h-3 text-secondary" />
                            ) : (
                              <span className="text-xs leading-none">
                                {MODE_GLYPH[leg.mode] || MODE_GLYPH.other}
                              </span>
                            )}{" "}
                            {carrier}
                          </div>
                        )}
                        {/* Overnight segment (e.g. a night ferry or sleeper train). */}
                        {overnight && (
                          <div className="mt-1.5 mr-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-[11px] font-medium">
                            <Moon className="w-3 h-3" /> Overnight
                          </div>
                        )}
                        {/* Short gap = connecting layover; long gap = the trip stay. */}
                        {layover > 0 && !isStay && (
                          tight ? (
                            <div className="mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-50 text-rose-600 border border-rose-200 text-[11px] font-medium">
                              <Clock className="w-3 h-3" /> Tight connection · {fmtDuration(layover)} in {leg.destination}
                            </div>
                          ) : (
                            <div className="mt-1.5 inline-block px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 text-[11px] font-medium">
                              {fmtDuration(layover)} layover in {leg.destination}
                            </div>
                          )
                        )}
                        {isStay && (
                          <div className="mt-1.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary/10 text-secondary border border-secondary/20 text-[11px] font-medium">
                            <BedDouble className="w-3 h-3" /> {Math.round(layover / 1440)} nights in{" "}
                            {leg.destination}
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </section>
          )}

          {/* Accommodation */}
          {stays.length > 0 && (
            <section>
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">Accommodation</h3>
              <div className="flex flex-col gap-2">
                {stays.map((s, i) => {
                  const n = nightsBetween(s.check_in, s.check_out);
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl bg-surface border border-pink-100 purple-shadow"
                    >
                      <div className="min-w-0">
                        {s.booking_link ? (
                          <a
                            href={s.booking_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="View this property"
                            className="group inline-flex items-center gap-1 text-sm font-bold text-foreground hover:text-primary"
                          >
                            <span className="truncate">{s.name}</span>
                            <ExternalLink className="w-3 h-3 text-secondary opacity-60 group-hover:opacity-100 shrink-0" />
                          </a>
                        ) : (
                          <div className="text-sm font-bold text-foreground truncate">{s.name}</div>
                        )}
                        <div className="flex items-center gap-1 text-xs text-foreground/70">
                          <MapPin className="w-3 h-3 text-secondary" /> {s.location}
                          {n ? ` · ${n} nights` : ""}
                        </div>
                      </div>
                      <span className="shrink-0 text-sm font-bold text-foreground">
                        {formatPrice(s.cost, currency)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Day-by-day */}
          {days.length > 0 && (
            <section>
              <div className="flex items-center justify-between gap-2 mb-2">
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70">
                  Day-by-day itinerary
                  <span className="ml-1.5 text-foreground/40">{days.length} days</span>
                </h3>
                {days.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setOpenDays(allDaysOpen ? new Set() : new Set(days.map((_, i) => i)))}
                    className="text-[11px] font-bold text-primary hover:underline"
                  >
                    {allDaysOpen ? "Collapse all" : "Expand all"}
                  </button>
                )}
              </div>
              <div className="flex flex-col gap-2">
                {days.map((d, i) => (
                  <DayRow
                    key={i}
                    day={d}
                    open={openDays.has(i)}
                    onToggle={() => toggleDay(i)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Reasoning */}
          {scenario.reasoning_summary && (
            <section className="px-3 py-2.5 rounded-xl bg-pink-50/60 border border-pink-100">
              <p className="text-xs text-foreground/80 leading-relaxed">{scenario.reasoning_summary}</p>
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-pink-100 flex flex-col gap-1.5">
          {savedId ? (
            <button
              type="button"
              onClick={handleRemove}
              disabled={removeState === "removing"}
              className={`w-full py-2.5 rounded-xl text-sm font-bold inline-flex items-center justify-center gap-2 bouncy-hover border ${
                removeState === "error"
                  ? "border-rose-300 text-rose-600 bg-rose-50"
                  : "border-pink-200 text-rose-600 hover:bg-rose-50"
              } ${removeState === "removing" ? "opacity-70" : ""}`}
            >
              <Trash2 className="w-4 h-4" />
              {removeState === "removing"
                ? "Removing…"
                : removeState === "error"
                ? "Couldn't remove — retry"
                : "Remove from saved"}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSave}
              disabled={saveState === "saving" || saveState === "saved"}
              className={`w-full py-2.5 rounded-xl text-sm font-bold inline-flex items-center justify-center gap-2 bouncy-hover pink-shadow ${
                saveState === "saved"
                  ? "bg-emerald-500 text-white"
                  : saveState === "error"
                  ? "bg-rose-500 text-white"
                  : "bg-primary text-white"
              } ${saveState === "saving" ? "opacity-70" : ""}`}
            >
              {saveState === "saved" ? <Check className="w-4 h-4" /> : <Heart className="w-4 h-4" />}
              {SAVE_LABEL[saveState]}
            </button>
          )}
          <button
            type="button"
            onClick={handleViewOnMap}
            className="hidden lg:inline-flex w-full py-2 rounded-xl border border-pink-200 text-primary text-sm font-semibold items-center justify-center gap-2 bouncy-hover hover:bg-pink-50"
          >
            <MapPin className="w-4 h-4" /> View on map
          </button>
          <button
            type="button"
            onClick={onClose}
            className="w-full py-1.5 text-xs font-semibold text-foreground/60 hover:text-foreground"
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
