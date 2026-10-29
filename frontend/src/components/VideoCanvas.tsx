"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Sliders, Eye, EyeOff, Camera, Laptop, Radio, AlertCircle, RefreshCw } from "lucide-react";
import { DetectionItem } from "@/types/telemetry";

interface VideoCanvasProps {
  frameImage: string | null;
  detections: DetectionItem[];
  latencyMs: number;
  frameIndex: number;
}

const BACKEND_INGEST_URL = process.env.NEXT_PUBLIC_INGEST_URL || "http://localhost:8000/api/v1/telemetry/frame";

export const VideoCanvas: React.FC<VideoCanvasProps> = ({
  frameImage,
  detections,
  latencyMs,
  frameIndex,
}) => {
  // Default to in-browser webcam mode so webcam opens directly inside the website
  const [sourceMode, setSourceMode] = useState<"remote" | "webcam">("webcam");
  const [minConfidence, setMinConfidence] = useState<number>(0.35);
  const [showOverlays, setShowOverlays] = useState<boolean>(true);
  const [webcamError, setWebcamError] = useState<string | null>(null);
  const [webcamFps, setWebcamFps] = useState<number>(8); // 8 FPS for smooth balance of low latency & light CPU
  const [videoAspectRatio, setVideoAspectRatio] = useState<string>("16 / 9");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const captureIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hiddenCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const webcamFrameIndexRef = useRef<number>(0);
  const isSendingRef = useRef<boolean>(false);

  // Stop local camera stream
  const stopWebcam = useCallback(() => {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsStreaming(false);
    setWebcamError(null);
  }, []);

  // Frame transmitter for browser webcam -> FastAPI Backend
  const captureAndSendWebcamFrame = useCallback(async () => {
    if (!videoRef.current || videoRef.current.readyState < 2) return;
    if (isSendingRef.current) return; // Prevent concurrent request backlog

    const video = videoRef.current;
    let canvas = hiddenCanvasRef.current;
    if (!canvas) {
      canvas = document.createElement("canvas");
      hiddenCanvasRef.current = canvas;
    }

    // Scale to standard 800px width for fast local transmission & low YOLO latency
    const targetWidth = Math.min(video.videoWidth || 800, 800);
    const scale = targetWidth / (video.videoWidth || 800);
    const targetHeight = Math.round((video.videoHeight || 600) * scale);

    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    isSendingRef.current = true;
    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          isSendingRef.current = false;
          return;
        }
        webcamFrameIndexRef.current += 1;
        try {
          await fetch(BACKEND_INGEST_URL, {
            method: "POST",
            headers: {
              "Content-Type": "image/jpeg",
              "X-Device-Id": "laptop_webcam_browser",
              "X-Frame-Index": webcamFrameIndexRef.current.toString(),
              "X-Timestamp-Ms": Date.now().toString(),
            },
            body: blob,
          });
        } catch (err) {
          console.debug("Webcam frame upload failed (Backend offline?):", err);
        } finally {
          isSendingRef.current = false;
        }
      },
      "image/jpeg",
      0.82
    );
  }, []);

  // Start local camera stream
  const startWebcam = useCallback(async () => {
    stopWebcam();
    try {
      setWebcamError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user",
        },
        audio: false,
      });

      mediaStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsStreaming(true);

      // Schedule periodic snapshot transmission
      const intervalMs = Math.round(1000 / webcamFps);
      captureIntervalRef.current = setInterval(captureAndSendWebcamFrame, intervalMs);
    } catch (err: any) {
      console.error("Failed to access laptop webcam:", err);
      setIsStreaming(false);
      setWebcamError(
        err.name === "NotAllowedError" || err.name === "PermissionDeniedError"
          ? "Camera permission denied by browser. Please allow camera access in your browser bar."
          : `Unable to access webcam: ${err.message || "Device may be in use by another program"}`
      );
    }
  }, [stopWebcam, webcamFps, captureAndSendWebcamFrame]);

  // Handle source mode change or FPS change
  useEffect(() => {
    if (sourceMode === "webcam") {
      startWebcam();
    } else {
      stopWebcam();
    }

    return () => {
      stopWebcam();
    };
  }, [sourceMode, startWebcam, stopWebcam]);

  // Update dynamic aspect ratio when video metadata arrives
  const handleLoadedMetadata = () => {
    if (videoRef.current && videoRef.current.videoWidth && videoRef.current.videoHeight) {
      setVideoAspectRatio(`${videoRef.current.videoWidth} / ${videoRef.current.videoHeight}`);
    }
  };

  // Filter detections based on confidence threshold
  const visibleDetections = detections.filter((d) => d.confidence >= minConfidence);

  return (
    <div className="flex flex-col bg-lab-850 rounded-xl border border-lab-700 overflow-hidden shadow-xl">
      {/* Viewport Top Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-lab-800/80 border-b border-lab-700 gap-2">
        <div className="flex items-center gap-3">
          {/* Source Selector Tabs */}
          <div className="inline-flex rounded-lg bg-lab-900/90 p-0.5 border border-lab-700 text-xs">
            <button
              onClick={() => setSourceMode("webcam")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-colors ${
                sourceMode === "webcam"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Laptop className="w-3.5 h-3.5 text-cyan-400" />
              Laptop Camera (In-Website)
            </button>
            <button
              onClick={() => setSourceMode("remote")}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-colors ${
                sourceMode === "remote"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Radio className="w-3.5 h-3.5 text-emerald-400" />
              ESP32 / Remote Stream
            </button>
          </div>

          <span className="font-mono text-slate-400 text-[11px] hidden sm:inline">
            [Frame #{sourceMode === "webcam" ? webcamFrameIndexRef.current : frameIndex}]
          </span>
        </div>

        {/* Viewport Controls */}
        <div className="flex items-center gap-3">
          {/* FPS Selector for Webcam */}
          {sourceMode === "webcam" && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <span className="hidden md:inline text-[11px]">Rate:</span>
              <select
                value={webcamFps}
                onChange={(e) => setWebcamFps(Number(e.target.value))}
                className="bg-lab-900 border border-lab-700 text-cyan-300 rounded px-1.5 py-0.5 text-xs focus:outline-none"
              >
                <option value={5}>5 FPS</option>
                <option value={8}>8 FPS</option>
                <option value={12}>12 FPS</option>
              </select>
            </div>
          )}

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
              className="w-20 accent-cyan-500 h-1 bg-lab-700 rounded-lg cursor-pointer"
            />
            <span className="font-mono text-slate-200 w-8">{Math.round(minConfidence * 100)}%</span>
          </div>

          {/* Toggle Overlay Button */}
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            title={showOverlays ? "Hide Bounding Boxes" : "Show Bounding Boxes"}
            className="p-1.5 rounded bg-lab-700 hover:bg-lab-600 text-slate-300 transition-colors"
          >
            {showOverlays ? <Eye className="w-3.5 h-3.5 text-cyan-400" /> : <EyeOff className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Main Stream Viewport */}
      <div className="relative aspect-video w-full bg-slate-950 flex items-center justify-center overflow-hidden">
        {/* WEBCAM SOURCE MODE */}
        {sourceMode === "webcam" && (
          <div className="relative w-full h-full flex items-center justify-center">
            {webcamError ? (
              <div className="flex flex-col items-center gap-3 text-rose-400 p-6 text-center max-w-md">
                <AlertCircle className="w-10 h-10 stroke-[1.5]" />
                <p className="text-sm font-semibold text-rose-300">{webcamError}</p>
                <button
                  onClick={startWebcam}
                  className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 bg-rose-500/20 border border-rose-500/40 rounded text-xs hover:bg-rose-500/30 text-rose-200 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Retry Camera
                </button>
              </div>
            ) : (
              <div
                className="relative max-w-full max-h-full flex items-center justify-center"
                style={{ aspectRatio: videoAspectRatio }}
              >
                <video
                  ref={videoRef}
                  onLoadedMetadata={handleLoadedMetadata}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-contain select-none block"
                />

                {/* Real-time Dynamic SVG Bounding Box Overlays */}
                {showOverlays && (
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    {visibleDetections.map((det, idx) => {
                      if (!det.normalized_box) return null;
                      const [nx1, ny1, nx2, ny2] = det.normalized_box;
                      const x = `${nx1 * 100}%`;
                      const y = `${ny1 * 100}%`;
                      const width = `${Math.max((nx2 - nx1) * 100, 0)}%`;
                      const height = `${Math.max((ny2 - ny1) * 100, 0)}%`;
                      const isNearTop = ny1 < 0.08;

                      return (
                        <g key={idx}>
                          {/* Bounding Box Rectangle */}
                          <rect
                            x={x}
                            y={y}
                            width={width}
                            height={height}
                            fill="rgba(6, 182, 212, 0.14)"
                            stroke="#06b6d4"
                            strokeWidth="2.5"
                            rx="3"
                          />
                          {/* Label Badge */}
                          <rect
                            x={x}
                            y={isNearTop ? `calc(${y} + 4px)` : `calc(${y} - 20px)`}
                            width={`${Math.min(det.class_name.length * 8 + 48, 180)}px`}
                            height="18"
                            fill="#06b6d4"
                            rx="3"
                          />
                          <text
                            x={`calc(${x} + 4px)`}
                            y={isNearTop ? `calc(${y} + 17px)` : `calc(${y} - 7px)`}
                            fill="#082f49"
                            fontSize="10.5"
                            fontFamily="monospace"
                            fontWeight="bold"
                          >
                            {det.class_name} {Math.round(det.confidence * 100)}%
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>
            )}
          </div>
        )}

        {/* REMOTE / ESP32 SOURCE MODE */}
        {sourceMode === "remote" && (
          <>
            {frameImage ? (
              <div className="relative w-full h-full">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={frameImage}
                  alt="Live Camera Feed"
                  className="w-full h-full object-contain select-none"
                />

                {showOverlays && (
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    {visibleDetections.map((det, idx) => {
                      if (!det.normalized_box) return null;
                      const [nx1, ny1, nx2, ny2] = det.normalized_box;
                      const x = `${nx1 * 100}%`;
                      const y = `${ny1 * 100}%`;
                      const width = `${Math.max((nx2 - nx1) * 100, 0)}%`;
                      const height = `${Math.max((ny2 - ny1) * 100, 0)}%`;

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
                            rx="3"
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
                <div className="text-xs text-slate-500 max-w-sm space-y-2">
                  <p>
                    Streaming from physical ESP32 or external stream.
                  </p>
                  <p className="pt-2">
                    <span className="text-slate-400 font-semibold">Tip:</span> Switch back to{" "}
                    <button
                      onClick={() => setSourceMode("webcam")}
                      className="text-cyan-400 underline font-semibold hover:text-cyan-300"
                    >
                      Laptop Camera (In-Website)
                    </button>{" "}
                    to view your webcam directly!
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {/* Floating In-Stream Telemetry Pill */}
        {(frameImage || isStreaming) && (
          <div className="absolute bottom-3 left-3 px-2.5 py-1 rounded bg-black/80 backdrop-blur border border-white/10 text-[11px] font-mono text-emerald-400 flex items-center gap-2 z-10">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                sourceMode === "webcam" ? "bg-cyan-400 animate-pulse" : "bg-emerald-400 animate-ping"
              }`}
            />
            <span className={sourceMode === "webcam" ? "text-cyan-400" : "text-emerald-400"}>
              SOURCE: {sourceMode === "webcam" ? "LAPTOP WEBCAM (IN-WEBSITE)" : "REMOTE/ESP32"}
            </span>
            <span className="text-slate-500">|</span>
            <span>INFER: {latencyMs}ms</span>
            <span className="text-slate-500">|</span>
            <span>OBJECTS: {visibleDetections.length}</span>
          </div>
        )}
      </div>
    </div>
  );
};
