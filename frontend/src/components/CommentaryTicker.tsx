"use client";

import React, { useState, useEffect, useRef } from "react";
import { Mic, Activity, Clock, Sparkles, Volume2, VolumeX, MessageSquare } from "lucide-react";
import { LiveCommentaryItem } from "@/types/telemetry";

interface CommentaryTickerProps {
  commentaryFeed: LiveCommentaryItem[];
  latestCommentary?: LiveCommentaryItem | null;
}

export const CommentaryTicker: React.FC<CommentaryTickerProps> = ({
  commentaryFeed,
  latestCommentary,
}) => {
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(false);
  const lastSpokenIdRef = useRef<string>("");

  // Speak live commentary aloud if Voice Narration is enabled
  useEffect(() => {
    if (!voiceEnabled || !latestCommentary || typeof window === "undefined") return;
    if (latestCommentary.id === lastSpokenIdRef.current) return;
    lastSpokenIdRef.current = latestCommentary.id;

    try {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel(); // Stop prior utterance
        const utterance = new SpeechSynthesisUtterance(latestCommentary.text);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
      }
    } catch (e) {
      console.debug("Speech synthesis error:", e);
    }
  }, [latestCommentary, voiceEnabled]);

  const getActionBadge = (actionType: string) => {
    switch (actionType) {
      case "people_talking":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-mono tracking-wider">
            CONVERSATION
          </span>
        );
      case "person_left":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 font-mono tracking-wider">
            MOVED AWAY
          </span>
        );
      case "person_entered":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono tracking-wider">
            ENTERED SCENE
          </span>
        );
      case "using_phone":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 font-mono tracking-wider">
            USING PHONE
          </span>
        );
      case "working_laptop":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40 font-mono tracking-wider">
            WORKING COMPUTER
          </span>
        );
      case "person_moved":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono tracking-wider">
            POSITION SHIFT
          </span>
        );
      case "drinking":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono tracking-wider">
            HANDLING DRINK
          </span>
        );
      case "picked_up":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 font-mono tracking-wider">
            PICKED UP
          </span>
        );
      case "placed_down":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono tracking-wider">
            SET DOWN
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700 font-mono tracking-wider">
            OBSERVATION
          </span>
        );
    }
  };

  const allItems = commentaryFeed.length > 0 ? commentaryFeed : (latestCommentary ? [latestCommentary] : []);

  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-4 flex flex-col h-full shadow-xl space-y-3 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Mic className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              Live Commentary
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-950/80 text-rose-400 border border-rose-800/80">
                AI Narrator
              </span>
            </h3>
          </div>
        </div>

        {/* Voice Toggle Button */}
        <button
          onClick={() => setVoiceEnabled(!voiceEnabled)}
          title={voiceEnabled ? "Mute Voice Narration" : "Enable Voice Narration"}
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
            voiceEnabled
              ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm"
              : "bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700/60"
          }`}
        >
          {voiceEnabled ? (
            <>
              <Volume2 className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
              <span className="font-mono text-[11px] font-semibold">Voice: ON</span>
            </>
          ) : (
            <>
              <VolumeX className="w-3.5 h-3.5 text-slate-400" />
              <span className="font-mono text-[11px]">Voice: OFF</span>
            </>
          )}
        </button>
      </div>

      {/* Latest Highlight Banner */}
      {latestCommentary && (
        <div className="p-3 rounded-xl bg-slate-950/90 border border-cyan-500/40 shadow-md text-xs space-y-1.5 ring-1 ring-cyan-500/10">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-cyan-400 flex items-center gap-1 text-[11px]">
              <Sparkles className="w-3 h-3" />
              Current Activity
            </span>
            {getActionBadge(latestCommentary.action_type)}
          </div>
          <p className="text-slate-100 font-medium text-xs leading-relaxed">
            &ldquo;{latestCommentary.text}&rdquo;
          </p>
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono pt-1">
            <span>Location: {latestCommentary.region}</span>
            <span>Target: {latestCommentary.target}</span>
          </div>
        </div>
      )}

      {/* Chronological Commentary Log */}
      <div className="flex-1 overflow-y-auto space-y-2 max-h-72 pr-1 text-xs">
        {allItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-2">
            <Mic className="w-8 h-8 stroke-[1.5] text-slate-600 animate-pulse" />
            <p className="text-xs font-medium text-slate-400">Observing scene activity...</p>
            <p className="text-[11px] text-slate-500 max-w-xs">
              Commentary will trigger automatically when people talk, move away, enter, or handle devices.
            </p>
          </div>
        ) : (
          allItems.map((item) => (
            <div
              key={item.id}
              className="p-2.5 rounded-xl bg-slate-950/50 border border-slate-800/80 hover:border-cyan-500/30 transition-colors flex flex-col space-y-1"
            >
              <div className="flex items-center justify-between">
                {getActionBadge(item.action_type)}
                <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5 text-slate-500" />
                  {new Date(item.timestamp * 1000).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
              </div>
              <p className="text-slate-200 text-xs font-medium">
                {item.text}
              </p>
              <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                <span className="capitalize">{item.region}</span>
                <span>{item.target}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
