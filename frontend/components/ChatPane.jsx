"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  Send, Bot, User, Sparkles, Compass, 
  Plane, Hotel, Calendar, DollarSign, X, Eye 
} from "lucide-react";

export default function ChatPane({ 
  messages, 
  onSendMessage, 
  isGenerating
}) {
  const [inputValue, setInputValue] = useState("");
  const [activeDetailsScenario, setActiveDetailsScenario] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    onSendMessage(inputValue.trim());
    setInputValue("");
  };

  return (
    <div className="flex-1 flex flex-col bg-pink-50/10 h-full relative">
      {/* Header Info */}
      <div className="px-6 py-3 bg-white/80 backdrop-blur-md border-b border-pink-100 flex items-center gap-2">
        <Bot className="w-5 h-5 text-primary" />
        <div>
          <h2 className="text-xs font-extrabold text-foreground flex items-center gap-1.5">
            Kompass Agent Session
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </h2>
          <p className="text-[10px] font-bold text-muted">Powered by PydanticAI & Gemini 2.5 Flash</p>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center max-w-md mx-auto gap-4">
            <div className="p-4 bg-white border-2 border-pink-100 rounded-3xl pink-shadow animate-bounce">
              <Compass className="w-12 h-12 text-primary" />
            </div>
            <h3 className="text-base font-extrabold text-foreground">Welcome to Kompass.ai!</h3>
            <p className="text-xs font-medium text-muted leading-relaxed">
              I am your autonomous travel architect. Tell me where you want to go, and I'll generate custom itineraries for you.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isBot = msg.role === "agent" || msg.role === "assistant";
            return (
              <div 
                key={index} 
                className={`flex gap-3 max-w-[85%] ${isBot ? "self-start" : "self-end flex-row-reverse"}`}
              >
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 font-extrabold text-white text-xs ${
                  isBot ? "bg-secondary purple-shadow" : "bg-primary pink-shadow"
                }`}>
                  {isBot ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                {/* Bubble Container */}
                <div className="flex flex-col">
                  <div className={`p-4 rounded-3xl text-sm font-medium ${
                    isBot 
                      ? "bg-white text-foreground border border-pink-100/50 purple-shadow" 
                      : "bg-primary text-white pink-shadow-deep"
                  }`}>
                    {/* Render message text */}
                    <div className="whitespace-pre-line leading-relaxed text-xs">
                      {msg.content}
                    </div>

                    {/* Scenario List Preview */}
                    {isBot && msg.scenarios && msg.scenarios.length > 0 && (
                      <div className="mt-4 flex flex-col gap-2 border-t border-pink-50 pt-3">
                        <div className="text-[10px] uppercase tracking-wider font-extrabold text-secondary flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-primary" />
                          Generated Scenarios ({msg.scenarios.length})
                        </div>
                        <div className="grid grid-cols-1 gap-2 mt-1">
                          {msg.scenarios.map((sc, idx) => (
                            <div 
                              key={sc.id || idx}
                              className="p-3 rounded-2xl border border-pink-100 bg-pink-50/10 flex flex-col gap-1.5 hover:border-primary/30 transition-all"
                            >
                              <div className="text-xs font-bold text-foreground flex items-center justify-between">
                                <span className="truncate max-w-[180px]">{sc.title}</span>
                                <span className="px-1.5 py-0.5 rounded-full text-[9px] bg-slate-100 text-slate-600 shrink-0">
                                  {sc.duration_days} Days
                                </span>
                              </div>
                              
                              {sc.highlights && sc.highlights.length > 0 && (
                                <ul className="text-[10px] text-muted list-disc list-inside leading-normal font-medium">
                                  {sc.highlights.slice(0, 2).map((hi, hidx) => (
                                    <li key={hidx} className="truncate">{hi}</li>
                                  ))}
                                </ul>
                              )}

                              <div className="flex items-center justify-between text-[10px] text-muted font-bold mt-1 pt-1.5 border-t border-pink-50/60">
                                <span className="flex items-center gap-0.5 text-secondary">
                                  <DollarSign className="w-3 h-3 text-secondary" />
                                  {sc.estimated_cost_usd} USD
                                </span>
                                <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold ${
                                  sc.stress_score <= 2 
                                    ? "bg-emerald-50 text-emerald-600" 
                                    : sc.stress_score <= 3 
                                    ? "bg-amber-50 text-amber-600" 
                                    : "bg-rose-50 text-rose-600"
                                }`}>
                                  Stress Score: {sc.stress_score}/5
                                </span>
                              </div>
                              
                              <button
                                type="button"
                                onClick={() => setActiveDetailsScenario(sc)}
                                className="mt-2 w-full py-1.5 px-3 bg-white border border-pink-100 hover:border-primary text-[10px] font-bold text-secondary hover:text-primary rounded-xl bouncy-hover text-center transition-all flex items-center justify-center gap-1 cursor-pointer"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                View Detailed Plan
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}


                  </div>
                  <span className={`text-[9px] font-bold text-muted mt-1 px-1 ${isBot ? "self-start" : "self-end"}`}>
                    {isBot ? "Kompass" : "You"}
                  </span>
                </div>
              </div>
            );
          })
        )}

        {/* Shimmer / Generating Loader state */}
        {isGenerating && (
          <div className="flex gap-3 max-w-[80%] self-start">
            <div className="w-8 h-8 rounded-full bg-secondary purple-shadow flex items-center justify-center text-white shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="flex flex-col gap-2">
              <div className="p-4 bg-white border border-pink-100 rounded-3xl purple-shadow flex flex-col gap-3 min-w-[250px]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-primary animate-ping" />
                  <span className="text-[10px] font-extrabold text-primary uppercase tracking-wider animate-pulse">
                    Calling MCP Services...
                  </span>
                </div>
                {/* Skeleton shimmer lines */}
                <div className="h-3 w-44 bg-pink-100/60 rounded-md shimmer" />
                <div className="h-3 w-56 bg-pink-100/60 rounded-md shimmer" />
                <div className="h-3 w-36 bg-pink-100/60 rounded-md shimmer" />
              </div>
              <span className="text-[9px] font-bold text-muted mt-1 px-1">Kompass is orchestrating...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 bg-white border-t border-pink-100">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            placeholder="Type your travel request..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isGenerating}
            className="flex-1 px-5 py-3 border-2 border-pink-100 rounded-full focus:outline-none focus:border-primary bg-background text-sm font-medium text-foreground placeholder:text-muted disabled:opacity-50"
          />
          <button 
            type="submit"
            disabled={isGenerating || !inputValue.trim()}
            className="p-3.5 bg-primary text-white rounded-full bouncy-hover pink-shadow hover:pink-shadow-deep disabled:opacity-50 disabled:pointer-events-none transition-all flex items-center justify-center"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* Overlay Modal for Detailed Plan */}
      {activeDetailsScenario && (
        <div className="absolute inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-pink-100 w-full max-w-2xl h-[85%] rounded-3xl shadow-bouncy flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-pink-50/20 border-b border-pink-100/60 flex items-center justify-between shrink-0">
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] uppercase tracking-widest font-extrabold text-primary">Detailed Scenario Plan</span>
                <h3 className="text-sm font-bold text-foreground line-clamp-1">{activeDetailsScenario.title}</h3>
              </div>
              <button 
                type="button"
                onClick={() => setActiveDetailsScenario(null)}
                className="p-1.5 hover:bg-pink-100/60 rounded-full transition-colors cursor-pointer"
              >
                <X className="w-5 h-5 text-secondary" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
              {/* Highlights & Stress Info */}
              <div className="p-4 rounded-2xl bg-pink-50/10 border border-pink-100 flex flex-col gap-2">
                <span className="text-[10px] font-extrabold uppercase text-secondary tracking-wider flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-primary" /> Highlights
                </span>
                <p className="text-xs text-foreground/80 leading-relaxed font-semibold italic">
                  "{activeDetailsScenario.highlights ? activeDetailsScenario.highlights[0] : "Custom AI planned scenario optimized for budget and comfort."}"
                </p>
                <div className="grid grid-cols-2 gap-4 mt-2 pt-2.5 border-t border-pink-100/50">
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted font-bold">ESTIMATED BUDGET</span>
                    <span className="text-sm font-extrabold text-primary">${activeDetailsScenario.estimated_cost_usd} USD</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] text-muted font-bold">STRESS DIFFICULTY</span>
                    <span className={`text-sm font-extrabold ${
                      activeDetailsScenario.stress_score <= 2 
                        ? "text-emerald-600" 
                        : activeDetailsScenario.stress_score <= 3 
                        ? "text-amber-600" 
                        : "text-rose-600"
                    }`}>
                      {activeDetailsScenario.stress_score} / 5
                    </span>
                  </div>
                </div>
              </div>

              {/* Flights & Stays */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Flights Card */}
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 flex flex-col gap-2">
                  <h4 className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Plane className="w-4 h-4 text-accent" />
                    Flight Details
                  </h4>
                  {activeDetailsScenario.flights && activeDetailsScenario.flights.length > 0 ? (
                    activeDetailsScenario.flights.map((flight, fidx) => (
                      <div key={fidx} className="text-xs text-foreground flex flex-col gap-1 border-t border-slate-200/60 pt-2 first:border-0 first:pt-0">
                        <div className="flex justify-between font-bold">
                          <span>{flight.airline} ({flight.flight_number})</span>
                          <span className="text-accent">${flight.price_usd}</span>
                        </div>
                        <div className="text-[11px] text-muted flex items-center justify-between">
                          <span>{flight.origin} ➔ {flight.destination}</span>
                          <span>{flight.departure_time} - {flight.arrival_time}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-[11px] text-muted italic">No flights booked. Custom routes available.</p>
                  )}
                </div>

                {/* Stays Card */}
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 flex flex-col gap-2">
                  <h4 className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Hotel className="w-4 h-4 text-primary" />
                    Accommodation Details
                  </h4>
                  {activeDetailsScenario.stays && activeDetailsScenario.stays.length > 0 ? (
                    activeDetailsScenario.stays.map((stay, sidx) => (
                      <div key={sidx} className="text-xs text-foreground flex flex-col gap-1 border-t border-slate-200/60 pt-2 first:border-0 first:pt-0">
                        <div className="flex justify-between font-bold">
                          <span>{stay.name}</span>
                          <span className="text-primary">${stay.total_price_usd}</span>
                        </div>
                        <div className="text-[11px] text-muted flex items-center justify-between">
                          <span>{stay.location}</span>
                          <span>★ {stay.rating}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-[11px] text-muted italic">No hotels booked. Self-managed stays.</p>
                  )}
                </div>
              </div>

              {/* Daily Schedule */}
              <div className="flex flex-col gap-4">
                <h4 className="text-xs font-bold text-secondary uppercase tracking-wider flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-primary" />
                  Day-by-Day Itinerary
                </h4>
                <div className="flex flex-col gap-4">
                  {activeDetailsScenario.days.map((day) => (
                    <div key={day.day_number} className="border border-pink-100/50 rounded-2xl overflow-hidden shadow-sm bg-white">
                      <div className="bg-pink-50/30 px-4 py-2 border-b border-pink-100/50 flex items-center justify-between">
                        <span className="text-xs font-bold text-foreground">Day {day.day_number}: {day.title}</span>
                        {day.date && <span className="text-[10px] text-muted font-bold">{day.date}</span>}
                      </div>
                      <div className="p-4 flex flex-col gap-3.5">
                        {day.activities && day.activities.length > 0 ? (
                          day.activities.map((act, actIdx) => (
                            <div key={act.id || actIdx} className="flex gap-3 relative pb-3 last:pb-0 border-b border-slate-50 last:border-b-0">
                              {/* Left timeline dot */}
                              <div className="flex flex-col items-center">
                                <div className="w-2 h-2 rounded-full bg-primary mt-1.5" />
                                <div className="w-0.5 flex-1 bg-pink-100/50 my-1 last:hidden" />
                              </div>
                              {/* Content */}
                              <div className="flex-1 flex flex-col gap-0.5">
                                <div className="flex items-center justify-between text-xs font-bold text-foreground">
                                  <span>{act.title}</span>
                                  {act.time && <span className="text-[10px] text-muted">{act.time}</span>}
                                </div>
                                <p className="text-[11px] text-muted leading-relaxed font-medium">
                                  {act.description}
                                </p>
                                {act.cost_usd !== undefined && act.cost_usd > 0 && (
                                  <span className="text-[10px] font-bold text-accent bg-accent/10 px-2 py-0.5 rounded-md self-start mt-1">
                                    Cost: ${act.cost_usd}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))
                        ) : (
                          <p className="text-[11px] text-muted italic">No activities planned for this day.</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end shrink-0">
              <button 
                type="button"
                onClick={() => setActiveDetailsScenario(null)}
                className="px-5 py-2.5 bg-secondary text-white font-bold text-xs rounded-full bouncy-hover purple-shadow cursor-pointer"
              >
                Close Plan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
