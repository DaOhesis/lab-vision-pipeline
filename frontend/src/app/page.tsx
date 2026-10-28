"use client";

import React from "react";
import { useLabStream } from "@/hooks/useLabStream";
import { Header } from "@/components/Header";
import { VideoCanvas } from "@/components/VideoCanvas";
import { InventoryCards } from "@/components/InventoryCards";
import { DetectionFeed } from "@/components/DetectionFeed";

export default function DashboardPage() {
  const { status, telemetry, frameImage, fps, reconnect } = useLabStream();

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

          {/* Chronological Detection Event Log */}
          <div className="lg:col-span-1 h-full">
            <DetectionFeed
              detections={detections}
              timestampMs={telemetry?.timestamp_ms}
            />
          </div>
        </section>
      </main>

      {/* Dashboard Footer */}
      <footer className="border-t border-lab-700/60 bg-lab-900/60 py-3 px-6 text-center text-xs text-slate-500">
        IoT Lab Vision Intelligence System &bull; Local Pipeline &bull; ESP32-CAM &bull; FastAPI &bull; YOLO11 &bull; Next.js
      </footer>
    </div>
  );
}
