"use client";

import { useState } from "react";
import { Compass, Settings, Menu } from "lucide-react";
import { SettingsModal } from "./settings-modal";

export function AppHeader({ onMenuClick, showMenu = false }) {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <header className="flex items-center justify-between px-4 sm:px-6 py-4 bg-surface border-b border-pink-100 pink-shadow shrink-0">
      <div className="flex items-center gap-2 sm:gap-3">
        {showMenu && (
          <button
            type="button"
            onClick={onMenuClick}
            aria-label="Open trips menu"
            className="p-2 rounded-2xl text-secondary border border-pink-100 bouncy-hover hover:bg-pink-50"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <div className="p-2.5 bg-primary text-white rounded-2xl bouncy-hover pink-shadow">
          <Compass className="w-6 h-6 animate-spin-slow" />
        </div>
        <span className="text-xl font-extrabold tracking-tight text-foreground">
          Kompass
        </span>
      </div>

      <button
        type="button"
        onClick={() => setSettingsOpen(true)}
        aria-label="Travel preferences"
        title="Travel preferences"
        className="p-2.5 rounded-2xl text-secondary border border-pink-100 bouncy-hover hover:bg-pink-50"
      >
        <Settings className="w-5 h-5" />
      </button>

      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </header>
  );
}
