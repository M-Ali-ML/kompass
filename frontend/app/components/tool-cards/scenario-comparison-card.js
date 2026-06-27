"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useAgent } from "@copilotkit/react-core/v2";
import {
  Compass,
  Plane,
  BedDouble,
  Info,
  X,
  Clock,
  Moon,
  Timer,
  Repeat,
  MapPin,
  ChevronDown,
  Heart,
  Check,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { z } from "zod";
import { formatPrice, parseResult, googleFlightsUrl } from "../../lib/format";
import { saveScenario, deleteSavedScenario } from "../../lib/trips-api";
import { useMapState, routeFromScenario } from "../map/map-context";
import { MODE_GLYPH } from "../../lib/transport";
import { TripBackdrop } from "../trip-backdrop";

export const scenarioComparisonParameters = z.object({
  destination: z.string().optional(),
  estimated: z.boolean().optional(),
});

const STRESS_LABEL = { 1: "Relaxed", 2: "Easy", 3: "Moderate", 4: "Busy", 5: "Intense" };

// Transit fares are priced per person, so with a group we show the per-person
// unit price alongside the count (e.g. "2× €49"). Stays are a whole-property
// total, so they stay as a single figure.
const PER_PERSON_MODES = new Set(["flight", "train", "bus", "ferry"]);

const formatLegPrice = (leg, travelers, currency) => {
  const perPerson =
    travelers > 1 && PER_PERSON_MODES.has(leg.mode) && leg.cost > 0;
  return perPerson
    ? `${travelers}× ${formatPrice(leg.cost / travelers, currency)}`
    : formatPrice(leg.cost, currency);
};

// Lower stress is better, so the gauge runs calm-green → busy-rose.
const stressTone = (score) =>
  score <= 2
    ? { text: "text-emerald-600", pip: "bg-emerald-400" }
    : score === 3
    ? { text: "text-amber-600", pip: "bg-amber-400" }
    : { text: "text-rose-500", pip: "bg-rose-400" };

const fmtDay = (iso) => {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
};

const fmtYear = (iso) => {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? "" : d.getFullYear();
};

const fmtTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false });
};

const fmtDuration = (mins) => {
  if (!mins || mins <= 0) return "";
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  return h ? `${h}h${m ? ` ${m}m` : ""}` : `${m}m`;
};

const legMinutes = (leg) => {
  const d = (new Date(leg.arrival_time) - new Date(leg.departure_time)) / 60000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : 0;
};

const layoverMinutes = (a, b) => {
  const d = (new Date(b.departure_time) - new Date(a.arrival_time)) / 60000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : 0;
};

// A connection is "tight" when the buffer is too short to comfortably catch the
// next leg. Flights need more margin (deplaning, baggage, security) than ground
// transit, mirroring the backend stress thresholds (<1.5h flight / <30m ground).
const isTightConnection = (mins, nextLeg) => {
  if (!mins || mins <= 0) return false;
  const threshold = nextLeg?.mode === "flight" ? 90 : 30;
  return mins < threshold;
};

// Overnight when the leg crosses a local calendar day (e.g. a night ferry/train).
const isOvernightLeg = (leg) => {
  const dep = new Date(leg.departure_time);
  const arr = new Date(leg.arrival_time);
  if (Number.isNaN(dep.getTime()) || Number.isNaN(arr.getTime())) return false;
  return dep.toDateString() !== arr.toDateString();
};

// A gap longer than this between two legs is the trip stay itself (e.g. the
// nights spent at the destination between the outbound and return flights), not
// a connecting-flight layover. Used to avoid mislabeling a 14-day stay as a
// "338h layover" and to split legs into outbound/return journeys.
const TRIP_GAP_MINUTES = 24 * 60;

// Split legs into journeys (outbound, return, ...) at trip-length gaps.
const splitJourneys = (legs) => {
  const journeys = [];
  let current = [];
  legs.forEach((leg, i) => {
    current.push(leg);
    const next = legs[i + 1];
    if (next && layoverMinutes(leg, next) > TRIP_GAP_MINUTES) {
      journeys.push(current);
      current = [];
    }
  });
  if (current.length) journeys.push(current);
  return journeys;
};

