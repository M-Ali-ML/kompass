"use client";

import React from "react";
import { Compass, MessageSquare, BarChart3, Bell, User, MapPin } from "lucide-react";

export default function TopAppBar({ activeTab, setActiveTab, currentDestination, onSearchDestination }) {
  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 bg-surface border-b border-pink-100 pink-shadow">
      {/* Brand logo */}
      <div className="flex items-center gap-3">
        <div className="p-2.5 bg-primary text-white rounded-2xl bouncy-hover pink-shadow">
          <Compass className="w-6 h-6 animate-spin-slow" />
        </div>
        <span className="text-xl font-bold tracking-tight text-foreground">
          Kompass<span className="text-primary">.ai</span>
        </span>
      </div>

      {/* Destination search bar */}
      <div className="flex items-center max-w-md gap-2 px-4 py-2 border-2 border-pink-100 rounded-full bg-background focus-within:border-primary transition-all">
        <MapPin className="w-4 h-4 text-primary" />
        <input
          type="text"
          placeholder="Where to? (e.g. Bali, Tokyo...)"
          className="w-full text-sm font-medium bg-transparent outline-none text-foreground placeholder:text-muted"
          value={currentDestination}
          onChange={(e) => onSearchDestination(e.target.value)}
        />
      </div>

      {/* Navigation & Controls */}
      <div className="flex items-center gap-4">
        <nav className="flex items-center gap-1.5 p-1 bg-pink-50 rounded-full">
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-full transition-all bouncy-hover ${
              activeTab === "chat"
                ? "bg-primary text-white pink-shadow"
                : "text-secondary hover:bg-pink-100/50"
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Chat Builder</span>
          </button>
          
          <button
            onClick={() => setActiveTab("comparison")}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-full transition-all bouncy-hover ${
              activeTab === "comparison"
                ? "bg-secondary text-white purple-shadow"
                : "text-secondary hover:bg-pink-100/50"
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Comparison Matrix</span>
          </button>
        </nav>

        {/* Notifications and Profile */}
        <div className="flex items-center gap-2.5">
          <button className="p-2.5 border-2 border-pink-50 text-secondary rounded-full hover:bg-pink-50 bouncy-hover transition-colors">
            <Bell className="w-4.5 h-4.5" />
          </button>
          
          <div className="flex items-center gap-2 p-1.5 pr-3 border-2 border-pink-50 rounded-full hover:bg-pink-50 transition-colors cursor-pointer bouncy-hover">
            <div className="flex items-center justify-center w-8 h-8 font-extrabold text-white rounded-full bg-accent blue-shadow text-xs">
              AL
            </div>
            <span className="text-xs font-bold text-foreground">Aly</span>
          </div>
        </div>
      </div>
    </header>
  );
}
