import { CalendarSearch, Sparkles } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { PriceBar } from "../price-bar";
import { SkeletonGrid } from "../skeletons";
import { formatPrice, parseResult, resultError, isPreparing } from "../../lib/format";

export const cheapestDatesParameters = z.object({
  origin: z.string().optional(),
  destination: z.string().optional(),
  month: z.string().optional(),
  duration_days: z.number().nullable().optional(),
});

// Generative UI for find_cheapest_dates — a two-column grid of travel windows
// (cheapest first) with an at-a-glance price bar and a "Best value" badge.
export function CheapestDatesCard({ status, parameters, result }) {
  const route = `${parameters?.origin || "?"} → ${parameters?.destination || "?"}`;

  if (status !== "complete") {
    const month = parameters?.month ? ` · ${parameters.month}` : "";
    return (
      <ToolCard
        icon={CalendarSearch}
        loading
        label={isPreparing(status) ? "Preparing date search…" : `Finding cheapest dates ${route}${month}`}
        skeleton={<SkeletonGrid count={4} tileClassName="h-16" />}
      />
    );
  }

  const data = parseResult(result);
  const error = resultError(data);
  if (error) {
    return <ToolCard icon={CalendarSearch} label={`Cheapest dates · ${route}`} error={error} />;
  }
  const currency = data?.currency || "EUR";
  const options = (data?.options || [])
    .slice(0, 6)
    .sort((a, b) => (a.price ?? Infinity) - (b.price ?? Infinity));
  if (options.length === 0) return null;

  const prices = options.map((o) => o.price).filter((p) => typeof p === "number");
  const minPrice = prices.length ? Math.min(...prices) : 0;
  const maxPrice = prices.length ? Math.max(...prices) : 0;

  return (
    <ToolCard icon={CalendarSearch} label={`Cheapest dates · ${route}`} approx={data?.estimated}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {options.map((o, i) => {
          const best = i === 0 && typeof o.price === "number";
          return (
            <div
              key={i}
              className={`relative rounded-2xl p-3 ${
                best ? "bg-pink-50 border-2 border-primary pink-shadow" : "bg-pink-50/50 border border-pink-100"
              }`}
            >
              {best && (
                <span className="absolute -top-2 left-3 z-10 inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-white pink-shadow">
                  <Sparkles className="w-3 h-3" /> Best value
                </span>
              )}
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-semibold text-foreground">
                  {o.departure_date}
                  {o.return_date ? ` – ${o.return_date}` : ""}
                </span>
                <span className="text-base font-extrabold text-primary">
                  {formatPrice(o.price, o.currency || currency)}
                </span>
              </div>
              <PriceBar value={o.price} min={minPrice} max={maxPrice} className="mt-2" />
            </div>
          );
        })}
      </div>
    </ToolCard>
  );
}
