"use client";

import React, { useState } from "react";
import { Sparkles, Trash2, Plus, Hotel, Plane, Calendar, X, Heart } from "lucide-react";

export default function LeftSidebar({ 
  constraints, 
  setConstraints, 
  savedAssets, 
  setSavedAssets, 
  onNewTrip 
}) {
  const [newConstraint, setNewConstraint] = useState("");

  const addConstraint = (e) => {
    e.preventDefault();
    if (!newConstraint.trim()) return;
    if (!constraints.includes(newConstraint.trim())) {
      setConstraints([...constraints, newConstraint.trim()]);
    }
    setNewConstraint("");
  };

  const removeConstraint = (val) => {
    setConstraints(constraints.filter((c) => c !== val));
  };

  const removeAsset = (id) => {
    setSavedAssets(savedAssets.filter((a) => a.id !== id));
  };

  return (
    <aside className="w-80 flex flex-col bg-surface border-r border-pink-100 p-6 gap-6 h-[calc(100vh-73px)] overflow-y-auto">
      {/* New Trip Button */}
      <button 
        onClick={onNewTrip}
        className="w-full py-3.5 bg-primary text-white font-bold rounded-full pink-shadow hover:pink-shadow-deep transition-all bouncy-hover flex items-center justify-center gap-2"
      >
        <Plus className="w-5 h-5" />
        <span>Plan New Trip</span>
      </button>

      {/* Constraints Panel */}
      <div className="flex flex-col gap-3 p-4 bg-pink-50/50 rounded-3xl border border-pink-100/50">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-secondary flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-primary animate-pulse" />
            <span>Active Constraints</span>
          </h3>
          <span className="text-xs font-extrabold text-white bg-primary px-2 py-0.5 rounded-full">
            {constraints.length}
          </span>
        </div>
        
        {/* Constraints List */}
        <div className="flex flex-wrap gap-1.5 min-h-[40px]">
          {constraints.length === 0 ? (
            <p className="text-xs font-medium text-muted/80 italic p-1">No active constraints. Add your preferences below or let the AI discover them.</p>
          ) : (
            constraints.map((c, i) => (
              <span 
                key={i} 
                className="flex items-center gap-1 px-3 py-1.5 bg-white border border-pink-200 text-xs font-bold text-primary rounded-full pink-shadow"
              >
                <span>{c}</span>
                <button 
                  onClick={() => removeConstraint(c)}
                  className="hover:bg-pink-100 rounded-full p-0.5 transition-colors"
                >
                  <X className="w-3 h-3 text-primary" />
                </button>
              </span>
            ))
          )}
        </div>

        {/* Add Constraint Input */}
        <form onSubmit={addConstraint} className="flex gap-1.5 mt-2">
          <input
            type="text"
            placeholder="Add constraint (e.g. Vegetarian)"
            value={newConstraint}
            onChange={(e) => setNewConstraint(e.target.value)}
            className="flex-1 px-3 py-2 text-xs font-bold bg-white border border-pink-200 rounded-full focus:outline-none focus:border-primary text-foreground"
          />
          <button 
            type="submit"
            className="p-2 bg-primary text-white rounded-full bouncy-hover hover:pink-shadow"
          >
            <Plus className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* Saved Assets Drawer */}
      <div className="flex-1 flex flex-col gap-3 min-h-[200px]">
        <h3 className="text-sm font-bold text-secondary flex items-center gap-1.5">
          <Heart className="w-4 h-4 text-primary fill-primary" />
          <span>Saved Assets</span>
        </h3>
        
        <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1">
          {savedAssets.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-pink-100 rounded-3xl p-6 text-center">
              <Hotel className="w-8 h-8 text-pink-200 mb-2" />
              <p className="text-xs font-medium text-muted leading-relaxed">Like accommodations or flights in your timeline to pin them here.</p>
            </div>
          ) : (
            savedAssets.map((asset) => (
              <div 
                key={asset.id} 
                className="group flex flex-col border border-pink-100 rounded-2xl p-3 bg-white bouncy-hover shadow-sm hover:pink-shadow transition-all relative"
              >
                <button 
                  onClick={() => removeAsset(asset.id)}
                  className="absolute top-2 right-2 p-1 bg-pink-50 text-primary rounded-full opacity-0 group-hover:opacity-100 hover:bg-pink-100 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>

                <div className="flex items-start gap-2.5">
                  <div className={`p-2 rounded-xl text-white ${
                    asset.type === "stay" ? "bg-accent blue-shadow" : "bg-secondary purple-shadow"
                  }`}>
                    {asset.type === "stay" ? <Hotel className="w-4 h-4" /> : <Plane className="w-4 h-4" />}
                  </div>
                  <div>
                    <h4 className="text-xs font-extrabold text-foreground pr-4 line-clamp-1">{asset.title}</h4>
                    <p className="text-[10px] font-bold text-primary mt-0.5">{asset.subtitle}</p>
                    <p className="text-[10px] font-bold text-muted mt-1">{asset.details}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
