import { Compass } from "lucide-react";

export function AppHeader() {
  return (
    <header className="flex items-center justify-between px-6 py-4 bg-surface border-b border-pink-100 pink-shadow shrink-0">
      <div className="flex items-center gap-3">
        <div className="p-2.5 bg-primary text-white rounded-2xl bouncy-hover pink-shadow">
          <Compass className="w-6 h-6 animate-spin-slow" />
        </div>
        <span className="text-xl font-extrabold tracking-tight text-foreground">
          Kompass
        </span>
      </div>
    </header>
  );
}
