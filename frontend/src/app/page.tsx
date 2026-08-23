"use client";
import { useState, useRef, useCallback } from "react";

import MicButton from "@/components/MicButton";
import ShoppingList from "@/components/ShoppingList";
import SuggestionsStrip from "@/components/SuggestionsStrip";
import ToastContainer from "@/components/Toast";
import LanguageToggle from "@/components/LanguageToggle";
import { useSpeech } from "@/hooks/useSpeech";
import { useShoppingList } from "@/hooks/useShoppingList";

export default function Home() {
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [textInput, setTextInput] = useState("");
  const [transcript, setTranscript] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const { list, suggestions, substitutes, toasts, loading, sendCommand, removeItem } =
    useShoppingList();

  const handleResult = useCallback(
    async (result: string) => {
      if (!result.startsWith("__audio__")) setTranscript(result);
      await sendCommand(result, lang);
      setTranscript("");
    },
    [sendCommand, lang]
  );

  const { micState, interim, toggle, setIdle } = useSpeech({
    onResult: handleResult,
    onError: (_msg: string) => {
      setIdle();
    },
  });

  // After command completes, reset mic to idle
  const handleMicClick = useCallback(() => {
    toggle(lang);
  }, [toggle, lang]);

  const handleTextSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const val = textInput.trim();
      if (!val || loading) return;
      setTextInput("");
      await sendCommand(val, lang);
    },
    [textInput, loading, sendCommand, lang]
  );

  const handleSuggestionSelect = useCallback(
    (name: string) => {
      sendCommand(`Add ${name}`, lang);
    },
    [sendCommand, lang]
  );

  return (
    <>
      <div className="app-wrapper">
        {/* ── Header ─────────────────────────────────────── */}
        <header className="header">
          <div className="header-logo">
            <div className="logo-icon">🛒</div>
            VoiceCart
          </div>
          <LanguageToggle lang={lang} onChange={setLang} />
        </header>

        {/* ── Main ───────────────────────────────────────── */}
        <main className="main-content">
          {/* Mic */}
          <MicButton state={micState} onClick={handleMicClick} />

          {/* Live transcript bubble */}
          {(interim || transcript) && (
            <div className={`transcript-bubble active`}>
              <div className="transcript-dot" />
              <span>{interim || transcript}</span>
            </div>
          )}
          {!interim && !transcript && micState === "idle" && (
            <div className="transcript-bubble">
              <span>
                {lang === "hi"
                  ? "बोलें: \"दूध जोड़ो\" या नीचे टाइप करें"
                  : "Say something like \"Add 2 bottles of water\""}
              </span>
            </div>
          )}

          {/* Text fallback input */}
          <form className="text-input-section" onSubmit={handleTextSubmit}>
            <input
              ref={inputRef}
              className="text-input"
              type="text"
              placeholder={lang === "hi" ? "यहाँ लिखें…" : "Or type a command…"}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              id="text-command-input"
              disabled={loading}
            />
            <button
              type="submit"
              className="send-btn"
              disabled={!textInput.trim() || loading}
              id="text-command-submit"
              aria-label="Send command"
            >
              ➤
            </button>
          </form>

          {/* Substitutes panel */}
          {substitutes.length > 0 && (
            <div className="substitutes-panel fade-in">
              <p className="substitutes-title">
                {lang === "hi" ? "विकल्प" : "Substitutes"}
              </p>
              <div className="substitutes-chips">
                {substitutes.map((s) => (
                  <button
                    key={s}
                    className="sub-chip"
                    onClick={() => sendCommand(`Add ${s}`, lang)}
                    id={`sub-${s.replace(/\s+/g, "-")}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Shopping list */}
          <ShoppingList list={list} onRemove={removeItem} />

          {/* Suggestions */}
          <SuggestionsStrip
            suggestions={suggestions}
            onSelect={handleSuggestionSelect}
          />
        </main>
      </div>

      {/* Toasts */}
      <ToastContainer toasts={toasts} />
    </>
  );
}
