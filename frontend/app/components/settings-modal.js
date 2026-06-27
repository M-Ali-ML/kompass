"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, Check, Plane, Loader2, Tag } from "lucide-react";
import { getProfile, updateProfile } from "../lib/trips-api";
import { MODE_GLYPH } from "../lib/transport";

// Editable global travel profile. Mirrors the backend `UserPreferences` schema
// and is persisted to the singleton profile via PUT /api/profile. These values
// become the agent baseline applied to every trip (the agent's
// `gather_preferences` tool can also overwrite them — last write wins).

const TRANSIT_MODES = ["flight", "train", "bus", "ferry", "car"];

const HOTEL_CLASSES = [
  { value: "", label: "No preference" },
  { value: "3-star", label: "3-star" },
  { value: "4-star", label: "4-star" },
  { value: "5-star", label: "5-star" },
  { value: "boutique", label: "Boutique" },
  { value: "budget/hostel", label: "Budget / hostel" },
];

const CURRENCIES = ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "SEK", "NOK", "DKK"];

const EMPTY_PREFS = {
  direct_flights_only: false,
  preferred_transit_modes: [],
  hotel_class: null,
  vibe_tags: [],
  currency: "EUR",
};

export function SettingsModal({ onClose }) {
  const [prefs, setPrefs] = useState(EMPTY_PREFS);
  const [loadState, setLoadState] = useState("loading");
  const [saveState, setSaveState] = useState("idle");
  const [vibeDraft, setVibeDraft] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getProfile();
        if (!cancelled) {
          setPrefs({ ...EMPTY_PREFS, ...data });
          setLoadState("ready");
        }
      } catch (e) {
        console.error("Failed to load profile", e);
        if (!cancelled) setLoadState("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  const toggleMode = (mode) => {
    setSaveState("idle");
    setPrefs((p) => {
      const has = p.preferred_transit_modes.includes(mode);
      return {
        ...p,
        preferred_transit_modes: has
          ? p.preferred_transit_modes.filter((m) => m !== mode)
          : [...p.preferred_transit_modes, mode],
      };
    });
  };

  const addVibe = () => {
    const tag = vibeDraft.trim().toLowerCase();
    if (!tag) return;
    setSaveState("idle");
    setPrefs((p) =>
      p.vibe_tags.includes(tag) ? p : { ...p, vibe_tags: [...p.vibe_tags, tag] }
    );
    setVibeDraft("");
  };

  const removeVibe = (tag) => {
    setSaveState("idle");
    setPrefs((p) => ({ ...p, vibe_tags: p.vibe_tags.filter((t) => t !== tag) }));
  };

  const handleSave = async () => {
    if (saveState === "saving") return;
    setSaveState("saving");
    try {
      await updateProfile({
        direct_flights_only: !!prefs.direct_flights_only,
        preferred_transit_modes: prefs.preferred_transit_modes,
        hotel_class: prefs.hotel_class || null,
        vibe_tags: prefs.vibe_tags,
        currency: prefs.currency || "EUR",
      });
      setSaveState("saved");
    } catch (e) {
      console.error("Failed to save profile", e);
      setSaveState("error");
    }
  };

  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Travel preferences"
    >
      <div className="absolute inset-0 bg-foreground/40 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-[520px] max-h-[92vh] sm:max-h-[88vh] flex flex-col rounded-t-3xl sm:rounded-3xl bg-surface pink-shadow-deep overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3 border-b border-pink-100">
          <div>
            <h2 className="text-lg font-extrabold text-foreground leading-tight">Travel preferences</h2>
            <p className="text-xs text-foreground/60 mt-0.5">
              Applied as your baseline on every new trip.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full text-foreground/60 hover:bg-pink-50 hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-6">
          {loadState === "loading" ? (
            <div className="flex items-center gap-2 text-sm text-muted py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading preferences…
            </div>
          ) : loadState === "error" ? (
            <div className="text-sm text-rose-600 py-8 text-center">
              Couldn&apos;t load your preferences. Close and try again.
            </div>
          ) : (
            <>
              {/* Direct flights */}
              <section className="flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-1.5 text-sm font-bold text-foreground">
                    <Plane className="w-4 h-4 text-secondary" /> Direct flights only
                  </div>
                  <p className="text-xs text-foreground/60 mt-0.5">
                    Prefer nonstop routes when available.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={!!prefs.direct_flights_only}
                  aria-label="Direct flights only"
                  onClick={() => {
                    setSaveState("idle");
                    setPrefs((p) => ({ ...p, direct_flights_only: !p.direct_flights_only }));
                  }}
                  className={`relative shrink-0 w-12 h-7 rounded-full transition-colors ${
                    prefs.direct_flights_only ? "bg-primary" : "bg-pink-100"
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-white pink-shadow transition-transform ${
                      prefs.direct_flights_only ? "translate-x-5" : ""
                    }`}
                  />
                </button>
              </section>

              {/* Transit modes */}
              <section>
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">
                  Preferred transport
                </h3>
                <div className="flex flex-wrap gap-2">
                  {TRANSIT_MODES.map((mode) => {
                    const active = prefs.preferred_transit_modes.includes(mode);
                    return (
                      <button
                        key={mode}
                        type="button"
                        aria-pressed={active}
                        onClick={() => toggleMode(mode)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border bouncy-hover capitalize ${
                          active
                            ? "bg-primary text-white border-primary pink-shadow"
                            : "bg-surface text-foreground/70 border-pink-200 hover:bg-pink-50"
                        }`}
                      >
                        <span className="text-base leading-none">{MODE_GLYPH[mode]}</span>
                        {mode}
                      </button>
                    );
                  })}
                </div>
              </section>

              {/* Hotel class */}
              <section>
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">
                  Accommodation standard
                </h3>
                <select
                  aria-label="Accommodation standard"
                  value={prefs.hotel_class || ""}
                  onChange={(e) => {
                    setSaveState("idle");
                    setPrefs((p) => ({ ...p, hotel_class: e.target.value || null }));
                  }}
                  className="w-full px-3 py-2.5 rounded-xl border border-pink-200 bg-surface text-sm font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                >
                  {HOTEL_CLASSES.map((h) => (
                    <option key={h.value} value={h.value}>
                      {h.label}
                    </option>
                  ))}
                </select>
              </section>

              {/* Vibe tags */}
              <section>
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">
                  Vibe tags
                </h3>
                {prefs.vibe_tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {prefs.vibe_tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-pink-50 text-pink-700 border border-pink-100 rounded-full text-xs font-medium"
                      >
                        {tag}
                        <button
                          type="button"
                          onClick={() => removeVibe(tag)}
                          aria-label={`Remove ${tag}`}
                          className="text-pink-400 hover:text-pink-700"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Tag className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-secondary" />
                    <input
                      type="text"
                      value={vibeDraft}
                      onChange={(e) => setVibeDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addVibe();
                        }
                      }}
                      placeholder="e.g. foodie, relaxation, adventure"
                      className="w-full pl-8 pr-3 py-2.5 rounded-xl border border-pink-200 bg-surface text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={addVibe}
                    className="shrink-0 px-4 py-2.5 rounded-xl border border-pink-200 text-primary text-sm font-semibold bouncy-hover hover:bg-pink-50"
                  >
                    Add
                  </button>
                </div>
              </section>

              {/* Currency */}
              <section>
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-foreground/70 mb-2">
                  Currency
                </h3>
                <select
                  aria-label="Currency"
                  value={prefs.currency || "EUR"}
                  onChange={(e) => {
                    setSaveState("idle");
                    setPrefs((p) => ({ ...p, currency: e.target.value }));
                  }}
                  className="w-full px-3 py-2.5 rounded-xl border border-pink-200 bg-surface text-sm font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                >
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </section>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-pink-100 flex flex-col gap-1.5">
          <button
            type="button"
            onClick={handleSave}
            disabled={loadState !== "ready" || saveState === "saving" || saveState === "saved"}
            className={`w-full py-2.5 rounded-xl text-sm font-bold inline-flex items-center justify-center gap-2 bouncy-hover pink-shadow disabled:opacity-60 ${
              saveState === "saved"
                ? "bg-emerald-500 text-white"
                : saveState === "error"
                ? "bg-rose-500 text-white"
                : "bg-primary text-white"
            }`}
          >
            {saveState === "saving" ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Saving…
              </>
            ) : saveState === "saved" ? (
              <>
                <Check className="w-4 h-4" /> Saved
              </>
            ) : saveState === "error" ? (
              "Couldn't save — retry"
            ) : (
              "Save preferences"
            )}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="w-full py-1.5 text-xs font-semibold text-foreground/60 hover:text-foreground"
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