// Door-to-door minutes for one journey (first departure → last arrival,
// including any in-journey connection layovers).
const journeyMinutes = (journey) => {
  if (!journey || journey.length === 0) return 0;
  const d =
    (new Date(journey[journey.length - 1].arrival_time) - new Date(journey[0].departure_time)) /
    60000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : 0;
};

// Drop placeholder carriers (e.g. "TBD", "Flight (Direct)") so we only show a
// real airline name.
const cleanCarrier = (carrier) => {
  const t = String(carrier || "").trim();
  if (!t || /^tbd$/i.test(t) || /^flight\b/i.test(t)) return "";
  return t;
};

const nightsBetween = (checkIn, checkOut) => {
  const d = (new Date(checkOut) - new Date(checkIn)) / 86400000;
  return Number.isFinite(d) && d >= 1 ? Math.round(d) : null;
};

const tripNights = (start, end) => {
  const d = (new Date(`${end}T00:00:00`) - new Date(`${start}T00:00:00`)) / 86400000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : null;
};

function StressGauge({ score }) {
  const tone = stressTone(score);
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={`h-1.5 flex-1 rounded-full ${n <= score ? tone.pip : "bg-pink-100"}`}
        />
      ))}
    </div>
  );
}

// Icon for a transit leg. Flights use a slightly upward-tilted plane (ascending)
// that reads as travel/departure; other modes keep their glyph.
function LegIcon({ mode, className = "" }) {
  if (mode === "flight") {
    return <Plane className={`w-4 h-4 text-primary ${className}`} />;
  }
  return (
    <span className={`text-base leading-none ${className}`}>
      {MODE_GLYPH[mode] || MODE_GLYPH.other}
    </span>
  );
}

function StatTile({ icon: Icon, label, value }) {
  return (
    <div className="flex-1 min-w-[120px] px-3 py-2.5 rounded-xl bg-pink-50/60 border border-pink-100">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-foreground/60">
        <Icon className="w-3.5 h-3.5 text-secondary" /> {label}
      </div>
      <div className="mt-1 text-lg font-extrabold text-foreground">{value}</div>
    </div>
  );
}

