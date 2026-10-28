"use client";

import React from "react";
import { Printer, Monitor, Cpu, Flame, Wrench, ShieldCheck, HelpCircle } from "lucide-react";

interface InventoryCardsProps {
  equipmentCounts: Record<string, number>;
  totalActive: number;
}

interface EquipmentCardDef {
  key: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  borderColor: string;
}

const EQUIPMENT_CATALOG: EquipmentCardDef[] = [
  {
    key: "3d_printer",
    name: "3D Printers",
    icon: Printer,
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
  },
  {
    key: "dell_monitor",
    name: "Dell Displays",
    icon: Monitor,
    color: "text-sky-400",
    bgColor: "bg-sky-500/10",
    borderColor: "border-sky-500/30",
  },
  {
    key: "microcontroller",
    name: "Microcontrollers",
    icon: Cpu,
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
  },
  {
    key: "soldering_station",
    name: "Soldering Rigs",
    icon: Flame,
    color: "text-rose-400",
    bgColor: "bg-rose-500/10",
    borderColor: "border-rose-500/30",
  },
  {
    key: "oscilloscope",
    name: "Oscilloscopes",
    icon: Wrench,
    color: "text-purple-400",
    bgColor: "bg-purple-500/10",
    borderColor: "border-purple-500/30",
  },
];

export const InventoryCards: React.FC<InventoryCardsProps> = ({
  equipmentCounts,
  totalActive,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          Active Equipment Telemetry
        </h2>
        <span className="text-xs px-2.5 py-1 rounded bg-lab-800 text-slate-300 border border-lab-700 font-mono">
          Total In-Lab: <strong className="text-emerald-400 font-bold">{totalActive}</strong>
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {EQUIPMENT_CATALOG.map((item) => {
          const count = equipmentCounts[item.key] || 0;
          const Icon = item.icon;
          const isActive = count > 0;

          return (
            <div
              key={item.key}
              className={`p-3.5 rounded-xl border bg-lab-850 flex flex-col justify-between transition-all duration-200 ${
                isActive ? item.borderColor : "border-lab-700/60 opacity-80"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-300">{item.name}</span>
                <div className={`p-1.5 rounded-lg ${item.bgColor} ${item.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>

              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold font-mono text-slate-100">
                  {count}
                </span>
                <span
                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                    isActive
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-slate-800 text-slate-500"
                  }`}
                >
                  {isActive ? "ACTIVE" : "NONE"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
