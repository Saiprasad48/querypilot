"use client";

import { useEffect, useRef } from "react";

import { ChatInput } from "@/components/chat-input";
import { TurnView } from "@/components/turn-view";
import { Button } from "@/components/ui/button";
import { useAgentChat } from "@/hooks/use-agent-chat";

const STARTERS = [
  "Which 5 customer states had the highest late delivery rate in 2018?",
  "Show the monthly revenue trend in 2018",
  "Top 5 product categories by items sold",
  "What share of payments used boleto vs credit card?",
];

export default function Home() {
  const { turns, running, ask, stop, reset } = useAgentChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          <div>
            <h1 className="font-semibold">QueryPilot</h1>
            <p className="text-xs text-muted-foreground">
              AI data analyst for the Olist ecommerce dataset (2016 to 2018)
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={reset} disabled={turns.length === 0}>
            New chat
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl flex-1 space-y-8 px-4 py-6">
        {turns.length === 0 ? (
          <section className="mt-16 space-y-6 text-center">
            <div className="space-y-2">
              <h2 className="text-2xl font-semibold">What would you like to know?</h2>
              <p className="text-sm text-muted-foreground">
                Ask in plain English. QueryPilot writes safe SQL, runs it, and explains the result.
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {STARTERS.map((q) => (
                <button
                  key={q}
                  onClick={() => ask(q)}
                  className="rounded-lg border p-3 text-left text-sm transition-colors hover:bg-muted"
                >
                  {q}
                </button>
              ))}
            </div>
          </section>
        ) : (
          turns.map((t) => (
            <TurnView key={t.id} turn={t} onFollowup={ask} disabled={running} />
          ))
        )}
        <div ref={bottomRef} />
      </main>

      <footer className="sticky bottom-0 border-t bg-background/95 backdrop-blur">
        <div className="mx-auto max-w-4xl px-4 py-3">
          <ChatInput onSubmit={ask} onStop={stop} running={running} />
        </div>
      </footer>
    </div>
  );
}