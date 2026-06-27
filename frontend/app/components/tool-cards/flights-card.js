import { Plane, ExternalLink, Sparkles } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { PriceBar } from "../price-bar";
import { SkeletonGrid } from "../skeletons";
import {
  formatPrice,
  formatClock,
  parseResult,
  googleFlightsUrl,
  resultError,
  isPreparing,
} from "../../lib/format";

export const flightsParameters = z.object({
  origin: z.string().optional(),
  destination: z.string().optional(),
  departure_date: z.string().optional(),
  passengers: z.number().optional(),
  max_stops: z.number().nullable().optional(),
  preferred_time: z.string().nullable().optional(),
});

function FlightTile({ o, parameters, currency, minPrice, maxPrice, cheapest }) {
  const href =
    o.booking_link ||
    googleFlightsUrl(
      o.origin || parameters?.origin,
      o.destination || parameters?.destination,
      o.departure_time || parameters?.departure_date
    );
  return (
    <a
      href={href || undefined}
      target="_blank"
      rel="noopener noreferrer"
      title="View this route on Google Flights"
      className={`group relative block h-full rounded-2xl p-3 transition-colors ${
        cheapest
          ? "bg-pink-50 border-2 border-primary pink-shadow"
          : "bg-pink-50/50 border border-pink-100 hover:border-primary/40 hover:bg-pink-50"
      }`}
    >
      {cheapest && (
        <span className="absolute -top-2 left-3 z-10 inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-white pink-shadow">
          <Sparkles className="w-3 h-3" /> Best price
        </span>
      )}
      <div className="flex h-full flex-col gap-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1 text-sm font-semibold text-foreground">
              <span className="truncate">{o.airline}</span>
              <ExternalLink className="w-3 h-3 text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
            </div>
            <div className="text-[11px] text-foreground/55 mt-0.5">
              {formatClock(o.departure_time)} ·{" "}
              {o.stops === 0 ? "Direct" : `${o.stops} stop${o.stops > 1 ? "s" : ""}`}
            </div>
          </div>
        </div>
        <div className="mt-auto pt-1">
          <div className="flex items-baseline gap-1.5">
            <span className="text-base font-extrabold text-primary">
              {formatPrice(o.price, o.currency || currency)}
            </span>
          </div>
          <PriceBar value={o.price} min={minPrice} max={maxPrice} className="mt-1.5" />
        </div>
      </div>
    </a>
  );
}

// Generative UI for search_flights — a two-column grid of flight options
// (cheapest first) with an at-a-glance price bar and a "Best price" badge.
export function FlightsCard({ status, parameters, result }) {
  const route = `${parameters?.origin || "?"} → ${parameters?.destination || "?"}`;

  if (status !== "complete") {
    const date = parameters?.departure_date ? ` · ${parameters.departure_date}` : "";
    return (
      <ToolCard
        icon={Plane}
        loading
        label={isPreparing(status) ? "Preparing flight search…" : `Searching flights ${route}${date}`}
        skeleton={<SkeletonGrid count={4} tileClassName="h-24" />}
      />
    );
  }

  const data = parseResult(result);
  const error = resultError(data);
  if (error) {
    return <ToolCard icon={Plane} label={`Flights · ${route}`} error={error} />;
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
    <ToolCard icon={Plane} label={`Flights · ${route}`} approx={data?.estimated}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {options.map((o, i) => (
          <FlightTile
            key={i}
            o={o}
            parameters={parameters}
            currency={currency}
            minPrice={minPrice}
            maxPrice={maxPrice}
            cheapest={i === 0 && typeof o.price === "number"}
          />
        ))}
      </div>
    </ToolCard>
  );
}
