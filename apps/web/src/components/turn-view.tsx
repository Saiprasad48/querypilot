import { AnswerCard } from "@/components/answer-card";
import { StepTracker } from "@/components/step-tracker";
import type { Turn } from "@/lib/types";

type Props = { turn: Turn; onFollowup: (q: string) => void; disabled: boolean };

export function TurnView({ turn, onFollowup, disabled }: Props) {
  const running = turn.status === "running";
  const totalMs = turn.steps.reduce((sum, s) => sum + (s.ms ?? 0), 0);

  return (
    <article className="space-y-3">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-primary px-4 py-2 text-primary-foreground">
          {turn.question}
        </div>
      </div>

      {turn.understoodAs && turn.understoodAs !== turn.question && (
        <p className="text-xs text-muted-foreground">Understood as: {turn.understoodAs}</p>
      )}

      {running ? (
        <StepTracker steps={turn.steps} running />
      ) : (
        turn.steps.length > 0 && (
          <details className="text-sm">
            <summary className="cursor-pointer text-muted-foreground">
              How I got this: {turn.steps.length} steps in {(totalMs / 1000).toFixed(1)}s
            </summary>
            <div className="mt-2">
              <StepTracker steps={turn.steps} running={false} />
            </div>
          </details>
        )
      )}

      {turn.error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          {turn.error}
        </div>
      )}

      <AnswerCard turn={turn} onFollowup={onFollowup} disabled={disabled} />
    </article>
  );
}