"use client";
import { MicState } from "@/hooks/useSpeech";

const LABELS: Record<MicState, string> = {
  idle:      "Tap to speak",
  listening: "Listening…",
  thinking:  "Processing…",
};

const ICONS: Record<MicState, string> = {
  idle:      "🎤",
  listening: "⏹",
  thinking:  "⏳",
};

interface Props {
  state: MicState;
  onClick: () => void;
}

export default function MicButton({ state, onClick }: Props) {
  return (
    <div className="mic-section">
      <div className="mic-outer">
        <div className={`mic-ring ${state}`} />
        <button
          className={`mic-btn ${state}`}
          onClick={onClick}
          disabled={state === "thinking"}
          aria-label={LABELS[state]}
          id="mic-button"
        >
          {ICONS[state]}
        </button>
      </div>
      <span className="mic-label">{LABELS[state]}</span>
    </div>
  );
}
