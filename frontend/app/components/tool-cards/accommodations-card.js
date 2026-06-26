import { BedDouble, Star, ExternalLink } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { formatPrice, parseResult } from "../../lib/format";

export const accommodationsParameters = z.object({
  destination: z.string().optional(),
  check_in_date: z.string().optional(),
  check_out_date: z.string().optional(),
  guests: z.number().optional(),
  max_price: z.number().nullable().optional(),
  min_rating: z.number().nullable().optional(),
});

// Generative UI for search_accommodations — lists the returned lodging options.
export function AccommodationsCard({ status, parameters, result }) {
  const place = parameters?.destination || "?";
  const dates =
    parameters?.check_in_date && parameters?.check_out_date
      ? ` · ${parameters.check_in_date} → ${parameters.check_out_date}`
      : "";

  if (status !== "complete") {
    return <ToolCard icon={BedDouble} loading label={`Searching stays · ${place}${dates}`} />;
  }

  const data = parseResult(result);
  const options = (data?.options || []).slice(0, 6);
  if (options.length === 0) return null;
  const currency = data?.currency || "EUR";

  return (
    <ToolCard icon={BedDouble} label={`Stays · ${place}`} approx={data?.estimated}>
      <ul className="flex flex-col gap-1.5">
        {options.map((o, i) => {
          const cur = o.currency || currency;
          const body = (
            <>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1 text-sm font-semibold text-foreground">
                  <span className="truncate">{o.name}</span>
                  {o.link && (
                    <ExternalLink className="w-3 h-3 text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted mt-0.5">
                  {o.rating != null && (
                    <span className="inline-flex items-center gap-0.5">
                      <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                      {Number(o.rating).toFixed(1)}
                    </span>
                  )}
                  {o.property_type && <span className="capitalize truncate">{o.property_type}</span>}
                </div>
              </div>
              <div className="shrink-0 text-right leading-tight whitespace-nowrap">
                <div className="text-sm font-bold text-primary">
                  {formatPrice(o.rate_per_night, cur)}
                  <span className="text-[10px] font-medium text-muted">/night</span>
                </div>
                {o.total_rate != null && (
                  <div className="text-[10px] text-muted">
                    {formatPrice(o.total_rate, cur)} total
                  </div>
                )}
              </div>
            </>
          );
          const className =
            "group flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-pink-50/60 border border-pink-100";
          return (
            <li key={i}>
              {o.link ? (
                <a
                  href={o.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="View this property"
                  className={`${className} hover:border-primary/40 hover:bg-pink-50 transition-colors`}
                >
                  {body}
                </a>
              ) : (
                <div className={className}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    </ToolCard>
  );
}
