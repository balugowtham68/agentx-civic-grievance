// @ts-nocheck
import React, { useState, useEffect, useRef, FormEvent } from "react";
import { useLocation, useNavigate, Link, useSearchParams } from "react-router-dom";
import {
  Send,
  CheckCircle2,
  Clock,
  MapPin,
  Building2,
  FileText,
  Shield,
  ShieldCheck,
  AlertCircle,
  Copy,
  Check,
  ExternalLink,
  ChevronRight,
  Loader2,
  RotateCw,
  Sparkles,
  ArrowRight,
  Radio,
  Navigation,
  FileCheck,
  Zap,
  Camera,
  Crosshair,
  X,
  Lightbulb,
  Droplet,
  AlertTriangle,
  Activity,
  Trash2,
  HelpCircle as QuestionIcon,
} from "lucide-react";
import { spandanApi } from "../services/spandanApi";
import {
  PROBLEM_CATEGORIES,
  getDiagnosticQuestions,
} from "../data/multilingualDiagnostics";
import { fetchLiveDeviceLocation } from "../services/locationService";

const CATEGORY_ICON_MAP: Record<string, any> = {
  Lightbulb,
  Droplets: Droplet,
  AlertTriangle,
  Activity,
  Trash2,
};

interface TimelineItem {
  id: string;
  complaint_id: string;
  stage: string;
  message: string;
  timestamp: string;
  details?: Record<string, any>;
  icon: string;
}

interface PipelineState {
  complaint_id: string;
  tracking_id: string;
  status: string;
  issue: string | null;
  location: string | null;
  department_id: string | null;
  jurisdiction_id: string | null;
  timeline: TimelineItem[];
}

const STAGES = [
  { key: "RECEIVED", label: "Received", icon: Clock, desc: "Instant acknowledgement & tracking ID issued" },
  { key: "UNDERSTOOD", label: "Understood", icon: Sparkles, desc: "Multi-signal regional language & grievance extraction" },
  { key: "LOCATION_RESOLVED", label: "Location & Ward", icon: MapPin, desc: "Multi-signal geolocation & municipal jurisdiction routing" },
  { key: "CLASSIFIED", label: "Classified & RAG", icon: Building2, desc: "Department routing against citizen charter rules" },
  { key: "DRAFTED", label: "Petition Drafted", icon: FileText, desc: "Formal legal civic grievance petition generated" },
  { key: "FILED", label: "Authority Filing", icon: FileCheck, desc: "Registered with municipal portal & SLA clock initialized" },
  { key: "MONITORING", label: "Autonomous Watchdog", icon: Shield, desc: "Active watchdog monitoring & automated escalation ready" },
];

