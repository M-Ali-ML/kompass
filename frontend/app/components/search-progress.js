// Animated indeterminate progress bar shown inside a tool card while the agent
// is mid-search (e.g. "Searching flights BER → ATH…"). A candy-gradient pill
// slides across a soft pink track — purely decorative, communicating that work
// is in flight without claiming a real percentage.
export function SearchProgress({ className = "" }) {
  return (
    <div
      role="progressbar"
      aria-label="Searching…"
      className={`mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-pink-100/70 ${className}`}
    >
      <div className="progress-slide h-full w-1/3 rounded-full bg-gradient-to-r from-primary/40 via-primary to-secondary" />
    </div>
  );
}
