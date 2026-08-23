"use client";
import { useState, useRef, useCallback } from "react";

export type MicState = "idle" | "listening" | "thinking";

interface UseSpeechOptions {
  onResult: (transcript: string) => void;
  onError?: (msg: string) => void;
}

export function useSpeech({ onResult, onError }: UseSpeechOptions) {
  const [micState, setMicState] = useState<MicState>("idle");
  const [interim, setInterim] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const stopAll = useCallback(() => {
    recognitionRef.current?.stop();
    mediaRecorderRef.current?.stop();
    setInterim("");
  }, []);

  const startWebSpeech = useCallback(
    (lang: string) => {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) return false;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const recognition: any = new SpeechRecognition();
      recognition.lang = lang === "hi" ? "hi-IN" : "en-US";
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognitionRef.current = recognition;

      recognition.onstart = () => setMicState("listening");

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (e: any) => {
        let interimText = "";
        let finalText = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) {
            finalText += e.results[i][0].transcript;
          } else {
            interimText += e.results[i][0].transcript;
          }
        }
        setInterim(interimText || finalText);
        if (finalText.trim()) {
          setMicState("thinking");
          setInterim("");
          onResult(finalText.trim());
        }
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onerror = (e: any) => {
        setMicState("idle");
        setInterim("");
        // Fall back to Whisper on no-speech or audio-capture errors
        if (e.error === "no-speech") {
          onError?.("No speech detected — try again");
        } else if (e.error === "not-allowed") {
          onError?.("Mic permission denied — use the text input below");
        }
      };

      recognition.onend = () => {
        if (micState !== "thinking") setMicState("idle");
      };

      recognition.start();
      return true;
    },
    [onResult, onError, micState]
  );

  const startWhisper = useCallback(
    async (lang: string) => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
        mediaRecorderRef.current = recorder;
        chunksRef.current = [];

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data);
        };

        recorder.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop());
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const reader = new FileReader();
          reader.onload = () => {
            const b64 = (reader.result as string).split(",")[1];
            setMicState("thinking");
            onResult(`__audio__${b64}`); // Signal audio to parent
          };
          reader.readAsDataURL(blob);
        };

        recorder.start();
        setMicState("listening");
      } catch {
        onError?.("Mic access denied");
        setMicState("idle");
      }
    },
    [onResult, onError]
  );

  const toggle = useCallback(
    (lang: string) => {
      if (micState === "listening") {
        stopAll();
        setMicState("idle");
        return;
      }
      if (micState === "thinking") return;

      // Try Web Speech first; fall back to Whisper
      const started = startWebSpeech(lang);
      if (!started) startWhisper(lang);
    },
    [micState, stopAll, startWebSpeech, startWhisper]
  );

  const setIdle = useCallback(() => setMicState("idle"), []);

  return { micState, interim, toggle, setIdle };
}
