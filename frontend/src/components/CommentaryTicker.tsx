"use client";

import React from "react";
import { Mic, Activity, Clock, Sparkles } from "lucide-react";
import { LiveCommentaryItem } from "@/types/telemetry";

interface CommentaryTickerProps {
  commentaryFeed: LiveCommentaryItem[];
  latestCommentary?: LiveCommentaryItem | null;
}

export const CommentaryTicker: React.FC<CommentaryTickerProps> = ({
  commentaryFeed,
  latestCommentary,
}) => {
  const getActionBadge = (actionType: string) => {
    switch (actionType) {
      case "picked_up":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">PICKED UP</span>;
      case "placed_down":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">SET DOWN</span>;
      case "person_entered":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">ENTERED</span>;
      case "person_left":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-700 text-slate-400">LEFT</span>;
      case "equipment_interaction":
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-400 border border-purple-500/30">LAB WORK</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-sky-500/20 text-sky-400 border border-sky-500/30">ACTION</span>;
    }
  };

  return (
    <div className="bg-lab-850 rounded-xl border border-lab-700 p-4 flex flex-col h-full shadow-lg space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-lab-700">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Mic className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              Live Stream Commentary
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-950 text-rose-400 border border-rose-800">
                AI Narrator
              </span>
            </h3>
          </div>
        </div>

        <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
          <Activity className="w-3 h-3 text-emerald-400" />
          Active
        </span>
      </div>

      {/* Latest Highlight Banner */}
      {latestCommentary && (
        <div className="p-3 rounded-lg bg-slate-900 border border-cyan-500/30 shadow-md text-xs space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-cyan-400 flex items-center gap-1 text-[11px]">
              <Sparkles className="w-3 h-3" />
              Latest Action Narration
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
        {commentaryFeed.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center text-slate-500 space-y-2">
            <Mic className="w-8 h-8 stroke-[1.5] text-slate-600 animate-pulse" />
            <p className="text-xs font-medium text-slate-400">Waiting for scene action events...</p>
            <p className="text-[11px] text-slate-500 max-w-xs">
              Pick up an item, walk into frame, or move equipment to trigger live AI commentary.
            </p>
          </div>
        ) : (
          commentaryFeed.map((item) => (
            <div
              key={item.id}
              className="p-2.5 rounded-lg bg-lab-800/80 border border-lab-700/80 hover:border-cyan-500/30 transition-colors flex flex-col space-y-1"
            >
              <div className="flex items-center justify-between">
                {getActionBadge(item.action_type)}
                <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5 text-slate-500" />
                  {new Date(item.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-slate-200 text-xs font-medium">
                {item.text}
              </p>
              <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                <span>{item.region}</span>
                <span>{item.model_used || "Qwen 2.5"}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
