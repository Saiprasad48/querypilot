import { ResultTableView } from "@/components/result-table";
import { SqlBlock } from "@/components/sql-block";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Turn, Usage } from "@/lib/types";

function UsageLine({ usage }: { usage: Usage }) {
  const totalMs = usage.steps.reduce((sum, s) => sum + s.ms, 0);
  const cached = usage.calls.length > 0 && usage.calls.every((c) => c.cached);
  return (
    <p className="text-xs text-muted-foreground">
      {usage.calls.length} LLM call{usage.calls.length === 1 ? "" : "s"} ·{" "}
      {usage.input_tokens.toLocaleString()} in / {usage.output_tokens.toLocaleString()} out tokens
      · {(totalMs / 1000).toFixed(1)}s{cached && " · served from cache"}
    </p>
  );
}

type Props = { turn: Turn; onFollowup: (q: string) => void; disabled: boolean };

export function AnswerCard({ turn, onFollowup, disabled }: Props) {
  const answer = turn.answer;
  if (!answer) return null;

  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <p className="leading-relaxed">{answer.summary}</p>

        {answer.key_numbers.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {answer.key_numbers.map((k) => (
              <Badge key={k} variant="secondary" className="font-normal">
                {k}
              </Badge>
            ))}
          </div>
        )}

        {answer.caveats.length > 0 && (
          <ul className="space-y-1 text-sm text-amber-700 dark:text-amber-400">
            {answer.caveats.map((c) => (
              <li key={c}>⚠ {c}</li>
            ))}
          </ul>
        )}

        {turn.table && turn.sql && (
          <Tabs defaultValue="table">
            <TabsList>
              <TabsTrigger value="table">Table</TabsTrigger>
              <TabsTrigger value="sql">SQL</TabsTrigger>
            </TabsList>
            <TabsContent value="table">
              <ResultTableView table={turn.table} />
            </TabsContent>
            <TabsContent value="sql">
              <SqlBlock sql={turn.sql} />
            </TabsContent>
          </Tabs>
        )}

        {answer.followups.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {answer.followups.map((f) => (
              <Button
                key={f}
                size="sm"
                variant="outline"
                disabled={disabled}
                onClick={() => onFollowup(f)}
                className="h-auto whitespace-normal py-1.5 text-left"
              >
                {f}
              </Button>
            ))}
          </div>
        )}

        {turn.usage && <UsageLine usage={turn.usage} />}
      </CardContent>
    </Card>
  );
}