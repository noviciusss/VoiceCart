"use client";
import { useState, useEffect, useCallback } from "react";
import { api, ListItem, CommandResponse } from "@/lib/api";

function getSessionId(): string {
  if (typeof window === "undefined") return "ssr";
  const key = "vcsa_session_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export interface Toast {
  id: string;
  text: string;
  type: "success" | "error";
}

export function useShoppingList() {
  const [list, setList] = useState<Record<string, ListItem[]>>({});
  const [suggestions, setSuggestions] = useState<{ name: string; category: string }[]>([]);
  const [substitutes, setSubstitutes] = useState<string[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [loading, setLoading] = useState(false);
  const sessionId = getSessionId();

  const addToast = useCallback((text: string, type: Toast["type"] = "success") => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const fetchList = useCallback(async () => {
    try {
      const res = await api.getList(sessionId);
      setList(res.categories);
    } catch {
      // silently ignore on initial load
    }
  }, [sessionId]);

  useEffect(() => { fetchList(); }, [fetchList]);

  const sendCommand = useCallback(
    async (input: string, responseLang: string) => {
      setLoading(true);
      try {
        let body: Parameters<typeof api.command>[0];

        if (input.startsWith("__audio__")) {
          body = {
            session_id: sessionId,
            audio_base64: input.replace("__audio__", ""),
            response_language: responseLang,
          };
        } else {
          body = {
            session_id: sessionId,
            text: input,
            response_language: responseLang,
          };
        }

        const res: CommandResponse = await api.command(body);
        setList(res.list);
        setSuggestions(res.suggestions);
        setSubstitutes(res.substitutes);
        addToast(res.confirmation, res.intent.intent === "unknown" ? "error" : "success");
        return res;
      } catch (err: any) {
        addToast(err.message || "Something went wrong", "error");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [sessionId, addToast]
  );

  const removeItem = useCallback(
    async (itemId: string, itemName: string) => {
      try {
        await api.deleteItem(itemId, sessionId);
        setList((prev) => {
          const next = { ...prev };
          for (const cat of Object.keys(next)) {
            next[cat] = next[cat].filter((i) => i.id !== itemId);
            if (next[cat].length === 0) delete next[cat];
          }
          return next;
        });
        addToast(`Removed ${itemName} ✓`);
      } catch (err: any) {
        addToast(err.message, "error");
      }
    },
    [sessionId, addToast]
  );

  return {
    list,
    suggestions,
    substitutes,
    toasts,
    loading,
    sendCommand,
    removeItem,
    sessionId,
  };
}
