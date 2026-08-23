# VoiceCart
### Voice-First Intelligent Shopping Assistant powered by Groq & PostgreSQL

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Groq](https://img.shields.io/badge/AI-Groq%20LPU-orange?style=flat-square)](https://groq.com/)
[![Neon PostgreSQL](https://img.shields.io/badge/Database-Neon%20Serverless%20Postgres-00E599?style=flat-square&logo=postgresql)](https://neon.tech/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-blue?style=flat-square&logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Language-Python%203.11+-3776AB?style=flat-square&logo=python)](https://www.python.org/)

**VoiceCart** is a modern, responsive web application that turns spoken natural language into an organized, categorized shopping list in real time. It features low-latency voice capture, LLM-driven Natural Language Understanding (NLU), smart grocery categorization, historical frequency suggestions, intelligent product substitutions, and bilingual support (English and Hindi).

---

## Key Features

- **Zero-Latency Voice Input**: Integrated with the Web Speech API for real-time speech transcription, with an automatic fallback to **Groq Whisper (`whisper-large-v3`)** for unsupported audio formats and noisy environments.
- **LLM Structured Intent Extraction**: Single-call structured JSON extraction via **Groq LPU**, accurately extracting intent, item name, quantity, unit, and grocery category across diverse human phrasings.
- **Multilingual Support (English and Hindi)**:
  - Speak in English (*"Add 2 bottles of water"*) or Hindi (*"दूध जोड़ो"* / *"सेब चाहिए"*).
  - Built-in UI language switcher (**EN / हि**) for localized feedback toasts and interface guidance.
- **Automatic Categorization & Badging**: Automatically maps items into clean categories (Dairy, Produce, Beverages, Bakery, Meat & Seafood, Grains, Pantry, Snacks) with quantity badges.
- **Smart Product Substitutions**: Integrated dietary and pantry substitution engine (e.g., *"I prefer almond milk instead of milk"* surfaces almond milk, oat milk, soy milk, and coconut milk).
- **History-Driven Recommendations**: SQL-powered recommendation engine analyzing purchase and addition frequency to suggest items you might need.
- **Resilient Text Fallback**: Embedded command input bar as a fallback for browsers without microphone permissions or noisy environments.
- **Session Isolation**: UUID-based session management ensuring independent shopping lists across tabs and users without requiring heavy authentication.

---

## System Architecture

```
┌────────────────────────────────────────────────────────┐
│               VoiceCart Next.js Frontend               │
│  - Web Speech API Capture / MediaRecorder Audio Blob   │
│  - 3-State Reactive Mic Button (Idle/Listening/Thinking)│
│  - Category Grouped List, Suggestion Chips, Toasts    │
└───────────────────────────┬────────────────────────────┘
                            │ POST /command { text | audio_base64, session_id }
                            ▼
┌────────────────────────────────────────────────────────┐
│                   FastAPI Backend                      │
│                                                        │
│  1. Audio Fallback: Groq Whisper-Large-v3 Transcribe   │
│  2. NLU Pipeline: Groq LPU → Structured Intent Schema  │
│  3. Intent Router:                                     │
│     - add_item (upsert quantity, log to history)       │
│     - remove_item / mark_purchased                     │
│     - suggest_substitute                               │
│     - list_items                                       │
│  4. PostgreSQL Query: Active List & Frequency Query    │
│  5. Response Builder: Confirmation Toast + Data        │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
                 ┌────────────────────┐
                 │  Neon PostgreSQL   │
                 │   - items table    │
                 │   - history table  │
                 └────────────────────┘
```

---

## Intent Schema & NLU

Instead of building brittle regex matchers or complex grammar rules, VoiceCart uses a unified few-shot system prompt on Groq LLMs that guarantees strict JSON output:

```json
{
  "intent": "add_item | remove_item | search_item | list_items | mark_purchased | suggest_substitute | unknown",
  "item": "water",
  "quantity": 2,
  "unit": "bottles",
  "category": "beverages",
  "filters": {
    "brand": null,
    "max_price": null
  },
  "detected_language": "en"
}
```

### Supported Intent Variations
| Phrasing | Parsed Intent | Normalized Item | Quantity / Unit | Category |
| :--- | :--- | :--- | :--- | :--- |
| *"Add 2 bottles of water"* | `add_item` | `water` | `2 bottles` | `beverages` |
| *"I need apples"* | `add_item` | `apple` | `1` | `produce` |
| *"Remove milk from my list"* | `remove_item` | `milk` | `1` | `dairy` |
| *"दूध जोड़ो"* | `add_item` | `milk` | `1` | `dairy` |
| *"I prefer almond milk instead"* | `suggest_substitute` | `milk` | `1` | `dairy` |

---

## Database Schema

Serverless PostgreSQL hosted on **Neon**:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS items (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  TEXT        NOT NULL,
  name        TEXT        NOT NULL,
  category    TEXT        DEFAULT 'other',
  quantity    INT         DEFAULT 1,
  unit        TEXT        DEFAULT '',
  status      TEXT        DEFAULT 'active',   -- active | purchased
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS history (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  TEXT        NOT NULL,
  item_name   TEXT        NOT NULL,
  category    TEXT        DEFAULT 'other',
  event       TEXT        NOT NULL,            -- added | purchased | removed
  timestamp   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_items_session   ON items(session_id, status);
CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id);
```

---

## API Reference

### `POST /command`
Main conversational entry point for both voice transcripts and typed commands.
```json
// Request Body
{
  "session_id": "uuid-string",
  "text": "Add 2 bottles of water",
  "audio_base64": null,
  "response_language": "en"
}

// Response
{
  "transcript": "Add 2 bottles of water",
  "intent": { ... },
  "confirmation": "Added 2 bottles water to your list ✓",
  "detected_language": "en",
  "list": {
    "beverages": [
      { "id": "8cb91724-...", "name": "water", "quantity": 2, "unit": "bottles" }
    ]
  },
  "substitutes": [],
  "suggestions": []
}
```

### `GET /items/list?session_id={session_id}`
Returns all active items grouped by category.

### `DELETE /items/{item_id}?session_id={session_id}`
Removes an item and logs the removal event to the `history` table.

### `GET /suggestions?session_id={session_id}`
Queries top frequent items from `history` that are not currently in the active list.

### `GET /health`
Liveness check returning `{"status": "ok"}`.

---

## Tech Stack & Architecture Decisions

| Layer | Technology | Engineering Rationale |
|---|---|---|
| **Frontend** | **Next.js 14 (App Router) + TypeScript** | Server components where beneficial, client hooks for speech recognition, zero config deployment on Vercel. |
| **Styling** | **Custom CSS Variables & Glassmorphism** | Dark theme (`#0b0c10`), responsive layout, customized pulsing mic keyframe animations. |
| **Speech Capture** | **Web Speech API + Groq Whisper** | Free, zero-latency browser native capture with Whisper large-v3 fallback for resilience. |
| **NLU Engine** | **Groq LPU (Ultra-Fast Inference)** | Sub-second structured extraction replacing fragile regex parsers. |
| **Backend** | **FastAPI + asyncpg** | High-performance asynchronous Python API with connection pooling and automated migration lifespans. |
| **Database** | **Neon PostgreSQL** | Serverless PostgreSQL with native UUID support, relational indexing, and instant provisioning. |

---

## Getting Started

### 1. Prerequisites
- **Node.js**: v18.0 or higher
- **Python**: v3.11 or higher
- **Groq API Key**: Available at [console.groq.com](https://console.groq.com/)
- **Neon PostgreSQL**: Free serverless database at [neon.tech](https://neon.tech/)

### 2. Clone the Repository
```bash
git clone https://github.com/noviciusss/VoiceCart.git
cd VoiceCart
```

### 3. Backend Setup
```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env

# Add your credentials to backend/.env:
# GROQ_API_KEY=gsk_...
# DATABASE_URL=postgresql://user:password@ep-xyz.neon.tech/neondb?sslmode=require

# Run the FastAPI server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Create environment configuration
copy .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Start development server
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 30-Second Verification Script

Test the application using voice or the input box with these sample commands:

1. **Add item with quantity**: `"Add 2 bottles of water"` *(Adds to Beverages)*
2. **Add item with phrasing variation**: `"I need apples"` *(Adds to Produce)*
3. **Hindi command**: Switch language toggle to **हि** → say *"दूध जोड़ो"* *(Adds milk to Dairy with Hindi confirmation)*
4. **Substitution query**: `"I prefer almond milk instead of milk"` *(Surfaces substitute options)*
5. **Item deletion**: Click the `×` button or say `"Remove apples from my list"`
6. **List check**: `"What is on my list?"`

---

## Deployment

- **Frontend**: Deploy directly to **Vercel** with `NEXT_PUBLIC_API_URL` set to your production backend URL.
- **Backend**: Deploy to **Render** / **Railway** using the included [`backend/render.yaml`](file:///d:/Voice_command/backend/render.yaml).

---

## License
MIT License.
