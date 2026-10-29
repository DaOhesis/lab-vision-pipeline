"use client";

import React from "react";
import {
  ListFilter,
  User,
  Monitor,
  Smartphone,
  Mouse,
  Keyboard,
  Coffee,
  Package,
  Layers,
  Sparkles
} from "lucide-react";
import { DetectionItem } from "@/types/telemetry";

interface DetectionFeedProps {
  detections: DetectionItem[];
  timestampMs?: number;
}

const getClassIcon = (className: string) => {
  const name = className.toLowerCase();
  if (name.includes("person")) return User;
  if (name.includes("monitor") || name.includes("tv") || name.includes("laptop")) return Monitor;
  if (name.includes("phone")) return Smartphone;
  if (name.includes("mouse")) return Mouse;
  if (name.includes("keyboard")) return Keyboard;
  if (name.includes("cup") || name.includes("bottle")) return Coffee;
  return Package;
};

export const DetectionFeed: React.FC<DetectionFeedProps> = ({
  detections,
}) => {
  return (
    <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-4 flex flex-col h-full shadow-xl backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <ListFilter className="w-4 h-4 text-cyan-400" />
          Live Detections
        </h3>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-cyan-300 font-semibold border border-slate-700/60">
          {detections.length} Active
        </span>
      </div>

      {/* Detections List */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 max-h-[420px]">
        {detections.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <div className="p-3 rounded-2xl bg-slate-800/50 border border-slate-700/40 mb-3 text-slate-400 animate-pulse">
              <Layers className="w-6 h-6 stroke-[1.5]" />
            </div>
            <p className="text-xs font-medium text-slate-400">Scanning scene for objects...</p>
            <p className="text-[11px] text-slate-600 mt-1 max-w-[200px]">
              Point your camera at everyday items, people, monitors, or phones
            </p>
          </div>
        ) : (
          detections.map((item, idx) => {
            const confPct = Math.round(item.confidence * 100);
            const Icon = getClassIcon(item.class_name);
            const displayName = item.class_name.replace(/_/g, " ");

            return (
              <div
                key={idx}
                className="group flex flex-col p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-cyan-500/40 transition-all shadow-sm"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-slate-200 capitalize tracking-tight">
                        {displayName}
                      </span>
                      <p className="text-[10px] font-mono text-slate-500">
                        Box: [{item.box.map((v) => Math.round(v)).join(", ")}]
                      </p>
                    </div>
                  </div>

                  <span
                    className={`text-xs font-mono font-bold px-2 py-0.5 rounded-md ${
                      confPct >= 80
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                        : confPct >= 50
                        ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/20"
                        : "bg-amber-500/15 text-amber-400 border border-amber-500/20"
                    }`}
                  >
                    {confPct}%
                  </span>
                </div>

                {/* Confidence Bar */}
                <div className="w-full bg-slate-850 h-1.5 rounded-full overflow-hidden mt-1 border border-slate-800">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      confPct >= 80
                        ? "bg-emerald-400"
                        : confPct >= 50
                        ? "bg-cyan-400"
                        : "bg-amber-400"
                    }`}
                    style={{ width: `${confPct}%` }}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
