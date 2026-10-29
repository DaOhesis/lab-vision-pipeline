"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Sliders, Eye, EyeOff, Camera, Laptop, Radio, AlertCircle, RefreshCw, Cpu, Mic } from "lucide-react";
import { DetectionItem, LiveCommentaryItem } from "@/types/telemetry";

interface VideoCanvasProps {
  frameImage: string | null;
  detections: DetectionItem[];
  latencyMs: number;
  frameIndex: number;
  latestCommentary?: LiveCommentaryItem | null;
}

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const BACKEND_INGEST_URL = `${BACKEND_BASE_URL}/api/v1/telemetry/frame`;

export const VideoCanvas: React.FC<VideoCanvasProps> = ({
  frameImage,
  detections,
  latencyMs,
  frameIndex,
  latestCommentary,
}) => {
  // Default to in-browser webcam mode so webcam opens directly inside the website
  const [sourceMode, setSourceMode] = useState<"remote" | "webcam">("webcam");
  const [minConfidence, setMinConfidence] = useState<number>(0.45);
  const [showOverlays, setShowOverlays] = useState<boolean>(true);
  const [showCommentary, setShowCommentary] = useState<boolean>(true);
  const [activeBanner, setActiveBanner] = useState<LiveCommentaryItem | null>(null);
  const [webcamError, setWebcamError] = useState<string | null>(null);
  const [webcamFps, setWebcamFps] = useState<number>(8); // 8 FPS for smooth balance of low latency & light CPU
  const [videoAspectRatio, setVideoAspectRatio] = useState<string>("16 / 9");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>("yolo11s.pt");
  const [isSwitchingModel, setIsSwitchingModel] = useState<boolean>(false);

  // Auto-dismiss or refresh live commentary banner
  useEffect(() => {
    if (latestCommentary) {
      setActiveBanner(latestCommentary);
      const timer = setTimeout(() => {
        // Leave active banner or fade out after 6.5s
      }, 6500);
      return () => clearTimeout(timer);
    }
  }, [latestCommentary]);

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

  // Dynamic model switching
  const handleModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    setIsSwitchingModel(true);
    try {
      await fetch(`${BACKEND_BASE_URL}/api/v1/model/select`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_name: newModel }),
      });
    } catch (err) {
      console.error("Failed to switch model:", err);
    } finally {
      setIsSwitchingModel(false);
    }
  };

  // Sync confidence slider with backend
  const handleConfidenceChange = (newConf: number) => {
    setMinConfidence(newConf);
    fetch(`${BACKEND_BASE_URL}/api/v1/model/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confidence_threshold: newConf }),
    }).catch(() => {});
  };

  // Update dynamic aspect ratio when video metadata arrives
  const handleLoadedMetadata = () => {
    if (videoRef.current && videoRef.current.videoWidth && videoRef.current.videoHeight) {
      setVideoAspectRatio(`${videoRef.current.videoWidth} / ${videoRef.current.videoHeight}`);
    }
  };

  // Filter detections based on confidence threshold
  const visibleDetections = detections.filter((d) => d.confidence >= minConfidence);

  return (
    <div className="flex flex-col bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl backdrop-blur-sm">
      {/* Viewport Top Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-3 bg-slate-950/70 border-b border-slate-800 gap-2">
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
              Laptop Camera
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
              ESP32 / Stream
            </button>
          </div>

          <span className="font-mono text-slate-400 text-[11px] hidden sm:inline">
            [Frame #{sourceMode === "webcam" ? webcamFrameIndexRef.current : frameIndex}]
          </span>
        </div>

        {/* Viewport Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Model Selector Dropdown */}
          <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-lab-900/90 px-2 py-1 rounded-md border border-lab-700">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <select
              value={selectedModel}
              onChange={handleModelChange}
              disabled={isSwitchingModel}
              className="bg-transparent text-cyan-300 font-mono text-[11px] focus:outline-none cursor-pointer"
            >
              <option value="yolo11s.pt" className="bg-lab-900">YOLO11s (High Acc)</option>
              <option value="yolo11m.pt" className="bg-lab-900">YOLO11m (Max Acc)</option>
              <option value="yolo11n.pt" className="bg-lab-900">YOLO11n (Fast Nano)</option>
            </select>
          </div>

          {/* FPS Selector for Webcam */}
          {sourceMode === "webcam" && (
            <div className="hidden sm:flex items-center gap-1 text-xs text-slate-400">
              <span className="text-[11px]">FPS:</span>
              <select
                value={webcamFps}
                onChange={(e) => setWebcamFps(Number(e.target.value))}
                className="bg-lab-900 border border-lab-700 text-cyan-300 rounded px-1.5 py-0.5 text-xs focus:outline-none"
              >
                <option value={5}>5</option>
                <option value={8}>8</option>
                <option value={12}>12</option>
              </select>
            </div>
          )}

          {/* Confidence Slider */}
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-400">
            <Sliders className="w-3.5 h-3.5" />
            <span>Conf:</span>
            <input
              type="range"
              min="0.2"
              max="0.85"
              step="0.05"
              value={minConfidence}
              onChange={(e) => handleConfidenceChange(parseFloat(e.target.value))}
              className="w-16 lg:w-20 accent-cyan-500 h-1 bg-lab-700 rounded-lg cursor-pointer"
            />
            <span className="font-mono text-slate-200 w-7">{Math.round(minConfidence * 100)}%</span>
          </div>

          {/* Toggle Overlay Button */}
          <button
            onClick={() => setShowOverlays(!showOverlays)}
            title={showOverlays ? "Hide Bounding Boxes" : "Show Bounding Boxes"}
            className="p-1.5 rounded bg-lab-700 hover:bg-lab-600 text-slate-300 transition-colors"
          >
            {showOverlays ? <Eye className="w-3.5 h-3.5 text-cyan-400" /> : <EyeOff className="w-3.5 h-3.5" />}
          </button>

          {/* Toggle Live Commentary Button */}
          <button
            onClick={() => setShowCommentary(!showCommentary)}
            title={showCommentary ? "Disable AI Commentary Overlay" : "Enable AI Commentary Overlay"}
            className={`p-1.5 rounded transition-colors flex items-center gap-1.5 text-[11px] font-medium ${
              showCommentary
                ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                : "bg-lab-700 hover:bg-lab-600 text-slate-400"
            }`}
          >
            <Mic className={`w-3.5 h-3.5 ${showCommentary ? "text-rose-400 animate-pulse" : ""}`} />
            <span className="hidden lg:inline">AI Narrator</span>
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

                {/* Real-time Dynamic HTML Bounding Box & Label Overlays */}
                {showOverlays && (
                  <div className="absolute inset-0 pointer-events-none overflow-hidden">
                    {visibleDetections.map((det, idx) => {
                      if (!det.normalized_box) return null;
                      const [nx1, ny1, nx2, ny2] = det.normalized_box;
                      const left = Math.max(0, Math.min(100, nx1 * 100));
                      const top = Math.max(0, Math.min(100, ny1 * 100));
                      const width = Math.max(0, Math.min(100 - left, (nx2 - nx1) * 100));
                      const height = Math.max(0, Math.min(100 - top, (ny2 - ny1) * 100));
                      const isNearTop = ny1 < 0.08;

                      return (
                        <div
                          key={idx}
                          className="absolute border-2 border-cyan-400 bg-cyan-400/15 rounded pointer-events-none transition-all duration-75 shadow-sm"
                          style={{
                            left: `${left}%`,
                            top: `${top}%`,
                            width: `${width}%`,
                            height: `${height}%`,
                          }}
                        >
                          {/* Object Name Badge directly on top of the blue box */}
                          <div
                            className={`absolute ${
                              isNearTop ? "top-1 left-1" : "-top-7 left-0"
                            } bg-cyan-400 text-slate-950 font-mono font-bold text-xs px-2 py-0.5 rounded shadow-lg whitespace-nowrap flex items-center gap-1.5 z-30 select-none`}
                          >
                            <span className="capitalize">{det.class_name.replace(/_/g, " ")}</span>
                            <span className="bg-slate-950/25 text-slate-950 text-[10px] px-1 py-0.2 rounded font-semibold">
                              {Math.round(det.confidence * 100)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* REMOTE / ESP32 SOURCE MODE */}
        {sourceMode === "remote" && (
          <>
            {frameImage ? (
              <div className="relative w-full h-full flex items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={frameImage}
                  alt="Live Camera Feed"
                  className="w-full h-full object-contain select-none block"
                />

                {showOverlays && (
                  <div className="absolute inset-0 pointer-events-none overflow-hidden">
                    {visibleDetections.map((det, idx) => {
                      if (!det.normalized_box) return null;
                      const [nx1, ny1, nx2, ny2] = det.normalized_box;
                      const left = Math.max(0, Math.min(100, nx1 * 100));
                      const top = Math.max(0, Math.min(100, ny1 * 100));
                      const width = Math.max(0, Math.min(100 - left, (nx2 - nx1) * 100));
                      const height = Math.max(0, Math.min(100 - top, (ny2 - ny1) * 100));
                      const isNearTop = ny1 < 0.08;

                      return (
                        <div
                          key={idx}
                          className="absolute border-2 border-emerald-400 bg-emerald-400/15 rounded pointer-events-none transition-all duration-75 shadow-sm"
                          style={{
                            left: `${left}%`,
                            top: `${top}%`,
                            width: `${width}%`,
                            height: `${height}%`,
                          }}
                        >
                          {/* Object Name Badge directly on top of the green box */}
                          <div
                            className={`absolute ${
                              isNearTop ? "top-1 left-1" : "-top-7 left-0"
                            } bg-emerald-400 text-slate-950 font-mono font-bold text-xs px-2 py-0.5 rounded shadow-lg whitespace-nowrap flex items-center gap-1.5 z-30 select-none`}
                          >
                            <span className="capitalize">{det.class_name.replace(/_/g, " ")}</span>
                            <span className="bg-slate-950/25 text-slate-950 text-[10px] px-1 py-0.2 rounded font-semibold">
                              {Math.round(det.confidence * 100)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
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
                      Laptop Camera
                    </button>{" "}
                    to view your webcam directly!
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {/* Live Broadcast Commentary Overlay Banner */}
        {showCommentary && activeBanner && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 max-w-[94%] sm:max-w-xl transition-all duration-300 pointer-events-none select-none">
            <div className="flex items-center gap-2.5 px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-full bg-slate-950/90 backdrop-blur-md border border-cyan-500/50 shadow-2xl text-slate-100">
              <div className="flex items-center gap-1.5 shrink-0 px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30 text-[10px] font-bold tracking-wider uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                AI NARRATOR
              </div>
              <p className="text-xs sm:text-sm font-medium text-cyan-200 line-clamp-2">
                {activeBanner.text}
              </p>
            </div>
          </div>
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
              MODEL: {selectedModel.replace(".pt", "").toUpperCase()}
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
