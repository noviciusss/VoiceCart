const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface IntentData {
  intent: string;
  item: string | null;
  quantity: number;
  unit: string;
  category: string;
  filters: { brand: string | null; max_price: string | null };
  detected_language: string;
}

export interface ListItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
}

export interface CommandResponse {
  transcript: string;
  intent: IntentData;
  confirmation: string;
  detected_language: string;
  list: Record<string, ListItem[]>;
  substitutes: string[];
  suggestions: { name: string; category: string }[];
}

export interface ListResponse {
  categories: Record<string, ListItem[]>;
  total: number;
}

export interface SuggestionsResponse {
  suggestions: { name: string; category: string; frequency: number }[];
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  return res.json() as Promise<T>;
}

export const api = {
  command: (body: {
    session_id: string;
    text?: string;
    audio_base64?: string;
    response_language?: string;
  }) =>
    apiFetch<CommandResponse>("/command", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getList: (sessionId: string) =>
    apiFetch<ListResponse>(`/items/list?session_id=${encodeURIComponent(sessionId)}`),

  deleteItem: (itemId: string, sessionId: string) =>
    apiFetch<{ deleted: string; item: string }>(
      `/items/${itemId}?session_id=${encodeURIComponent(sessionId)}`,
      { method: "DELETE" }
    ),

  getSuggestions: (sessionId: string) =>
    apiFetch<SuggestionsResponse>(
      `/suggestions?session_id=${encodeURIComponent(sessionId)}`
    ),
};
