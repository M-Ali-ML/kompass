import { AlertTriangle } from "lucide-react";
import { SearchProgress } from "./search-progress";

// All tool cards share a single width so the chat-side column reads as one tidy,
// aligned stack regardless of which tool produced the card.
const CARD_WIDTH = "max-w-2xl";

// Shared shell for generative-UI tool cards: the rounded surface, the
// icon + uppercase label header, an optional "approx" badge, and a body slot.
//
// States:
//   - error   → a rose-tinted card explaining a failed/unavailable data source
//   - loading → pulsing header + either a `skeleton` body or an animated
//               SearchProgress bar (when bodyless)
//   - default → the resting card with its result body
export function ToolCard({
  icon: Icon,
  label,
  loading = false,
  spin = false,
  approx = false,
  error = null,
  skeleton = null,
  children,
}) {
  if (error) {
    return (
      <div className={`p-4 my-2.5 rounded-2xl bg-rose-50 border border-rose-200 ${CARD_WIDTH}`}>
        <div className="flex items-center gap-2 mb-1.5">
          <AlertTriangle className="w-4 h-4 text-rose-500" />
          <span className="text-xs font-bold uppercase tracking-wider text-rose-600">
            {label}
          </span>
        </div>
        <p className="text-xs text-rose-700/90 leading-relaxed">{error}</p>
      </div>
    );
  }

  const showSkeleton = loading && skeleton;
  return (
    <div
      className={`p-4 my-2.5 rounded-2xl bg-surface border border-pink-100 pink-shadow ${CARD_WIDTH} ${
        loading ? "animate-pulse" : "bouncy-hover"
      }`}
    >
      <div className={`flex items-center gap-2 ${children || showSkeleton ? "mb-3" : ""}`}>
        <Icon className={`w-4 h-4 text-primary ${spin ? "animate-spin" : ""}`} />
        <span className="text-xs font-bold uppercase tracking-wider text-primary">
          {label}
        </span>
        {approx && (
          <span
            title="Live prices were unavailable, so these are approximate estimates."
            className="px-2 py-0.5 bg-amber-400 text-amber-950 border border-amber-500 rounded-full text-[10px] font-bold"
          >
            ≈ approx
          </span>
        )}
      </div>
      {/* Loading: prefer skeleton tiles (so the grid doesn't jump when results
          arrive); otherwise show the animated search bar. */}
      {showSkeleton && skeleton}
      {loading && !skeleton && !children && <SearchProgress />}
      {children}
    </div>
  );
}
