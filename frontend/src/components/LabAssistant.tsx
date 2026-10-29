"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  Send,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Cpu,
  MessageSquare,
  HelpCircle,
} from "lucide-react";
import { ChatMessage, AgentBriefingResponse, AgentQueryResponse } from "@/types/telemetry";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const QUICK_PROMPTS = [
  "Summarize visible objects",
  "Are there any safety hazards?",
  "What is in the foreground?",
  "Describe the scene",
];

export const LabAssistant: React.FC = () => {
  const [briefing, setBriefing] = useState<AgentBriefingResponse | null>(null);
  const [loadingBriefing, setLoadingBriefing] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial",
      sender: "assistant",
      text: "Hello! I am your local Lab Vision AI Assistant powered by Liquid AI LFM3 & Qwen 2.5. I am continuously monitoring your camera stream and can answer questions about equipment locations, workbench status, or safety protocols.",
      modelUsed: "lfm3:1.7b",
      timestamp: Date.now(),
    },
  ]);
  const [inputQuery, setInputQuery] = useState<string>("");
  const [isQuerying, setIsQuerying] = useState<boolean>(false);

  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isQuerying]);

  // Fetch AI situation briefing
  const fetchBriefing = async () => {
    try {
      setLoadingBriefing(true);
      const res = await fetch(`${API_BASE}/agent/briefing`);
      if (res.ok) {
        const data: AgentBriefingResponse = await res.json();
        setBriefing(data);
      }
    } catch (err) {
      console.warn("Failed to fetch lab briefing:", err);
    } finally {
      setLoadingBriefing(false);
    }
  };

  useEffect(() => {
    fetchBriefing();
  }, []);

  // Handle user query submission
  const handleSubmitQuery = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || isQuerying) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: textToSend.trim(),
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInputQuery("");
    setIsQuerying(true);

    try {
      const res = await fetch(`${API_BASE}/agent/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: textToSend.trim() }),
      });

      if (res.ok) {
        const data: AgentQueryResponse = await res.json();
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          sender: "assistant",
          text: data.answer,
          modelUsed: data.model_used,
          latencyMs: data.latency_ms,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        text: "Sorry, I encountered an error communicating with the local reasoning backend. Ensure FastAPI and Ollama are active.",
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsQuerying(false);
    }
  };

  const getSafetyBadge = (status: string = "nominal") => {
    switch (status) {
      case "caution":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3" />
            SAFETY: CAUTION
          </span>
        );
      case "hazard":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <AlertTriangle className="w-3 h-3" />
            SAFETY: HAZARD
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <ShieldCheck className="w-3 h-3" />
            SAFETY: NOMINAL
          </span>
        );
    }
  };

  return (
    <div className="bg-lab-850 rounded-xl border border-lab-700 p-4 flex flex-col h-full shadow-lg space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-lab-700">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              Lab AI Copilot
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                SLM Local
              </span>
            </h3>
          </div>
        </div>

        <button
          onClick={fetchBriefing}
          disabled={loadingBriefing}
          title="Refresh AI Situation Briefing"
          className="p-1 rounded bg-lab-800 hover:bg-lab-700 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loadingBriefing ? "animate-spin text-cyan-400" : ""}`} />
        </button>
      </div>

      {/* Live AI Situation Briefing Card */}
      <div className="p-3 rounded-lg bg-lab-800/90 border border-lab-700 text-xs space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-slate-300 flex items-center gap-1 text-[11px]">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            Live Scene Briefing
          </span>
          {getSafetyBadge(briefing?.safety_status)}
        </div>
        <p className="text-slate-300 text-[11px] leading-relaxed">
          {briefing ? briefing.summary : "Analyzing workbench camera telemetry..."}
        </p>
        {briefing && (
          <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500 font-mono">
            <span>Model: {briefing.model_used}</span>
            <span>Latency: {briefing.latency_ms}ms</span>
          </div>
        )}
      </div>

      {/* Chat Messages Log */}
      <div className="flex-1 overflow-y-auto space-y-2.5 max-h-56 pr-1 text-xs">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.sender === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`p-2.5 rounded-xl max-w-[88%] leading-relaxed ${
                msg.sender === "user"
                  ? "bg-cyan-600 text-white rounded-br-sm"
                  : "bg-lab-800 border border-lab-700/80 text-slate-200 rounded-bl-sm"
              }`}
            >
              <p className="text-[11px]">{msg.text}</p>
            </div>
            {msg.sender === "assistant" && msg.modelUsed && (
              <span className="text-[9px] text-slate-500 font-mono mt-0.5 px-1">
                {msg.modelUsed} {msg.latencyMs ? `• ${msg.latencyMs}ms` : ""}
              </span>
            )}
          </div>
        ))}

        {isQuerying && (
          <div className="flex items-center gap-1.5 text-xs text-cyan-400 p-2 bg-lab-800/50 rounded-lg">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" />
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.2s]" />
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.4s]" />
            <span className="text-[11px] text-slate-400 font-mono ml-1">Reasoning over vision telemetry...</span>
          </div>
        )}
        <div ref={chatBottomRef} />
      </div>

      {/* Quick Prompt Suggestion Chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto py-1 scrollbar-none">
        {QUICK_PROMPTS.map((prompt, i) => (
          <button
            key={i}
            onClick={() => handleSubmitQuery(prompt)}
            disabled={isQuerying}
            className="whitespace-nowrap px-2 py-0.5 rounded bg-lab-800 hover:bg-lab-700 border border-lab-700 text-[10px] text-slate-300 hover:text-cyan-300 transition-colors"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Query Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmitQuery();
        }}
        className="flex items-center gap-1.5 pt-1 border-t border-lab-700"
      >
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask AI about lab equipment..."
          disabled={isQuerying}
          className="flex-1 bg-lab-900 border border-lab-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
        />
        <button
          type="submit"
          disabled={isQuerying || !inputQuery.trim()}
          className="p-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg transition-colors flex items-center justify-center"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
