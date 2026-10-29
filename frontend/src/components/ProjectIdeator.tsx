"use client";

import React, { useState, useEffect } from "react";
import {
  Cpu,
  Layers,
  Wrench,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Terminal,
  Zap,
  ArrowRight,
  Code2
} from "lucide-react";
import { ProjectIdea, DetectionItem } from "@/types/telemetry";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface ProjectIdeatorProps {
  detections: DetectionItem[];
  onAskCopilot?: (question: string) => void;
}

const COMMON_HARDWARE_PRESETS = [
  { id: "raspberry_pi", label: "Raspberry Pi" },
  { id: "microcontroller", label: "Microcontroller (ESP32/Arduino)" },
  { id: "soldering_station", label: "Soldering Station" },
  { id: "3d_printer", label: "3D Printer" },
  { id: "dell_monitor", label: "Dell Monitor" },
];

export const ProjectIdeator: React.FC<ProjectIdeatorProps> = ({
  detections,
  onAskCopilot,
}) => {
  // Extract currently detected components from camera
  const liveDetected = Array.from(
    new Set(detections.map((d) => d.class_name.toLowerCase()))
  );

  const [selectedHardware, setSelectedHardware] = useState<string[]>(
    liveDetected.length > 0 ? liveDetected : ["raspberry_pi", "microcontroller"]
  );
  const [projects, setProjects] = useState<ProjectIdea[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [expandedProjectId, setExpandedProjectId] = useState<string | null>("edge_ai_gateway");
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Record<string, boolean>>({});
  const [aiSuggestions, setAiSuggestions] = useState<string | null>(null);

  // Sync with live detections when they arrive
  useEffect(() => {
    if (liveDetected.length > 0) {
      setSelectedHardware((prev) => {
        const combined = Array.from(new Set([...prev, ...liveDetected]));
        return combined;
      });
    }
  }, [detections]);

  // Fetch project recommendations for selected hardware
  const fetchProjects = async (comps: string[]) => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/projects/current`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch (err) {
      console.warn("Failed to fetch project ideas:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(selectedHardware);
  }, []);

  const toggleHardware = (hwId: string) => {
    const next = selectedHardware.includes(hwId)
      ? selectedHardware.filter((id) => id !== hwId)
      : [...selectedHardware, hwId];
    setSelectedHardware(next);
  };

  const handleCopy = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedSection(id);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const toggleStep = (stepKey: string) => {
    setCompletedSteps((prev) => ({
      ...prev,
      [stepKey]: !prev[stepKey],
    }));
  };

  const handleGenerateAI = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/projects/ideate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ components: selectedHardware }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.curated_projects) {
          setProjects(data.curated_projects);
        }
        if (data.llm_custom_suggestions) {
          setAiSuggestions(data.llm_custom_suggestions);
        }
      }
    } catch (err) {
      console.warn("AI Ideation failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[650px] bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-950/40 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Wrench className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              IoT Lab Project Builder
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono">
                Hardware Ideator
              </span>
            </h2>
            <p className="text-[11px] text-slate-400">
              Detect components & generate wiring guides, firmware & instructions
            </p>
          </div>
        </div>

        <button
          onClick={handleGenerateAI}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-all shadow-sm active:scale-95 disabled:opacity-50"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>{loading ? "Reasoning..." : "Ideate with AI"}</span>
        </button>
      </div>

      {/* Hardware Tags Bar */}
      <div className="p-3 bg-slate-950/60 border-b border-slate-800/60 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Cpu className="w-3 h-3 text-cyan-400" />
            Active Components on Bench:
          </span>
          <span className="text-[10px] text-slate-400">
            Click tags to toggle hardware
          </span>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {COMMON_HARDWARE_PRESETS.map((preset) => {
            const isSelected = selectedHardware.includes(preset.id);
            return (
              <button
                key={preset.id}
                onClick={() => toggleHardware(preset.id)}
                className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-all ${
                  isSelected
                    ? "bg-cyan-500/20 border-cyan-500/50 text-cyan-200 shadow-sm"
                    : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-300 hover:border-slate-700"
                }`}
              >
                {isSelected ? "✓ " : "+ "}
                {preset.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Scrollable Project Cards Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans">
        {/* Optional AI Custom Ideation Note */}
        {aiSuggestions && (
          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-emerald-500/30 text-xs space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold">
              <Sparkles className="w-4 h-4" />
              <span>AI Architect Recommendation:</span>
            </div>
            <p className="text-slate-300 whitespace-pre-line leading-relaxed font-mono text-[11px]">
              {aiSuggestions}
            </p>
          </div>
        )}

        {/* Project Cards */}
        {projects.map((proj) => {
          const isExpanded = expandedProjectId === proj.id;
          return (
            <div
              key={proj.id}
              className={`rounded-xl border transition-all duration-200 overflow-hidden ${
                isExpanded
                  ? "bg-slate-950/70 border-cyan-500/40 shadow-lg"
                  : "bg-slate-950/40 border-slate-800/80 hover:border-slate-700"
              }`}
            >
              {/* Card Header */}
              <div
                onClick={() =>
                  setExpandedProjectId(isExpanded ? null : proj.id)
                }
                className="p-3.5 cursor-pointer flex items-start justify-between gap-3 select-none"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-semibold text-slate-100">
                      {proj.title}
                    </h3>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                        proj.difficulty === "Beginner"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : proj.difficulty === "Intermediate"
                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                          : "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                      }`}
                    >
                      {proj.difficulty}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {proj.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {proj.summary}
                  </p>
                </div>

                <div className="text-slate-400 p-1">
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-cyan-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </div>
              </div>

              {/* Expanded Project Details */}
              {isExpanded && (
                <div className="px-3.5 pb-4 pt-1 border-t border-slate-800/60 space-y-3.5 text-xs">
                  {/* System Architecture */}
                  <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] uppercase font-semibold text-cyan-400 tracking-wider block mb-1">
                      System Architecture:
                    </span>
                    <p className="text-slate-200 font-mono text-[11px]">
                      {proj.architecture}
                    </p>
                  </div>

                  {/* Wiring & Pinouts */}
                  <div className="p-3 rounded-lg bg-slate-900/80 border border-amber-500/20 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-amber-400 font-semibold text-[11px]">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Wiring & Pinout Connections:</span>
                    </div>
                    <pre className="text-slate-300 font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
                      {proj.wiring_summary}
                    </pre>
                  </div>

                  {/* Firmware Code Snippet */}
                  {proj.firmware_snippet && (
                    <div className="rounded-lg bg-slate-900 border border-slate-800 overflow-hidden">
                      <div className="px-3 py-1.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between text-[11px] text-slate-300">
                        <span className="flex items-center gap-1.5 font-mono text-cyan-300">
                          <Code2 className="w-3.5 h-3.5" />
                          Microcontroller Firmware (C++)
                        </span>
                        <button
                          onClick={() =>
                            handleCopy(
                              proj.firmware_snippet!,
                              `${proj.id}-firmware`
                            )
                          }
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                        >
                          {copiedSection === `${proj.id}-firmware` ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span className="text-emerald-400">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="p-3 text-[11px] font-mono text-emerald-300/90 overflow-x-auto max-h-48 leading-relaxed">
                        {proj.firmware_snippet}
                      </pre>
                    </div>
                  )}

                  {/* Host Script Snippet */}
                  {proj.host_snippet && (
                    <div className="rounded-lg bg-slate-900 border border-slate-800 overflow-hidden">
                      <div className="px-3 py-1.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between text-[11px] text-slate-300">
                        <span className="flex items-center gap-1.5 font-mono text-amber-300">
                          <Terminal className="w-3.5 h-3.5" />
                          Raspberry Pi Host Script (Python)
                        </span>
                        <button
                          onClick={() =>
                            handleCopy(
                              proj.host_snippet!,
                              `${proj.id}-host`
                            )
                          }
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                        >
                          {copiedSection === `${proj.id}-host` ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              <span className="text-emerald-400">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="p-3 text-[11px] font-mono text-amber-300/90 overflow-x-auto max-h-48 leading-relaxed">
                        {proj.host_snippet}
                      </pre>
                    </div>
                  )}

                  {/* Step-by-Step Instructions */}
                  <div className="space-y-2">
                    <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider block">
                      Implementation Steps:
                    </span>
                    <div className="space-y-1.5">
                      {proj.steps.map((st, idx) => {
                        const stepKey = `${proj.id}-step-${idx}`;
                        const isDone = !!completedSteps[stepKey];
                        return (
                          <div
                            key={idx}
                            onClick={() => toggleStep(stepKey)}
                            className={`p-2 rounded-lg border flex items-start gap-2.5 cursor-pointer transition-all ${
                              isDone
                                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300 line-through opacity-75"
                                : "bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700"
                            }`}
                          >
                            <div className="mt-0.5">
                              {isDone ? (
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                              ) : (
                                <div className="w-3.5 h-3.5 rounded-full border border-slate-500 flex items-center justify-center text-[9px] font-mono">
                                  {idx + 1}
                                </div>
                              )}
                            </div>
                            <span className="text-[11px] leading-relaxed flex-1">
                              {st}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Quick Ask Copilot Button */}
                  {onAskCopilot && (
                    <button
                      onClick={() =>
                        onAskCopilot(
                          `How do I wire and test ${proj.title} using Raspberry Pi and Microcontroller?`
                        )
                      }
                      className="w-full py-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-medium flex items-center justify-center gap-1.5 transition-all"
                    >
                      <span>Ask AI Copilot for deep-dive questions</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
