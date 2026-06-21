"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, CheckSquare, Users, Sparkles, AlertCircle, Compass } from "lucide-react";

export default function ChatPane({ 
  messages, 
  onSendMessage, 
  isGenerating, 
  activeVibes, 
  setActiveVibes, 
  travelers, 
  setTravelers 
}) {
  const [inputValue, setInputValue] = useState("");
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

  const toggleVibe = (vibe) => {
    if (activeVibes.includes(vibe)) {
      setActiveVibes(activeVibes.filter((v) => v !== vibe));
    } else {
      setActiveVibes([...activeVibes, vibe]);
    }
  };

  const updateTravelers = (amount) => {
    setTravelers(Math.max(1, travelers + amount));
  };

  // Render Custom Widgets based on message types or instructions
  const renderWidget = (widgetType) => {
    if (widgetType === "vibe_selector") {
      const vibesList = ["Beach Bliss", "Mountain Adventure", "Cultural Immersion", "Nightlife Explorer", "Culinary Journey", "Wellness Retreat"];
      return (
        <div className="mt-3 p-4 bg-white border-2 border-accent/30 rounded-3xl blue-shadow flex flex-col gap-3 max-w-sm">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-accent" />
            <h4 className="text-xs font-extrabold text-secondary">Tune Trip Vibe Checklist</h4>
          </div>
          <p className="text-[10px] text-muted font-medium">Select one or more vibes to fine-tune the recommendation score:</p>
          <div className="grid grid-cols-2 gap-1.5">
            {vibesList.map((vibe) => {
              const isSelected = activeVibes.includes(vibe);
              return (
                <button
                  key={vibe}
                  onClick={() => toggleVibe(vibe)}
                  className={`px-2.5 py-1.5 text-[10px] font-bold rounded-full border transition-all text-left truncate bouncy-hover ${
                    isSelected 
                      ? "bg-accent/10 border-accent text-accent" 
                      : "bg-pink-50/20 border-pink-100 text-foreground hover:bg-pink-50/50"
                  }`}
                >
                  {vibe}
                </button>
              );
            })}
          </div>
        </div>
      );
    }

    if (widgetType === "traveler_counter") {
      return (
        <div className="mt-3 p-4 bg-white border-2 border-primary/30 rounded-3xl pink-shadow flex flex-col gap-3 max-w-sm">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            <h4 className="text-xs font-extrabold text-secondary">Travelers Count</h4>
          </div>
          <p className="text-[10px] text-muted font-medium">Set the headcount to optimize accommodation and transit pricing:</p>
          <div className="flex items-center gap-4 bg-pink-50/30 p-2 rounded-full border border-pink-100 max-w-[150px] justify-between self-center">
            <button 
              onClick={() => updateTravelers(-1)}
              className="w-8 h-8 rounded-full bg-white border border-pink-200 text-primary font-extrabold flex items-center justify-center hover:bg-primary hover:text-white hover:border-primary transition-all bouncy-hover"
            >
              -
            </button>
            <span className="text-sm font-extrabold text-foreground">{travelers}</span>
            <button 
              onClick={() => updateTravelers(1)}
              className="w-8 h-8 rounded-full bg-white border border-pink-200 text-primary font-extrabold flex items-center justify-center hover:bg-primary hover:text-white hover:border-primary transition-all bouncy-hover"
            >
              +
            </button>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="flex-1 flex flex-col bg-pink-50/10 h-[calc(100vh-73px)] relative">
      {/* Header Info */}
      <div className="px-6 py-3 bg-white/80 backdrop-blur-md border-b border-pink-100 flex items-center gap-2">
        <Bot className="w-5 h-5 text-primary" />
        <div>
          <h2 className="text-xs font-extrabold text-foreground flex items-center gap-1.5">
            Kompass Agent Session
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </h2>
          <p className="text-[10px] font-bold text-muted">Powered by PydanticAI & Gemini 1.5 Flash</p>
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
              I am your autonomous travel architect. Ask me to plan a trip (e.g. <span className="text-primary font-bold">"Plan a 4-day budget-friendly trip to Bali with culture vibes"</span>).
            </p>
            <div className="flex flex-col gap-2 w-full mt-2">
              <button 
                onClick={() => onSendMessage("Plan a 5-day trip to Bali with 2 travelers")} 
                className="w-full py-2.5 bg-white border border-pink-200 hover:border-primary text-xs font-bold text-secondary rounded-full bouncy-hover hover:pink-shadow text-center transition-all"
              >
                🌴 Bali Adventure (5 Days, 2 Travelers)
              </button>
              <button 
                onClick={() => onSendMessage("Create a Tokyo Itinerary focusing on food and culture, under $3000")} 
                className="w-full py-2.5 bg-white border border-pink-200 hover:border-primary text-xs font-bold text-secondary rounded-full bouncy-hover hover:pink-shadow text-center transition-all"
              >
                🍣 Tokyo Food & Culture (under $3000)
              </button>
            </div>
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
                    {/* Render markdown / list formatted text simply */}
                    <div className="whitespace-pre-line leading-relaxed text-xs">
                      {msg.content}
                    </div>

                    {/* Check if we have embedded widget parameters */}
                    {isBot && msg.widget && renderWidget(msg.widget)}
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
    </div>
  );
}
