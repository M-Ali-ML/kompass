"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useRenderTool } from "@copilotkit/react-core/v2";
import { Compass, Loader2, CheckCircle2 } from "lucide-react";
import { z } from "zod";

export default function Home() {
  useRenderTool({
    name: "calculate_sum",
    parameters: z.object({
      a: z.number().describe("The first number to add"),
      b: z.number().describe("The second number to add"),
    }),
    render: ({ status, parameters, result }) => {
      const isComplete = status === "complete";
      const a = parameters?.a ?? "?";
      const b = parameters?.b ?? "?";
      
      if (isComplete) {
        return (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-secondary/10 text-secondary border border-secondary/20 rounded-full text-xs font-medium w-fit my-1.5 bouncy-hover shadow-purple">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Added {a} + {b} = {result}</span>
          </div>
        );
      }

      return (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 text-primary border border-primary/20 rounded-full text-xs font-medium w-fit my-1.5 bouncy-hover animate-pulse shadow-bouncy">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Adding {a} + {b}...</span>
        </div>
      );
    },
  });

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* Header */}
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

      {/* CopilotChat — handles streaming, tool calls, thinking display */}
      <div className="flex-1 overflow-hidden">
        <CopilotChat
          className="h-full"
          labels={{
            title: "Kompass Math Agent",
            initial: "Hello! I am the Kompass Math Agent. How can I help you add numbers today?",
            placeholder: "Type your question (e.g. What is 15 + 27?)...",
          }}
        />
      </div>
    </div>
  );
}

