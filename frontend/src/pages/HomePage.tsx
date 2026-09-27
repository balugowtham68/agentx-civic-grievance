// @ts-nocheck
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Mic,
  Send,
  MapPin,
  Loader2,
  ArrowRight,
  Activity,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Cpu,
  Sparkles,
  Volume2,
  Copy,
  Check,
  ExternalLink,
  Crosshair,
  Search,
  Building2,
  ShieldCheck,
  Camera,
  Image as ImageIcon,
  Trash2,
  X,
  Navigation,
  Database,
  FileText,
  Layers,
  Clock,
  ArrowLeft,
  Edit3,
} from "lucide-react";
import { useLanguage } from "../context/LanguageContext";
import { spandanApi } from "../services/spandanApi";
import { validateCivicInput } from "../utils/civicValidator";

export default function HomePage() {
  const navigate = useNavigate();
  const {
    t,
    detectAndSetLanguage,
    detectAndSetAudio,
    activeLang,
    setSelectedLang,
    needsConfirmation,
    pendingLanguage,
    pendingLanguageName,
    confirmPendingLanguage,
    rejectPendingLanguage,
    detectionResult,
  } = useLanguage();

  const [text, setText] = useState("");
  const [location, setLocation] = useState("");
  const [status, setStatus] = useState<
    "IDLE" | "LISTENING" | "DETECTING" | "DETECTED" | "SUBMITTING"
  >("IDLE");
  const [detectedBanner, setDetectedBanner] = useState("");
  const [showDebugPanel, setShowDebugPanel] = useState(false);

  // Voice Mode: 'auto' (Multimodal Audio AI) or specific locale ('te-IN', 'ta-IN', 'kn-IN', 'hi-IN', 'en-IN')
  const [voiceLocale, setVoiceLocale] = useState<string>("auto");

  // Fast Acknowledgement & Autonomous Redressal state
  const [fastAck, setFastAck] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [geoLocating, setGeoLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [trackQuery, setTrackQuery] = useState("");
  const [trackLoading, setTrackLoading] = useState(false);
  const [trackError, setTrackError] = useState("");
  const [isVoiceInput, setIsVoiceInput] = useState(false);

  // Mandatory Photo Proof state
  const [photoData, setPhotoData] = useState<string | null>(null);
  const [photoName, setPhotoName] = useState<string | null>(null);
  const [photoSize, setPhotoSize] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Civic Validation & Nonsense Alert state
  const [validationAlert, setValidationAlert] = useState<{
    title: string;
    message: string;
    type?: "nonsense" | "gps" | "photo" | "general";
  } | null>(null);

  // PostgreSQL Problem Detection & Draft Confirmation state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [detectedData, setDetectedData] = useState<any>(null);
  const [selectedOption, setSelectedOption] = useState<any>(null);
  const [isReviewingDraft, setIsReviewingDraft] = useState(false);
  const [editableSubject, setEditableSubject] = useState("");
  const [editableBody, setEditableBody] = useState("");
  const [showEditDraft, setShowEditDraft] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<any>(null);

  // Clear validation alert when text changes
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    if (validationAlert?.type === "nonsense") {
      setValidationAlert(null);
    }
  };

  // Debounced auto-detection when user types
  useEffect(() => {
    if (!text.trim() || text.trim().length < 4 || status === "LISTENING") return;

    const timer = setTimeout(async () => {
      setStatus("DETECTING");
      const res = await detectAndSetLanguage(text);
      if (res && res.confidence_tier === "HIGH" && res.language) {
        setStatus("DETECTED");
        const langNames: Record<string, string> = {
          te: "తెలుగు గుర్తించబడింది",
          ta: "தமிழ் கண்டறியப்பட்டது",
          kn: "ಕನ್ನಡ పತ್ತೆಯಾಗಿದೆ",
          hi: "हिन्दी पहचानी गई",
          en: "English detected",
        };
        setDetectedBanner(langNames[res.language] || `${res.language_name} detected`);
        setTimeout(() => setStatus("IDLE"), 2500);
      } else {
        setStatus("IDLE");
      }
    }, 750);

    return () => clearTimeout(timer);
  }, [text]);

  // Mandatory Photo Upload Handler
  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setValidationAlert({
        title: "Invalid File Type",
        message: "Please select an image file (JPEG, PNG, WebP) as photo proof.",
        type: "photo",
      });
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setValidationAlert({
        title: "Photo File Too Large",
        message: "Photo size exceeds 10MB limit. Please capture or select a smaller photo.",
        type: "photo",
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setPhotoData(result);
      setPhotoName(file.name);
      setPhotoSize((file.size / (1024 * 1024)).toFixed(2) + " MB");
      if (validationAlert?.type === "photo") {
        setValidationAlert(null);
      }
    };
    reader.onerror = () => {
      setValidationAlert({
        title: "Photo Load Error",
        message: "Failed to read the selected image file. Please try again.",
        type: "photo",
      });
    };
    reader.readAsDataURL(file);
  };

  const handleRemovePhoto = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setPhotoData(null);
    setPhotoName(null);
    setPhotoSize(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Mandatory Live GPS Location Locator
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setGeoError("Geolocation is not supported by your browser");
      setValidationAlert({
        title: "📍 Live GPS Unavailable",
        message: "Your browser does not support automatic geolocation. Please allow location permissions in browser settings.",
        type: "gps",
      });
      return;
    }
    setGeoLocating(true);
    setGeoError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        setCoords({ lat: latitude, lng: longitude });
        setLocation(`GPS: ${latitude.toFixed(5)}° N, ${longitude.toFixed(5)}° E`);
        setGeoLocating(false);
        setGeoError(null);
        if (validationAlert?.type === "gps") {
          setValidationAlert(null);
        }
      },
      (err) => {
        console.warn("Geolocation error:", err);
        setGeoLocating(false);
        let errorMsg = "Unable to retrieve live GPS coordinates. Please check your browser location permissions.";
        if (err.code === 1) {
          errorMsg = "Location permission was denied. Please allow location access in your browser or device settings to lodge a civic grievance.";
        } else if (err.code === 2) {
          errorMsg = "GPS position unavailable. Please ensure your device GPS/location is enabled.";
        } else if (err.code === 3) {
          errorMsg = "GPS location request timed out. Please try clicking 'Acquire Live GPS' again.";
        }
        setGeoError(errorMsg);
        setValidationAlert({
          title: "📍 Live GPS Acquisition Failed",
          message: errorMsg,
          type: "gps",
        });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  // Step 1: Compare user data with PostgreSQL, figure out problem-related options, and draft
  const handleAnalyzeAndDraft = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setValidationAlert(null);

    // 1. Text & Nonsense Check
    const civicCheck = validateCivicInput(text);
    if (!civicCheck.isValid) {
      setValidationAlert({
        title: "⚠️ Meaningful Civic Grievance Required",
        message: civicCheck.error || "Please describe a real civic issue clearly before submitting.",
        type: "nonsense",
      });
      return;
    }

    // 2. Mandatory Live GPS Location Check
    if (!coords || coords.lat === null || coords.lng === null) {
      setValidationAlert({
        title: "📍 Live GPS Location is Mandatory",
        message: "Live GPS coordinates are mandatory to verify and map the civic grievance location. Please click 'Acquire Live GPS' below.",
        type: "gps",
      });
      handleGetLocation();
      return;
    }

    // 3. Mandatory Photo Proof Check
    if (!photoData || !photoData.trim()) {
      setValidationAlert({
        title: "📸 Photo Proof is Mandatory",
        message: "Photo proof of the civic problem is mandatory for automated verification and authority action. Please click 'Attach Photo Proof' below.",
        type: "photo",
      });
      if (fileInputRef.current) {
        fileInputRef.current.click();
      }
      return;
    }

    setIsAnalyzing(true);
    const res = await detectAndSetLanguage(text);
    const finalLang = res?.language || activeLang || "en";

    try {
      const resData = await spandanApi.detectProblemAndOptions({
        text: text.trim(),
        language: finalLang,
        latitude: coords.lat,
        longitude: coords.lng,
        photo_data: photoData,
        location: location || null,
      });
      setDetectedData(resData);
      setSelectedOption(resData.detected_problem);
      setEditableSubject(resData.draft.subject);
      setEditableBody(resData.draft.body);
      setIsReviewingDraft(true);
    } catch (err: any) {
      console.error("Problem analysis failed:", err);
      const errMsg =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to cross-check problem with database.";

      setValidationAlert({
        title: "Analysis Failed",
        message: errMsg,
        type: "general",
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Switch selected problem option from related options queried from PostgreSQL
  const handleSelectOption = (opt: any) => {
    setSelectedOption(opt);
    if (detectedData) {
      const locStr = detectedData.location_summary || location || "Ward 93";
      setEditableSubject(`Administrative Grievance: Urgent attention requested for ${opt.label} at ${locStr}`);
    }
  };

  // Step 2: Citizen Confirms Drafting -> Submits to PostgreSQL & Starts Autonomous Watchdog
  const handleConfirmAndSubmitDraft = async () => {
    setStatus("SUBMITTING");
    const finalLang = activeLang || "en";

    try {
      const ack = await spandanApi.submitFastComplaint({
        text: text.trim(),
        language: finalLang,
        channel: isVoiceInput ? "voice" : "text",
        location: location || detectedData?.location_summary || `GPS: ${coords?.lat.toFixed(5)}° N, ${coords?.lng.toFixed(5)}° E`,
        latitude: coords?.lat || null,
        longitude: coords?.lng || null,
        photo_data: photoData,
        confirmed_category: selectedOption?.category || detectedData?.detected_problem?.category,
        confirmed_department: selectedOption?.department_id || detectedData?.detected_problem?.department_id,
        draft_subject: editableSubject,
        draft_body: editableBody,
      });
      setFastAck(ack);
      setIsReviewingDraft(false);
      setStatus("IDLE");
    } catch (err: any) {
      console.error("Draft confirmation submission failed:", err);
      const errMsg =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to submit confirmed complaint.";

      setValidationAlert({
        title: "Submission Blocked",
        message: errMsg,
        type: "general",
      });
      setStatus("IDLE");
    }
  };

  // Backward-compatible submit alias
  const handleSubmit = (e: React.FormEvent) => {
    handleAnalyzeAndDraft(e);
  };

  // Track existing grievance by tracking ID
  const handleTrackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trackQuery.trim()) return;
    setTrackLoading(true);
    setTrackError("");
    try {
      const data = await spandanApi.getTimeline(trackQuery.trim().toUpperCase());
      setFastAck({
        complaint_id: data.complaint_id,
        tracking_id: data.tracking_id,
        status: data.current_status,
        message: "Loaded tracking details",
        created_at: new Date().toISOString(),
      });
      setTimeline(data);
    } catch (err: any) {
      setTrackError("Tracking ID not found. Please check and try again.");
    } finally {
      setTrackLoading(false);
    }
  };

  // Poll timeline every 3 seconds for active complaint
  useEffect(() => {
    if (!fastAck?.tracking_id) return;
    let isMounted = true;

    const fetchTimeline = async () => {
      try {
        const data = await spandanApi.getTimeline(fastAck.tracking_id);
        if (isMounted) {
          setTimeline(data);
        }
      } catch (err) {
        console.warn("Failed to fetch timeline:", err);
      }
    };

    fetchTimeline();
    const interval = setInterval(fetchTimeline, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [fastAck]);

  // Start Voice Input (Multimodal Audio Recorder + Browser Speech API)
  const startListening = async () => {
    setStatus("LISTENING");
    setIsVoiceInput(true);
    audioChunksRef.current = [];

    // 1. Start MediaRecorder for true multimodal audio analysis
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(250); // collect chunks every 250ms
    } catch (err) {
      console.warn("Microphone stream not accessible:", err);
    }

    // 2. Run browser Web Speech API in parallel for real-time live preview
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;

        const langMap: Record<string, string> = {
          te: "te-IN",
          ta: "ta-IN",
          kn: "kn-IN",
          hi: "hi-IN",
          ml: "ml-IN",
          en: "en-IN",
        };
        recognition.lang =
          voiceLocale !== "auto" ? voiceLocale : langMap[activeLang] || "te-IN";

        recognition.onresult = (event: any) => {
          let transcript = "";
          for (let i = 0; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
          }
          if (transcript.trim()) {
            setText(transcript);
          }
        };

        recognitionRef.current = recognition;
        recognition.start();
      } catch (err) {
        console.warn("Browser SpeechRecognition failed:", err);
      }
    }
  };

  // Stop Listening and Process Audio
  const stopListening = async () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }

    setStatus("DETECTING");

    // Wait a brief moment for final audio chunks to settle
    setTimeout(async () => {
      let resolvedText = text;
      if (audioChunksRef.current.length > 0) {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });

        try {
          // Send actual audio to backend multimodal pipeline
          const audioResult = await detectAndSetAudio(audioBlob);
          if (audioResult && audioResult.transcript) {
            resolvedText = audioResult.transcript;
            setText(audioResult.transcript);
            setStatus("DETECTED");

            const langNames: Record<string, string> = {
              te: "తెలుగు గుర్తించబడింది",
              ta: "தமிழ் கண்டறியப்பட்டது",
              kn: "ಕನ್ನಡ ಪತ್ತೆಯಾಗಿದೆ",
              hi: "हिन्दी पहचानी गई",
              en: "English detected",
            };
            setDetectedBanner(
              langNames[audioResult.result.language || ""] ||
                `${audioResult.result.language_name} detected`
            );
            setTimeout(() => setStatus("IDLE"), 2500);
            return;
          }
        } catch (err) {
          console.warn("Backend audio recognition error, using live speech transcription:", err);
        }
      }

      // If backend audio failed or browser speech already captured text, keep text and run language fusion
      if (resolvedText.trim() || text.trim()) {
        const finalText = (resolvedText || text).trim();
        const res = await detectAndSetLanguage(finalText);
        if (res && res.confidence_tier === "HIGH" && res.language) {
          setStatus("DETECTED");
          const langNames: Record<string, string> = {
            te: "తెలుగు గుర్తించబడింది",
            ta: "தமிழ் கண்டறியப்பட்டது",
            kn: "ಕನ್ನಡ ಪತ್ತೆಯಾಗಿದೆ",
            hi: "हिन्दी पहचानी गई",
            en: "English detected",
          };
          setDetectedBanner(langNames[res.language] || `${res.language_name} detected`);
          setTimeout(() => setStatus("IDLE"), 2500);
          return;
        }
      }

      setStatus("IDLE");
    }, 600);
  };

  const toggleListening = () => {
    if (status === "LISTENING") {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 md:py-16 w-full max-w-4xl mx-auto">
      {/* Hero Header */}
      <div className="text-center mb-6 w-full animate-in fade-in slide-in-from-bottom-3 duration-500">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-blue-50 text-blue-700 font-bold text-xs tracking-widest uppercase mb-4 border border-blue-100 shadow-xs">
          <Activity size={14} className="animate-pulse" />
          <span>{t.subtitle}</span>
        </div>
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-tight mb-3">
          {t.brand}
        </h1>
        <p className="text-lg md:text-xl text-slate-600 font-medium max-w-2xl mx-auto leading-relaxed">
          {t.heroTitle}
        </p>
      </div>

      {/* Voice Mode Selector Chips */}
      <div className="w-full flex items-center justify-center space-x-2 mb-6 overflow-x-auto py-1 px-2 text-xs">
        <span className="text-slate-400 font-semibold flex items-center space-x-1 shrink-0">
          <Volume2 size={14} />
          <span>Voice Model:</span>
        </span>
        <button
          onClick={() => setVoiceLocale("auto")}
          className={`px-3 py-1.5 rounded-full font-bold transition-all shrink-0 flex items-center space-x-1.5 ${
            voiceLocale === "auto"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
          }`}
        >
          <Sparkles size={13} />
          <span>AI Multimodal Auto</span>
        </button>
        <button
          onClick={() => setVoiceLocale("te-IN")}
          className={`px-3 py-1.5 rounded-full font-bold transition-all shrink-0 ${
            voiceLocale === "te-IN"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
          }`}
        >
          తెలుగు (Telugu)
        </button>
        <button
          onClick={() => setVoiceLocale("hi-IN")}
          className={`px-3 py-1.5 rounded-full font-bold transition-all shrink-0 ${
            voiceLocale === "hi-IN"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
          }`}
        >
          हिन्दी (Hindi)
        </button>
        <button
          onClick={() => setVoiceLocale("ta-IN")}
          className={`px-3 py-1.5 rounded-full font-bold transition-all shrink-0 ${
            voiceLocale === "ta-IN"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
          }`}
        >
          தமிழ் (Tamil)
        </button>
        <button
          onClick={() => setVoiceLocale("kn-IN")}
          className={`px-3 py-1.5 rounded-full font-bold transition-all shrink-0 ${
            voiceLocale === "kn-IN"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
          }`}
        >
          ಕನ್ನಡ (Kannada)
        </button>
        <button
          onClick={() => setVoiceLocale("en-IN")}
          className={`px-3 py-1.5 rounded-full font-bold transition-all shrink-0 ${
            voiceLocale === "en-IN"
              ? "bg-blue-600 text-white shadow-xs"
              : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
          }`}
        >
          English
        </button>
      </div>

      {/* Medium Confidence Confirmation Banner */}
      {needsConfirmation && (
        <div className="w-full mb-6 p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm animate-in fade-in duration-300">
          <div className="flex items-center space-x-3">
            <HelpCircle className="text-amber-600 shrink-0" size={24} />
            <div>
              <p className="font-bold text-sm">
                {pendingLanguage === "te"
                  ? "మీరు తెలుగు మాట్లాడుతున్నట్లు అనిపిస్తోంది. (It looks like you are speaking Telugu.)"
                  : `It looks like you are speaking ${pendingLanguageName}.`}
              </p>
              <p className="text-xs text-amber-700 mt-0.5">
                Is this correct? Click Yes to adapt the entire application.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={confirmPendingLanguage}
              className="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors"
            >
              {pendingLanguage === "te" ? "అవును (Yes)" : "Yes"}
            </button>
            <button
              onClick={rejectPendingLanguage}
              className="px-3 py-1.5 bg-white border border-amber-300 text-amber-800 hover:bg-amber-100 font-semibold text-xs rounded-xl transition-colors"
            >
              {pendingLanguage === "te" ? "కాదు (No)" : "No"}
            </button>
          </div>
        </div>
      )}

      {/* Low Confidence Guidance Banner */}
      {detectionResult &&
        detectionResult.confidence_tier === "LOW" &&
        text.trim().length > 6 && (
          <div className="w-full mb-6 p-4 rounded-2xl bg-slate-100 border border-slate-200 text-slate-700 flex items-center space-x-3 shadow-xs animate-in fade-in duration-300">
            <AlertCircle className="text-slate-500 shrink-0" size={20} />
            <div className="text-xs">
              <span className="font-bold">
                భాషను ఖచ్చితంగా గుర్తించలేకపోయాము:
              </span>{" "}
              దయచేసి పైన ఉన్న భాషల జాబితా నుండి మీ భాషను ఎంచుకోండి. (Could not detect language with high confidence. Please choose your language from the top selector.)
            </div>
          </div>
        )}

      {/* Grievance Lodged Autonomous Redressal View */}
      {fastAck ? (
        <div className="w-full bg-white rounded-3xl shadow-xl shadow-slate-200/70 border border-slate-200 p-6 md:p-8 animate-in fade-in zoom-in-95 duration-400">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-100 gap-4">
            <div>
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 font-bold text-xs tracking-wider uppercase mb-2 border border-emerald-200">
                <CheckCircle2 size={14} />
                <span>Grievance Lodged Successfully</span>
              </div>
              <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                SPANDAN AI is Working For You
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                You can safely close this page. Our autonomous AI watchdog continues working after you leave.
              </p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-col items-start md:items-end shrink-0">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">
                Official Tracking ID
              </span>
              <div className="flex items-center space-x-2 mt-1">
                <span className="font-mono text-xl font-black text-blue-600 tracking-wide">
                  {fastAck.tracking_id}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(fastAck.tracking_id);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="p-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-600 transition-colors"
                  title="Copy Tracking ID"
                >
                  {copied ? <Check size={16} className="text-emerald-600" /> : <Copy size={16} />}
                </button>
              </div>
            </div>
          </div>

          {/* Autonomous Status Pipeline */}
          <div className="py-6 border-b border-slate-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase">
                Autonomous Redressal Progress
              </h3>
              {timeline?.current_status && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  Status: {timeline.current_status}
                </span>
              )}
            </div>

            <div className="space-y-4">
              {(timeline?.stages || [
                { stage: "RECEIVED", label: "Complaint Received", description: "Citizen grievance received and tracking ID issued.", status: "COMPLETED" },
                { stage: "UNDERSTOOD", label: "Language & Facts Extracted", description: "AI extracting issue facts, duration, and locality.", status: "IN_PROGRESS" },
                { stage: "CLASSIFIED", label: "Responsible Department Identified", description: "Routing to civic jurisdiction and department.", status: "PENDING" },
                { stage: "DRAFTED", label: "Formal Grievance Drafted", description: "Bilingual administrative complaint preparation.", status: "PENDING" },
                { stage: "FILED", label: "Filed with Civic Authority", description: "Lodged with municipal authority system.", status: "PENDING" },
                { stage: "MONITORING", label: "SLA Monitoring Active", description: "Automated watchdog active for escalation.", status: "PENDING" },
              ]).map((st: any) => {
                const isDone = st.status === "COMPLETED";
                const isCurrent = st.status === "IN_PROGRESS";

                return (
                  <div key={st.stage} className="flex items-start space-x-3.5">
                    <div className="mt-0.5 shrink-0">
                      {isDone ? (
                        <div className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow-xs">
                          <CheckCircle2 size={15} />
                        </div>
                      ) : isCurrent ? (
                        <div className="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center animate-pulse shadow-xs">
                          <Loader2 size={13} className="animate-spin" />
                        </div>
                      ) : (
                        <div className="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 text-slate-300 flex items-center justify-center">
                          <div className="w-2 h-2 rounded-full bg-slate-300" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className={`text-sm font-bold ${isCurrent ? "text-blue-700" : isDone ? "text-slate-900" : "text-slate-400"}`}>
                          {st.label}
                        </span>
                        {isCurrent && (
                          <span className="text-[10px] font-bold px-2 py-0.2 bg-blue-100 text-blue-700 rounded-full animate-pulse">
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                        {st.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Department & Location metadata if resolved */}
          {(timeline?.department || timeline?.location) && (
            <div className="py-4 border-b border-slate-100 flex flex-wrap gap-4 text-xs">
              {timeline.location && (
                <div className="flex items-center text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                  <MapPin size={14} className="text-slate-400 mr-1.5" />
                  <span><strong>Location:</strong> {timeline.location}</span>
                </div>
              )}
              {timeline.department && (
                <div className="flex items-center text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                  <Building2 size={14} className="text-slate-400 mr-1.5" />
                  <span><strong>Assigned Authority:</strong> {timeline.department} ({timeline.jurisdiction || "Civic"})</span>
                </div>
              )}
            </div>
          )}

          {/* Mandatory Evidence & GPS Verification Summary */}
          <div className="py-4 border-b border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* GPS Location Proof */}
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-start space-x-3">
              <div className="p-2 rounded-xl bg-emerald-100 text-emerald-700 shrink-0 mt-0.5">
                <MapPin size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] font-extrabold uppercase tracking-wider text-emerald-700">
                    Live GPS Verified ✓
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                    Official
                  </span>
                </div>
                <p className="text-xs font-semibold text-slate-800 mt-1 truncate">
                  {timeline?.location || fastAck.location_summary || location || (coords ? `GPS: ${coords.lat.toFixed(5)}° N, ${coords.lng.toFixed(5)}° E` : "Satellite Pinpoint Recorded")}
                </p>
                {(coords || timeline?.gps_coordinates) && (
                  <a
                    href={`https://www.google.com/maps?q=${coords?.lat || timeline?.gps_coordinates?.latitude},${coords?.lng || timeline?.gps_coordinates?.longitude}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center space-x-1 text-[11px] text-blue-600 hover:text-blue-800 font-bold mt-1.5 transition-colors"
                  >
                    <span>View on Google Maps</span>
                    <ExternalLink size={12} />
                  </a>
                )}
              </div>
            </div>

            {/* Photo Proof Evidence */}
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-start space-x-3">
              <div className="p-2 rounded-xl bg-blue-100 text-blue-700 shrink-0 mt-0.5">
                <ShieldCheck size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] font-extrabold uppercase tracking-wider text-blue-700">
                    Photo Proof Verified ✓
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Attached
                  </span>
                </div>
                {(photoData || timeline?.photo_url) ? (
                  <div className="mt-2 flex items-center space-x-3">
                    <img
                      src={photoData || timeline?.photo_url}
                      alt="Submitted grievance proof"
                      className="w-12 h-12 object-cover rounded-xl border border-slate-300 shadow-2xs cursor-pointer hover:opacity-85 transition-opacity"
                      onClick={() => {
                        const win = window.open();
                        win?.document.write(`<img src="${photoData || timeline?.photo_url}" style="max-width:100%; height:auto;" />`);
                      }}
                      title="Click to view full photo"
                    />
                    <div className="text-[11px] text-slate-500">
                      <p className="font-semibold text-slate-700 truncate max-w-[140px]">{photoName || "Photo evidence"}</p>
                      <p className="text-[10px] text-blue-600 font-medium">Click image to expand</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-600 mt-1">Photo evidence linked to administrative audit</p>
                )}
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <button
              type="button"
              onClick={() => {
                setFastAck(null);
                setTimeline(null);
                setText("");
                setLocation("");
                setCoords(null);
                setPhotoData(null);
                setPhotoName(null);
                setPhotoSize(null);
                setValidationAlert(null);
              }}
              className="text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
            >
              + File Another Complaint
            </button>

            <button
              type="button"
              onClick={() => navigate(`/complaints/${fastAck.complaint_id}`)}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-900 text-white font-bold text-xs hover:bg-slate-800 transition-colors shadow-sm"
            >
              <span>View Full Audit Trail & Evidence</span>
              <ExternalLink size={14} />
            </button>
          </div>
        </div>
      ) : isReviewingDraft && detectedData ? (
        /* Problem Detection & Citizen Draft Confirmation View */
        <div className="w-full bg-white rounded-3xl shadow-xl shadow-slate-200/70 border border-slate-200 p-6 md:p-8 animate-in fade-in zoom-in-95 duration-300">
          {/* Header */}
          <div className="pb-5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 text-blue-700 font-bold text-xs tracking-wider uppercase mb-2 border border-blue-200 shadow-2xs">
                <Database size={13} className="text-blue-600" />
                <span>PostgreSQL Cross-Check & Problem Detection</span>
              </div>
              <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                Review Problem Options & Confirm Draft
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                SPANDAN AI compared your grievance with municipal database records. Select the appropriate problem option and confirm the administrative draft.
              </p>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl px-4 py-2 text-left md:text-right shrink-0">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">
                Database Records
              </span>
              <span className="text-sm font-black text-slate-700">
                {detectedData.total_db_complaints} Municipal Reports Active
              </span>
            </div>
          </div>

          {/* Section 1: Problem Detection & Problem-Related Options from PostgreSQL */}
          <div className="py-6 border-b border-slate-100 space-y-4">
            <div>
              <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase mb-2 flex items-center space-x-1.5">
                <Layers size={14} />
                <span>Detected Problem Category (from PostgreSQL Comparison)</span>
              </h3>

              {/* Selected Primary Option Card */}
              <div className="p-4 rounded-2xl bg-blue-50/80 border-2 border-blue-500 text-blue-950 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
                <div className="flex items-start space-x-3.5">
                  <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                    <CheckCircle2 size={20} />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h4 className="font-extrabold text-base text-slate-900">
                        {selectedOption?.label}
                      </h4>
                      {selectedOption?.label_local && selectedOption.label_local !== selectedOption.label && (
                        <span className="text-xs text-blue-700 font-bold bg-blue-100/80 px-2 py-0.5 rounded-md">
                          {selectedOption.label_local}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 mt-0.5 font-medium">
                      {selectedOption?.description}
                    </p>
                    <div className="flex flex-wrap items-center gap-2.5 mt-2.5 text-xs">
                      <span className="inline-flex items-center space-x-1 text-slate-600 font-semibold bg-white border border-slate-200 px-2.5 py-1 rounded-lg">
                        <Building2 size={13} className="text-slate-400" />
                        <span>{selectedOption?.department_name}</span>
                      </span>
                      <span className="inline-flex items-center space-x-1 text-amber-700 font-bold bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-lg">
                        <Clock size={13} />
                        <span>SLA: {selectedOption?.sla_hours} Hours</span>
                      </span>
                      <span className="inline-flex items-center space-x-1 text-emerald-700 font-bold bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg">
                        <Database size={13} />
                        <span>{selectedOption?.db_count || 0} matching reports in DB</span>
                      </span>
                    </div>
                  </div>
                </div>
                <span className="px-3 py-1 rounded-full text-[11px] font-bold bg-blue-600 text-white shadow-2xs self-start sm:self-auto shrink-0">
                  Active Selection ✓
                </span>
              </div>
            </div>

            {/* Problem-Related Options (Select / Switch) */}
            {detectedData.related_options && detectedData.related_options.length > 0 && (
              <div className="pt-2">
                <span className="text-xs font-bold text-slate-600 block mb-2.5">
                  Or switch to a problem-related option queried from PostgreSQL:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {detectedData.related_options.map((opt: any) => {
                    const isSelected = selectedOption?.category === opt.category;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => handleSelectOption(opt)}
                        className={`p-3 rounded-2xl border text-left transition-all ${
                          isSelected
                            ? "bg-blue-50 border-blue-500 ring-2 ring-blue-400"
                            : "bg-white hover:bg-slate-50 border-slate-200 text-slate-700"
                        } shadow-2xs cursor-pointer`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-900 truncate">
                            {opt.label}
                          </span>
                          <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md shrink-0 ml-1">
                            {opt.db_count} in DB
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 mt-1 truncate">
                          {opt.department_name} • {opt.sla_hours}h SLA
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* PostgreSQL Database Past Complaints Matched in Locality */}
            {detectedData.postgres_matches && detectedData.postgres_matches.length > 0 && (
              <div className="mt-3 p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-xs">
                <div className="flex items-center space-x-1.5 font-bold text-slate-700 mb-2">
                  <Database size={14} className="text-blue-600" />
                  <span>Similar Complaints in PostgreSQL Database (Locality Matches):</span>
                </div>
                <div className="space-y-1.5">
                  {detectedData.postgres_matches.map((m: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between text-[11px] bg-white p-2 rounded-xl border border-slate-200">
                      <div className="flex items-center space-x-2 truncate">
                        <span className="font-mono font-bold text-blue-600">{m.tracking_id}</span>
                        <span className="text-slate-700 truncate">{m.issue}</span>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600 shrink-0 ml-2">
                        {m.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Administrative Draft Generated for Confirmation */}
          <div className="py-6 border-b border-slate-100 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase flex items-center space-x-1.5">
                <FileText size={14} />
                <span>Generated Administrative Draft (Citizen Confirmation Required)</span>
              </h3>
              <button
                type="button"
                onClick={() => setShowEditDraft(!showEditDraft)}
                className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center space-x-1 cursor-pointer"
              >
                <Edit3 size={13} />
                <span>{showEditDraft ? "Done Editing" : "Edit Draft"}</span>
              </button>
            </div>

            <div className="bg-slate-50/90 border border-slate-200 rounded-2xl p-5 space-y-3.5">
              <div>
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block mb-1">
                  Official Subject
                </span>
                {showEditDraft ? (
                  <input
                    type="text"
                    value={editableSubject}
                    onChange={(e) => setEditableSubject(e.target.value)}
                    className="w-full text-sm font-bold text-slate-900 bg-white border border-slate-300 rounded-xl p-2.5 outline-none focus:border-blue-500"
                  />
                ) : (
                  <div>
                    <h4 className="font-bold text-sm text-slate-900 leading-snug">
                      {editableSubject}
                    </h4>
                    {detectedData.draft.subject_local && (
                      <p className="text-xs font-semibold text-blue-800 mt-1">
                        {detectedData.draft.subject_local}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Verified Location & Photo Attached */}
              <div className="flex flex-wrap gap-2.5 text-xs pt-1">
                <div className="flex items-center space-x-1.5 bg-white border border-slate-200 px-3 py-1.5 rounded-xl text-slate-700">
                  <MapPin size={14} className="text-emerald-600" />
                  <span className="font-semibold">
                    {coords ? `GPS: ${coords.lat.toFixed(4)}°, ${coords.lng.toFixed(4)}°` : detectedData.location_summary}
                  </span>
                </div>
                {photoData && (
                  <div className="flex items-center space-x-1.5 bg-white border border-slate-200 px-3 py-1.5 rounded-xl text-slate-700">
                    <img src={photoData} alt="Thumb" className="w-5 h-5 rounded object-cover" />
                    <span className="font-semibold text-emerald-700">✓ Photo Evidence Attached</span>
                  </div>
                )}
              </div>

              {/* Formal Grievance Description */}
              <div className="pt-2">
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block mb-1">
                  Formal Administrative Grievance Text
                </span>
                {showEditDraft ? (
                  <textarea
                    rows={6}
                    value={editableBody}
                    onChange={(e) => setEditableBody(e.target.value)}
                    className="w-full text-xs font-mono text-slate-800 bg-white border border-slate-300 rounded-xl p-3 outline-none focus:border-blue-500"
                  />
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl p-3.5 text-xs font-mono text-slate-700 whitespace-pre-line leading-relaxed max-h-48 overflow-y-auto">
                    {editableBody}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Section 3: Confirmation Actions */}
          <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <button
              type="button"
              onClick={() => setIsReviewingDraft(false)}
              className="text-xs font-bold text-slate-500 hover:text-slate-800 transition-colors flex items-center space-x-1.5 cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Edit Complaint Details</span>
            </button>

            <button
              type="button"
              onClick={handleConfirmAndSubmitDraft}
              disabled={status === "SUBMITTING"}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-7 py-3 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-sm shadow-md hover:shadow-lg transition-all active:scale-98 disabled:opacity-50 cursor-pointer"
            >
              {status === "SUBMITTING" ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Filing Confirmed Grievance...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} />
                  <span>Confirm & Lodge Official Grievance</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* Composer Card */
        <div className="w-full bg-white rounded-3xl shadow-xl shadow-slate-200/60 border border-slate-200/90 p-2 overflow-hidden relative">
          {/* Hidden File Input for Mandatory Photo Proof */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handlePhotoSelect}
            className="hidden"
          />

          {/* State Banner / Overlay */}
          {((status !== "IDLE" && status !== "SUBMITTING") || isAnalyzing) && (
            <div className="absolute inset-0 bg-white/95 backdrop-blur-xs z-20 flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-200">
              {isAnalyzing && (
                <>
                  <div className="w-14 h-14 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-3">
                    <Database size={28} className="animate-pulse" />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-1">
                    Comparing with Municipal Database (PostgreSQL)...
                  </h3>
                  <p className="text-xs text-slate-500 max-w-sm">
                    Cross-checking records, figuring problem-related options, and drafting administrative complaint...
                  </p>
                </>
              )}
              {status === "LISTENING" && (
                <>
                  <div className="relative mb-4">
                    <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center animate-ping absolute inset-0 opacity-75"></div>
                    <div className="w-20 h-20 bg-red-600 text-white rounded-full flex items-center justify-center relative shadow-md">
                      <Mic size={34} />
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-1">{t.listening}</h3>
                  <p className="text-slate-500 text-sm mb-6 max-w-sm">
                    {text ? `"${text}"` : "Recording speech in high-fidelity audio..."}
                  </p>
                  <button
                    type="button"
                    onClick={stopListening}
                    className="px-6 py-2.5 bg-slate-900 text-white rounded-full font-bold text-sm hover:bg-slate-800 transition-colors shadow-sm"
                  >
                    Done Speaking
                  </button>
                </>
              )}

              {status === "DETECTING" && (
                <>
                  <Loader2 size={36} className="text-blue-600 animate-spin mb-3" />
                  <h3 className="text-lg font-bold text-slate-900">
                    Transcribing & Analyzing Language Signals...
                  </h3>
                </>
              )}

              {status === "DETECTED" && (
                <>
                  <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-3">
                    <CheckCircle2 size={30} />
                  </div>
                  <h3 className="text-xl font-extrabold text-emerald-700">{detectedBanner}</h3>
                </>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col h-full">
            {/* Prominent Nonsense & Mandatory Validation Alert Banner */}
            {validationAlert && (
              <div className="mx-3 md:mx-4 mt-3 mb-1 p-4 rounded-2xl bg-rose-50 border-2 border-rose-300 text-rose-900 shadow-sm animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="flex items-start space-x-3">
                  <div className="p-2 rounded-xl bg-rose-200/80 text-rose-800 shrink-0 mt-0.5">
                    <AlertTriangle size={20} className="animate-pulse" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="font-black text-sm text-rose-950 tracking-tight">
                        {validationAlert.title}
                      </h4>
                      <button
                        type="button"
                        onClick={() => setValidationAlert(null)}
                        className="p-1 rounded-lg text-rose-400 hover:text-rose-700 hover:bg-rose-100 transition-colors ml-2"
                        title="Dismiss alert"
                      >
                        <X size={16} />
                      </button>
                    </div>
                    <p className="text-xs text-rose-800 font-semibold mt-1 leading-relaxed">
                      {validationAlert.message}
                    </p>

                    {/* Specific Actionable Help based on alert type */}
                    {validationAlert.type === "nonsense" && (
                      <div className="mt-2.5 pt-2 border-t border-rose-200 text-[11px] text-rose-700 font-medium">
                        💡 <strong>How to change your complaint:</strong> Clearly describe what is broken (e.g. <em>"Streetlight pole sparking near bus shelter"</em>, <em>"Sewage overflow on 4th cross road"</em>, or <em>"రోడ్డుపై పెద్ద గుంతలు పడ్డాయి"</em>).
                      </div>
                    )}

                    {validationAlert.type === "gps" && (
                      <div className="mt-2.5 pt-2 border-t border-rose-200 flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={handleGetLocation}
                          disabled={geoLocating}
                          className="px-3 py-1.5 bg-rose-700 hover:bg-rose-800 text-white rounded-xl text-xs font-bold shadow-xs transition-colors inline-flex items-center space-x-1.5"
                        >
                          <Crosshair size={14} />
                          <span>{geoLocating ? "Acquiring Coordinates..." : "Acquire Live GPS Now"}</span>
                        </button>
                      </div>
                    )}

                    {validationAlert.type === "photo" && (
                      <div className="mt-2.5 pt-2 border-t border-rose-200 flex items-center space-x-2">
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="px-3 py-1.5 bg-rose-700 hover:bg-rose-800 text-white rounded-xl text-xs font-bold shadow-xs transition-colors inline-flex items-center space-x-1.5"
                        >
                          <Camera size={14} />
                          <span>Attach Photo Proof Now</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Textarea for Complaint Description */}
            <div className="p-4 md:p-6 pb-3">
              <textarea
                value={text}
                onChange={handleTextChange}
                placeholder={t.placeholder}
                disabled={status === "SUBMITTING"}
                rows={4}
                className="w-full resize-none text-xl md:text-2xl text-slate-900 placeholder:text-slate-300 outline-none bg-transparent font-medium leading-relaxed"
              />
            </div>

            {/* Mandatory Verification Bar: Live GPS + Photo Proof */}
            <div className="px-4 md:px-6 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* 1. Live GPS Location (Mandatory) */}
              {coords ? (
                <div className="flex items-center justify-between p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 shadow-2xs">
                  <div className="flex items-center space-x-2.5 overflow-hidden">
                    <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0">
                      <CheckCircle2 size={18} />
                    </div>
                    <div className="truncate">
                      <div className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 flex items-center space-x-1">
                        <span>✓ Live GPS Verified</span>
                      </div>
                      <div className="text-xs font-mono font-bold text-slate-800 truncate">
                        {coords.lat.toFixed(4)}° N, {coords.lng.toFixed(4)}° E
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleGetLocation}
                    disabled={geoLocating}
                    className="text-[11px] font-bold text-emerald-700 hover:text-emerald-900 bg-white border border-emerald-200 px-2.5 py-1 rounded-lg hover:bg-emerald-100 transition-colors shrink-0 ml-2"
                    title="Update GPS coordinates"
                  >
                    {geoLocating ? <Loader2 size={12} className="animate-spin" /> : "Re-check"}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleGetLocation}
                  disabled={geoLocating}
                  className={`flex items-center justify-between p-3 rounded-2xl border text-left transition-all ${
                    validationAlert?.type === "gps"
                      ? "bg-rose-50 border-rose-300 text-rose-900 ring-2 ring-rose-400"
                      : "bg-amber-50/80 hover:bg-amber-100/90 border-amber-300 text-amber-900"
                  } shadow-2xs`}
                >
                  <div className="flex items-center space-x-2.5">
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                        validationAlert?.type === "gps" ? "bg-rose-600 text-white" : "bg-amber-500 text-white"
                      }`}
                    >
                      {geoLocating ? <Loader2 size={16} className="animate-spin" /> : <Crosshair size={18} />}
                    </div>
                    <div>
                      <div className="text-[10px] font-extrabold uppercase tracking-wider flex items-center space-x-1 text-amber-900">
                        <span>📍 Live GPS Location</span>
                        <span className="text-rose-600 font-black">* Mandatory</span>
                      </div>
                      <div className="text-xs font-semibold text-slate-600">
                        {geoLocating ? "Acquiring live coordinates..." : "Click to lock current GPS"}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-amber-800 bg-white/80 border border-amber-200 px-2 py-1 rounded-lg shrink-0">
                    {geoLocating ? "Locating..." : "Acquire"}
                  </span>
                </button>
              )}

              {/* 2. Photo Proof (Mandatory) */}
              {photoData ? (
                <div className="flex items-center justify-between p-2.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 shadow-2xs">
                  <div className="flex items-center space-x-2.5 overflow-hidden">
                    <img
                      src={photoData}
                      alt="Photo proof"
                      className="w-10 h-10 object-cover rounded-xl border border-emerald-300 shadow-2xs shrink-0"
                    />
                    <div className="truncate">
                      <div className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700 flex items-center space-x-1">
                        <span>✓ Photo Proof Attached</span>
                      </div>
                      <div className="text-xs font-semibold text-slate-700 truncate max-w-[130px]">
                        {photoName || "photo-evidence.jpg"}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemovePhoto}
                    className="text-[11px] font-bold text-rose-600 hover:text-rose-800 bg-white border border-rose-200 px-2.5 py-1.5 rounded-lg hover:bg-rose-50 transition-colors shrink-0 ml-2 flex items-center space-x-1"
                    title="Remove photo"
                  >
                    <Trash2 size={12} />
                    <span>Remove</span>
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className={`flex items-center justify-between p-3 rounded-2xl border text-left transition-all ${
                    validationAlert?.type === "photo"
                      ? "bg-rose-50 border-rose-300 text-rose-900 ring-2 ring-rose-400"
                      : "bg-blue-50/80 hover:bg-blue-100/90 border-blue-300 text-blue-900"
                  } shadow-2xs`}
                >
                  <div className="flex items-center space-x-2.5">
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                        validationAlert?.type === "photo" ? "bg-rose-600 text-white" : "bg-blue-600 text-white"
                      }`}
                    >
                      <Camera size={18} />
                    </div>
                    <div>
                      <div className="text-[10px] font-extrabold uppercase tracking-wider flex items-center space-x-1 text-blue-900">
                        <span>📸 Photo Proof</span>
                        <span className="text-rose-600 font-black">* Mandatory</span>
                      </div>
                      <div className="text-xs font-semibold text-slate-600">
                        Take photo or upload image proof
                      </div>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-blue-800 bg-white/80 border border-blue-200 px-2 py-1 rounded-lg shrink-0">
                    Upload
                  </span>
                </button>
              )}
            </div>

            {/* Bottom Input & Action Bar */}
            <div className="px-4 md:px-6 py-4 bg-slate-50/70 border-t border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4 rounded-b-2xl">
              {/* Location description input */}
              <div className="flex-1 flex items-center space-x-2 bg-white px-3.5 py-2.5 rounded-xl border border-slate-200 shadow-2xs">
                <MapPin size={18} className="text-slate-400 shrink-0" />
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder={coords ? `GPS: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}` : t.locationPlaceholder}
                  className="w-full text-sm font-medium outline-none text-slate-700 bg-transparent placeholder:text-slate-400"
                />
                <button
                  type="button"
                  onClick={handleGetLocation}
                  disabled={geoLocating}
                  className="p-1 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-blue-600 transition-colors shrink-0"
                  title="Use current GPS location"
                >
                  {geoLocating ? (
                    <Loader2 size={16} className="animate-spin text-blue-600" />
                  ) : (
                    <Crosshair size={16} />
                  )}
                </button>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-3 md:w-auto">
                <button
                  type="button"
                  onClick={toggleListening}
                  className={`flex-1 md:flex-none flex items-center justify-center space-x-2 px-6 py-3.5 rounded-xl font-bold transition-all shadow-xs ${
                    status === "LISTENING"
                      ? "bg-red-600 text-white hover:bg-red-700"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <Mic size={19} className={status === "LISTENING" ? "animate-pulse" : ""} />
                  <span>{status === "LISTENING" ? "Stop" : t.speak}</span>
                </button>

                <button
                  type="submit"
                  disabled={!text.trim() || isAnalyzing || status === "SUBMITTING"}
                  className="flex-1 md:flex-none flex items-center justify-center space-x-2 px-6 py-3.5 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md active:scale-98 cursor-pointer"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 size={19} className="animate-spin" />
                      <span>Comparing Database...</span>
                    </>
                  ) : (
                    <>
                      <span>Review & Confirm Draft</span>
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Quick Track Input Bar */}
      {!fastAck && (
        <div className="w-full mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
          <form onSubmit={handleTrackSubmit} className="flex items-center bg-white border border-slate-200 rounded-2xl p-1.5 shadow-xs w-full max-w-md">
            <Search size={16} className="text-slate-400 ml-2.5 mr-2 shrink-0" />
            <input
              type="text"
              value={trackQuery}
              onChange={(e) => setTrackQuery(e.target.value)}
              placeholder="Track grievance (e.g. SPN-4B9F12)..."
              className="w-full text-xs font-medium outline-none text-slate-700 placeholder:text-slate-400 bg-transparent"
            />
            <button
              type="submit"
              disabled={!trackQuery.trim() || trackLoading}
              className="px-4 py-1.5 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 disabled:opacity-50 transition-colors shrink-0"
            >
              {trackLoading ? <Loader2 size={13} className="animate-spin" /> : "Track"}
            </button>
          </form>
          {trackError && <span className="text-xs text-red-600 font-semibold">{trackError}</span>}
        </div>
      )}

      {/* How It Works Pipeline */}
      <div className="mt-14 w-full text-center">
        <h3 className="text-xs font-bold tracking-widest text-slate-400 uppercase mb-6">
          {t.howItWorks}
        </h3>

        <div className="flex flex-wrap items-center justify-center gap-2.5 text-xs font-bold text-slate-600">
          <div className="px-3.5 py-1.5 bg-white border border-slate-200 rounded-full shadow-2xs">
            {t.step1}
          </div>
          <ArrowRight size={14} className="text-slate-300 hidden md:block" />
          <div className="px-3.5 py-1.5 bg-white border border-slate-200 rounded-full shadow-2xs">
            {t.step2}
          </div>
          <ArrowRight size={14} className="text-slate-300 hidden md:block" />
          <div className="px-3.5 py-1.5 bg-white border border-slate-200 rounded-full shadow-2xs">
            {t.step3}
          </div>
          <ArrowRight size={14} className="text-slate-300 hidden md:block" />
          <div className="px-3.5 py-1.5 bg-blue-50 border border-blue-200 text-blue-700 rounded-full shadow-2xs">
            {t.step4}
          </div>
          <ArrowRight size={14} className="text-slate-300 hidden md:block" />
          <div className="px-3.5 py-1.5 bg-amber-50 border border-amber-200 text-amber-700 rounded-full shadow-2xs">
            {t.step5}
          </div>
        </div>
      </div>

      {/* Development & Demo Mode Diagnostics Panel */}
      <div className="mt-10 w-full">
        <button
          onClick={() => setShowDebugPanel(!showDebugPanel)}
          className="mx-auto flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 bg-slate-200/60 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
        >
          <Cpu size={14} />
          <span>Multi-Signal AI Diagnostics (Demo Mode)</span>
          {showDebugPanel ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showDebugPanel && (
          <div className="mt-4 p-5 rounded-2xl bg-slate-900 text-slate-200 text-xs font-mono border border-slate-800 shadow-lg animate-in fade-in duration-300">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
              <span className="font-bold text-slate-400 uppercase tracking-wider">
                Language Fusion Engine Live Signals
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-blue-900/60 text-blue-300 border border-blue-700 font-bold">
                {detectionResult?.confidence_tier || "IDLE"} CONFIDENCE
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-slate-400 block mb-1">Final Decision</span>
                <div className="text-sm font-bold text-white">
                  {detectionResult?.language_name || "None"} ({detectionResult?.language || "und"})
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Score: {detectionResult?.confidence ? `${(detectionResult.confidence * 100).toFixed(1)}%` : "0%"}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-slate-400 block mb-1">Fusion Method</span>
                <div className="text-sm font-bold text-emerald-400">
                  {detectionResult?.method || "None"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Reason: {detectionResult?.reason_code || "N/A"}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-slate-400 block mb-1">Script Analysis</span>
                <div className="text-sm font-bold text-blue-300">
                  {detectionResult?.signals?.script?.dominant_script || "None"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Native Ratio: {detectionResult?.signals?.script?.native_char_ratio ?? 0} | Code-Mixed:{" "}
                  {detectionResult?.signals?.script?.is_code_mixed ? "YES" : "NO"}
                </div>
              </div>
            </div>

            {/* Classifier Probabilities */}
            {detectionResult?.signals?.classifier?.probabilities && (
              <div className="pt-2 border-t border-slate-800">
                <span className="text-slate-400 block mb-2 font-bold">
                  N-Gram Classifier Probabilities:
                </span>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(detectionResult.signals.classifier.probabilities).map(
                    ([code, prob]) => (
                      <span
                        key={code}
                        className={`px-2.5 py-1 rounded-md text-[11px] border ${
                          code === detectionResult.language
                            ? "bg-blue-600/30 border-blue-500 text-blue-200 font-bold"
                            : "bg-slate-800 border-slate-700 text-slate-400"
                        }`}
                      >
                        {code.toUpperCase()}: {(prob * 100).toFixed(1)}%
                      </span>
                    )
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
