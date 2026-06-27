"use client";

import { useState } from "react";
import { Plane, MapPin, ChevronDown } from "lucide-react";
import { formatPrice } from "../../lib/format";
import { stressTone } from "../../lib/itinerary";
import { MODE_GLYPH } from "../../lib/transport";

// Shared presentational building blocks for the scenario comparison cards and
// the scenario detail modal. Each is a small, stateless (bar DayRow's local
// open/closed toggle) display component driven entirely by props.

export function StressGauge({ score }) {
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
export function LegIcon({ mode, className = "" }) {
  if (mode === "flight") {
    return <Plane className={`w-4 h-4 text-primary ${className}`} />;
  }
  return (
    <span className={`text-base leading-none ${className}`}>
      {MODE_GLYPH[mode] || MODE_GLYPH.other}
    </span>
  );
}

export function StatTile({ icon: Icon, label, value }) {
  return (
    <div className="flex-1 min-w-[120px] px-3 py-2.5 rounded-xl bg-pink-50/60 border border-pink-100">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-foreground/60">
        <Icon className="w-3.5 h-3.5 text-secondary" /> {label}
      </div>
      <div className="mt-1 text-lg font-extrabold text-foreground">{value}</div>
    </div>
  );
}

export function CostBar({ icon: Icon, label, amount, total, currency, barClass }) {
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

export function DayRow({ day, defaultOpen }) {
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
