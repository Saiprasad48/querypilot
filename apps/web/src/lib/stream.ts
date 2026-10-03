import type { Answer, ResultTable, Step, Usage } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type AgentEvent =
  | { event: "thread"; data: { thread_id: string } }
  | { event: "step"; data: Step }
  | { event: "sql"; data: { sql: string } }
  | { event: "rows"; data: ResultTable }
  | {
      event: "answer";
      data: { question: string; standalone_question: string | null; intent: string; answer: Answer };
    }
  | { event: "usage"; data: Usage }
  | { event: "error"; data: { message: string } }
  | { event: "done"; data: Record<string, never> };

export class RateLimitError extends Error {}

/** POST a question and yield each Server Sent Event as soon as it arrives. */
export async function* streamAsk(
  question: string,
  threadId: string | null,
  clientId: string,
  signal: AbortSignal,
): AsyncGenerator<AgentEvent> {
  const response = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Client-Id": clientId },
    body: JSON.stringify({ question, thread_id: threadId }),
    signal,
  });

  if (response.status === 429) {
    const body = await response.json().catch(() => ({}));
    throw new RateLimitError(body.detail ?? "Too many questions. Please wait a moment.");
  }
  if (!response.ok || !response.body) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;

    // Events are separated by a blank line.
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (data) yield { event, data: JSON.parse(data) } as AgentEvent;
      boundary = buffer.indexOf("\n\n");
    }
  }
}