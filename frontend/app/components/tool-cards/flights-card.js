import { Plane, ExternalLink } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { formatPrice, formatClock, parseResult, googleFlightsUrl } from "../../lib/format";

export const flightsParameters = z.object({
  origin: z.string().optional(),
  destination: z.string().optional(),
  departure_date: z.string().optional(),
  passengers: z.number().optional(),
  max_stops: z.number().nullable().optional(),
  preferred_time: z.string().nullable().optional(),
});

// Generative UI for search_flights — lists the returned flight options.
export function FlightsCard({ status, parameters, result }) {
  const route = `${parameters?.origin || "?"} → ${parameters?.destination || "?"}`;

  if (status !== "complete") {
    return (
      <ToolCard
        icon={Plane}
        loading
        label={`Searching flights ${route}${parameters?.departure_date ? ` · ${parameters.departure_date}` : ""}`}
      />
    );
  }

  const data = parseResult(result);
  const options = (data?.options || []).slice(0, 5);
  if (options.length === 0) return null;
  const currency = data?.currency || "EUR";

  return (
    <ToolCard icon={Plane} label={`Flights · ${route}`} approx={data?.estimated}>
      <ul className="flex flex-col gap-1.5">
        {options.map((o, i) => {
          const href =
            o.booking_link ||
            googleFlightsUrl(
              o.origin || parameters?.origin,
              o.destination || parameters?.destination,
              o.departure_time || parameters?.departure_date
            );
          return (
            <li key={i}>
              <a
                href={href || undefined}
                target="_blank"
                rel="noopener noreferrer"
                title="View this route on Google Flights"
                className="group flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-pink-50/60 border border-pink-100 hover:border-primary/40 hover:bg-pink-50 transition-colors"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-foreground truncate">
                    {o.airline}
                    <ExternalLink className="w-3 h-3 text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </div>
                  <div className="text-xs text-muted">
                    {formatClock(o.departure_time)} ·{" "}
                    {o.stops === 0 ? "Direct" : `${o.stops} stop${o.stops > 1 ? "s" : ""}`}
                  </div>
                </div>
                <span className="text-sm font-bold text-primary shrink-0">
                  {formatPrice(o.price, o.currency || currency)}
                </span>
              </a>
            </li>
          );
        })}
      </ul>
    </ToolCard>
  );
}
