"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

export function SqlBlock({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="relative">
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-3 pr-12 font-mono text-xs leading-relaxed">
        {sql}
      </pre>
      <Button
        size="icon"
        variant="ghost"
        className="absolute right-1 top-1 h-8 w-8"
        onClick={copy}
        aria-label="Copy SQL"
      >
        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
      </Button>
    </div>
  );
}