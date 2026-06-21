"use client";

import React from "react";
import { Check, Compass, Sparkles, DollarSign, Clock, Calendar, BarChart3 } from "lucide-react";

export default function ComparisonDashboard({ itineraries, activeItineraryId, onSelectActive }) {
  if (!itineraries || itineraries.length === 0) {
    return (
      <div className="flex-1 flex flex-col justify-center items-center p-12 text-center h-[calc(100vh-73px)]">
        <div className="p-4 bg-pink-100/30 rounded-full mb-3">
          <BarChart3 className="w-12 h-12 text-secondary animate-pulse" />
        </div>
        <h3 className="text-base font-extrabold text-secondary">No Itineraries to Compare Yet</h3>
        <p className="text-xs text-muted max-w-sm mt-1 leading-relaxed">
          Start chatting with the Kompass agent to generate different trip scenarios and compare them here.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 bg-pink-50/10 h-[calc(100vh-73px)] overflow-y-auto">
      {/* Title */}
      <div className="mb-8">
        <h2 className="text-lg font-extrabold text-foreground flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-primary" />
          <span>Itinerary Comparison Matrix</span>
        </h2>
        <p className="text-xs text-muted font-bold mt-1">Review and compare the AI-architected travel scenarios side-by-side.</p>
      </div>

      {/* Grid Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {itineraries.map((plan, i) => {
          const isActive = activeItineraryId === plan.id;
          const letter = String.fromCharCode(65 + i); // Plan A, B, C...
          
          return (
            <div 
              key={plan.id || i}
              className={`flex flex-col border-2 rounded-3xl p-6 bg-white bouncy-hover relative transition-all ${
                isActive 
                  ? "border-primary pink-shadow-deep scale-[1.01]" 
                  : "border-pink-100 hover:border-pink-200 shadow-sm"
              }`}
            >
              {/* Plan Label */}
              <div className="absolute top-4 left-4 px-3 py-1 bg-secondary text-white text-[10px] font-extrabold rounded-full uppercase tracking-wider shadow-sm">
                Scenario {letter}
              </div>

              {/* Cover Image Placeholder */}
              <div className="w-full h-32 rounded-2xl overflow-hidden bg-pink-100/50 flex items-center justify-center mb-5 border border-pink-100/30 relative">
                <Compass className="w-10 h-10 text-primary opacity-20" />
                <div className="absolute inset-0 bg-gradient-to-t from-pink-200/20 to-transparent" />
              </div>

              {/* Title & Stats */}
              <div className="mb-4">
                <h3 className="text-sm font-extrabold text-foreground leading-snug">{plan.title}</h3>
                <p className="text-[10px] font-bold text-muted mt-0.5">{plan.destination} • {plan.duration_days} Days</p>
              </div>

              {/* Comparison Stats List */}
              <div className="flex flex-col gap-2.5 border-y border-pink-50 py-4 mb-5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted font-bold flex items-center gap-1.5">
                    <DollarSign className="w-4 h-4 text-primary" />
                    Estimated Cost
                  </span>
                  <span className="font-extrabold text-primary">${plan.estimated_cost_usd}</span>
                </div>

                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted font-bold flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-accent" />
                    Stress Score
                  </span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-16 bg-pink-50 rounded-full h-1.5 overflow-hidden">
                      <div 
                        className="bg-accent h-full rounded-full" 
                        style={{ width: `${(plan.stress_score || 3) * 20}%` }}
                      />
                    </div>
                    <span className="font-extrabold text-secondary">{plan.stress_score || 3}/5</span>
                  </div>
                </div>

                <div className="flex justify-between items-center text-xs">
                  <span className="text-muted font-bold flex items-center gap-1.5">
                    <Calendar className="w-4 h-4 text-secondary" />
                    Total Activities
                  </span>
                  <span className="font-extrabold text-foreground">
                    {plan.days?.reduce((acc, d) => acc + (d.activities?.length || 0), 0) || 0}
                  </span>
                </div>
              </div>

              {/* Highlights/Vibes Checklist */}
              <div className="flex-1 flex flex-col gap-2 mb-6">
                <h4 className="text-[10px] font-extrabold text-secondary uppercase tracking-wider">Key Highlights:</h4>
                <ul className="flex flex-col gap-2">
                  {plan.highlights?.slice(0, 3).map((hl, hlIdx) => (
                    <li key={hlIdx} className="flex items-start gap-2 text-xs font-medium text-foreground">
                      <div className="p-0.5 bg-emerald-50 rounded-full mt-0.5 shrink-0 border border-emerald-200">
                        <Check className="w-3 h-3 text-emerald-500" />
                      </div>
                      <span className="line-clamp-2">{hl}</span>
                    </li>
                  ))}
                  {(!plan.highlights || plan.highlights.length === 0) && (
                    <li className="text-[10px] text-muted font-medium italic">No custom highlights provided.</li>
                  )}
                </ul>
              </div>

              {/* Select Button */}
              <button
                onClick={() => onSelectActive(plan.id)}
                disabled={isActive}
                className={`w-full py-3 font-bold rounded-full transition-all bouncy-hover text-xs flex items-center justify-center gap-1.5 ${
                  isActive 
                    ? "bg-emerald-50 border border-emerald-200 text-emerald-600 cursor-default" 
                    : "bg-primary hover:bg-primary/95 text-white pink-shadow hover:pink-shadow-deep"
                }`}
              >
                {isActive ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Active Scenario</span>
                  </>
                ) : (
                  <span>Select & View Timeline</span>
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
