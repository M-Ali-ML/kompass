"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";

// Route-level error boundary: catches any uncaught render/runtime error in the
// workspace tree (chat, tool cards, map) so a single bad card can't blank the
// whole app. `reset` re-renders the segment; a full reload is the fallback.
export default function Error({ error, reset }) {
  return (
    <div className="flex h-screen items-center justify-center bg-background p-6">
      <div className="max-w-md w-full rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-rose-800">Something went wrong</p>
            <p className="mt-1 text-xs text-rose-700/80 leading-relaxed">
              {error?.message || "An unexpected error occurred while rendering the app."}
            </p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => reset()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700 transition-colors"
              >
                <RotateCcw className="w-3 h-3" /> Try again
              </button>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="inline-flex items-center rounded-lg border border-rose-300 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100 transition-colors"
              >
                Reload page
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
