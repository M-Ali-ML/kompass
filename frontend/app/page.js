"use client";

import React, { useState, useRef, useEffect } from "react";
import { Compass, Send, Bot, User } from "lucide-react";

export default function Home() {
  const [messages, setMessages] = useState([
    {
      id: "init",
      role: "agent",
      content: "Hello! I am the Kompass Math Agent. How can I help you add numbers today?"
    }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isGenerating) return;

    const userMessageText = inputValue.trim();
    setInputValue("");
    
    // Add user message
    const userMsg = {
      id: `user-${Date.now()}`,
      role: "user",
      content: userMessageText
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsGenerating(true);

    try {
      const response = await fetch(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessageText })
      });

      if (response.ok) {
        const data = await response.json();
        const agentMsg = {
          id: `agent-${Date.now()}`,
          role: "agent",
          content: data.response || "No response received."
        };
        setMessages((prev) => [...prev, agentMsg]);
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.error || `HTTP error! Status: ${response.status}`;
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "agent",
            content: errorMsg
          }
        ]);
      }
    } catch (err) {
      console.error("Failed to fetch response:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "agent",
          content: "Failed to connect to the backend server. Please make sure the backend is running."
        }
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

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

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl w-full mx-auto flex flex-col gap-4" id="messages-list">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              data-testid={isUser ? "message-user" : "message-agent"}
              className={`flex gap-3 max-w-[80%] ${isUser ? "self-end flex-row-reverse" : "self-start"}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-white text-xs font-bold ${
                isUser ? "bg-primary pink-shadow" : "bg-secondary purple-shadow"
              }`}>
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`p-4 rounded-2xl text-sm leading-relaxed font-medium ${
                isUser ? "bg-primary text-white pink-shadow" : "bg-surface text-foreground border border-pink-50 purple-shadow"
              }`}>
                {msg.content}
              </div>
            </div>
          );
        })}

        {isGenerating && (
          <div data-testid="loading-indicator" className="flex gap-3 max-w-[80%] self-start">
            <div className="w-8 h-8 rounded-full bg-secondary purple-shadow flex items-center justify-center text-white shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-4 bg-surface border border-pink-50 rounded-2xl purple-shadow flex flex-col gap-2 min-w-[150px]">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                <span className="text-[10px] font-extrabold text-primary uppercase tracking-wider">Agent is calculating...</span>
              </div>
              <div className="h-2 w-28 bg-pink-100/50 rounded shimmer" />
              <div className="h-2 w-20 bg-pink-100/50 rounded shimmer" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-surface border-t border-pink-100 shrink-0">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-2">
          <input
            id="message-input"
            type="text"
            placeholder="Type your question (e.g. What is 15 + 27?)..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isGenerating}
            className="flex-1 px-5 py-3 border-2 border-pink-100 rounded-full focus:outline-none focus:border-primary bg-background text-sm font-medium text-foreground placeholder:text-muted disabled:opacity-50"
          />
          <button
            id="send-button"
            type="submit"
            disabled={isGenerating || !inputValue.trim()}
            className="p-3.5 bg-primary text-white rounded-full bouncy-hover pink-shadow disabled:opacity-50 transition-all flex items-center justify-center cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
