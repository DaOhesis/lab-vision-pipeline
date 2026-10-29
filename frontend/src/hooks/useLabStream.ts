"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { TelemetryData, WebSocketFrameMessage, ConnectionStatus, LiveCommentaryItem } from "@/types/telemetry";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws/stream";

export function useLabStream() {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [frameImage, setFrameImage] = useState<string | null>(null);
  const [fps, setFps] = useState<number>(0);
  const [latestCommentary, setLatestCommentary] = useState<LiveCommentaryItem | null>(null);
  const [commentaryFeed, setCommentaryFeed] = useState<LiveCommentaryItem[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);
  const frameCountRef = useRef<number>(0);
  const lastFpsTimeRef = useRef<number>(Date.now());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      setStatus("connecting");
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketFrameMessage = JSON.parse(event.data);
          if (data.type === "live_commentary" && data.commentary) {
            setLatestCommentary(data.commentary);
            setCommentaryFeed((prev) => [data.commentary!, ...prev.slice(0, 20)]);
          } else if (data.telemetry) {
            setTelemetry(data.telemetry);
            if (data.telemetry.latest_commentary) {
              setLatestCommentary(data.telemetry.latest_commentary);
            }
          }
          if (data.annotated_frame_base64) {
            setFrameImage(data.annotated_frame_base64);
          }

          // Calculate running FPS
          frameCountRef.current += 1;
          const now = Date.now();
          const elapsed = now - lastFpsTimeRef.current;
          if (elapsed >= 1000) {
            setFps(Math.round((frameCountRef.current * 1000) / elapsed));
            frameCountRef.current = 0;
            lastFpsTimeRef.current = now;
          }
        } catch (err) {
          console.error("Error parsing WebSocket frame message:", err);
        }
      };

      ws.onerror = (err) => {
        console.warn("WebSocket stream error:", err);
        setStatus("error");
      };

      ws.onclose = () => {
        setStatus("disconnected");
        // Attempt auto-reconnect after 2.5 seconds
        if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2500);
      };
    } catch (err) {
      console.error("Failed to initiate WebSocket connection:", err);
      setStatus("disconnected");
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    status,
    telemetry,
    frameImage,
    fps,
    latestCommentary,
    commentaryFeed,
    reconnect: connect
  };
}
