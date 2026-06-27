"use client";

import { useState, useEffect } from "react";
import { Compass, Plane, BedDouble, Info, MapPin } from "lucide-react";
import { z } from "zod";
import { formatPrice, parseResult } from "../../lib/format";
import { useMapState, routeFromScenario } from "../map/map-context";
import { STRESS_LABEL, stressTone, fmtDay, fmtYear, fmtTime } from "../../lib/itinerary";
import { StressGauge, LegIcon } from "./scenario-parts";
import { ScenarioDetailModal } from "./scenario-detail-modal";

export const scenarioComparisonParameters = z.object({
  destination: z.string().optional(),
  estimated: z.boolean().optional(),
});

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
