"use client";

import { useCallback, useRef, useState } from "react";

import { RateLimitError, streamAsk } from "@/lib/stream";
import type { Turn } from "@/lib/types";

/** An anonymous ID per browser, used by the API's per user rate limit. */
function getClientId(): string {
  try {
    const existing = localStorage.getItem("qp-client-id");
    if (existing) return existing;
    const id = crypto.randomUUID();
    localStorage.setItem("qp-client-id", id);
    return id;
  } catch {
    return "anonymous-browser";
  }
}

export function useAgentChat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const ask = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || running) return;

      const id = crypto.randomUUID();
      const patch = (fn: (t: Turn) => Turn) =>
        setTurns((prev) => prev.map((t) => (t.id === id ? fn(t) : t)));

      setTurns((prev) => [...prev, { id, question: q, status: "running", steps: [] }]);
      setRunning(true);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        for await (const ev of streamAsk(q, threadId, getClientId(), controller.signal)) {
          switch (ev.event) {
            case "thread": {
              setThreadId(ev.data.thread_id);
              break;
            }
            case "step": {
              const step = ev.data;
              patch((t) => ({ ...t, steps: [...t.steps, step] }));
              break;
            }
            case "sql": {
              const { sql } = ev.data;
              patch((t) => ({ ...t, sql }));
              break;
            }
            case "rows": {
              const table = ev.data;
              patch((t) => ({ ...t, table }));
              break;
            }
            case "answer": {
              const { answer, standalone_question, intent } = ev.data;
              patch((t) => ({ ...t, answer, understoodAs: standalone_question, intent }));
              break;
            }
            case "usage": {
              const usage = ev.data;
              patch((t) => ({ ...t, usage }));
              break;
            }
            case "error": {
              const { message } = ev.data;
              patch((t) => ({ ...t, status: "error", error: message }));
              break;
            }
            case "done": {
              patch((t) => (t.status === "running" ? { ...t, status: "done" } : t));
              break;
            }
          }
        }
      } catch (err) {
        const message =
          err instanceof RateLimitError
            ? err.message
            : err instanceof DOMException && err.name === "AbortError"
              ? "Stopped."
              : "Could not reach the QueryPilot API. Is it running?";
        patch((t) => ({ ...t, status: "error", error: message }));
      } finally {
        setRunning(false);
        abortRef.current = null;
      }
    },
    [running, threadId],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setTurns([]);
    setThreadId(null);
  }, []);

  return { turns, running, ask, stop, reset };
}