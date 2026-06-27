// A grid of shimmer placeholder tiles shown while a list/grid tool card is
// loading, so the layout doesn't jump when real results stream in. Mirrors the
// two-column result grids used by the flights / dates / stays cards.
export function SkeletonGrid({ count = 4, tileClassName = "h-20" }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`shimmer rounded-2xl ${tileClassName}`} />
      ))}
    </div>
  );
}
