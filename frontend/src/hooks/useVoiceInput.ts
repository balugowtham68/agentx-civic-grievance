import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Voice input, in order of preference:
 *   'browser' - Web Speech API (Chrome/Edge). Speech becomes text in the browser;
 *               the text is submitted with input_channel = 'voice'.
 *   'upload'  - MediaRecorder recording sent to POST /intake/voice, only when the server
 *               has speech-to-text (local model first, optional remote). The server
 *               validates the audio and never stores it.
 *   'none'    - neither is available: the citizen types (fallback shown in the UI).
 * Browser speech support varies by browser and language; it is never assumed.
 */
export type VoiceMode = 'browser' | 'upload' | 'none'

interface RecognitionResultEvent {
  resultIndex: number
  results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }>
}

interface RecognitionLike {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((event: RecognitionResultEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}

type RecognitionConstructor = new () => RecognitionLike

function speechRecognitionConstructor(): RecognitionConstructor | undefined {
  const w = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition
}

function canRecordAudio(): boolean {
  return typeof window.MediaRecorder !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)
}

export function detectVoiceMode(serverSpeechToText: boolean): VoiceMode {
  if (speechRecognitionConstructor()) return 'browser'
  if (serverSpeechToText && canRecordAudio()) return 'upload'
  return 'none'
}

/** Recordings stop automatically at the server's limit (MAX_AUDIO_SECONDS, default 120). */
export const MAX_RECORDING_MS = 120_000

interface Options {
  locale: string
  serverSpeechToText: boolean
  onTranscript: (text: string) => void
  onAudio: (audio: Blob) => void
}

export function useVoiceInput({ locale, serverSpeechToText, onTranscript, onAudio }: Options) {
  const mode = detectVoiceMode(serverSpeechToText)
  const [active, setActive] = useState(false)
  const [failed, setFailed] = useState(false)
  const recognition = useRef<RecognitionLike | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)

  const stop = useCallback(() => {
    recognition.current?.stop()
    if (recorder.current && recorder.current.state !== 'inactive') recorder.current.stop()
  }, [])

  useEffect(() => stop, [stop])

  const start = useCallback(async () => {
    setFailed(false)
    if (mode === 'browser') {
      const Recognition = speechRecognitionConstructor()!
      const instance = new Recognition()
      instance.lang = locale
      instance.interimResults = false
      instance.continuous = true
      instance.onresult = (event) => {
        let text = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) text += event.results[i][0].transcript
        }
        if (text.trim()) onTranscript(text.trim())
      }
      instance.onerror = () => setFailed(true)
      instance.onend = () => setActive(false)
      recognition.current = instance
      instance.start()
      setActive(true)
      return
    }
    if (mode === 'upload') {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const media = new MediaRecorder(stream)
        const chunks: Blob[] = []
        media.ondataavailable = (event) => chunks.push(event.data)
        media.onstop = () => {
          stream.getTracks().forEach((track) => track.stop())
          setActive(false)
          const blob = new Blob(chunks, { type: media.mimeType || 'audio/webm' })
          if (blob.size > 0) onAudio(blob)
        }
        recorder.current = media
        media.start()
        setActive(true)
        window.setTimeout(() => {
          if (media.state !== 'inactive') media.stop()
        }, MAX_RECORDING_MS)
      } catch {
        setFailed(true)
      }
    }
  }, [mode, locale, onTranscript, onAudio])

  return { mode, active, failed, start, stop }
}
