"use client";

interface Props {
  lang: "en" | "hi";
  onChange: (lang: "en" | "hi") => void;
}

export default function LanguageToggle({ lang, onChange }: Props) {
  return (
    <div className="lang-toggle" role="group" aria-label="Response language">
      <button
        className={`lang-btn ${lang === "en" ? "active" : ""}`}
        onClick={() => onChange("en")}
        id="lang-en"
      >
        EN
      </button>
      <button
        className={`lang-btn ${lang === "hi" ? "active" : ""}`}
        onClick={() => onChange("hi")}
        id="lang-hi"
      >
        हि
      </button>
    </div>
  );
}
