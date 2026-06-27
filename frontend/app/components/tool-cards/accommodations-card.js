import { BedDouble, Star, ExternalLink, Sparkles } from "lucide-react";
import { z } from "zod";
import { ToolCard } from "../tool-card";
import { PriceBar } from "../price-bar";
import { SkeletonGrid } from "../skeletons";
import { useMapState } from "../map/map-context";
import { formatPrice, parseResult, resultError, isPreparing } from "../../lib/format";

export const accommodationsParameters = z.object({
  destination: z.string().optional(),
  check_in_date: z.string().optional(),
  check_out_date: z.string().optional(),
  guests: z.number().optional(),
  max_price: z.number().nullable().optional(),
  min_rating: z.number().nullable().optional(),
});

// A small, curated subset of amenities is far more useful than the full dump —
// lead with the ones travelers actually filter on. Anything else falls through
// to its raw label.
const AMENITY_LABEL = (a) => {
  const s = a.toLowerCase();
  if (s.includes("pool")) return "Pool";
  if (s.includes("wi-fi") || s.includes("wifi")) return "Wi-Fi";
  if (s.includes("spa")) return "Spa";
  if (s.includes("breakfast")) return "Breakfast";
  if (s.includes("hot tub")) return "Hot tub";
  if (s.includes("gym") || s.includes("fitness")) return "Gym";
  if (s.includes("parking")) return "Parking";
  if (s.includes("bar")) return "Bar";
  if (s.includes("restaurant")) return "Restaurant";
  if (s.includes("air condition")) return "A/C";
  return a;
};

// De-duplicate amenities after normalizing (e.g. "Free Wi-Fi" + "Wi-Fi" → one).
const topAmenities = (amenities, n = 3) => {
  const seen = new Set();
  const out = [];
  for (const a of amenities || []) {
    const label = AMENITY_LABEL(a);
    if (seen.has(label)) continue;
    seen.add(label);
    out.push(label);
    if (out.length >= n) break;
  }
  return out;
};

function HotelTile({ o, currency, topPick, minRate, maxRate }) {
  const { setHoveredStay } = useMapState();
  const cur = o.currency || currency;
  const amenities = topAmenities(o.amenities);
  const hasCoords = typeof o.latitude === "number" && typeof o.longitude === "number";

  const onEnter = () => {
    if (hasCoords) setHoveredStay({ name: o.name, lat: o.latitude, lng: o.longitude });
  };
  const onLeave = () => setHoveredStay(null);

  const body = (
    <div className="flex h-full flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1 text-sm font-semibold text-foreground">
            <span className="truncate">{o.name}</span>
            {o.link && (
              <ExternalLink className="w-3 h-3 text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
            )}
          </div>
          {o.property_type && (
            <div className="text-[11px] capitalize text-foreground/55 mt-0.5">{o.property_type}</div>
          )}
        </div>
        {o.rating != null && (
          <div className="shrink-0 inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5">
            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
            <span className="text-xs font-bold text-amber-700">{Number(o.rating).toFixed(1)}</span>
            {o.reviews != null && (
              <span className="text-[10px] text-amber-700/70">({o.reviews})</span>
            )}
          </div>
        )}
      </div>

      {amenities.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {amenities.map((a) => (
            <span
              key={a}
              className="px-2 py-0.5 rounded-full bg-pink-100/70 text-[10px] font-semibold text-pink-700"
            >
              {a}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto pt-1">
        <div className="flex items-baseline gap-1.5">
          <span className="text-base font-extrabold text-primary">{formatPrice(o.rate_per_night, cur)}</span>
          <span className="text-[10px] font-medium text-foreground/55">/night</span>
          {o.total_rate != null && (
            <span className="ml-auto text-[11px] text-foreground/55">{formatPrice(o.total_rate, cur)} total</span>
          )}
        </div>
        <PriceBar value={o.rate_per_night} min={minRate} max={maxRate} className="mt-1.5" />
      </div>
    </div>
  );

  const className = `group relative block h-full rounded-2xl p-3 transition-colors ${
    topPick
      ? "bg-pink-50 border-2 border-primary pink-shadow"
      : "bg-pink-50/50 border border-pink-100"
  }`;
  const hover = o.link ? "hover:border-primary/40 hover:bg-pink-50" : "";

  const badge = topPick && (
    <span className="absolute -top-2 left-3 z-10 inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-white pink-shadow">
      <Sparkles className="w-3 h-3" /> Top pick
    </span>
  );

  return o.link ? (
    <a
      href={o.link}
      target="_blank"
      rel="noopener noreferrer"
      title="View this property"
      className={`${className} ${hover}`}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      {badge}
      {body}
    </a>
  ) : (
    <div className={className} onMouseEnter={onEnter} onMouseLeave={onLeave}>
      {badge}
      {body}
    </div>
  );
}

// Generative UI for search_accommodations — a two-column grid of lodging options
// (cheapest first) with guest rating, key amenities, an at-a-glance price bar,
// a "Top pick" badge, and hover-to-locate on the trip map.
export function AccommodationsCard({ status, parameters, result }) {
  const place = parameters?.destination || "?";
  const dates =
    parameters?.check_in_date && parameters?.check_out_date
      ? ` · ${parameters.check_in_date} → ${parameters.check_out_date}`
      : "";

  if (status !== "complete") {
    return (
      <ToolCard
        icon={BedDouble}
        loading
        label={isPreparing(status) ? "Preparing stay search…" : `Searching stays · ${place}${dates}`}
        skeleton={<SkeletonGrid count={4} />}
      />
    );
  }

  const data = parseResult(result);
  const error = resultError(data);
  if (error) {
    return <ToolCard icon={BedDouble} label={`Stays · ${place}`} error={error} />;
  }
  const currency = data?.currency || "EUR";
  const options = (data?.options || [])
    .slice(0, 6)
    .sort((a, b) => (a.rate_per_night ?? Infinity) - (b.rate_per_night ?? Infinity));
  if (options.length === 0) return null;

  const rates = options.map((o) => o.rate_per_night).filter((r) => typeof r === "number");
  const minRate = rates.length ? Math.min(...rates) : 0;
  const maxRate = rates.length ? Math.max(...rates) : 0;

  // Top pick = highest guest rating, ties broken by the lower nightly rate.
  let topPickIdx = -1;
  let bestRating = -Infinity;
  let bestRate = Infinity;
  options.forEach((o, i) => {
    const r = typeof o.rating === "number" ? o.rating : -Infinity;
    const price = o.rate_per_night ?? Infinity;
    if (r > bestRating || (r === bestRating && price < bestRate)) {
      bestRating = r;
      bestRate = price;
      topPickIdx = i;
    }
  });

  return (
    <ToolCard icon={BedDouble} label={`Stays · ${place}`} approx={data?.estimated}>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {options.map((o, i) => (
          <HotelTile
            key={i}
            o={o}
            currency={currency}
            topPick={i === topPickIdx}
            minRate={minRate}
            maxRate={maxRate}
          />
        ))}
      </div>
    </ToolCard>
  );
}
