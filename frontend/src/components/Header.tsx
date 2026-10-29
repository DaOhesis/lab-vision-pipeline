"use client";

import React from "react";
import { Sparkles, Activity, RefreshCw, Zap } from "lucide-react";
import { ConnectionStatus } from "@/types/telemetry";

interface HeaderProps {
  status: ConnectionStatus;
  fps: number;
  latencyMs: number;
  deviceId?: string;
  onReconnect: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  fps,
  latencyMs,
  onReconnect,
}) => {
  return (
    <header className="sticky top-0 z-40 w-full bg-slate-950/85 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-8 py-3.5 flex items-center justify-between transition-all">
      {/* Brand & Title */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-500/20 via-sky-500/10 to-emerald-500/20 text-cyan-400 border border-cyan-500/30 shadow-inner">
          <Sparkles className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-lg font-bold text-white tracking-tight">
              Vision AI
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold tracking-wide">
              YOLO11 LIVE
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            Real-time Edge Vision Intelligence & Live Telemetry
          </p>
        </div>
      </div>

      {/* Real-time Telemetry Stats & Status */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Inference Latency */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs shadow-sm">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-400 hidden md:inline">Latency:</span>
          <span className="font-mono font-semibold text-slate-200">
            {latencyMs > 0 ? `${latencyMs}ms` : "--"}
          </span>
        </div>

        {/* Frame Rate */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs shadow-sm">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-slate-400 hidden md:inline">Rate:</span>
          <span className="font-mono font-semibold text-slate-200">{fps} FPS</span>
        </div>

        {/* Connection Status Badge */}
        {status === "connected" && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>ONLINE</span>
          </div>
        )}

        {status === "connecting" && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 font-mono">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-spin" />
            <span>CONNECTING</span>
          </div>
        )}

        {(status === "error" || status === "disconnected") && (
          <button
            onClick={onReconnect}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20 transition-colors font-mono"
          >
            <RefreshCw className="w-3 h-3" />
            <span>RECONNECT</span>
          </button>
        )}
      </div>
    </header>
  );
};
