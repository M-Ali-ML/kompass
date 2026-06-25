import { CalendarSearch } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { formatPrice, parseResult } from "../../lib/format";

export const cheapestDatesParameters = z.object({
  origin: z.string().optional(),
  destination: z.string().optional(),
  month: z.string().optional(),
  duration_days: z.number().nullable().optional(),
});

// Generative UI for find_cheapest_dates — lists the cheapest travel windows.
export function CheapestDatesCard({ status, parameters, result }) {
  const route = `${parameters?.origin || "?"} → ${parameters?.destination || "?"}`;

  if (status !== "complete") {
    return (
      <ToolCard
        icon={CalendarSearch}
        loading
        label={`Finding cheapest dates ${route}${parameters?.month ? ` · ${parameters.month}` : ""}`}
      />
    );
  }

  const data = parseResult(result);
  const options = (data?.options || []).slice(0, 6);
  if (options.length === 0) return null;
  const currency = data?.currency || "EUR";

  return (
    <ToolCard icon={CalendarSearch} label={`Cheapest dates · ${route}`} approx={data?.estimated}>
      <ul className="flex flex-col gap-1.5">
        {options.map((o, i) => (
          <li
            key={i}
            className="flex items-center justify-between px-3 py-2 rounded-xl bg-pink-50/60 border border-pink-100"
          >
            <span className="text-sm font-medium text-foreground">
              {o.departure_date}
              {o.return_date ? ` – ${o.return_date}` : ""}
            </span>
            <span className="text-sm font-bold text-primary">
              {formatPrice(o.price, o.currency || currency)}
            </span>
          </li>
        ))}
      </ul>
    </ToolCard>
  );
}
