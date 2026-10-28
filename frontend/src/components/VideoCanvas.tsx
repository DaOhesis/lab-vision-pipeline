"use client";

import React, { useState } from "react";
import { Maximize2, Sliders, Eye, EyeOff, Camera } from "lucide-react";
import { DetectionItem } from "@/types/telemetry";

interface VideoCanvasProps {
  frameImage: string | null;
  detections: DetectionItem[];
  latencyMs: number;
  frameIndex: number;
}

const CLASS_COLORS: Record<string, { border: string; bg: string; text: string }> = {
  "3d_printer": { border: "border-emerald-500", bg: "bg-emerald-500/20", text: "text-emerald-400" },
  "dell_monitor": { border: "border-sky-500", bg: "bg-sky-500/20", text: "text-sky-400" },
  "microcontroller": { border: "border-amber-500", bg: "bg-amber-500/20", text: "text-amber-400" },
  "oscilloscope": { border: "border-purple-500", bg: "bg-purple-500/20", text: "text-purple-400" },
  "soldering_station": { border: "border-rose-500", bg: "bg-rose-500/20", text: "text-rose-400" },
};

export const VideoCanvas: React.FC<VideoCanvasProps> = ({
  frameImage,
  detections,
  latencyMs,
  frameIndex,
}) => {
  const [minConfidence, setMinConfidence] = useState<number>(0.35);
  const [showOverlays, setShowOverlays] = useState<boolean>(true);

  // Filter detections based on confidence threshold
  const visibleDetections = detections.filter((d) => d.confidence >= minConfidence);

  return (
    <div className="flex flex-col bg-lab-850 rounded-xl border border-lab-700 overflow-hidden shadow-xl">
      {/* Viewport Top Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-lab-800/80 border-b border-lab-700">
        <div className="flex items-center gap-2 text-xs text-slate-300">
          <Camera className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold uppercase tracking-wider text-slate-200">
            ESP32-CAM Viewport
          </span>
          <span className="font-mono text-slate-400 text-[11px]">
            [Frame #{frameIndex}]
          </span>
        </div>

        {/* Viewport Controls */}
        <div className="flex items-center gap-3">
          {/* Confidence Slider */}
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-400">
            <Sliders className="w-3.5 h-3.5" />
            <span>Min Conf:</span>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              className="w-20 accent-emerald-500 h-1 bg-lab-700 rounded-lg cursor-pointer"
            />
            <span className="font-mono text-slate-200 w-8">{Math.round(minConfidence * 100)}%</span>
          </div>

          {/* Toggle Overlay Button */}
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            title={showOverlays ? "Hide Bounding Boxes" : "Show Bounding Boxes"}
            className="p-1.5 rounded bg-lab-700 hover:bg-lab-600 text-slate-300 transition-colors"
          >
            {showOverlays ? <Eye className="w-3.5 h-3.5 text-emerald-400" /> : <EyeOff className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Main Stream Area */}
      <div className="relative aspect-[4/3] sm:aspect-[16/10] bg-slate-950 flex items-center justify-center overflow-hidden">
        {frameImage ? (
          <div className="relative w-full h-full">
            {/* The JPEG Frame */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={frameImage}
              alt="ESP32 Live Feed"
              className="w-full h-full object-contain select-none"
            />

            {/* Interactive Client-Side Dynamic Bounding Box Overlay */}
            {showOverlays && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                {visibleDetections.map((det, idx) => {
                  if (!det.normalized_box) return null;
                  const [nx1, ny1, nx2, ny2] = det.normalized_box;
                  const x = `${nx1 * 100}%`;
                  const y = `${ny1 * 100}%`;
                  const width = `${(nx2 - nx1) * 100}%`;
                  const height = `${(ny2 - ny1) * 100}%`;

                  const colorInfo = CLASS_COLORS[det.class_name] || {
                    border: "border-emerald-500",
                    bg: "bg-emerald-500/20",
                    text: "text-emerald-400",
                  };

                  return (
                    <g key={idx}>
                      <rect
                        x={x}
                        y={y}
                        width={width}
                        height={height}
                        fill="rgba(16, 185, 129, 0.08)"
                        stroke="#10b981"
                        strokeWidth="2"
                        strokeDasharray="4 2"
                      />
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-slate-500 p-8 text-center">
            <Camera className="w-12 h-12 stroke-[1.5] animate-pulse text-slate-600" />
            <p className="text-sm font-medium text-slate-400">Waiting for incoming frame stream...</p>
            <p className="text-xs text-slate-600 max-w-sm">
              Verify that the ESP32-CAM or camera simulator is streaming to{" "}
              <code className="text-emerald-400 font-mono">POST /api/v1/telemetry/frame</code>
            </p>
          </div>
        )}

        {/* Floating In-Stream Telemetry Pill */}
        {frameImage && (
          <div className="absolute bottom-3 left-3 px-2.5 py-1 rounded bg-black/75 backdrop-blur border border-white/10 text-[11px] font-mono text-emerald-400 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span>INFER: {latencyMs}ms</span>
            <span className="text-slate-500">|</span>
            <span>OBJECTS: {visibleDetections.length}</span>
          </div>
        )}
      </div>
    </div>
  );
};
