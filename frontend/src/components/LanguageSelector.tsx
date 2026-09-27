import { Globe, ChevronDown } from "lucide-react";
import { useLanguage } from "../context/LanguageContext";

export const SUPPORTED_LANGUAGES = [
  { code: "auto", label: "Auto Detect", native: "Auto Detect", flag: "✨" },
  { code: "en", label: "English", native: "English", flag: "🇬🇧" },
  { code: "te", label: "Telugu", native: "తెలుగు", flag: "🇮🇳" },
  { code: "ta", label: "Tamil", native: "தமிழ்", flag: "🇮🇳" },
  { code: "kn", label: "Kannada", native: "ಕನ್ನಡ", flag: "🇮🇳" },
  { code: "hi", label: "Hindi", native: "हिन्दी", flag: "🇮🇳" },
];

interface LanguageSelectorProps {
  className?: string;
  variant?: "dropdown" | "pills";
}

export default function LanguageSelector({ className = "", variant = "dropdown" }: LanguageSelectorProps) {
  const { selectedLang, setSelectedLang, activeLang, t } = useLanguage();

  if (variant === "pills") {
    return (
      <div className={`flex flex-wrap items-center justify-center gap-2 ${className}`}>
        {SUPPORTED_LANGUAGES.map((lang) => {
          const isSelected = selectedLang === lang.code;
          return (
            <button
              key={lang.code}
              type="button"
              onClick={() => setSelectedLang(lang.code)}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-2xs ${
                isSelected
                  ? "bg-blue-600 text-white shadow-md ring-2 ring-blue-400/40"
                  : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
              }`}
            >
              <span>{lang.flag}</span>
              <span>{lang.code === "auto" ? t.autoDetect || "Auto Detect" : lang.native}</span>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className={`relative inline-block w-full ${className}`}>
      <label htmlFor="language-select" className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1.5">
        {t.language || "Language"}
      </label>
      <div className="relative flex items-center bg-white border border-slate-300 rounded-2xl px-3.5 py-2.5 shadow-2xs hover:border-blue-400 focus-within:ring-2 focus-within:ring-blue-500/30 focus-within:border-blue-500 transition-all">
        <Globe size={18} className="text-slate-400 mr-2.5 shrink-0" />
        <select
          id="language-select"
          value={selectedLang}
          onChange={(e) => setSelectedLang(e.target.value)}
          aria-label={t.language || "Language"}
          className="w-full bg-transparent text-sm font-semibold text-slate-800 outline-none cursor-pointer appearance-none pr-8"
        >
          <option value="auto">
            ✨ {t.autoDetect || "Auto Detect"} {selectedLang === "auto" ? `(${activeLang.toUpperCase()})` : ""}
          </option>
          <option value="en">English</option>
          <option value="te">తెలుగు (Telugu)</option>
          <option value="ta">தமிழ் (Tamil)</option>
          <option value="kn">ಕನ್ನಡ (Kannada)</option>
          <option value="hi">हिन्दी (Hindi)</option>
        </select>
        <ChevronDown size={16} className="text-slate-400 pointer-events-none absolute right-3.5" />
      </div>
    </div>
  );
}
