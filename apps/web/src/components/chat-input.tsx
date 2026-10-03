"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Props = { onSubmit: (q: string) => void; onStop: () => void; running: boolean };
export function ChatInput({ onSubmit, onStop, running }: Props) {
  const [value, setValue] = useState("");
  const submit = () => {
    if (!value.trim() || running) return;
    onSubmit(value);
    setValue("");
  };
  return (
    <div className="flex items-end gap-2">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask about orders, revenue, deliveries, customers…"
        maxLength={500}
        rows={1}
        className="min-h-11 resize-none"
        aria-label="Your question"
      />
      {running ? (
        <Button variant="outline" onClick={onStop}>
          Stop
        </Button>
      ) : (
        <Button onClick={submit} disabled={!value.trim()}>
          Ask
        </Button>
      )}
    </div>
  );
}