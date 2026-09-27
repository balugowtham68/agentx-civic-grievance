import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Mic,
  MapPin,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Camera,
  Crosshair,
  X,
  Check,
  RotateCcw,
  ArrowRight,
  Radio,
} from "lucide-react";
import { useLanguage } from "../context/LanguageContext";
import { spandanApi } from "../services/spandanApi";
import { getDiagnosticQuestions } from "../data/multilingualDiagnostics";
import { fetchLiveDeviceLocation } from "../services/locationService";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import LanguageSelector, { SUPPORTED_LANGUAGES } from "../components/LanguageSelector";

type VoiceUIState = "READY" | "LISTENING" | "PROCESSING" | "CONFIRMATION" | "COMPLETED" | "ERROR";

export default function HomePage() {
  const navigate = useNavigate();
  const {
    t,
    selectedLang,
    activeLang,
    setActiveLang,
    needsConfirmation,
    pendingLanguage,
    pendingLanguageName,
    confirmPendingLanguage,
    rejectPendingLanguage,
    detectAndSetLanguage,
    detectAndSetAudio,
    isUserLocked,
  } = useLanguage();

  // Core UI State
  const [voiceState, setVoiceState] = useState<VoiceUIState>("READY");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form Fields
  const [text, setText] = useState("");
  const [location, setLocation] = useState("");
  const [detectedBanner, setDetectedBanner] = useState<string | null>(null);
  const [englishTranslation, setEnglishTranslation] = useState<string | null>(null);

  // Successful submission result
  const [submittedResult, setSubmittedResult] = useState<{
    complaintId: string;
    trackingId: string;
    status: string;
    message: string;
    createdAt: string;
  } | null>(null);

  // Diagnostic Questions State
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [diagnosticAnswers, setDiagnosticAnswers] = useState<Record<string, string>>({});

  // Civic Intent Validation
  const [civicValidation, setCivicValidation] = useState<{
    isCivic: boolean | null;
    category: string | null;
    message: string | null;
    questions: any[];
  }>({
    isCivic: null,
    category: null,
    message: null,
    questions: [],
  });

  // Photo Proof State (Preserved)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoData, setPhotoData] = useState<string | null>(null);
  const [photoName, setPhotoName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Live GPS State (Preserved)
  const [gpsCoords, setGpsCoords] = useState<{
    latitude: number;
    longitude: number;
    accuracy: number;
  } | null>(null);
  const [isAcquiringGps, setIsAcquiringGps] = useState(false);
  const [isLocationAutoDetected, setIsLocationAutoDetected] = useState(false);

  // Idempotency ref to prevent duplicate submissions
  const isSubmissionLockedRef = useRef(false);

  // Speech Recognition Hook
  const {
    isListening,
    transcript: liveTranscript,
    isSpeechSupported,
    startListening,
    stopListening,
    setTranscript,
    error: speechError,
  } = useSpeechRecognition({
    locale: activeLang,
    onInterimResult: (transcriptText) => {
      // Keep transcript updated while speaking; DO NOT change language mid-speech!
      setText(transcriptText);
      autoDetectCategoryFromText(transcriptText);
    },
    onError: (err) => {
      if (err === "permission-denied") {
        setErrorMessage(t.micPermissionRequired || "Microphone permission required.");
      }
    },
  });

  // Auto-fetch Live Device Location on mount
  useEffect(() => {
    handleAutoFetchLocation(false);
  }, []);

  // Sync voiceState with isListening
  useEffect(() => {
    if (isListening && voiceState !== "LISTENING") {
      setVoiceState("LISTENING");
    }
  }, [isListening, voiceState]);

  // Handle Location Acquisition (GPS)
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
        accuracy: res.accuracy,
      });
      setLocation(res.shortAddress || res.formattedAddress);
      setIsLocationAutoDetected(true);
    } catch (err: any) {
      console.warn("Auto-location fetch dismissed or failed:", err);
      if (manualPrompt) {
        alert("Could not access live location. Please grant location permissions in your browser.");
      }
    } finally {
      setIsAcquiringGps(false);
    }
  };

  // Handle Photo Select (Preserved)
  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      alert("Image is too large. Please select a photo under 10MB.");
      return;
    }

    setPhotoName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setPhotoPreview(result);
      setPhotoData(result);
    };
    reader.readAsDataURL(file);
  };

  const removePhoto = () => {
    setPhotoPreview(null);
    setPhotoData(null);
    setPhotoName(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Auto detect category from text
  const autoDetectCategoryFromText = (input: string) => {
    if (!input || input.trim().length < 3) return;
    const lower = input.toLowerCase();
    let detectedCat: string | null = null;
    if (
      lower.includes("road") ||
      lower.includes("pothole") ||
      lower.includes("గుంత") ||
      lower.includes("రోడ్") ||
      lower.includes("சாலை") ||
      lower.includes("குழி") ||
      lower.includes("ರಸ್ತೆ") ||
      lower.includes("ಗುಂಡಿ") ||
      lower.includes("सड़क") ||
      lower.includes("गड्ढ")
    ) {
      detectedCat = "ROAD_DAMAGE";
    } else if (
      lower.includes("water") ||
      lower.includes("pipeline") ||
      lower.includes("leak") ||
      lower.includes("నీరు") ||
      lower.includes("పైప్") ||
      lower.includes("తాగునీరు") ||
      lower.includes("தண்ணீர்") ||
      lower.includes("குழாய்") ||
      lower.includes("ನೀರು") ||
      lower.includes("ಪೈಪ್") ||
      lower.includes("पानी") ||
      lower.includes("जल")
    ) {
      detectedCat = "WATER_SUPPLY_LEAK";
    } else if (
      lower.includes("drain") ||
      lower.includes("sewage") ||
      lower.includes("sewer") ||
      lower.includes("gutter") ||
      lower.includes("మురుగు") ||
      lower.includes("కాలువ") ||
      lower.includes("சாக்கடை") ||
      lower.includes("ಒಳಚರಂಡಿ") ||
      lower.includes("ಚರಂಡಿ") ||
      lower.includes("नाली") ||
      lower.includes("सीवर")
    ) {
      detectedCat = "DRAINAGE_OVERFLOW";
    } else if (
      lower.includes("light") ||
      lower.includes("lamp") ||
      lower.includes("dark") ||
      lower.includes("లైట్") ||
      lower.includes("స్ట్రీట్") ||
      lower.includes("விளக்கு") ||
      lower.includes("ದೀಪ") ||
      lower.includes("लाइट") ||
      lower.includes("बत्ती")
    ) {
      detectedCat = "STREETLIGHT_OUTAGE";
    } else if (
      lower.includes("garbage") ||
      lower.includes("trash") ||
      lower.includes("waste") ||
      lower.includes("dump") ||
      lower.includes("చెత్త") ||
      lower.includes("కుప్ప") ||
      lower.includes("குப்பை") ||
      lower.includes("ಕಸ") ||
      lower.includes("कचरा")
    ) {
      detectedCat = "GARBAGE_ACCUMULATION";
    }

    if (detectedCat) {
      setSelectedCategory(detectedCat);
      setCivicValidation({
        isCivic: true,
        category: detectedCat,
        message: null,
        questions: getDiagnosticQuestions(detectedCat, activeLang),
      });
    }
  };

  const handleDiagnosticAnswer = (questionId: string, answer: string) => {
    setDiagnosticAnswers((prev) => {
      if (prev[questionId] === answer) {
        const copy = { ...prev };
        delete copy[questionId];
        return copy;
      }
      return {
        ...prev,
        [questionId]: answer,
      };
    });
  };

  // -------------------------------------------------------------
  // Voice Flow: Speak -> Done Speaking -> Process -> File/Confirm
  // -------------------------------------------------------------

  const handleStartSpeaking = async () => {
    setErrorMessage(null);
    setDetectedBanner(null);
    const success = await startListening(selectedLang !== "auto" ? selectedLang : undefined);
    if (success) {
      setVoiceState("LISTENING");
    }
  };

  // Idempotent Done Speaking handler (Section 8, 18, 19, 20)
  const handleDoneSpeaking = async () => {
    if (isSubmissionLockedRef.current) return;
    isSubmissionLockedRef.current = true;

    setVoiceState("PROCESSING");

    try {
      const { transcript: finalTranscript, audioBlob } = await stopListening();
      const speechText = finalTranscript || text;
      setText(speechText);

      let detectedLangCode = activeLang;
      let trans: string | null = null;

      // 1. If audio was recorded, process via multimodal audio identification
      if (audioBlob) {
        try {
          const audioResult = await detectAndSetAudio(audioBlob);
          if (audioResult) {
            if (audioResult.transcript && audioResult.transcript.trim()) {
              setText(audioResult.transcript);
              autoDetectCategoryFromText(audioResult.transcript);
            }
            if (audioResult.result?.language) {
              detectedLangCode = audioResult.result.language;
            }
            if (audioResult.result?.english_translation) {
              trans = audioResult.result.english_translation;
              setEnglishTranslation(trans);
            }
          }
        } catch (e) {
          console.warn("Audio LID fallback:", e);
        }
      }

      // 2. Multi-signal language identification on finalized transcript
      if (speechText.trim()) {
        autoDetectCategoryFromText(speechText);
        try {
          const res = await detectAndSetLanguage(speechText);
          if (res) {
            if (res.language) {
              detectedLangCode = res.language;
            }
            if (res.english_translation) {
              trans = res.english_translation;
              setEnglishTranslation(trans);
            }

            // Language switching rule (Section 5 & 18):
            // If user explicitly chose a language, it is authoritative.
            // If Auto Detect is active:
            if (!isUserLocked && selectedLang === "auto") {
              if (res.confidence_tier === "HIGH" && res.language && res.language !== "und") {
                // Confident: immediately switch the whole portal UI!
                setActiveLang(res.language);
                const nativeName = SUPPORTED_LANGUAGES.find((l) => l.code === res.language)?.native || res.language_name;
                setDetectedBanner(`${nativeName} (${Math.round(res.confidence * 100)}%)`);
              } else if (res.confidence_tier === "MEDIUM") {
                // Medium confidence: trigger confirmation prompt
                setDetectedBanner(`${res.language_name}`);
              }
            }
          }
        } catch (e) {
          console.warn("Language detect error:", e);
        }
      }

      // Small delay for citizen visual feedback of PROCESSING state
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Check if ready for auto-submission or requires confirmation
      const isGpsReady = gpsCoords !== null && gpsCoords.latitude !== undefined;
      const isPhotoReady = Boolean(photoData);

      if (isGpsReady && isPhotoReady && speechText.trim().length >= 4) {
        // All requirements satisfied: submit directly!
        await executeSubmission(speechText, detectedLangCode);
      } else {
        // Move to CONFIRMATION state so citizen can attach photo or confirm location
        setVoiceState("CONFIRMATION");
      }
    } catch (err: any) {
      console.error("Done speaking processing error:", err);
      setVoiceState("ERROR");
      setErrorMessage(err.message || t.serviceError || "Something went wrong.");
    } finally {
      isSubmissionLockedRef.current = false;
    }
  };

  // Execute submission safely
  const executeSubmission = async (complaintText: string, langCode: string) => {
    setIsSubmitting(true);
    setVoiceState("PROCESSING");

    try {
      const locLabel =
        location.trim() ||
        (gpsCoords
          ? `GPS: ${gpsCoords.latitude.toFixed(5)}° N, ${gpsCoords.longitude.toFixed(5)}° E`
          : "Location Pending");

      const ack = await spandanApi.submitComplaintFast({
        text: complaintText,
        language: langCode || activeLang || "en",
        location: locLabel,
        latitude: gpsCoords?.latitude ?? null,
        longitude: gpsCoords?.longitude ?? null,
        photo_data: photoData,
        photo_name: photoName,
        diagnostic_details: diagnosticAnswers,
      });

      setSubmittedResult({
        complaintId: ack.complaint_id,
        trackingId: ack.tracking_id,
        status: ack.status,
        message: ack.message,
        createdAt: ack.created_at,
      });

      setVoiceState("COMPLETED");
    } catch (err: any) {
      console.error("Submission error:", err);
      setVoiceState("ERROR");
      setErrorMessage(err.message || t.serviceError || "Failed to submit grievance.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || text.trim().length < 4) return;

    if (!gpsCoords || !photoData) {
      if (!gpsCoords && !photoData) {
        alert(`${t.gpsRequired || "Live GPS location is mandatory."} ${t.photoRequired || "Photographic proof is mandatory."}`);
      } else if (!gpsCoords) {
        alert(t.gpsRequired || "Live GPS location is mandatory.");
      } else {
        alert(t.photoRequired || "Photographic proof is mandatory.");
      }
      return;
    }

    await executeSubmission(text, activeLang);
  };

  const handleResetForNewComplaint = () => {
    setText("");
    setTranscript("");
    setPhotoPreview(null);
    setPhotoData(null);
    setPhotoName(null);
    setSelectedCategory(null);
    setDiagnosticAnswers({});
    setSubmittedResult(null);
    setDetectedBanner(null);
    setEnglishTranslation(null);
    setErrorMessage(null);
    setVoiceState("READY");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const isGpsValid = gpsCoords !== null && gpsCoords.latitude !== undefined;
  const isPhotoValid = Boolean(photoData);
  const isTextValid = text.trim().length >= 4;
  const canSubmit = isTextValid && isGpsValid && isPhotoValid && !isSubmitting && voiceState !== "LISTENING";

  const questionsToAsk = selectedCategory
    ? getDiagnosticQuestions(selectedCategory, activeLang)
    : civicValidation.questions?.length > 0
    ? civicValidation.questions
    : [];

  return (
    <div className="flex-1 flex flex-col items-center justify-start px-4 py-8 md:py-12 w-full max-w-2xl mx-auto font-sans">
      {/* ------------------------------------------------------------- */}
      {/* Header Container (Consistent Width & Centered Alignment)       */}
      {/* ------------------------------------------------------------- */}
      <div className="text-center mb-6 w-full">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-blue-50 text-blue-700 font-bold text-xs tracking-wider uppercase mb-3 border border-blue-200">
          <Sparkles size={14} className="text-blue-600" />
          <span>{t.brand || "SPANDAN AI"}</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
        </div>

        <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight leading-tight mb-2">
          {t.howCanWeHelp || "How can we help?"}
        </h1>

        <p className="text-slate-500 text-sm sm:text-base font-medium max-w-lg mx-auto">
          {t.heroDesc || "Speak or type naturally in your regional language. SPANDAN AI understands you and works autonomously until resolution."}
        </p>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Medium-Confidence Language Confirmation Banner (Section 6)   */}
      {/* ------------------------------------------------------------- */}
      {needsConfirmation && pendingLanguage && (
        <div className="w-full mb-5 p-4 rounded-2xl bg-indigo-50/90 border border-indigo-200 text-indigo-950 shadow-sm animate-in fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0">
                AI
              </div>
              <div>
                <p className="text-xs font-bold text-indigo-950">
                  {t.weThinkSpeaking
                    ? t.weThinkSpeaking.replace("{lang}", pendingLanguageName || "")
                    : `We think you're speaking ${pendingLanguageName}. Is that correct?`}
                </p>
                <p className="text-[11px] text-indigo-700">
                  {activeLang === "te"
                    ? "పోర్టల్ పూర్తిగా మీ ప్రాంతీయ భాషలోకి మారుతుంది."
                    : "The portal will switch completely to your regional language."}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2 shrink-0">
              <button
                type="button"
                onClick={confirmPendingLanguage}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-xs"
              >
                ✓ {t.yes || "Yes"}
              </button>
              <button
                type="button"
                onClick={rejectPendingLanguage}
                className="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-semibold transition"
              >
                {t.changeLanguage || "Change Language"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* Error Notice                                                  */}
      {/* ------------------------------------------------------------- */}
      {errorMessage && (
        <div className="w-full mb-5 p-4 rounded-2xl bg-red-50 border border-red-200 text-red-900 shadow-sm animate-in fade-in flex items-start space-x-3">
          <AlertCircle className="text-red-600 shrink-0 mt-0.5" size={18} />
          <div className="flex-1 text-xs font-medium">
            <p className="font-bold">{t.somethingWentWrong || "Something went wrong"}</p>
            <p className="mt-0.5 text-red-700">{errorMessage}</p>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-red-400 hover:text-red-700"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* SUCCESS STATE: Complaint Received & Tracking ID (Section 26)  */}
      {/* ------------------------------------------------------------- */}
      {voiceState === "COMPLETED" && submittedResult && (
        <div className="w-full bg-white rounded-3xl p-6 sm:p-8 border border-emerald-200 shadow-xl shadow-emerald-500/5 mb-6 text-center animate-in zoom-in-95 duration-300">
          <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm">
            <CheckCircle2 size={36} />
          </div>

          <h2 className="text-2xl font-black text-slate-900 mb-1">
            {t.complaintReceived || "Complaint received ✓"}
          </h2>
          <p className="text-xs text-slate-500 mb-5">
            {t.monitoringMessage || "SPANDAN AI will continue monitoring your complaint."}
          </p>

          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 max-w-sm mx-auto mb-6">
            <span className="text-xs uppercase font-bold tracking-wider text-slate-400 block mb-1">
              {t.trackingId || "Tracking ID"}
            </span>
            <span className="text-2xl font-black text-blue-600 tracking-wider font-mono">
              {submittedResult.trackingId}
            </span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => navigate(`/intake?id=${submittedResult.complaintId}`)}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold text-sm transition shadow-md"
            >
              <span>Track Resolution Timeline</span>
              <ArrowRight size={16} />
            </button>
            <button
              type="button"
              onClick={handleResetForNewComplaint}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-5 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-2xl font-semibold text-sm transition"
            >
              <RotateCcw size={15} />
              <span>{t.speakAgain || "File Another Grievance"}</span>
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* PROCESSING STATE (Section 7, 9, 26)                           */}
      {/* ------------------------------------------------------------- */}
      {voiceState === "PROCESSING" && (
        <div className="w-full bg-white rounded-3xl p-8 border border-slate-200 shadow-xl mb-6 text-center animate-in fade-in">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Loader2 size={36} className="animate-spin text-blue-600" />
          </div>

          <h3 className="text-xl font-black text-slate-900 mb-2">
            {t.processing || "Processing..."}
          </h3>
          <p className="text-xs text-slate-500 mb-6">
            {t.processingComplaint || "Processing your complaint..."}
          </p>

          <div className="space-y-2.5 max-w-sm mx-auto text-left bg-slate-50 p-4 rounded-2xl border border-slate-200 text-xs">
            <div className="flex items-center space-x-2 text-slate-700 font-semibold">
              <Check size={16} className="text-emerald-600" />
              <span>
                {t.language || "Language"}: <strong className="text-blue-600 uppercase">{activeLang}</strong>
              </span>
            </div>
            <div className="flex items-center space-x-2 text-slate-700 font-semibold">
              <Check size={16} className="text-emerald-600" />
              <span>{t.detectedLanguage || "Language detected"}</span>
            </div>
            <div className="flex items-center space-x-2 text-slate-700 font-semibold">
              <Check size={16} className="text-emerald-600" />
              <span>{t.complaintCaptured || "Complaint captured"}</span>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* LISTENING STATE (Section 7, 8, 9, 10, 26)                     */}
      {/* ------------------------------------------------------------- */}
      {voiceState === "LISTENING" && (
        <div className="w-full bg-white rounded-3xl p-6 sm:p-8 border border-red-200 shadow-xl shadow-red-500/5 mb-6 text-center animate-in fade-in">
          <div className="relative w-20 h-20 mx-auto mb-4 flex items-center justify-center">
            <div className="w-20 h-20 bg-red-100 rounded-full animate-ping absolute inset-0 opacity-60" />
            <div className="w-16 h-16 bg-red-600 text-white rounded-full flex items-center justify-center relative shadow-md">
              <Mic size={30} className="animate-pulse" />
            </div>
          </div>

          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-red-50 text-red-700 text-xs font-bold mb-2 border border-red-200">
            <Radio size={12} className="animate-pulse" />
            <span>{t.listening || "Listening..."}</span>
          </div>

          <p className="text-xs text-slate-500 mb-4 font-medium">
            {t.listeningHelp || "Speak in your regional language. SPANDAN AI will auto-detect your language."}
          </p>

          {/* Transcript Display (Section 10) */}
          <div className="w-full text-left mb-5">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1.5 px-1">
              {t.youSaid || "You said:"}
            </span>
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl min-h-[90px] max-h-48 overflow-y-auto">
              <p className="text-sm sm:text-base font-medium text-slate-800 leading-relaxed italic">
                {liveTranscript || text || "..."}
              </p>
            </div>
          </div>

          {/* Prominent Done Speaking Button (Section 8) */}
          <button
            type="button"
            onClick={handleDoneSpeaking}
            aria-label="Done speaking"
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-8 py-3.5 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl font-bold text-sm transition shadow-lg active:scale-98"
          >
            <Check size={18} />
            <span>{t.doneSpeaking || "Done Speaking"}</span>
          </button>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* REVIEW & CONFIRMATION STATE (Section 6, 21)                    */}
      {/* ------------------------------------------------------------- */}
      {voiceState === "CONFIRMATION" && (
        <div className="w-full bg-white rounded-3xl p-6 border border-blue-200 shadow-xl mb-6 animate-in fade-in">
          <div className="flex items-center space-x-2 text-blue-900 font-bold text-xs uppercase tracking-wider mb-4">
            <Sparkles size={16} className="text-blue-600" />
            <span>{t.reviewTitle || "We understood your complaint as follows:"}</span>
          </div>

          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 mb-4 space-y-3">
            <div>
              <span className="text-xs font-bold text-slate-400 block">{t.youSaid || "Your Grievance:"}</span>
              <p className="text-sm font-semibold text-slate-900">{text}</p>
            </div>

            {englishTranslation && activeLang !== "en" && (
              <div className="pt-2 border-t border-slate-200">
                <span className="text-xs font-bold text-slate-400 block">English Translation (For Officials):</span>
                <p className="text-sm font-medium text-slate-700 italic">"{englishTranslation}"</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 font-bold block">{t.location || "Location"}:</span>
                <span className="font-semibold text-slate-800">{location || "GPS Locked"}</span>
              </div>
              <div>
                <span className="text-slate-400 font-bold block">{t.language || "Language"}:</span>
                <span className="font-semibold text-emerald-700 uppercase">{activeLang}</span>
              </div>
            </div>
          </div>

          {/* Validation warnings if photo or GPS still missing */}
          {(!isGpsValid || !isPhotoValid) && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 font-medium">
              {!isGpsValid && <p>• {t.gpsRequired || "Live GPS location is mandatory."}</p>}
              {!isPhotoValid && <p>• {t.photoRequired || "Photographic proof is mandatory."}</p>}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => executeSubmission(text, activeLang)}
              disabled={!canSubmit}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-xl text-xs font-bold transition shadow-sm active:scale-98"
            >
              ✓ {t.confirmBtn || "Looks Correct — Proceed"}
            </button>
            <button
              type="button"
              onClick={() => setVoiceState("READY")}
              className="px-4 py-3 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-semibold transition"
            >
              ✏ {t.editBtn || "Edit"}
            </button>
            <button
              type="button"
              onClick={handleStartSpeaking}
              className="px-4 py-3 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-semibold transition inline-flex items-center space-x-1.5"
            >
              <RotateCcw size={13} />
              <span>{t.speakAgain || "Speak Again"}</span>
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* MAIN COMPOSITION CARD (Section 11, 12, 26)                    */}
      {/* ------------------------------------------------------------- */}
      {(voiceState === "READY" || voiceState === "ERROR") && (
        <div className="w-full bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-xl shadow-slate-200/50 mb-6 space-y-6">
          {/* Primary Voice Action (Section 11) */}
          <div>
            <button
              type="button"
              onClick={handleStartSpeaking}
              aria-label="Start speaking"
              className="w-full py-8 px-6 bg-gradient-to-b from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-2xl flex flex-col items-center justify-center space-y-3 transition-all shadow-md shadow-blue-500/20 active:scale-99 cursor-pointer group"
            >
              <div className="w-16 h-16 bg-white/15 rounded-full flex items-center justify-center group-hover:scale-105 transition-transform">
                <Mic size={32} className="text-white" />
              </div>
              <div className="text-center">
                <span className="text-lg sm:text-xl font-black block tracking-tight">
                  {t.speakComplaint || "Speak complaint"}
                </span>
                <span className="text-xs text-blue-100 font-medium">
                  {t.tapToSpeak || "Tap to speak in your regional language"}
                </span>
              </div>
            </button>

            {!isSpeechSupported && (
              <p className="mt-2 text-xs text-amber-700 text-center font-medium">
                {t.speechUnavailable || "Voice input is not available in this browser. Please type below."}
              </p>
            )}
          </div>

          {/* Divider: "or" */}
          <div className="relative flex items-center justify-center">
            <div className="border-t border-slate-200 w-full" />
            <span className="bg-white px-3 text-xs font-bold uppercase tracking-wider text-slate-400 absolute">
              {t.or || "or"}
            </span>
          </div>

          {/* Fallback Text Input */}
          <div>
            <label htmlFor="complaint-text" className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
              {t.typeComplaint || "Type your complaint"}
            </label>
            <textarea
              id="complaint-text"
              value={text}
              onChange={(e) => {
                const val = e.target.value;
                setText(val);
                autoDetectCategoryFromText(val);
              }}
              placeholder={t.placeholder || "Tell us what happened..."}
              rows={3}
              className="w-full p-4 rounded-2xl bg-slate-50 border border-slate-200 text-slate-800 placeholder:text-slate-400 text-sm font-medium outline-none focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20 transition-all resize-none leading-relaxed"
            />
          </div>

          {/* Diagnostic Details if Category Detected */}
          {questionsToAsk.length > 0 && (
            <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-200 animate-in fade-in">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-900 block mb-2">
                Diagnostic Details
              </span>
              <div className="space-y-3">
                {questionsToAsk.map((q: any) => (
                  <div key={q.id}>
                    <p className="text-xs font-semibold text-slate-800 mb-1.5">{q.question}</p>
                    <div className="flex flex-wrap gap-2">
                      {q.options.map((opt: string) => {
                        const isChosen = diagnosticAnswers[q.id] === opt;
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

          {/* Location Control (Section 12: Consistent Central Alignment) */}
          <div>
            <label htmlFor="location-input" className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
              {t.location || "Location"}
            </label>
            <div className="flex items-center space-x-2 bg-slate-50 border border-slate-200 rounded-2xl px-3.5 py-2.5 focus-within:bg-white focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
              <MapPin size={18} className={isLocationAutoDetected ? "text-emerald-600 shrink-0" : "text-slate-400 shrink-0"} />
              <input
                id="location-input"
                type="text"
                value={location}
                onChange={(e) => {
                  setLocation(e.target.value);
                  setIsLocationAutoDetected(false);
                }}
                placeholder={t.enterLocation || "Locality, street name or landmark"}
                className="w-full bg-transparent text-sm font-medium text-slate-800 outline-none placeholder:text-slate-400"
              />
              <button
                type="button"
                onClick={() => handleAutoFetchLocation(true)}
                disabled={isAcquiringGps}
                aria-label="Use my location"
                className={`shrink-0 flex items-center space-x-1 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                  isGpsValid
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-300"
                    : "bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200"
                }`}
              >
                {isAcquiringGps ? (
                  <Loader2 size={13} className="animate-spin text-blue-600" />
                ) : isGpsValid ? (
                  <Check size={13} className="text-emerald-600" />
                ) : (
                  <Crosshair size={13} className="text-blue-600" />
                )}
                <span>
                  {isAcquiringGps ? "Detecting..." : isGpsValid ? t.gpsReady || "GPS Ready ✓" : t.useMyLocation || "Use my location"}
                </span>
              </button>
            </div>
          </div>

          {/* Photo Proof Control (Preserved) */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
              {t.photoRequired || "Photo Proof *"}
            </label>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handlePhotoSelect}
              accept="image/*"
              capture="environment"
              className="hidden"
            />

            {!photoPreview ? (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                aria-label="Attach photo proof"
                className="w-full flex items-center justify-center space-x-2 py-3 px-4 rounded-2xl border border-dashed border-slate-300 hover:border-blue-400 hover:bg-blue-50/30 text-slate-600 text-xs font-bold transition-all cursor-pointer"
              >
                <Camera size={16} className="text-slate-400" />
                <span>Take Photo Proof or Upload Image</span>
              </button>
            ) : (
              <div className="flex items-center space-x-3 p-2.5 bg-slate-50 rounded-2xl border border-slate-200">
                <img
                  src={photoPreview}
                  alt="Proof preview"
                  className="w-12 h-12 object-cover rounded-xl border border-slate-300"
                />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-bold text-slate-800 block truncate">
                    {photoName || "Photo Proof"}
                  </span>
                  <span className="text-[11px] text-emerald-600 font-semibold flex items-center">
                    <Check size={12} className="mr-1" />
                    {t.photoAttached || "Photo Attached ✓"}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={removePhoto}
                  className="p-1 rounded-full text-slate-400 hover:text-red-600 hover:bg-slate-200 transition"
                  title="Remove photo"
                >
                  <X size={16} />
                </button>
              </div>
            )}
          </div>

          {/* Language Selector (Section 3, 12) */}
          <div>
            <LanguageSelector variant="dropdown" />
          </div>

          {/* Submit Button (Section 12, 20) */}
          <div>
            <button
              type="button"
              onClick={handleManualSubmit}
              disabled={!canSubmit}
              className="w-full py-3.5 px-6 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-2xl font-bold text-sm transition-all shadow-md active:scale-99 cursor-pointer flex items-center justify-center space-x-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>{t.processing || "Processing..."}</span>
                </>
              ) : (
                <span>{t.submit || "Submit Complaint"}</span>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
