"use client";

import React, { useState } from "react";
import { useLabStream } from "@/hooks/useLabStream";
import { Header } from "@/components/Header";
import { VideoCanvas } from "@/components/VideoCanvas";
import { DetectionFeed } from "@/components/DetectionFeed";
import { LabAssistant } from "@/components/LabAssistant";
import { CommentaryTicker } from "@/components/CommentaryTicker";
import { ProjectIdeator } from "@/components/ProjectIdeator";
import { ListFilter, Bot, Eye, Layers, Mic, Wrench } from "lucide-react";

export default function DashboardPage() {
  const { status, telemetry, frameImage, fps, latestCommentary, commentaryFeed, reconnect } = useLabStream();
  const [activeSideTab, setActiveSideTab] = useState<"narrator" | "builder" | "audit" | "copilot">("builder");
  const [queuedQuestion, setQueuedQuestion] = useState<string | null>(null);

  const detections = telemetry?.detections || [];
  const latencyMs = telemetry?.inference_latency_ms || 0;
  const frameIndex = telemetry?.frame_index || 0;
  const deviceId = telemetry?.device_id || "esp32_cam_lab_01";

  // Calculate dynamic tally of currently detected objects (only what is actually visible!)
  const dynamicCounts: Record<string, number> = {};
  for (const det of detections) {
    const name = det.class_name.replace(/_/g, " ");
    dynamicCounts[name] = (dynamicCounts[name] || 0) + 1;
  }
  const uniqueItems = Object.entries(dynamicCounts);

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation Bar */}
      <Header
        status={status}
        fps={fps}
        latencyMs={latencyMs}
        deviceId={deviceId}
        onReconnect={reconnect}
      />

      {/* Main Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-5">
        {/* Dynamic Scene Overview Strip */}
        <section className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800/80 px-4 py-3 flex flex-wrap items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
              <Eye className="w-4 h-4 text-cyan-400" />
              <span>Visible in Scene:</span>
            </div>

            {uniqueItems.length === 0 ? (
              <span className="text-xs text-slate-500 font-mono italic">
                No objects in frame · Scanning scene...
              </span>
            ) : (
              <div className="flex items-center gap-1.5 flex-wrap">
                {uniqueItems.map(([name, count]) => (
                  <span
                    key={name}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 text-xs font-medium capitalize"
                  >
                    <span>{name}</span>
                    <span className="px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-cyan-200 text-[10px] font-mono font-bold">
                      {count}
                    </span>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span className="px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700/60">
              Total: <strong className="text-cyan-400 font-semibold">{detections.length}</strong>
            </span>
          </div>
        </section>

        {/* Viewport & Real-Time Analytics Grid */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Main Visual Stream Viewport (8 Columns) */}
          <div className="lg:col-span-8">
            <VideoCanvas
              frameImage={frameImage}
              detections={detections}
              latencyMs={latencyMs}
              frameIndex={frameIndex}
              latestCommentary={latestCommentary}
            />
          </div>

          {/* Right Panel: Side Tab Switcher (4 Columns) */}
          <div className="lg:col-span-4 flex flex-col space-y-3">
            {/* Tab Selector */}
            <div className="grid grid-cols-4 rounded-xl bg-slate-900/90 p-1 border border-slate-800 text-xs shadow-md gap-1">
              <button
                onClick={() => setActiveSideTab("builder")}
                className={`inline-flex items-center justify-center gap-1 py-2 rounded-lg font-medium transition-all ${
                  activeSideTab === "builder"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-sm font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Wrench className="w-3.5 h-3.5 text-emerald-400" />
                <span className="truncate">Builder</span>
              </button>
              <button
                onClick={() => setActiveSideTab("narrator")}
                className={`inline-flex items-center justify-center gap-1 py-2 rounded-lg font-medium transition-all ${
                  activeSideTab === "narrator"
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/30 shadow-sm font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Mic className="w-3.5 h-3.5 text-rose-400" />
                <span className="truncate">Narrator</span>
              </button>
              <button
                onClick={() => setActiveSideTab("audit")}
                className={`inline-flex items-center justify-center gap-1 py-2 rounded-lg font-medium transition-all ${
                  activeSideTab === "audit"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ListFilter className="w-3.5 h-3.5 text-cyan-400" />
                <span className="truncate">Objects</span>
              </button>
              <button
                onClick={() => setActiveSideTab("copilot")}
                className={`inline-flex items-center justify-center gap-1 py-2 rounded-lg font-medium transition-all ${
                  activeSideTab === "copilot"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-sm font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Bot className="w-3.5 h-3.5 text-cyan-400" />
                <span className="truncate">AI Chat</span>
              </button>
            </div>

            {/* Active Panel View */}
            <div className="h-[650px]">
              {activeSideTab === "builder" ? (
                <ProjectIdeator
                  detections={detections}
                  onAskCopilot={(q) => {
                    setQueuedQuestion(q);
                    setActiveSideTab("copilot");
                  }}
                />
              ) : activeSideTab === "narrator" ? (
                <CommentaryTicker
                  commentaryFeed={commentaryFeed}
                  latestCommentary={latestCommentary}
                />
              ) : activeSideTab === "audit" ? (
                <DetectionFeed
                  detections={detections}
                  timestampMs={telemetry?.timestamp_ms}
                />
              ) : (
                <LabAssistant
                  queuedQuestion={queuedQuestion}
                  onQuestionHandled={() => setQueuedQuestion(null)}
                />
              )}
            </div>
          </div>
        </section>
      </main>

      {/* Dashboard Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950/60 py-4 px-6 text-center text-xs text-slate-500">
        Vision AI Studio &bull; Real-time Edge Computer Vision &bull; Next.js 14 &bull; FastAPI &bull; YOLO11
      </footer>
    </div>
  );
}
