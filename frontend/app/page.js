"use client";

import React, { useState } from "react";
import ChatPane from "../components/ChatPane";
import { Compass } from "lucide-react";

export default function Home() {
  const [isGenerating, setIsGenerating] = useState(false);
  
  const [messages, setMessages] = useState([
    {
      role: "agent",
      content: "Hello! I am Kompass, your autonomous travel planner. Where would you like to go?"
    }
  ]);

  const handleSendMessage = async (text) => {
    // 1. Add User Message
    const newMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, newMsg]);
    setIsGenerating(true);

    // 2. Perform API Call to backend
    try {
      const response = await fetch(process.env.NEXT_PUBLIC_COPILOTKIT_ENDPOINT || "http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: "demo-session"
        })
      });

      if (response.ok) {
        const data = await response.json();
        const payload = data.response; // ScenarioMatrix
        if (payload && payload.scenarios && payload.scenarios.length > 0) {
          // Map backend Scenarios to frontend
          const mapped = payload.scenarios.map((sc, idx) => ({
            id: sc.scenario_id || `plan-${idx}`,
            title: sc.title || `Plan ${idx + 1}`,
            duration_days: sc.itinerary?.length || 5,
            estimated_cost_usd: sc.grand_total_usd || 1500,
            stress_score: sc.stress_score || 2,
            highlights: sc.summary ? [sc.summary] : ["AI Generated travel itinerary"],
            flights: sc.flights || [],
            stays: sc.stays || [],
            days: sc.itinerary?.map((day) => ({
              day_number: day.day_number,
              title: day.title || `Day ${day.day_number}`,
              activities: day.activities?.map((act, actIdx) => ({
                id: `act-${day.day_number}-${actIdx}`,
                title: act.name || act.title,
                description: act.description,
                time: act.start_time || "10:00",
                cost_usd: act.cost_usd || 0
              }))
            })) || []
          }));

          setMessages((prev) => [...prev, {
            role: "agent",
            content: `I've successfully generated scenarios based on your request: "${text}"`,
            scenarios: mapped
          }]);
          return;
        }
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    } catch (err) {
      console.error("API Offline or request failed:", err);
      setMessages((prev) => [...prev, {
        role: "agent",
        content: "Failed to connect to the Kompass backend. Please verify that the backend server is running."
      }]);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      {/* Minimal Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-surface border-b border-pink-100 pink-shadow shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary text-white rounded-2xl bouncy-hover pink-shadow">
            <Compass className="w-6 h-6" />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">
            Kompass<span className="text-primary">.ai</span>
            <span className="ml-2 text-xs font-semibold uppercase tracking-widest bg-pink-100 text-primary px-2 py-0.5 rounded-full">
              Agent MVP
            </span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-bold text-muted">Agent System Online</span>
        </div>
      </header>

      {/* Main Workspace Frame - Simplified to only ChatPane */}
      <div className="flex flex-1 overflow-hidden justify-center">
        <div className="w-full max-w-4xl h-full border-x border-pink-100 bg-white">
          <ChatPane 
            messages={messages}
            onSendMessage={handleSendMessage}
            isGenerating={isGenerating}
          />
        </div>
      </div>
    </div>
  );
}

