// @ts-nocheck
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { Search, MapPin, AlertCircle, Clock, ShieldCheck, FileText, ChevronRight } from "lucide-react";
import { useApi } from "../hooks/useApi";
import { spandanApi } from "../services/spandanApi";
import type { ComplaintStatus } from "../types/api";

export default function ComplaintsPage() {
  const complaints = useApi((signal) => spandanApi.listComplaints({}, signal), "complaints");
  const [filter, setFilter] = useState<"ALL" | "ACTIVE" | "RESOLVED">("ALL");
  const [search, setSearch] = useState("");

  const getStatusColor = (status: string) => {
    switch (status) {
      case "RESOLVED":
      case "CLOSED":
        return "bg-slate-100 text-slate-700 border-slate-200";
      case "BREACHED":
      case "ESCALATED":
        return "bg-red-50 text-red-700 border-red-200";
      case "WARNING":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "FILED":
      case "MONITORING":
        return "bg-blue-50 text-blue-700 border-blue-200";
      default:
        return "bg-slate-100 text-slate-600 border-slate-200";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "RESOLVED":
      case "CLOSED":
        return <ShieldCheck size={14} className="mr-1.5" />;
      case "BREACHED":
      case "ESCALATED":
        return <AlertCircle size={14} className="mr-1.5" />;
      case "WARNING":
        return <AlertCircle size={14} className="mr-1.5" />;
      default:
        return <Clock size={14} className="mr-1.5" />;
    }
  };

  if (complaints.status === "loading") {
    return (
      <div className="max-w-5xl mx-auto p-4 py-12 flex justify-center">
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-12 h-12 bg-slate-200 rounded-full mb-4"></div>
          <div className="h-4 w-32 bg-slate-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (complaints.status === "error") {
    return (
      <div className="max-w-5xl mx-auto p-4 py-12">
        <div className="bg-red-50 text-red-700 p-4 rounded-xl flex items-center">
          <AlertCircle className="mr-3" />
          <p>Unable to load complaints. Please try again.</p>
        </div>
      </div>
    );
  }

  const items = complaints.data.items.filter(c => {
    if (filter === "ACTIVE" && ["RESOLVED", "CLOSED"].includes(c.status)) return false;
    if (filter === "RESOLVED" && !["RESOLVED", "CLOSED"].includes(c.status)) return false;
    
    if (search) {
      const q = search.toLowerCase();
      return c.tracking_id?.toLowerCase().includes(q) || c.issue?.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto p-4 py-12 w-full">
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">My Complaints</h1>
          <p className="text-slate-500">Track and monitor your filed civic issues.</p>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search tracking ID..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 w-full md:w-64"
            />
          </div>
          <select 
            value={filter} 
            onChange={(e) => setFilter(e.target.value as any)}
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm font-medium outline-none"
          >
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active Only</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center flex flex-col items-center">
          <FileText size={48} className="text-slate-300 mb-4" />
          <h3 className="text-lg font-bold text-slate-900 mb-2">No complaints found</h3>
          <p className="text-slate-500 mb-6">You haven't filed any complaints matching this filter.</p>
          <Link to="/" className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors">
            Report an Issue
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((c) => (
            <Link 
              key={c.id} 
              to={`/complaints/${c.id}`}
              className="group block bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition-all relative overflow-hidden"
            >
              {/* Left accent bar based on status */}
              <div className={`absolute left-0 top-0 bottom-0 w-1 ${
                ["BREACHED", "ESCALATED"].includes(c.status) ? "bg-red-500" :
                c.status === "WARNING" ? "bg-amber-400" :
                ["RESOLVED", "CLOSED"].includes(c.status) ? "bg-slate-300" :
                "bg-blue-500"
              }`}></div>
              
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pl-3">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className="font-mono text-xs font-semibold px-2 py-1 bg-slate-100 text-slate-600 rounded">
                      {c.tracking_id || "PENDING"}
                    </span>
                    <span className="text-sm text-slate-500">
                      Updated {formatDistanceToNow(new Date(c.updated_at), { addSuffix: true })}
                    </span>
                  </div>
                  <h3 className="font-bold text-lg text-slate-900 mb-1 group-hover:text-blue-700 transition-colors">
                    {c.issue || "Processing complaint..."}
                  </h3>
                </div>
                
                <div className="flex items-center space-x-4 md:justify-end">
                  <div className={`flex items-center px-3 py-1.5 rounded-full border text-xs font-bold tracking-wide ${getStatusColor(c.status)}`}>
                    {getStatusIcon(c.status)}
                    {c.status.replace("_", " ")}
                  </div>
                  <ChevronRight size={20} className="text-slate-400 group-hover:text-blue-600 transition-colors" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
