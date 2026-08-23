"use client";
import { Toast } from "@/hooks/useShoppingList";

interface Props { toasts: Toast[]; }

export default function ToastContainer({ toasts }: Props) {
  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type}`} role="status">
          <div className="toast-dot" />
          {t.text}
        </div>
      ))}
    </div>
  );
}
