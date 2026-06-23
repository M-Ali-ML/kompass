"use client";

import { useState, useEffect } from "react";
import { CopilotChat, UserMessage, AssistantMessage, Markdown } from "@copilotkit/react-ui";
import { useRenderTool } from "@copilotkit/react-core/v2";
import { Compass, Loader2, CheckCircle2, Brain, ChevronDown, ChevronUp } from "lucide-react";
import { z } from "zod";

function CustomReasoningMessage({ message, messages, inProgress }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [wasThinking, setWasThinking] = useState(false);

  // The agent is thinking if the reasoning message is the last message in the list
  const isThinking = inProgress && messages[messages.length - 1]?.id === message.id;

  // Auto-collapse when transition from thinking to complete happens
  useEffect(() => {
    if (isThinking) {
      setWasThinking(true);
    } else if (wasThinking && !isThinking) {
      setIsExpanded(false);
      setWasThinking(false);
    }
  }, [isThinking, wasThinking]);

  return (
    <div className="copilotKitMessage copilotKitAssistantMessage my-2 max-w-[85%]">
      <div 
        className="flex items-center gap-2 p-3 bg-secondary/5 border border-secondary/15 rounded-2xl cursor-pointer hover:bg-secondary/10 transition-colors select-none w-fit min-w-[200px]"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isThinking ? (
          <Brain className="w-4 h-4 text-secondary animate-pulse shrink-0" />
        ) : (
          <CheckCircle2 className="w-4 h-4 text-secondary/60 shrink-0" />
        )}
        <span className="text-xs font-semibold text-secondary leading-none">
          {isThinking ? "Thinking..." : "Thought process"}
        </span>
        <div className="ml-auto pl-4 flex items-center text-muted">
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-secondary/70" />
          ) : (
            <ChevronDown className="w-4 h-4 text-secondary/70" />
          )}
        </div>
      </div>

      {isExpanded && message.content && (
        <div className="mt-2 p-3 bg-white/50 border border-secondary/10 rounded-2xl text-xs text-muted-foreground leading-relaxed animate-fade-in max-w-full overflow-x-auto">
          <Markdown content={message.content} />
        </div>
      )}
    </div>
  );
}

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

  const customRenderMessage = (props) => {
    const { message, messages, inProgress, index, isCurrentMessage, onRegenerate, onCopy, onThumbsUp, onThumbsDown, markdownTagRenderers, ImageRenderer } = props;
    
    if (message.role === "user") {
      return (
        <UserMessage
          key={message.id || index}
          rawData={message}
          data-message-role="user"
          message={message}
          ImageRenderer={ImageRenderer}
        />
      );
    }
    
    if (message.role === "assistant") {
      return (
        <AssistantMessage
          key={message.id || index}
          data-message-role="assistant"
          subComponent={message.generativeUI?.()}
          rawData={message}
          message={message}
          messages={messages}
          isLoading={inProgress && isCurrentMessage && !message.content}
          isGenerating={inProgress && isCurrentMessage && !!message.content}
          isCurrentMessage={isCurrentMessage}
          onRegenerate={() => onRegenerate?.(message.id)}
          onCopy={onCopy}
          onThumbsUp={onThumbsUp}
          onThumbsDown={onThumbsDown}
          markdownTagRenderers={markdownTagRenderers}
          ImageRenderer={ImageRenderer}
        />
      );
    }
    
    if (message.role === "reasoning") {
      return (
        <CustomReasoningMessage
          key={message.id || index}
          message={message}
          messages={messages}
          inProgress={inProgress}
        />
      );
    }
    
    return null;
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

      {/* CopilotChat — handles streaming, tool calls, thinking display */}
      <div className="flex-1 overflow-hidden">
        <CopilotChat
          className="h-full"
          RenderMessage={customRenderMessage}
          labels={{
            title: "Kompass Math Agent",
            placeholder: "Type your question (e.g. What is 15 + 27?)...",
          }}
        />
      </div>
    </div>
  );
}


