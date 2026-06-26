"use client";

import { Separator } from "react-resizable-panels";
import { GripVertical } from "lucide-react";

// A thin draggable divider between two horizontal panels. Widens and tints on
// hover/drag, with a centered grip affordance so it's obviously draggable.
export function ResizeHandle() {
  return (
    <Separator className="group relative flex w-1.5 items-center justify-center bg-pink-100/60 transition-colors hover:bg-primary/30 active:bg-primary/50">
      <span className="pointer-events-none flex h-8 w-4 items-center justify-center rounded-full bg-surface border border-pink-200 opacity-0 shadow-sm transition-opacity group-hover:opacity-100 group-active:opacity-100">
        <GripVertical className="h-3.5 w-3.5 text-primary" />
      </span>
    </Separator>
  );
}
