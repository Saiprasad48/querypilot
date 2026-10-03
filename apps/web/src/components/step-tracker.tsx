import { Loader2 } from "lucide-react";

import type { Step } from "@/lib/types";

const LABELS: Record<string, string> = {
  route: "Understanding the question",
  retrieve: "Finding relevant tables",
  write_sql: "Writing SQL",
  validate: "Checking the query is safe",
  execute: "Running the query",
  analyze: "Analyzing the results",
  decline: "Preparing a response",
  fail: "Stopping after repeated errors",
};

export function StepTracker({ steps, running }: { steps: Step[]; running: boolean }) {
  return (
    <ol className="space-y-1 text-sm">
      {steps.map((s, i) => (
        <li key={`${s.node}-${i}`} className="flex items-center gap-2">
          <span className={s.error ? "text-amber-600" : "text-emerald-600"}>
            {s.error ? "↻" : "✓"}
          </span>
          <span>{LABELS[s.node] ?? s.node}</span>
          {s.ms != null && (
            <span className="tabular-nums text-muted-foreground">{(s.ms / 1000).toFixed(1)}s</span>
          )}
          {s.error && (
            <span className="truncate text-xs text-amber-700">fixing: {s.error}</span>
          )}
        </li>
      ))}
      {running && (
        <li className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Working…
        </li>
      )}
    </ol>
  );
}