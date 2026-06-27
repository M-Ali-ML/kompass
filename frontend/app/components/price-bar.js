// A tiny at-a-glance comparison bar: width scales with how this option's price
// sits within the [min, max] range across the result set (cheapest → short,
// priciest → full). Purely relative — it's a visual aid, not an axis.
export function PriceBar({ value, min, max, className = "" }) {
  const range = (max ?? 0) - (min ?? 0);
  const pct = range > 0 ? ((value - min) / range) * 100 : 0;
  const width = Math.max(8, Math.min(100, Math.round(pct)));
  return (
    <div
      className={`h-1.5 w-full overflow-hidden rounded-full bg-pink-100/70 ${className}`}
      title={`Relative price across these results`}
    >
      <div
        className="h-full rounded-full bg-gradient-to-r from-accent to-primary"
        style={{ width: `${width}%` }}
      />
    </div>
  );
}
