# Voice Command Shopping Assistant — Project Plan

**For:** Internship technical assessment
**Time budget:** 8 hours (hard cap)
**Build tool:** Antigravity
**Author:** Samarth

---

## 0. The call I'm making up front

The brief lists 12 feature groups. Building all of them properly in 8 hours is not possible — and trying to will produce something shallow across the board, which is worse for evaluation than doing 60% of it well. So this plan explicitly cuts scope and says so in the write-up. Evaluators are scoring **problem-solving approach** and **code quality**, not feature count. A small system with clean architecture, real error handling, and an honest "what I'd add with more time" section beats a feature-complete demo held together with hacks.

**Cut, and say so:** true multilingual voice UI (keep the *architecture* multilingual-ready, demo in English + one more language), price-range/brand search filters (nice-to-have, cut first if time runs short), seasonal recommendations (rule-based only, no real seasonal data feed).

**Keep, because they're the core signal:** voice → intent → action pipeline, list CRUD, categorization, basic history-based suggestions, substitutes, deployed and working.

---

## 1. Why this stack (mapped to what you already know)

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js + TypeScript**, Web Speech API for capture | You already ship Next.js/TS (Argus, DoCopilot). Web Speech API is free, zero-latency, browser-native — no audio upload roundtrip needed for the common case. |
| Speech-to-text (fallback/multilingual) | **Groq Whisper (`whisper-large-v3`)** | You're already on Groq. Free tier, fast, and this is what gives you real multilingual support instead of relying only on the browser's engine (Chrome's Web Speech API is English-strongest). |
| Intent parsing (NLU) | **Groq Llama (`llama-3.3-70b-versatile`)**, structured JSON output | You already do structured extraction work (GFS-AI). One well-designed prompt turns "I want to buy bananas" and "add 2 bottles of water" into the same intent schema. This *is* the NLP requirement — no need for a separate rules engine. |
| Backend | **FastAPI** | Your default. Thin — mostly orchestration between speech, LLM, and DB. |
| Database | **PostgreSQL (Neon, free tier)** | Same as DoCopilot. One table for list items, one for a tiny purchase-history log to drive suggestions. |
| Substitutes/suggestions matching | Simple rule table + history frequency, **no vector DB** | Qdrant would be over-engineering for ~30 grocery categories. Say this explicitly in the write-up — knowing when *not* to reach for a tool is a signal too. |
| Hosting | **Frontend → Vercel, Backend → Render (free web service)** | Fastest path to a working URL. Skip Azure Container Apps this time — that CI/CD pipeline alone ate real time on DoCopilot; you don't have hours to spend on infra here. |

---

## 2. Architecture

```
┌─────────────────────────────┐
│   Next.js frontend (Vercel) │
│  - Web Speech API capture   │
│  - Mic button + live list   │
│  - Sends transcript to API  │
└──────────────┬──────────────┘
               │ POST /command  { text, session_id }
               ▼
┌─────────────────────────────┐
│   FastAPI backend (Render)  │
│  1. If audio (fallback):    │
│     Groq Whisper → text     │
│  2. Groq Llama → structured │
│     intent JSON             │
│  3. Route intent → handler  │
│     (add/remove/search/…)   │
│  4. Query/update Postgres   │
│  5. Attach suggestions      │
└──────────────┬──────────────┘
               ▼
        ┌────────────┐
        │  Postgres   │
        │  (Neon)     │
        │ items, history│
        └────────────┘
```

---

## 3. Intent schema (the core NLU trick)

Instead of writing custom parsing rules, have the LLM return one schema for every phrasing:

```json
{
  "intent": "add_item | remove_item | search_item | list_items | unknown",
  "item": "milk",
  "quantity": 2,
  "unit": "bottles",
  "category": "dairy",
  "filters": { "brand": null, "max_price": null }
}
```

Prompt it with a handful of few-shot examples covering the phrasings in the brief ("Add milk" / "I need apples" / "I want to buy bananas" / "Remove milk from my list" / "Add 2 bottles of water"). This single prompt satisfies the "Voice Command Recognition + NLP flexibility" requirement — don't build a separate regex layer, it'll just fight the LLM.

For **multilingual**: ask the model to detect language and respond with the same schema regardless of input language (Llama 3.3 handles this natively). Demo in English + Hindi. Note in the write-up that Whisper's transcription layer is what actually carries the multilingual load — the LLM layer is language-agnostic by construction.

---

## 4. Data model (minimal)

**`items`**
| column | type |
|---|---|
| id | uuid |
| name | text |
| category | text |
| quantity | int |
| unit | text |
| status | enum(active, purchased) |
| created_at | timestamp |

**`history`** (one row per purchased/removed item — drives suggestions)
| column | type |
|---|---|
| id | uuid |
| item_name | text |
| category | text |
| event | enum(added, purchased, removed) |
| timestamp | timestamp |

Suggestions logic: if an item category shows up ≥N times in `history` and isn't currently in `items`, surface it ("looks like you're low on bread"). This is a plain SQL query — no ML needed, and that's fine to say out loud.

**Substitutes:** a small static JSON map (`{"milk": ["almond milk", "oat milk"], ...}`) checked when an item is marked unavailable or when the LLM detects a preference cue ("I prefer almond milk instead"). Seed it with ~15-20 common grocery substitutions from a public source (e.g. a grocery store's own substitution guide) — that satisfies "collect test data from public sources" without needing a real product catalog API.

---

## 5. API surface

- `POST /command` — main entry point; body is `{ text }` or `{ audio_base64 }`; returns updated list + any suggestion + a human-readable confirmation string for the UI to speak/display back
- `GET /list` — current active items, grouped by category
- `GET /suggestions` — on-demand suggestion refresh
- `DELETE /items/{id}` — explicit remove (used by both voice and a manual "x" button as a fallback when voice misfires)

Error handling: every LLM call wrapped with a timeout + retry-once; if intent parsing returns `unknown` or fails twice, respond with "Sorry, I didn't catch that — try again?" rather than silently dropping the command. Loading states: show a listening/thinking/confirmed three-state indicator on the mic button (this is explicitly asked for in the brief — don't skip it, it's cheap to build and visibly polishes the demo).

---

## 6. UI (minimal, voice-first)

- One screen. Big mic button, center.
- Below it: the list, grouped by category, with quantity badges.
- A slide-in toast for each recognized command ("Added 2 bottles of water ✓") — this is the "visual feedback" requirement.
- A thin suggestions strip under the list ("You might need: bread, eggs").
- No auth, no settings, no multi-user — out of scope, say so.

---

## 7. Hour-by-hour plan (8h budget)

| Hours | Work |
|---|---|
| 0–0.5 | Repo scaffold (Next.js + FastAPI), Neon DB provisioned, `.env` wiring |
| 0.5–1.5 | Postgres schema + FastAPI CRUD endpoints for `items` |
| 1.5–3 | Groq Llama intent-parsing prompt + `/command` route, tested with 10-15 text phrasings first (no voice yet) |
| 3–4 | Web Speech API integration in the frontend (capture → transcript → POST) |
| 4–5 | Suggestions (history query) + substitutes (static map) wired into `/command` response |
| 5–6 | UI polish: list view, category grouping, toast feedback, mic states |
| 6–7 | Groq Whisper fallback path for multilingual, basic error handling pass, manual QA across the required example commands from the brief |
| 7–8 | Deploy (Vercel + Render), README, 200-word write-up, final smoke test on the live URL |

If running behind at hour 6: cut the Whisper multilingual path first, keep everything else — a working English-only demo beats a broken multilingual one.

---

## 8. README structure

1. What it does (2-3 lines)
2. Architecture diagram (reuse section 2)
3. Setup instructions (env vars needed: `GROQ_API_KEY`, `DATABASE_URL`)
4. What's implemented vs. explicitly deferred (be direct about this — see section 0)
5. Live URL + a 30-second command script the reviewer can try verbatim

---

## 9. Write-up draft skeleton (200 words max)

- 1 sentence: what you built
- 2-3 sentences: the one deliberate architectural choice worth defending (recommend: "single LLM call for intent parsing instead of a rules engine, because it generalizes to phrasing variation for free")
- 1-2 sentences: what you deliberately cut and why (time-boxing discipline reads well to reviewers)
- 1 sentence: what you'd do next with more time (real product catalog API instead of static substitutes map, proper seasonal data source)

---

## 10. Questions worth resolving with the company if there's ambiguity

- Is a text-input fallback (typing instead of speaking) acceptable, given mic permissions can be flaky in a review environment? (Recommend: build it anyway as a safety net — costs ~10 minutes, saves the whole demo if their browser blocks mic access.)
- Do they expect real product/price data, or is a small curated dataset acceptable? (The brief says public-source test data is fine — treat that as settled unless told otherwise.)