export default function IntakePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlComplaintId = searchParams.get("id");

  const locState = useLocation().state as {
    complaintId?: string;
    trackingId?: string;
    status?: string;
    text?: string;
    lang?: string;
    location?: string;
    latitude?: number;
    longitude?: number;
    photoData?: string;
    photoName?: string;
    diagnosticDetails?: Record<string, any>;
    categoryHint?: string;
  } | null;

  const activeComplaintId = urlComplaintId || locState?.complaintId;

  const [text, setText] = useState(locState?.text || "");
  const [language, setLanguage] = useState(locState?.lang || "te");
  const [locationInput, setLocationInput] = useState(locState?.location || "");
  const [photoPreview, setPhotoPreview] = useState<string | null>(locState?.photoData || null);
  const [photoName, setPhotoName] = useState<string | null>(locState?.photoName || null);
  const [photoData, setPhotoData] = useState<string | null>(locState?.photoData || null);
  const [gpsCoords, setGpsCoords] = useState<{ latitude: number; longitude: number } | null>(
    locState?.latitude && locState?.longitude
      ? { latitude: locState.latitude, longitude: locState.longitude }
      : null
  );
  const [isAcquiringGps, setIsAcquiringGps] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(
    locState?.categoryHint || null
  );
  const [diagnosticDetails, setDiagnosticDetails] = useState<Record<string, any>>(
    locState?.diagnosticDetails || {}
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pipelineData, setPipelineData] = useState<PipelineState | null>(
    activeComplaintId && locState?.trackingId
      ? {
          complaint_id: activeComplaintId,
          tracking_id: locState.trackingId,
          status: locState.status || "RECEIVED",
          issue: null,
          location: locState.location || null,
          department_id: null,
          jurisdiction_id: null,
          timeline: [
            {
              id: "initial-ack",
              complaint_id: activeComplaintId,
              stage: "RECEIVED",
              message: `Complaint received. Tracking ID ${locState.trackingId} issued.`,
              timestamp: new Date().toISOString(),
              details: { tracking_id: locState.trackingId },
              icon: "inbox",
            },
          ],
        }
      : null
  );
  const [copiedTracking, setCopiedTracking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Location edit modal / inline edit state
  const [isEditingLocation, setIsEditingLocation] = useState(false);
  const [customLocation, setCustomLocation] = useState("");
  const [isSavingLocation, setIsSavingLocation] = useState(false);

  // Citizen Draft Confirmation State
  const [isConfirmingDraft, setIsConfirmingDraft] = useState(false);
  const [isEditingDraft, setIsEditingDraft] = useState(false);
  const [editedDraftBody, setEditedDraftBody] = useState("");
  const [draftConfirmed, setDraftConfirmed] = useState(false);

  const handleConfirmDraft = async () => {
    if (!activeComplaintId) return;
    setIsConfirmingDraft(true);
    try {
      await spandanApi.confirmDraft(activeComplaintId, {
        confirmed: true,
        edited_text: isEditingDraft && editedDraftBody.trim() ? editedDraftBody.trim() : undefined,
      });
      setDraftConfirmed(true);
      setIsEditingDraft(false);
      const updated = await spandanApi.getComplaintTimeline(activeComplaintId);
      setPipelineData(updated);
      startPolling(activeComplaintId);
    } catch (err: any) {
      alert(err.message || "Failed to confirm draft petition. Please retry.");
    } finally {
      setIsConfirmingDraft(false);
    }
  };

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const pollIntervalRef = useRef<any>(null);

  const isGpsValid = gpsCoords !== null && gpsCoords.latitude !== undefined;
  const isPhotoValid = Boolean(photoData);
  const canManualSubmit = text.trim().length >= 4 && isGpsValid && isPhotoValid && !isSubmitting;

  // Polling function for live pipeline
  const startPolling = (complaintId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await spandanApi.getComplaintTimeline(complaintId);
        setPipelineData(res);

        // Stop polling if reached terminal or monitoring state
        if (["MONITORING", "RESOLVED", "CLOSED", "BREACHED"].includes(res.status)) {
          const hasMonitoring = res.timeline?.some((t) => t.stage === "MONITORING");
          if (hasMonitoring) {
            clearInterval(pollIntervalRef.current);
          }
        }
      } catch (err) {
        console.error("Error polling timeline:", err);
      }
    }, 1500);
  };

  // If complaint ID is present in URL or state, fetch timeline and start polling
  useEffect(() => {
    if (activeComplaintId) {
      spandanApi
        .getComplaintTimeline(activeComplaintId)
        .then((res) => {
          setPipelineData(res);
          // If GPS or photo was not in state, attempt to recover from timeline details
          if (!gpsCoords && res.timeline) {
            const gpsStage = res.timeline.find((t) => t.stage === "GPS_LOCATED");
            if (gpsStage?.details?.latitude && gpsStage?.details?.longitude) {
              setGpsCoords({
                latitude: gpsStage.details.latitude,
                longitude: gpsStage.details.longitude,
              });
            }
          }
        })
        .catch((err) => {
          console.warn("Timeline fetch error:", err);
        });

      startPolling(activeComplaintId);
    }
  }, [activeComplaintId]);

  // Clean up poll interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Handle category chip selection in manual view
  const handleCategorySelect = (catId: string) => {
    setSelectedCategory(catId);
    const cat = PROBLEM_CATEGORIES.find((c) => c.id === catId);
    if (!cat) return;

    if (!text.trim()) {
      const template = cat.defaultText[language] || cat.defaultText["en"];
      setText(template);
    }
  };

  // Handle diagnostic option selection
  const handleDiagnosticAnswer = (questionId: string, answer: string) => {
    setDiagnosticDetails((prev) => ({
      ...prev,
      [questionId]: answer,
    }));
  };

  const [isLocationAutoDetected, setIsLocationAutoDetected] = useState(false);

  // Automatically fetch exact live location on mount if not provided from state
  useEffect(() => {
    if (!gpsCoords && !activeComplaintId) {
      handleAutoFetchLocation(false);
    }
  }, [activeComplaintId]);

  const handleAutoFetchLocation = async (manualPrompt = false) => {
    if (!navigator.geolocation) {
      if (manualPrompt) alert("Geolocation is not supported by your browser.");
      return;
    }
    setIsAcquiringGps(true);
    try {
      const res = await fetchLiveDeviceLocation();
      setGpsCoords({
        latitude: res.latitude,
        longitude: res.longitude,
      });
      setLocationInput(res.shortAddress || res.formattedAddress);
      setIsLocationAutoDetected(true);
    } catch (err: any) {
      console.warn("Auto-location fetch in IntakePage dismissed or failed:", err);
      if (manualPrompt) {
        alert("Could not access live location. Please grant location permissions in your browser.");
      }
    } finally {
      setIsAcquiringGps(false);
    }
  };

  // Acquire / Refresh Live GPS Location
  const handleGetLiveLocation = () => {
    handleAutoFetchLocation(true);
  };

  // Handle photo upload
  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoName(file.name);
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      setPhotoPreview(base64);
      setPhotoData(base64);
    };
    reader.readAsDataURL(file);
  };

  // Manual Grievance Submission from Intake Workspace
  const handleManualSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    if (!isGpsValid || !isPhotoValid) {
      if (!isGpsValid && !isPhotoValid) {
        setErrorMessage("Both Live GPS Location and Photo Proof are mandatory before submission.");
      } else if (!isGpsValid) {
        setErrorMessage("Live GPS Location is mandatory. Please click 'Share Live GPS'.");
      } else {
        setErrorMessage("Photo proof is mandatory. Please attach a photo of the civic issue.");
      }
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const locLabel =
        locationInput.trim() ||
        `GPS: ${gpsCoords.latitude.toFixed(5)}° N, ${gpsCoords.longitude.toFixed(5)}° E`;

      const ack = await spandanApi.submitComplaintFast({
        text,
        language,
        location: locLabel,
        latitude: gpsCoords.latitude,
        longitude: gpsCoords.longitude,
        photo_data: photoData,
        photo_name: photoName,
        diagnostic_details: diagnosticDetails,
      });

      // Update URL query parameter to persist on refresh
      setSearchParams({ id: ack.complaint_id });

      setPipelineData({
        complaint_id: ack.complaint_id,
        tracking_id: ack.tracking_id,
        status: ack.status,
        issue: null,
        location: locLabel,
        department_id: null,
        jurisdiction_id: null,
        timeline: [
          {
            id: "initial-ack",
            complaint_id: ack.complaint_id,
            stage: "RECEIVED",
            message: ack.message,
            timestamp: ack.created_at,
            details: { tracking_id: ack.tracking_id },
            icon: "inbox",
          },
        ],
      });

      startPolling(ack.complaint_id);
    } catch (err: any) {
      console.error("Submit error:", err);
      setErrorMessage(
        err.message || "Failed to submit grievance. Please verify details and retry."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyTracking = () => {
    if (!pipelineData?.tracking_id) return;
    navigator.clipboard.writeText(pipelineData.tracking_id);
    setCopiedTracking(true);
    setTimeout(() => setCopiedTracking(false), 2000);
  };

  const handleConfirmLocation = async () => {
    if (!pipelineData) return;
    setIsSavingLocation(true);
    try {
      await spandanApi.confirmComplaintLocation(pipelineData.complaint_id, {
        confirmed: true,
        corrected_location: customLocation.trim() || undefined,
      });
      setIsEditingLocation(false);
      const refreshed = await spandanApi.getComplaintTimeline(pipelineData.complaint_id);
      setPipelineData(refreshed);
    } catch (err) {
      console.error("Error confirming location:", err);
    } finally {
      setIsSavingLocation(false);
    }
  };

  // Helper to determine stage status
  const getStageStatus = (stageKey: string) => {
    if (!pipelineData) return "PENDING";
    const completedStages = pipelineData.timeline.map((t) => t.stage);

    if (completedStages.includes(stageKey)) {
      return "COMPLETED";
    }

    const stageOrder = STAGES.map((s) => s.key);
    const highestIdx = Math.max(-1, ...completedStages.map((s) => stageOrder.indexOf(s)));
    const thisIdx = stageOrder.indexOf(stageKey);

    if (thisIdx === highestIdx + 1) {
      return "ACTIVE";
    }
    return "PENDING";
  };

  const getStageEntry = (stageKey: string) => {
    return pipelineData?.timeline?.find((t) => t.stage === stageKey);
  };

  // Active diagnostic questions for manual submission in chosen language
  const activeQuestions = selectedCategory
    ? getDiagnosticQuestions(selectedCategory, language)
    : [];

  // =========================================================================
  // VIEW 1: Rich Citizen Submission Workspace (if not yet submitted)
  // =========================================================================
  if (!pipelineData && !isSubmitting) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 md:py-12">
        {/* Header */}
        <div className="mb-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-800 text-xs font-semibold mb-3">
            <Zap size={14} className="text-blue-600" />
            <span>Spandan AI Autonomous Grievance Engine</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Report a Civic Grievance
          </h1>
          <p className="text-slate-600 text-sm mt-1">
            Submit once in your regional language. Live GPS & Photo Proof are mandatory for autonomous verification and municipal routing.
          </p>
        </div>

        {errorMessage && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-red-800 text-sm flex items-start space-x-3 shadow-xs">
            <AlertCircle size={18} className="text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Validation Required</p>
              <p className="text-xs text-red-700 mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6 md:p-8 space-y-6">
          {/* Quick Problem Category Chips */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-2.5">
              Select Problem Category:
            </label>
            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
              {PROBLEM_CATEGORIES.map((cat) => {
                const isSelected = selectedCategory === cat.id;
                const IconComponent = CATEGORY_ICON_MAP[cat.icon] || AlertTriangle;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => handleCategorySelect(cat.id)}
                    className={`flex items-center space-x-2 px-3.5 py-2 rounded-2xl text-xs font-bold shrink-0 transition-all shadow-2xs ${
                      isSelected
                        ? "bg-slate-900 text-white shadow-md scale-102 ring-2 ring-blue-500/30"
                        : "bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    <IconComponent size={15} className={isSelected ? "text-blue-400" : "text-slate-400"} />
                    <span>{cat.labels[language] || cat.labels["en"]}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <form onSubmit={handleManualSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-800 mb-2">
                Describe the problem (any regional language)
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="ఉదాహరణ: మా కాలనీలో 3 రోజులుగా వీధి దీపాలు వెలగడం లేదు, రాత్రి చీకటిగా ఉంది... / Example: Streetlight broken for 3 days on 4th cross road..."
                rows={4}
                className="w-full text-base p-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                required
              />
            </div>

            {/* Diagnostic Assistant Questions (in selected language) */}
            {activeQuestions.length > 0 && (
              <div className="p-4 bg-blue-50/70 border border-blue-200/80 rounded-2xl">
                <div className="flex items-center space-x-2 text-blue-900 font-bold text-xs uppercase tracking-wider mb-3">
                  <QuestionIcon size={14} className="text-blue-600" />
                  <span>Diagnostic Assistant (Specific Details for Ward Engineers)</span>
                </div>
                <div className="space-y-3">
                  {activeQuestions.map((q) => (
                    <div key={q.id}>
                      <p className="text-xs font-semibold text-slate-800 mb-1.5">{q.question}</p>
                      <div className="flex flex-wrap gap-2">
                        {q.options.map((opt: string) => {
                          const isChosen = diagnosticDetails[q.id] === opt;
                          return (
                            <button
                              key={opt}
                              type="button"
                              onClick={() => handleDiagnosticAnswer(q.id, opt)}
                              className={`text-xs px-3 py-1.5 rounded-xl font-medium transition-all ${
                                isChosen
                                  ? "bg-blue-600 text-white font-semibold shadow-xs"
                                  : "bg-white text-slate-700 border border-blue-200 hover:bg-blue-100/60"
                              }`}
                            >
                              {opt}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-slate-800 mb-2">
                  Colony / Landmark / Ward
                </label>
                <div className="relative flex items-center">
                  <MapPin size={18} className={`absolute left-3.5 top-3.5 ${isLocationAutoDetected ? "text-emerald-600" : "text-slate-400"}`} />
                  <input
                    type="text"
                    value={locationInput}
                    onChange={(e) => {
                      setLocationInput(e.target.value);
                      setIsLocationAutoDetected(false);
                    }}
                    placeholder="e.g. Madhapur, Hyderabad / Ward 104"
                    className="w-full pl-10 pr-24 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                  />
                  {isLocationAutoDetected && (
                    <span className="absolute right-2 top-2 text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-md">
                      Auto-Located ✓
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-800 mb-2">
                  Language Preference
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm font-medium"
                >
                  <option value="te">తెలుగు (Telugu)</option>
                  <option value="ta">தமிழ் (Tamil)</option>
                  <option value="kn">ಕನ್ನಡ (Kannada)</option>
                  <option value="hi">हिन्दी (Hindi)</option>
                  <option value="en">English</option>
                </select>
              </div>
            </div>

            {/* Mandatory Verification Bar */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/90 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-slate-700 flex items-center">
                  <span className="text-red-500 mr-1">*</span> Mandatory Proofs:
                </span>

                {/* GPS Status */}
                {isGpsValid ? (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-300 font-semibold shadow-2xs max-w-sm truncate">
                    <Check size={13} className="text-emerald-600 shrink-0" />
                    <span className="truncate">
                      {locationInput
                        ? `${locationInput} (${gpsCoords.latitude.toFixed(4)}°, ${gpsCoords.longitude.toFixed(4)}°)`
                        : `GPS: ${gpsCoords.latitude.toFixed(4)}°, ${gpsCoords.longitude.toFixed(4)}°`}{" "}
                      ✓
                    </span>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={handleGetLiveLocation}
                    disabled={isAcquiringGps}
                    className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-amber-50 text-amber-900 border border-amber-300 hover:bg-amber-100 font-bold transition shadow-2xs animate-pulse"
                  >
                    {isAcquiringGps ? (
                      <Loader2 size={13} className="animate-spin text-amber-700" />
                    ) : (
                      <Crosshair size={13} className="text-amber-700" />
                    )}
                    <span>{isAcquiringGps ? "Detecting Live Location..." : "* Fetch Exact Live Location"}</span>
                  </button>
                )}

                {/* Photo Proof Status */}
                {isPhotoValid ? (
                  <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-300 font-semibold shadow-2xs">
                    <Check size={13} className="text-emerald-600" />
                    <span>Photo Attached ({photoName || "1 image"}) ✓</span>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-amber-50 text-amber-900 border border-amber-300 hover:bg-amber-100 font-bold transition shadow-2xs animate-pulse"
                  >
                    <Camera size={13} className="text-amber-700" />
                    <span>* Photo Proof Required (Click to Upload)</span>
                  </button>
                )}
              </div>

              <span className="text-[11px] font-semibold text-slate-500">
                {canManualSubmit ? "Ready for Autonomous Redressal" : "Both GPS and Photo proof required before filing"}
              </span>
            </div>

            {/* Photo preview thumbnail */}
            {photoPreview && (
              <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-2xl border border-slate-200">
                <img src={photoPreview} alt="Preview" className="w-14 h-14 object-cover rounded-xl border" />
                <div className="flex-1">
                  <span className="text-xs font-bold text-slate-800 block truncate">{photoName || "Photo Proof"}</span>
                  <span className="text-[11px] text-emerald-600 font-semibold flex items-center">
                    <Check size={12} className="mr-1" />
                    Verified Photo Proof
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => { setPhotoPreview(null); setPhotoData(null); setPhotoName(null); }}
                  className="text-slate-400 hover:text-red-600 p-1.5 rounded-lg hover:bg-slate-200"
                >
                  <X size={16} />
                </button>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handlePhotoSelect}
                accept="image/*"
                capture="environment"
                className="hidden"
              />

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2.5 rounded-xl text-xs font-bold border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 flex items-center space-x-1.5"
                >
                  <Camera size={15} className="text-slate-500" />
                  <span>{photoPreview ? "Change Photo" : "Attach Photo Proof"}</span>
                </button>

                <button
                  type="button"
                  onClick={handleGetLiveLocation}
                  disabled={isAcquiringGps}
                  className="px-4 py-2.5 rounded-xl text-xs font-bold border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 flex items-center space-x-1.5"
                >
                  <Crosshair size={15} className="text-blue-600" />
                  <span>{gpsCoords ? "GPS Shared ✓" : "Share Live GPS"}</span>
                </button>
              </div>

              <button
                type="submit"
                disabled={!canManualSubmit}
                className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-3 px-7 rounded-xl flex items-center justify-center space-x-2 transition shadow-md shadow-blue-500/20"
              >
                <span>Submit Grievance to SPANDAN AI</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: Autonomous Engine Progress & Live Timeline
  // =========================================================================
  const isPipelineComplete =
    pipelineData?.status === "MONITORING" ||
    pipelineData?.status === "FILED" ||
    pipelineData?.status === "RESOLVED";

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      {/* Top Banner: Instant Acknowledgement Hero */}
      <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-indigo-950 rounded-3xl p-6 md:p-8 text-white shadow-xl relative overflow-hidden mb-8">
        <div className="absolute right-0 top-0 translate-x-10 -translate-y-10 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>Grievance Registered Successfully</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
              SPANDAN Autonomous Engine Active
            </h1>
            <p className="text-slate-300 text-sm mt-1 max-w-xl">
              "The citizen submits once. SPANDAN AI continues working after the citizen leaves."
            </p>
          </div>

          {/* Tracking ID Badge with copy */}
          <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/15 flex flex-col items-start md:items-end">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
              Official Tracking ID
            </span>
            <div className="flex items-center space-x-2 mt-1">
              <span className="text-2xl font-mono font-bold tracking-wider text-white">
                {pipelineData?.tracking_id || "GENERATING..."}
              </span>
              <button
                onClick={handleCopyTracking}
                title="Copy Tracking ID"
                className="p-1.5 rounded-lg bg-white/15 hover:bg-white/25 transition text-white"
              >
                {copiedTracking ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
              </button>
            </div>
            <span className="text-[11px] text-slate-400 mt-1">Save this ID to track any time</span>
          </div>
        </div>

        {/* Live Status Summary Pill Bar */}
        <div className="mt-6 pt-6 border-t border-white/10 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-slate-400 block">Identified Issue:</span>
            <span className="font-semibold text-white truncate block">
              {pipelineData?.issue || "Analyzing issue..."}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block">Civic Jurisdiction:</span>
            <span className="font-semibold text-white truncate block">
              {pipelineData?.jurisdiction_id || "Resolving ward..."}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block">Assigned Department:</span>
            <span className="font-semibold text-white truncate block">
              {pipelineData?.department_id || "Routing..."}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block">Watchdog Status:</span>
            <span className="font-semibold text-emerald-400 flex items-center space-x-1">
              <ShieldCheck size={14} className="inline mr-1" />
              <span>{isPipelineComplete ? "Active & Monitoring" : "Standing by..."}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Content Grid: Autonomous Stages Stepper & Details */}
      <div className="bg-white rounded-3xl shadow-sm border border-slate-200 p-6 md:p-8">
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Autonomous Execution Pipeline</h2>
            <p className="text-slate-500 text-sm mt-0.5">
              Live event stream of background AI workers executing on your behalf
            </p>
          </div>
          <div className="flex items-center space-x-2 text-xs font-medium text-slate-500 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
            <RotateCw size={12} className={`text-blue-600 ${!isPipelineComplete ? "animate-spin" : ""}`} />
            <span>{!isPipelineComplete ? "Autonomous workers running" : "All background steps completed"}</span>
          </div>
        </div>

        {/* Vertical Stepper with Rich Context Cards */}
        <div className="relative pl-6 md:pl-8 space-y-8 before:absolute before:left-3 md:before:left-4 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
          {STAGES.map((stage, idx) => {
            const status = getStageStatus(stage.key);
            const entry = getStageEntry(stage.key);
            const isCompleted = status === "COMPLETED";
            const isActive = status === "ACTIVE";

            return (
              <div key={stage.key} className="relative group">
                {/* Node Indicator */}
                <div
                  className={`absolute -left-6 md:-left-8 top-0.5 w-6 h-6 md:w-8 md:h-8 rounded-full flex items-center justify-center border-2 transition-all ${
                    isCompleted
                      ? "bg-emerald-600 border-emerald-600 text-white shadow-sm shadow-emerald-500/30"
                      : isActive
                      ? "bg-blue-600 border-blue-600 text-white animate-pulse"
                      : "bg-white border-slate-300 text-slate-400"
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 size={16} />
                  ) : isActive ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <span className="text-xs font-semibold">{idx + 1}</span>
                  )}
                </div>

                {/* Content Box */}
                <div
                  className={`rounded-2xl p-5 border transition-all ${
                    isCompleted
                      ? "bg-slate-50/70 border-slate-200"
                      : isActive
                      ? "bg-blue-50/50 border-blue-300 ring-2 ring-blue-500/10"
                      : "bg-white border-slate-200/60 opacity-60"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <stage.icon
                        size={18}
                        className={isCompleted ? "text-emerald-600" : isActive ? "text-blue-600" : "text-slate-400"}
                      />
                      <h3
                        className={`text-base font-bold ${
                          isCompleted ? "text-slate-900" : isActive ? "text-blue-900" : "text-slate-600"
                        }`}
                      >
                        {stage.label}
                      </h3>
                    </div>

                    {isCompleted && (
                      <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-100/80 px-2.5 py-0.5 rounded-full">
                        Completed
                      </span>
                    )}
                    {isActive && (
                      <span className="text-[11px] font-semibold text-blue-700 bg-blue-100 px-2.5 py-0.5 rounded-full animate-pulse">
                        In Progress
                      </span>
                    )}
                    {!isCompleted && !isActive && (
                      <span className="text-[11px] font-medium text-slate-400">Waiting</span>
                    )}
                  </div>

                  <p className="text-xs text-slate-500 mt-1">{stage.desc}</p>

                  {/* Stage Details / Result */}
                  {entry && (
                    <div className="mt-3 text-sm text-slate-700 bg-white rounded-xl p-3.5 border border-slate-200 shadow-2xs">
                      <p className="font-medium text-slate-800">{entry.message}</p>

                      {/* Display Photo Proof, GPS, and Diagnostics in initial stages */}
                      {stage.key === "RECEIVED" && (
                        <div className="mt-2.5 flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                          {photoPreview && (
                            <div className="inline-flex items-center space-x-2 p-1 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                              <img src={photoPreview} alt="Proof" className="w-8 h-8 object-cover rounded-md border" />
                              <span className="text-[11px] font-semibold text-emerald-700 pr-1">Photo Evidence Attached ✓</span>
                            </div>
                          )}
                          {gpsCoords && (
                            <span className="text-[11px] font-mono font-medium text-blue-700 bg-blue-50 border border-blue-200 px-2 py-1 rounded-lg">
                              📍 GPS: {gpsCoords.latitude.toFixed(4)}° N, {gpsCoords.longitude.toFixed(4)}° E
                            </span>
                          )}
                        </div>
                      )}

                      {stage.key === "UNDERSTOOD" && diagnosticDetails && Object.keys(diagnosticDetails).length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-slate-100">
                          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                            Recorded Diagnostic Details:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {Object.entries(diagnosticDetails).map(([k, v]) => (
                              <span key={k} className="text-xs bg-slate-100 text-slate-800 border border-slate-200 px-2.5 py-0.5 rounded-lg font-medium">
                                {v}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Interactive Location Confirmation (Stage 3) */}
                      {stage.key === "LOCATION_RESOLVED" && (
                        <div className="mt-3 pt-3 border-t border-slate-100">
                          {!isEditingLocation ? (
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <span className="text-xs text-slate-500">
                                Resolved Ward: <strong className="text-slate-800">{pipelineData.location || "Automatic"}</strong>
                              </span>
                              <button
                                onClick={() => {
                                  setCustomLocation(pipelineData.location || "");
                                  setIsEditingLocation(true);
                                }}
                                className="text-xs font-semibold text-blue-600 hover:text-blue-700 underline"
                              >
                                Need to correct location?
                              </button>
                            </div>
                          ) : (
                            <div className="space-y-2 mt-2">
                              <label className="text-xs font-semibold text-slate-700 block">
                                Correct Locality / Landmark:
                              </label>
                              <div className="flex gap-2">
                                <input
                                  type="text"
                                  value={customLocation}
                                  onChange={(e) => setCustomLocation(e.target.value)}
                                  className="flex-1 text-xs px-3 py-2 border rounded-lg outline-none focus:border-blue-500"
                                  placeholder="e.g. Ward 104, Madhapur, Street 4"
                                />
                                <button
                                  onClick={handleConfirmLocation}
                                  disabled={isSavingLocation}
                                  className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700"
                                >
                                  {isSavingLocation ? "Saving..." : "Confirm"}
                                </button>
                                <button
                                  onClick={() => setIsEditingLocation(false)}
                                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-200"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Interactive Draft Review & Citizen Confirmation (Stage 5) */}
                      {stage.key === "DRAFTED" && (
                        <div className="mt-3 pt-3 border-t border-slate-100">
                          <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200/90 text-amber-950 space-y-3">
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-center space-x-2">
                                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
                                <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900">
                                  Citizen Confirmation Required Before Authority Filing
                                </h4>
                              </div>
                              {pipelineData.status === "DRAFTED" && !draftConfirmed && (
                                <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-200 text-amber-900 uppercase">
                                  Awaiting Approval
                                </span>
                              )}
                            </div>

                            {/* Draft Title & Petition Body */}
                            <div className="bg-white p-3.5 rounded-xl border border-amber-200/70 shadow-2xs space-y-2">
                              <p className="text-xs font-bold text-slate-900">
                                {entry.details?.title || "Formal Civic Grievance Petition"}
                              </p>

                              {!isEditingDraft ? (
                                <p className="text-xs text-slate-700 whitespace-pre-line leading-relaxed font-sans bg-slate-50 p-3 rounded-lg border border-slate-200/80">
                                  {editedDraftBody || entry.details?.body || "Formal grievance petition drafted against municipal charter standards."}
                                </p>
                              ) : (
                                <textarea
                                  rows={5}
                                  value={editedDraftBody || entry.details?.body || ""}
                                  onChange={(e) => setEditedDraftBody(e.target.value)}
                                  className="w-full text-xs text-slate-800 p-2.5 border border-blue-400 rounded-lg outline-none focus:ring-1 focus:ring-blue-500 font-sans leading-relaxed"
                                  placeholder="Review or edit petition text..."
                                />
                              )}

                              <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                                <span>
                                  Target Department: <strong className="text-slate-800">{entry.details?.department || pipelineData.department_id || "Municipal Dept"}</strong>
                                </span>
                                <span>
                                  SLA Standard: <strong className="text-slate-800">{entry.details?.sla_rule || "48-Hour Legal Redressal"}</strong>
                                </span>
                              </div>
                            </div>

                            {/* Confirmation Actions */}
                            {pipelineData.status === "DRAFTED" && !draftConfirmed ? (
                              <div className="flex flex-wrap items-center gap-2 pt-1">
                                <button
                                  type="button"
                                  onClick={handleConfirmDraft}
                                  disabled={isConfirmingDraft}
                                  className="flex-1 sm:flex-initial inline-flex items-center justify-center space-x-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-sm transition active:scale-98"
                                >
                                  {isConfirmingDraft ? (
                                    <Loader2 size={14} className="animate-spin" />
                                  ) : (
                                    <CheckCircle2 size={14} />
                                  )}
                                  <span>{isConfirmingDraft ? "Filing Petition..." : "Confirm & Submit Petition to Authorities"}</span>
                                </button>

                                <button
                                  type="button"
                                  onClick={() => {
                                    if (!isEditingDraft && !editedDraftBody && entry.details?.body) {
                                      setEditedDraftBody(entry.details.body);
                                    }
                                    setIsEditingDraft(!isEditingDraft);
                                  }}
                                  className="px-3.5 py-2.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-semibold transition"
                                >
                                  {isEditingDraft ? "Save Edit" : "Edit Petition"}
                                </button>
                              </div>
                            ) : (
                              <div className="inline-flex items-center space-x-1.5 text-xs text-emerald-700 font-bold bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-xl">
                                <Check size={14} className="text-emerald-600" />
                                <span>Petition Confirmed by Citizen & Filed with Authority ✓</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Watchdog details badge (Stage 7) */}
                      {stage.key === "MONITORING" && (
                        <div className="mt-3 p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl flex items-start space-x-2.5 text-xs text-indigo-900">
                          <ShieldCheck size={16} className="text-indigo-600 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold block">SLA Watchdog Live</span>
                            <span>The civic authority SLA clock is active. If resolution fails by the deadline, SPANDAN automatically generates escalating legal appeals to higher municipal commissioners.</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Action Bar */}
        <div className="mt-10 pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
          <button
            onClick={() => {
              setPipelineData(null);
              setText("");
              setLocationInput("");
              setSearchParams({});
              navigate("/");
            }}
            className="w-full sm:w-auto px-5 py-2.5 border border-slate-200 rounded-xl text-slate-700 text-sm font-semibold hover:bg-slate-50 transition"
          >
            Report Another Issue
          </button>

          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <Link
              to={`/complaints/${pipelineData?.complaint_id}`}
              className="w-full sm:w-auto px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-sm font-semibold flex items-center justify-center space-x-2 shadow-md transition"
            >
              <span>View Full Dossier & SLA Watchdog</span>
              <ChevronRight size={16} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
