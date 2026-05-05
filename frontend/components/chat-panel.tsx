"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiPost } from "@/lib/api";
import {
  type ChatResponse,
  type ChatTurn,
  type ChatUsage,
} from "@/lib/chat";

type ChatPanelProps = {
  scope: string;
  initialTurns: ChatTurn[];
};

export function ChatPanel({ scope, initialTurns }: ChatPanelProps) {
  const [turns, setTurns] = useState<ChatTurn[]>(initialTurns);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUsage, setLastUsage] = useState<ChatUsage | null>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new turns appear or while waiting.
  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns, pending]);

  async function send() {
    const message = draft.trim();
    if (!message || pending) return;
    setError(null);
    setPending(true);

    // Optimistic user turn so the UI feels responsive while the agent thinks.
    const optimistic: ChatTurn = {
      id: `pending-${Date.now()}`,
      scope,
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    setTurns((prev) => [...prev, optimistic]);
    setDraft("");

    try {
      const response = await apiPost<ChatResponse>("/api/chat", {
        scope,
        message,
      });
      // Replace the optimistic turn with the real persisted user_turn, plus
      // the assistant_turn.
      setTurns((prev) => [
        ...prev.filter((t) => t.id !== optimistic.id),
        response.user_turn,
        response.assistant_turn,
      ]);
      setLastUsage(response.usage);
    } catch (err) {
      setTurns((prev) => prev.filter((t) => t.id !== optimistic.id));
      setError(err instanceof Error ? err.message : "Send failed.");
      setDraft(message); // restore so the user can retry without retyping
    } finally {
      setPending(false);
    }
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void send();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col gap-4">
      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto rounded-lg border border-border bg-card/30 p-4"
      >
        {turns.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex flex-col gap-4">
            {turns.map((turn) => (
              <TurnView key={turn.id} turn={turn} />
            ))}
            {pending && <ThinkingIndicator />}
          </div>
        )}
      </div>

      {lastUsage && !pending && (
        <p className="text-[11px] text-muted-foreground">
          Last reply via{" "}
          <span className="font-mono">{lastUsage.model}</span> ·{" "}
          {lastUsage.input_tokens.toLocaleString()} in /{" "}
          {lastUsage.output_tokens.toLocaleString()} out tokens ·{" "}
          {lastUsage.iterations} iteration
          {lastUsage.iterations === 1 ? "" : "s"}
        </p>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <Textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          placeholder="Ask about SBA loans, deal structure, due diligence, transition…"
          disabled={pending}
          className="resize-none"
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            Enter to send · Shift+Enter for newline
          </p>
          <Button type="submit" disabled={pending || !draft.trim()}>
            {pending ? "Thinking…" : "Send"}
          </Button>
        </div>
        {error && (
          <p
            role="alert"
            className="text-sm text-red-600 dark:text-red-400"
          >
            {error}
          </p>
        )}
      </form>
    </div>
  );
}

function TurnView({ turn }: { turn: ChatTurn }) {
  const isUser = turn.role === "user";
  return (
    <div
      className={
        "flex flex-col gap-1 " + (isUser ? "items-end" : "items-start")
      }
    >
      <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {isUser ? "You" : "Operator"}
      </span>
      <div
        className={
          "max-w-[85%] whitespace-pre-wrap rounded-lg px-4 py-2 text-sm leading-relaxed " +
          (isUser
            ? "bg-foreground text-background"
            : "bg-muted text-foreground")
        }
      >
        {turn.content}
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className="inline-block size-2 animate-pulse rounded-full bg-muted-foreground" />
      <span>Operator is thinking…</span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
      <p className="font-medium">Operator chat — global scope</p>
      <p className="max-w-sm text-xs">
        Ask about how to buy a small business: SBA financing, deal structure,
        due diligence checklists, closing mechanics, transition planning. The
        agent searches a curated knowledge base before answering and cites
        sources by filename.
      </p>
    </div>
  );
}
