"use client";

import React from "react";
import { ListFilter, Box, CheckCircle2 } from "lucide-react";
import { DetectionItem } from "@/types/telemetry";

interface DetectionFeedProps {
  detections: DetectionItem[];
  timestampMs?: number;
}

export const DetectionFeed: React.FC<DetectionFeedProps> = ({
  detections,
  timestampMs,
}) => {
  return (
    <div className="bg-lab-850 rounded-xl border border-lab-700 p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-lab-700 mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <ListFilter className="w-4 h-4 text-cyan-400" />
          Detection Audit Stream
        </h3>
        <span className="text-[11px] font-mono text-slate-500">
          {detections.length} objects localized
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 max-h-80 pr-1">
        {detections.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            No equipment localized in current scene.
          </div>
        ) : (
          detections.map((item, idx) => {
            const confPct = Math.round(item.confidence * 100);
            return (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 rounded-lg bg-lab-800/80 border border-lab-700/70 hover:border-emerald-500/40 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1 rounded bg-emerald-500/10 text-emerald-400">
                    <Box className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span className="text-xs font-medium text-slate-200 capitalize">
                      {item.class_name.replace("_", " ")}
                    </span>
                    <p className="text-[10px] font-mono text-slate-400">
                      [{item.box.map((v) => Math.round(v)).join(", ")}]
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                      confPct >= 80
                        ? "bg-emerald-500/20 text-emerald-400"
                        : confPct >= 50
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-slate-700 text-slate-300"
                    }`}
                  >
                    {confPct}%
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
