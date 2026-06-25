// Shared shell for generative-UI tool cards: the rounded surface, the
// icon + uppercase label header, an optional "approx" badge, and a body slot.
export function ToolCard({ icon: Icon, label, loading = false, spin = false, approx = false, children }) {
  return (
    <div
      className={`p-4 my-2.5 rounded-2xl bg-surface border border-pink-100 pink-shadow max-w-md ${
        loading ? "animate-pulse" : "bouncy-hover"
      }`}
    >
      <div className={`flex items-center gap-2 ${children ? "mb-3" : ""}`}>
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
      {children}
    </div>
  );
}
