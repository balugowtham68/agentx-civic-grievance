// @ts-nocheck
import React, { useState } from "react";

import { Activity, Server, Database, ShieldCheck, Cpu, RefreshCw, Play, Search } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { spandanApi } from "../services/spandanApi";

export default function ActivityPage() {
  // Mock recent global activity for the demo since we don't have a global events endpoint
  return (
    <div className="max-w-6xl mx-auto p-4 py-8 w-full">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">AI Operations Activity</h1>
        <p className="text-slate-500">Real-time autonomous actions taken by AGENT X across all complaints.</p>
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-sm font-bold text-slate-700 uppercase tracking-widest">Live Feed</span>
          </div>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Filter events..." 
              className="pl-9 pr-4 py-1.5 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        
        <div className="p-0">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white border-b border-slate-200 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-4 pl-6">Time</th>
                <th className="p-4">Action</th>
                <th className="p-4">Tracking ID</th>
                <th className="p-4">Agent</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              <tr className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-4 pl-6 font-medium text-slate-500">Just now</td>
                <td className="p-4"><span className="px-2 py-1 bg-red-100 text-red-700 rounded font-medium">Escalation Triggered</span></td>
                <td className="p-4 font-mono font-medium">AGX-2026-DEMO1</td>
                <td className="p-4 font-medium">Watchdog Agent</td>
              </tr>
              <tr className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-4 pl-6 font-medium text-slate-500">2 min ago</td>
                <td className="p-4"><span className="px-2 py-1 bg-amber-100 text-amber-700 rounded font-medium">SLA Warning</span></td>
                <td className="p-4 font-mono font-medium">AGX-2026-DEMO1</td>
                <td className="p-4 font-medium">Watchdog Agent</td>
              </tr>
              <tr className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-4 pl-6 font-medium text-slate-500">15 min ago</td>
                <td className="p-4"><span className="px-2 py-1 bg-blue-100 text-blue-700 rounded font-medium">Complaint Filed</span></td>
                <td className="p-4 font-mono font-medium">AGX-2026-DEMO1</td>
                <td className="p-4 font-medium">Filing Agent</td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="p-4 pl-6 font-medium text-slate-500">15 min ago</td>
                <td className="p-4"><span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded font-medium">Understood & Drafted</span></td>
                <td className="p-4 font-mono font-medium">AGX-2026-DEMO1</td>
                <td className="p-4 font-medium">Intake Agent</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function SystemPage() {
  const health = useApi((signal) => spandanApi.health(signal), "health");
  const [triggering, setTriggering] = useState(false);

  const runWatchdog = async () => {
    setTriggering(true);
    try {
      await fetch("http://localhost:8000/api/v1/watchdog/run", { method: "POST" });
      alert("Watchdog run triggered.");
    } catch (e) {
      alert("Failed to trigger watchdog");
    } finally {
      setTriggering(false);
    }
  };

  const resetDemo = async () => {
    if (!confirm("Are you sure you want to reset all demo data?")) return;
    try {
      await fetch("http://localhost:8000/api/v1/demo/reset", { method: "POST" });
      alert("Demo data reset.");
    } catch (e) {
      alert("Failed to reset");
    }
  };

  if (health.status === "loading") {
    return <div className="p-12 flex justify-center"><RefreshCw className="animate-spin text-slate-400" /></div>;
  }

  const h = health.status === "success" ? health.data : null;

  return (
    <div className="max-w-4xl mx-auto p-4 py-8 w-full">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">System Status</h1>
          <p className="text-slate-500">Backend service health and background operations.</p>
        </div>
        <div className="px-3 py-1 bg-blue-100 text-blue-700 font-bold rounded text-sm tracking-widest uppercase">
          DEMO MODE
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
            <Server size={24} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">Backend API</h3>
            <div className="flex items-center space-x-2">
              <div className={`w-2.5 h-2.5 rounded-full ${h ? "bg-emerald-500" : "bg-red-500"}`}></div>
              <span className="font-bold text-lg">{h ? "Operational" : "Offline"}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
            <Database size={24} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">Database</h3>
            <div className="flex items-center space-x-2">
              <div className={`w-2.5 h-2.5 rounded-full ${h?.database === "ok" ? "bg-emerald-500" : "bg-red-500"}`}></div>
              <span className="font-bold text-lg">{h?.database === "ok" ? "Connected" : "Disconnected"}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
            <Cpu size={24} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">AI Provider</h3>
            <div className="flex items-center space-x-2">
              <div className={`w-2.5 h-2.5 rounded-full ${h?.ai_provider ? "bg-emerald-500" : "bg-amber-500"}`}></div>
              <span className="font-bold text-lg">{h?.ai_provider || "Unknown"}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex items-center space-x-4">
          <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
            <Activity size={24} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">Watchdog Loop</h3>
            <div className="flex items-center space-x-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="font-bold text-lg">Running (10s)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-2xl shadow-sm p-6 text-white">
        <h2 className="text-lg font-bold mb-4 flex items-center">
          <Play size={20} className="mr-2 text-blue-400" />
          Demo Controls
        </h2>
        <div className="flex flex-wrap gap-4">
          <button 
            onClick={runWatchdog}
            disabled={triggering}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors"
          >
            Force Watchdog Run
          </button>
          <button 
            onClick={resetDemo}
            className="px-6 py-2.5 bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors"
          >
            Reset Demo Data
          </button>
        </div>
        <p className="mt-4 text-sm text-slate-400">
          These controls are only available because DEMO_MODE is true in the environment.
        </p>
      </div>
    </div>
  );
}
