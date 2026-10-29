"use client";

import React, { useState } from "react";
import { useLabStream } from "@/hooks/useLabStream";
import { Header } from "@/components/Header";
import { VideoCanvas } from "@/components/VideoCanvas";
import { InventoryCards } from "@/components/InventoryCards";
import { DetectionFeed } from "@/components/DetectionFeed";
import { LabAssistant } from "@/components/LabAssistant";
import { ListFilter, Bot } from "lucide-react";

export default function DashboardPage() {
  const { status, telemetry, frameImage, fps, reconnect } = useLabStream();
  const [activeSideTab, setActiveSideTab] = useState<"copilot" | "audit">("copilot");

  const detections = telemetry?.detections || [];
  const equipmentCounts = telemetry?.equipment_counts || {};
  const totalActive = telemetry?.total_detections || 0;
  const latencyMs = telemetry?.inference_latency_ms || 0;
  const frameIndex = telemetry?.frame_index || 0;
  const deviceId = telemetry?.device_id || "esp32_cam_lab_01";

  return (
    <div className="flex flex-col min-h-screen">
      {/* Top Navigation & Status Bar */}
      <Header
        status={status}
        fps={fps}
        latencyMs={latencyMs}
        deviceId={deviceId}
        onReconnect={reconnect}
      />

      {/* Main Dashboard Grid */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Inventory Summary Metrics */}
        <section>
          <InventoryCards
            equipmentCounts={equipmentCounts}
            totalActive={totalActive}
          />
        </section>

        {/* Viewport & Real-Time Event Audit Grid */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Main Visual Stream Viewport */}
          <div className="lg:col-span-2">
            <VideoCanvas
              frameImage={frameImage}
              detections={detections}
              latencyMs={latencyMs}
              frameIndex={frameIndex}
            />
          </div>

          {/* Right Panel: Side Tab Switcher (AI Copilot vs Audit Log) */}
          <div className="lg:col-span-1 flex flex-col space-y-3">
            {/* Tab Selector */}
            <div className="flex rounded-lg bg-lab-850 p-1 border border-lab-700 text-xs">
              <button
                onClick={() => setActiveSideTab("copilot")}
                className={`flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-colors ${
                  activeSideTab === "copilot"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Bot className="w-3.5 h-3.5" />
                Lab AI Copilot
              </button>
              <button
                onClick={() => setActiveSideTab("audit")}
                className={`flex-1 inline-flex items-center justify-center gap-1.5 py-1.5 rounded-md font-medium transition-colors ${
                  activeSideTab === "audit"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <ListFilter className="w-3.5 h-3.5" />
                Audit Stream ({detections.length})
              </button>
            </div>

            {/* Active Panel View */}
            <div className="h-[490px]">
              {activeSideTab === "copilot" ? (
                <LabAssistant />
              ) : (
                <DetectionFeed
                  detections={detections}
                  timestampMs={telemetry?.timestamp_ms}
                />
              )}
            </div>
          </div>
        </section>
      </main>

      {/* Dashboard Footer */}
      <footer className="border-t border-lab-700/60 bg-lab-900/60 py-3 px-6 text-center text-xs text-slate-500">
        IoT Lab Vision Intelligence System &bull; Local Pipeline &bull; ESP32-CAM &bull; FastAPI &bull; YOLO11 &bull; Qwen 2.5 SLM &bull; Next.js
      </footer>
    </div>
  );
}
