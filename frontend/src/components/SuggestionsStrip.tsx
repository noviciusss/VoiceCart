"use client";

interface Props {
  suggestions: { name: string; category: string }[];
  onSelect: (name: string) => void;
}

export default function SuggestionsStrip({ suggestions, onSelect }: Props) {
  if (suggestions.length === 0) return null;

  return (
    <div className="suggestions-section">
      <p className="suggestions-label">You might need</p>
      <div className="suggestions-scroll">
        {suggestions.map((s) => (
          <button
            key={s.name}
            className="suggestion-chip"
            onClick={() => onSelect(s.name)}
            id={`suggestion-${s.name.replace(/\s+/g, "-")}`}
          >
            + {s.name}
          </button>
        ))}
      </div>
    </div>
  );
}
