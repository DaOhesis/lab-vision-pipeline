"use client";

import React from "react";
import { Activity, Radio, Cpu, RefreshCw } from "lucide-react";
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
  deviceId = "esp32_cam_lab_01",
  onReconnect,
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case "connected":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            LIVE STREAM
          </span>
        );
      case "connecting":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-spin" />
            CONNECTING...
          </span>
        );
      case "error":
      case "disconnected":
        return (
          <button
            onClick={onReconnect}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            RECONNECT
          </button>
        );
    }
  };

  return (
    <header className="w-full bg-lab-850/90 backdrop-blur border-b border-lab-700 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Radio className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
            IoT Lab Vision Intelligence
            <span className="text-xs font-normal px-2 py-0.5 rounded bg-lab-700 text-slate-400">v1.0</span>
          </h1>
          <p className="text-xs text-slate-400 flex items-center gap-1">
            <Cpu className="w-3 h-3 text-slate-500" />
            Node: <span className="font-mono text-slate-300">{deviceId}</span>
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Latency Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-lab-800 border border-lab-700 text-xs">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-400">Inference:</span>
          <span className="font-mono font-semibold text-slate-200">
            {latencyMs > 0 ? `${latencyMs}ms` : "--"}
          </span>
        </div>

        {/* FPS Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-lab-800 border border-lab-700 text-xs">
          <span className="text-slate-400">Rate:</span>
          <span className="font-mono font-semibold text-slate-200">{fps} FPS</span>
        </div>

        {/* Live Status Badge */}
        {getStatusBadge()}
      </div>
    </header>
  );
};
