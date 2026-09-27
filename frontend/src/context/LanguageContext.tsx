import React, { createContext, useContext, useState } from "react";
import { useTranslations } from "../i18n/homeStrings";
import { spandanApi } from "../services/spandanApi";

export type ConfidenceTier = "HIGH" | "MEDIUM" | "LOW";

export interface DetectionSignals {
  audio?: { language?: string | null; confidence?: number | null; source?: string } | null;
  script?: { dominant_script?: string | null; script_language?: string | null; native_char_ratio?: number; latin_char_ratio?: number; is_code_mixed?: boolean } | null;
  lexical?: { language?: string | null; confidence?: number; marker_scores?: Record<string, number>; matched_markers?: string[]; english_loanword_count?: number } | null;
  classifier?: { predicted_language?: string | null; confidence?: number; probabilities?: Record<string, number> } | null;
  llm?: { language?: string | null; confidence?: number; reason_code?: string | null; executed?: boolean } | null;
}

export interface DetectionResult {
  language: string | null;
  language_name: string;
  confidence: number;
  confidence_tier: ConfidenceTier;
  needs_confirmation: boolean;
  method: string;
  reason_code: string;
  signals: DetectionSignals;
  english_translation?: string;
}

interface LanguageContextType {
  selectedLang: string; // 'auto' | 'en' | 'te' | 'ta' | 'kn' | 'hi'
  activeLang: string;   // 'en' | 'te' | 'ta' | 'kn' | 'hi'
  selectedLanguage: string;
  uiLanguage: string;
  detectedLanguage: string | null;
  languageConfidence: number;
  languageDetectionStatus: "IDLE" | "DETECTING" | "CONFIRMED" | "NEEDS_CONFIRMATION" | "FAILED";
  isUserLocked: boolean;
  confidenceTier: ConfidenceTier;
  needsConfirmation: boolean;
  pendingLanguage: string | null;
  pendingLanguageName: string | null;
  detectionResult: DetectionResult | null;
  setSelectedLang: (lang: string) => void;
  setSelectedLanguage: (lang: string) => void;
  setActiveLang: (lang: string) => void;
  setUiLanguage: (lang: string) => void;
  confirmPendingLanguage: () => void;
  rejectPendingLanguage: () => void;
  detectAndSetLanguage: (text: string, audioLang?: string, audioConf?: number) => Promise<DetectionResult | null>;
  detectAndSetAudio: (audioBlob: Blob) => Promise<{ transcript: string; result: DetectionResult } | null>;
  t: Record<string, string>;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedLang, setSelectedLangState] = useState<string>("auto");
  const [activeLang, setActiveLang] = useState<string>("en");
  const [isUserLocked, setIsUserLocked] = useState<boolean>(false);

  const [confidenceTier, setConfidenceTier] = useState<ConfidenceTier>("LOW");
  const [needsConfirmation, setNeedsConfirmation] = useState<boolean>(false);
  const [pendingLanguage, setPendingLanguage] = useState<string | null>(null);
  const [pendingLanguageName, setPendingLanguageName] = useState<string | null>(null);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);

  const setSelectedLang = (lang: string) => {
    setSelectedLangState(lang);
    if (lang !== "auto") {
      setActiveLang(lang);
      setIsUserLocked(true); // User explicit selection is authoritative!
      setNeedsConfirmation(false);
      setPendingLanguage(null);
    } else {
      setIsUserLocked(false);
    }
  };

  const confirmPendingLanguage = () => {
    if (pendingLanguage) {
      setActiveLang(pendingLanguage);
      setIsUserLocked(true); // Authoritative confirmation
    }
    setNeedsConfirmation(false);
    setPendingLanguage(null);
  };

  const rejectPendingLanguage = () => {
    setNeedsConfirmation(false);
    setPendingLanguage(null);
  };

  const detectAndSetLanguage = async (
    text: string,
    audioLang?: string,
    audioConf?: number
  ): Promise<DetectionResult | null> => {
    if (isUserLocked && selectedLang !== "auto") {
      return null;
    }

    try {
      const res = await spandanApi.detectLanguage(text, audioLang, audioConf);
      setDetectionResult(res);
      setConfidenceTier(res.confidence_tier);

      if (res.confidence_tier === "HIGH" && res.language && res.language !== "und") {
        setActiveLang(res.language);
        setNeedsConfirmation(false);
        setPendingLanguage(null);
        return res;
      } else if (res.confidence_tier === "MEDIUM" && res.language && res.language !== "und") {
        // Prompt user confirmation without switching immediately
        setPendingLanguage(res.language);
        setPendingLanguageName(res.language_name);
        setNeedsConfirmation(true);
        return res;
      } else {
        // LOW confidence or undetermined
        setNeedsConfirmation(false);
        setPendingLanguage(null);
        return res;
      }
    } catch (e) {
      console.error("Language detection error:", e);
    }
    return null;
  };

  const detectAndSetAudio = async (
    audioBlob: Blob
  ): Promise<{ transcript: string; result: DetectionResult } | null> => {
    try {
      const res = await spandanApi.detectAudio(audioBlob);
      const detection: DetectionResult = {
        language: res.language,
        language_name: res.language_name,
        confidence: res.confidence,
        confidence_tier: res.confidence_tier as ConfidenceTier,
        needs_confirmation: res.needs_confirmation,
        method: res.method,
        reason_code: res.reason_code,
        signals: res.signals,
        english_translation: res.english_translation,
      };

      setDetectionResult(detection);
      setConfidenceTier(detection.confidence_tier);

      if (detection.confidence_tier === "HIGH" && detection.language && detection.language !== "und") {
        setActiveLang(detection.language);
        setNeedsConfirmation(false);
        setPendingLanguage(null);
      } else if (detection.confidence_tier === "MEDIUM" && detection.language && detection.language !== "und") {
        setPendingLanguage(detection.language);
        setPendingLanguageName(detection.language_name);
        setNeedsConfirmation(true);
      } else {
        setNeedsConfirmation(false);
        setPendingLanguage(null);
      }

      return { transcript: res.transcript, result: detection };
    } catch (e) {
      console.error("Audio detection error:", e);
    }
    return null;
  };

  const t = useTranslations(activeLang);

  const languageDetectionStatus: "IDLE" | "DETECTING" | "CONFIRMED" | "NEEDS_CONFIRMATION" | "FAILED" =
    needsConfirmation ? "NEEDS_CONFIRMATION" : detectionResult ? "CONFIRMED" : "IDLE";

  return (
    <LanguageContext.Provider
      value={{
        selectedLang,
        activeLang,
        selectedLanguage: selectedLang,
        uiLanguage: activeLang,
        detectedLanguage: detectionResult?.language || null,
        languageConfidence: detectionResult?.confidence || 0,
        languageDetectionStatus,
        isUserLocked,
        confidenceTier,
        needsConfirmation,
        pendingLanguage,
        pendingLanguageName,
        detectionResult,
        setSelectedLang,
        setSelectedLanguage: setSelectedLang,
        setActiveLang,
        setUiLanguage: setActiveLang,
        confirmPendingLanguage,
        rejectPendingLanguage,
        detectAndSetLanguage,
        detectAndSetAudio,
        t,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
