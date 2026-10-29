export interface DetectionItem {
  class_name: string;
  confidence: number;
  box: [number, number, number, number]; // [x1, y1, x2, y2]
  normalized_box?: [number, number, number, number]; // [norm_x1, norm_y1, norm_x2, norm_y2]
}

export interface TelemetryData {
  device_id: string;
  frame_index: number;
  timestamp_ms: number;
  inference_latency_ms: number;
  total_detections: number;
  equipment_counts: Record<string, number>;
  detections: DetectionItem[];
  image_width: number;
  image_height: number;
}

export interface WebSocketFrameMessage {
  type: "frame_update" | "initial_state";
  telemetry: TelemetryData;
  annotated_frame_base64?: string;
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface AgentQueryResponse {
  answer: string;
  model_used: string;
  latency_ms: number;
  timestamp: number;
}

export interface AgentBriefingResponse {
  summary: string;
  safety_assessment: string;
  safety_status: "nominal" | "caution" | "hazard";
  equipment_tally: Record<string, number>;
  model_used: string;
  latency_ms: number;
  timestamp: number;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  modelUsed?: string;
  latencyMs?: number;
  timestamp: number;
}
