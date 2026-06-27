// Pure, presentation-free helpers for rendering travel scenarios: date/time and
// duration formatting, per-leg pricing, stress tone, and the journey/leg math
// shared by the scenario comparison cards and the detail modal. Keeping these
// out of the components keeps the JSX focused on layout and makes the logic
// unit-testable in isolation.
import { formatPrice } from "./format";

export const STRESS_LABEL = { 1: "Relaxed", 2: "Easy", 3: "Moderate", 4: "Busy", 5: "Intense" };

// Transit fares are priced per person, so with a group we show the per-person
// unit price alongside the count (e.g. "2× €49"). Stays are a whole-property
// total, so they stay as a single figure.
export const PER_PERSON_MODES = new Set(["flight", "train", "bus", "ferry"]);

export const formatLegPrice = (leg, travelers, currency) => {
  const perPerson = travelers > 1 && PER_PERSON_MODES.has(leg.mode) && leg.cost > 0;
  return perPerson
    ? `${travelers}× ${formatPrice(leg.cost / travelers, currency)}`
    : formatPrice(leg.cost, currency);
};

// Lower stress is better, so the gauge runs calm-green → busy-rose.
export const stressTone = (score) =>
  score <= 2
    ? { text: "text-emerald-600", pip: "bg-emerald-400" }
    : score === 3
    ? { text: "text-amber-600", pip: "bg-amber-400" }
    : { text: "text-rose-500", pip: "bg-rose-400" };

export const fmtDay = (iso) => {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
};

export const fmtYear = (iso) => {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? "" : d.getFullYear();
};

export const fmtTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false });
};

export const fmtDuration = (mins) => {
  if (!mins || mins <= 0) return "";
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  return h ? `${h}h${m ? ` ${m}m` : ""}` : `${m}m`;
};

export const legMinutes = (leg) => {
  const d = (new Date(leg.arrival_time) - new Date(leg.departure_time)) / 60000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : 0;
};

export const layoverMinutes = (a, b) => {
  const d = (new Date(b.departure_time) - new Date(a.arrival_time)) / 60000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : 0;
};

// A connection is "tight" when the buffer is too short to comfortably catch the
// next leg. Flights need more margin (deplaning, baggage, security) than ground
// transit, mirroring the backend stress thresholds (<1.5h flight / <30m ground).
export const isTightConnection = (mins, nextLeg) => {
  if (!mins || mins <= 0) return false;
  const threshold = nextLeg?.mode === "flight" ? 90 : 30;
  return mins < threshold;
};

// Overnight when the leg crosses a local calendar day (e.g. a night ferry/train).
export const isOvernightLeg = (leg) => {
  const dep = new Date(leg.departure_time);
  const arr = new Date(leg.arrival_time);
  if (Number.isNaN(dep.getTime()) || Number.isNaN(arr.getTime())) return false;
  return dep.toDateString() !== arr.toDateString();
};

// A gap longer than this between two legs is the trip stay itself (e.g. the
// nights spent at the destination between the outbound and return flights), not
// a connecting-flight layover. Used to avoid mislabeling a 14-day stay as a
// "338h layover" and to split legs into outbound/return journeys.
export const TRIP_GAP_MINUTES = 24 * 60;

// Split legs into journeys (outbound, return, ...) at trip-length gaps.
export const splitJourneys = (legs) => {
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
export const journeyMinutes = (journey) => {
  if (!journey || journey.length === 0) return 0;
  const d =
    (new Date(journey[journey.length - 1].arrival_time) - new Date(journey[0].departure_time)) /
    60000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : 0;
};

// Drop placeholder carriers (e.g. "TBD", "Flight (Direct)") so we only show a
// real airline name.
export const cleanCarrier = (carrier) => {
  const t = String(carrier || "").trim();
  if (!t || /^tbd$/i.test(t) || /^flight\b/i.test(t)) return "";
  return t;
};

export const nightsBetween = (checkIn, checkOut) => {
  const d = (new Date(checkOut) - new Date(checkIn)) / 86400000;
  return Number.isFinite(d) && d >= 1 ? Math.round(d) : null;
};

export const tripNights = (start, end) => {
  const d = (new Date(`${end}T00:00:00`) - new Date(`${start}T00:00:00`)) / 86400000;
  return Number.isFinite(d) && d > 0 ? Math.round(d) : null;
};
