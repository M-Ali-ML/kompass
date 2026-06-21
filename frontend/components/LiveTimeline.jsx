"use client";

import React from "react";
import { Calendar, Map, Check, Heart, Clock, DollarSign, Sparkles } from "lucide-react";

export default function LiveTimeline({ 
  itinerary, 
  savedAssets, 
  setSavedAssets, 
  onToggleMap,
  isMapOpen 
}) {
  const isPinned = (item) => {
    return savedAssets.some((a) => a.id === item.id);
  };

  const togglePin = (item, type) => {
    if (isPinned(item)) {
      setSavedAssets(savedAssets.filter((a) => a.id !== item.id));
    } else {
      setSavedAssets([
        ...savedAssets,
        {
          id: item.id || Math.random().toString(),
          type: type,
          title: item.title || item.name,
          subtitle: type === "stay" ? "Accommodation" : "Transit",
          details: type === "stay" ? `${item.location} • $${item.price_per_night}/night` : `${item.flight_number} • $${item.price_usd}`,
        }
      ]);
    }
  };

  if (!itinerary) {
    return (
      <div className="w-96 flex flex-col bg-white border-l border-pink-100 h-[calc(100vh-73px)] justify-center items-center p-6 text-center">
        <Calendar className="w-12 h-12 text-pink-200 mb-3 animate-pulse" />
        <h3 className="text-sm font-extrabold text-secondary">No Itinerary Loaded</h3>
        <p className="text-xs text-muted leading-relaxed mt-1 max-w-xs">
          Describe your dream trip in the chat, and I will architect a live sync timeline comparison right here.
        </p>
      </div>
    );
  }

  return (
    <div className="w-96 flex flex-col bg-surface border-l border-pink-100 h-[calc(100vh-73px)] relative">
      {/* Itinerary Header */}
      <div className="p-5 border-b border-pink-100/60 bg-pink-50/20">
        <div className="flex justify-between items-start">
          <div>
            <span className="text-[9px] font-extrabold text-primary bg-primary-fixed/50 px-2 py-0.5 rounded-full uppercase tracking-wider">
              {itinerary.status || "Syncing"}
            </span>
            <h3 className="text-sm font-extrabold text-foreground mt-1.5">{itinerary.title}</h3>
            <p className="text-[10px] font-bold text-muted mt-0.5">{itinerary.destination} • {itinerary.duration_days} Days</p>
          </div>
          <div className="text-right">
            <p className="text-[9px] font-bold text-muted">Estimated Cost</p>
            <p className="text-xs font-extrabold text-primary">${itinerary.estimated_cost_usd}</p>
          </div>
        </div>

        {/* Stress score indicators */}
        <div className="mt-4 flex items-center justify-between bg-white border border-pink-100/50 p-2.5 rounded-2xl">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-accent" />
            <span className="text-[10px] font-extrabold text-secondary">Stress Score:</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-20 bg-pink-100 rounded-full h-2 overflow-hidden">
              <div 
                className="bg-primary h-full rounded-full" 
                style={{ width: `${(itinerary.stress_score || 3) * 20}%` }}
              />
            </div>
            <span className="text-[10px] font-extrabold text-primary">{itinerary.stress_score || 3}/5</span>
          </div>
        </div>
      </div>

      {/* Timeline Scroll Area */}
      <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-6">
        {itinerary.days?.map((day, dayIdx) => (
          <div key={dayIdx} className="flex flex-col gap-3">
            {/* Day Title */}
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-secondary text-white font-extrabold text-xs shadow-sm">
                D{day.day_number}
              </div>
              <h4 className="text-xs font-extrabold text-secondary">{day.title}</h4>
            </div>

            {/* Day Activities */}
            <div className="border-l-2 border-dashed border-pink-200 ml-4 pl-5 flex flex-col gap-4">
              {day.activities?.map((activity, actIdx) => (
                <div 
                  key={actIdx} 
                  className="relative p-3.5 bg-white border border-pink-100/60 rounded-2xl shadow-sm hover:pink-shadow transition-all bouncy-hover"
                >
                  {/* Pin button */}
                  <button 
                    onClick={() => togglePin(activity, "stay")}
                    className="absolute top-2 right-2 p-1.5 rounded-full hover:bg-pink-50 transition-colors"
                  >
                    <Heart className={`w-3.5 h-3.5 ${
                      isPinned(activity) ? "text-primary fill-primary" : "text-muted hover:text-primary"
                    }`} />
                  </button>

                  <div className="flex items-center gap-1 text-[9px] font-bold text-muted mb-1.5">
                    <Clock className="w-3 h-3 text-accent" />
                    <span>{activity.time || "Morning"}</span>
                  </div>

                  <h5 className="text-xs font-extrabold text-foreground pr-5">{activity.title}</h5>
                  <p className="text-[10px] text-muted font-medium mt-1 leading-relaxed">{activity.description}</p>
                  
                  {activity.cost_usd > 0 && (
                    <div className="mt-2.5 flex items-center gap-0.5 text-[9px] font-extrabold text-primary bg-pink-50 px-2 py-0.5 rounded-full w-fit">
                      <DollarSign className="w-2.5 h-2.5" />
                      <span>{activity.cost_usd}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Floating Action Button (FAB) for Map Toggle */}
      <button
        onClick={onToggleMap}
        className={`absolute bottom-6 right-6 p-4 rounded-full shadow-lg transition-all bouncy-hover flex items-center justify-center z-20 ${
          isMapOpen 
            ? "bg-accent text-white hover:bg-accent/80 blue-shadow-deep" 
            : "bg-primary text-white hover:bg-primary/80 pink-shadow-deep"
        }`}
      >
        <Map className="w-5 h-5" />
      </button>
    </div>
  );
}