function CostBar({ icon: Icon, label, amount, total, currency, barClass }) {
  const pct = total > 0 ? Math.max(4, Math.round(((amount || 0) / total) * 100)) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-sm mb-1">
        <span className="flex items-center gap-1.5 font-medium text-foreground">
          <Icon className="w-4 h-4 text-secondary" /> {label}
        </span>
        <span className="font-bold text-foreground">{formatPrice(amount, currency)}</span>
      </div>
      <div className="h-2 rounded-full bg-pink-100 overflow-hidden">
        <div className={`h-full rounded-full ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function DayRow({ day, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);
  const schedule = day.schedule || [];
  const headline = day.title || day.description;
  return (
    <div className="rounded-xl border border-pink-100 bg-surface overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-pink-50/60"
      >
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-primary text-white text-xs font-bold shrink-0">
          {String(day.day_number).padStart(2, "0")}
        </span>
        <span className="flex-1 text-sm font-semibold text-foreground line-clamp-1">
          {headline}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-foreground/50 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="px-3 pb-3">
          {day.title && day.description && (
            <p className="text-xs text-foreground/70 mb-3">{day.description}</p>
          )}
          {schedule.length > 0 ? (
            <ol className="flex flex-col gap-3">
              {schedule.map((item, i) => (
                <li key={i} className="flex gap-3">
                  <span className="shrink-0 mt-0.5 w-16 break-words text-[11px] font-bold uppercase tracking-wide text-secondary">
                    {item.period}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-foreground">{item.activity}</div>
                    {item.location && (
                      <div className="flex items-center gap-1 text-xs text-foreground/70 mt-0.5">
                        <MapPin className="w-3 h-3 text-secondary" /> {item.location}
                      </div>
                    )}
                    {item.details && (
                      <p className="text-xs text-foreground/70 mt-0.5 leading-relaxed">{item.details}</p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            !day.title && day.description && (
              <p className="text-xs text-foreground/70">{day.description}</p>
            )
          )}
        </div>
      )}
    </div>
  );
}

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
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-foreground/40 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-[640px] max-h-[88vh] flex flex-col rounded-3xl bg-surface pink-shadow-deep overflow-hidden">
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
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">Itinerary highlights</h3>
              <div className="flex flex-col gap-2">
                {days.map((d, i) => (
                  <DayRow key={i} day={d} defaultOpen={i === 0} />
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

function ScenarioCard({ scenario, currency, destination, bestValue, lowestStress }) {
  const [detailOpen, setDetailOpen] = useState(false);
  const { setActiveRoute } = useMapState();
  const cb = scenario.cost_breakdown || {};
  const tone = stressTone(scenario.stress_score);
  const legs = (scenario.itinerary?.legs || []).slice(0, 4);
  const highlights = (scenario.highlights || []).slice(0, 4);

  return (
    <div
      className={`flex-1 min-w-[240px] flex flex-col p-4 rounded-2xl bg-surface bouncy-hover ${
        bestValue ? "border-2 border-primary pink-shadow-deep" : "border border-pink-100 pink-shadow"
      }`}
    >
      {/* Derived badges */}
      <div className="flex items-center justify-between gap-2 mb-2 min-h-[22px]">
        {lowestStress ? (
          <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full text-[10px] font-bold uppercase tracking-wider">
            Lowest stress
          </span>
        ) : (
          <span />
        )}
        {bestValue && (
          <span className="px-2.5 py-0.5 bg-primary text-white rounded-full text-[10px] font-bold uppercase tracking-wider">
            Best value
          </span>
        )}
      </div>

      {/* Title + dates */}
      <h3 className="text-base font-extrabold text-foreground leading-tight">
        {scenario.comparison_label || scenario.label}
      </h3>
      <p className="text-xs font-medium text-foreground/70 mt-0.5">
        {fmtDay(scenario.start_date)} — {fmtDay(scenario.end_date)}
        {fmtYear(scenario.end_date) ? `, ${fmtYear(scenario.end_date)}` : ""}
      </p>

      {/* Hero price + cost breakdown */}
      <div className="mt-3 pt-3 border-t border-pink-100">
        <div className="flex items-baseline justify-between">
          <span className="text-2xl font-extrabold text-primary">
            {formatPrice(cb.grand_total, currency)}
          </span>
          <span className="text-[11px] font-medium text-foreground/60">total</span>
        </div>
        <div className="mt-2 flex flex-col gap-1.5 text-sm">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-medium text-foreground">
              <Plane className="w-4 h-4 text-secondary" /> Transport
            </span>
            <span className="font-semibold text-foreground">
              {formatPrice(cb.transportation, currency)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-medium text-foreground">
              <BedDouble className="w-4 h-4 text-secondary" /> Stay
            </span>
            <span className="font-semibold text-foreground">
              {formatPrice(cb.accommodation, currency)}
            </span>
          </div>
        </div>
      </div>

      {/* Stress score */}
      <div className="mt-3 pt-3 border-t border-pink-100">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-foreground/70">
            Stress score
          </span>
          <span className={`text-xs font-bold ${tone.text}`}>
            {scenario.stress_score}/5 ({STRESS_LABEL[scenario.stress_score] || ""})
          </span>
        </div>
        <StressGauge score={scenario.stress_score} />
      </div>

      {/* Highlight chips */}
      {highlights.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {highlights.map((h, i) => (
            <span
              key={i}
              className="px-2 py-0.5 bg-pink-50 text-pink-700 border border-pink-100 rounded-full text-[11px] font-medium"
            >
              {h}
            </span>
          ))}
        </div>
      )}

      {/* Transport leg summary */}
      {legs.length > 0 && (
        <div className="mt-3 px-3 py-2 rounded-xl bg-pink-50/60 border border-pink-100">
          <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-foreground">
            {legs.map((leg, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-foreground/40">→</span>}
                <LegIcon mode={leg.mode} />
                <span className="font-semibold">{leg.origin}</span>
                {fmtTime(leg.departure_time) && (
                  <span className="text-foreground/70">{fmtTime(leg.departure_time)}</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Footer actions */}
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => setDetailOpen(true)}
          className="flex-1 py-2 rounded-xl border border-pink-200 text-primary text-sm font-semibold bouncy-hover hover:bg-pink-50"
        >
          View details
        </button>
        <button
          type="button"
          onClick={() => setActiveRoute(routeFromScenario(scenario, { destination, currency }))}
          title="Show this route on the map"
          aria-label="Show this route on the map"
          className="hidden lg:inline-flex shrink-0 px-3 py-2 rounded-xl border border-pink-200 text-primary items-center justify-center bouncy-hover hover:bg-pink-50"
        >
          <MapPin className="w-4 h-4" />
        </button>
      </div>

      {detailOpen && (
        <ScenarioDetailModal
          scenario={scenario}
          currency={currency}
          destination={destination}
          onClose={() => setDetailOpen(false)}
        />
      )}
    </div>
  );
}

function ComparisonShell({ destination, estimated, spin = false, children }) {
  return (
    <div
      className={`p-4 my-2.5 rounded-2xl bg-surface border border-pink-100 pink-shadow ${
        spin ? "animate-pulse" : ""
      }`}
    >
      <div className="flex items-center gap-2 mb-3">
        <Compass className={`w-4 h-4 text-primary ${spin ? "animate-spin" : ""}`} />
        <span className="text-xs font-bold uppercase tracking-wider text-primary">
          {spin ? "Building scenarios" : "Scenario Comparison"}
          {destination ? ` · ${destination}` : ""}
          {spin ? "…" : ""}
        </span>
        {estimated && !spin && (
          <span
            title="Live fares were unavailable, so these costs are approximate estimates."
            className="px-2.5 py-0.5 bg-amber-400 text-amber-950 border border-amber-500 rounded-full text-[11px] font-bold inline-flex items-center gap-1"
          >
            <Info className="w-3 h-3" /> approx costs
          </span>
        )}
      </div>
      <div className="flex flex-col md:flex-row gap-3 items-stretch">{children}</div>
    </div>
  );
}

// Generative UI for generate_scenarios — side-by-side scenario comparison cards.
export function ScenarioComparisonCard({ status, parameters, result }) {
  const destination = parameters?.destination || "";
  const { setActiveRoute } = useMapState();

  const data = status === "complete" ? parseResult(result) : null;
  const scenarios = data?.scenarios || [];
  const currency = data?.currency || "EUR";
  const mapDestination = data?.destination || destination;

  // Derive the highlighted options client-side: cheapest = best value,
  // least stressful = lowest stress.
  let bestValueIdx = 0;
  let lowestStressIdx = 0;
  scenarios.forEach((s, i) => {
    const total = s.cost_breakdown?.grand_total ?? Infinity;
    const best = scenarios[bestValueIdx]?.cost_breakdown?.grand_total ?? Infinity;
    if (total < best) bestValueIdx = i;
    if ((s.stress_score ?? 99) < (scenarios[lowestStressIdx]?.stress_score ?? 99)) lowestStressIdx = i;
  });

  // Auto-show the best-value scenario on the map once the comparison resolves.
  // Keyed by a stable signature so it only fires when the chosen route changes,
  // not on every re-render (parseResult returns a fresh object each time).
  const bestScenario = scenarios[bestValueIdx];
  const bestSig = bestScenario
    ? `${mapDestination}|${currency}|${bestScenario.label}|${bestScenario.start_date}|${bestScenario.cost_breakdown?.grand_total}`
    : null;
  useEffect(() => {
    if (bestScenario) {
      setActiveRoute(routeFromScenario(bestScenario, { destination: mapDestination, currency }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bestSig]);

  if (status !== "complete") {
    return (
      <ComparisonShell destination={destination} spin>
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex-1 min-w-[240px] h-56 rounded-2xl shimmer" />
        ))}
      </ComparisonShell>
    );
  }

  if (scenarios.length === 0) return null;

  return (
    <ComparisonShell destination={data?.destination || destination} estimated={data?.estimated}>
      {scenarios.map((s, i) => (
        <ScenarioCard
          key={i}
          scenario={s}
          currency={currency}
          destination={data?.destination || destination}
          bestValue={i === bestValueIdx}
          lowestStress={i === lowestStressIdx && scenarios.length > 1}
        />
      ))}
    </ComparisonShell>
  );
}
