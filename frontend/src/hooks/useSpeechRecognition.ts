import { useState, useRef, useCallback, useEffect } from "react";

export interface SpeechRecognitionResult {
  transcript: string;
  audioBlob?: Blob;
}

interface UseSpeechRecognitionOptions {
  locale?: string;
  onInterimResult?: (transcript: string) => void;
  onFinalResult?: (transcript: string) => void;
  onError?: (error: string) => void;
}

const LOCALE_MAP: Record<string, string> = {
  te: "te-IN",
  ta: "ta-IN",
  kn: "kn-IN",
  hi: "hi-IN",
  en: "en-IN",
};

export function useSpeechRecognition(options: UseSpeechRecognitionOptions = {}) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const transcriptRef = useRef<string>("");
  const isStoppingRef = useRef<boolean>(false);

  // Detect support
  const isSpeechSupported = typeof window !== "undefined" && Boolean(
    (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  );

  const startListening = useCallback(
    async (overrideLocale?: string): Promise<boolean> => {
      setError(null);
      setTranscript("");
      transcriptRef.current = "";
      audioChunksRef.current = [];
      isStoppingRef.current = false;

      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

      const effectiveLocale = overrideLocale || LOCALE_MAP[options.locale || "en"] || "en-IN";

      // 1. Start browser speech recognition
      if (SpeechRecognition) {
        try {
          if (recognitionRef.current) {
            try {
              recognitionRef.current.abort();
            } catch (e) {}
          }

          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = effectiveLocale;

          recognition.onresult = (event: any) => {
            let combined = "";
            for (let i = 0; i < event.results.length; i++) {
              combined += event.results[i][0].transcript;
            }
            if (combined.trim()) {
              transcriptRef.current = combined;
              setTranscript(combined);
              options.onInterimResult?.(combined);
            }
          };

          recognition.onerror = (event: any) => {
            console.warn("SpeechRecognition error:", event.error);
            if (event.error === "not-allowed") {
              setError("permission-denied");
              options.onError?.("permission-denied");
            } else if (event.error !== "no-speech") {
              setError(event.error);
              options.onError?.(event.error);
            }
          };

          recognition.onend = () => {
            if (!isStoppingRef.current && isListening) {
              // Browser may auto-stop on silence; keep transcript intact
              setIsListening(false);
            }
          };

          recognitionRef.current = recognition;
          recognition.start();
        } catch (err: any) {
          console.warn("Failed to start SpeechRecognition:", err);
          setError("start-failed");
        }
      } else {
        setError("not-supported");
      }

      // 2. Also record audio via MediaRecorder for backend multimodal audio fallback & Audio LID
      try {
        if (navigator.mediaDevices?.getUserMedia) {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "";
          const recorder = mimeType
            ? new MediaRecorder(stream, { mimeType })
            : new MediaRecorder(stream);
          mediaRecorderRef.current = recorder;

          recorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
              audioChunksRef.current.push(event.data);
            }
          };

          recorder.start(250);
        }
      } catch (err: any) {
        console.warn("MediaRecorder mic access error:", err);
        if (!SpeechRecognition) {
          setError("permission-denied");
          options.onError?.("permission-denied");
          return false;
        }
      }

      setIsListening(true);
      return true;
    },
    [options, isListening]
  );

  const stopListening = useCallback(async (): Promise<SpeechRecognitionResult> => {
    isStoppingRef.current = true;
    setIsListening(false);

    // Stop browser recognition
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }

    // Stop MediaRecorder
    let audioBlob: Blob | undefined;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      } catch (e) {}
    }

    if (audioChunksRef.current.length > 0) {
      audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    }

    const finalTranscript = transcriptRef.current;
    options.onFinalResult?.(finalTranscript);

    return {
      transcript: finalTranscript,
      audioBlob,
    };
  }, [options]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
        } catch (e) {}
      }
    };
  }, []);

  return {
    isListening,
    transcript,
    error,
    isSpeechSupported,
    startListening,
    stopListening,
    setTranscript,
  };
}
