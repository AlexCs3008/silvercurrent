"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiPost } from "@/lib/api";
import {
  type ChatResponse,
  type ChatTurn,
  type ChatUsage,
  type RoutedAgent,
  type RoutingInfo,
} from "@/lib/chat";

type ChatPanelProps = {
  scope: string;
  initialTurns: ChatTurn[];
  /**
   * Variant controls labels and empty-state copy. `global` = Operator-leaning
   * (general ETA chat); `listing` = Analyst-leaning (this specific deal).
   * The Router picks per-turn either way; this only changes UI framing.
   */
  variant?: "global" | "listing";
};

export function ChatPanel({
  scope,
  initialTurns,
  variant = "global",
}: ChatPanelProps) {
  const [turns, setTurns] = useState<ChatTurn[]>(initialTurns);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUsage, setLastUsage] = useState<ChatUsage | null>(null);
  const [lastRouting, setLastRouting] = useState<RoutingInfo | null>(null);
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
      setTurns((prev) => [
        ...prev.filter((t) => t.id !== optimistic.id),
        response.user_turn,
        response.assistant_turn,
      ]);
      setLastUsage(response.usage);
      setLastRouting(response.routing);
    } catch (err) {
      setTurns((prev) => prev.filter((t) => t.id !== optimistic.id));
      setError(err instanceof Error ? err.message : "Send failed.");
      setDraft(message);
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

  const heightClass =
    variant === "listing"
      ? "h-[36rem]"
      : "h-[calc(100vh-6rem)]";

  return (
    <div className={"flex flex-col gap-4 " + heightClass}>
      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto rounded-lg border border-border bg-card/30 p-4"
      >
        {turns.length === 0 ? (
          <EmptyState variant={variant} />
        ) : (
          <div className="flex flex-col gap-4">
            {turns.map((turn) => (
              <TurnView key={turn.id} turn={turn} />
            ))}
            {pending && <ThinkingIndicator agent={lastRouting?.agent} />}
          </div>
        )}
      </div>

      {lastUsage && lastRouting && !pending && (
        <p className="text-[11px] text-muted-foreground">
          Routed to{" "}
          <span className="font-mono">{agentLabel(lastRouting.agent)}</span>
          {" · "}
          <span className="font-mono">{lastUsage.model}</span> ·{" "}
          {lastUsage.input_tokens.toLocaleString()} in /{" "}
          {lastUsage.output_tokens.toLocaleString()} out tokens ·{" "}
          {lastUsage.iterations} iteration
          {lastUsage.iterations === 1 ? "" : "s"}
          {" · "}
          <span className="italic">{lastRouting.rationale}</span>
        </p>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <Textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          placeholder={placeholderFor(variant)}
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
        {isUser ? "You" : "Silvercurrent"}
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

function ThinkingIndicator({ agent }: { agent?: RoutedAgent }) {
  const label = agent ? agentLabel(agent) : "Silvercurrent";
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className="inline-block size-2 animate-pulse rounded-full bg-muted-foreground" />
      <span>{label} is thinking…</span>
    </div>
  );
}

function EmptyState({ variant }: { variant: "global" | "listing" }) {
  if (variant === "listing") {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
        <p className="font-medium">Chat about this listing</p>
        <p className="max-w-sm text-xs">
          Ask the Analyst about asking-multiples, SBA financing, fit against
          your criteria, or qualitative concerns. General ETA mechanics route
          to the Operator. The Router picks per turn.
        </p>
      </div>
    );
  }
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
      <p className="font-medium">Silvercurrent — global chat</p>
      <p className="max-w-sm text-xs">
        Ask about how to buy a small business: SBA financing, deal structure,
        due diligence, closing, transition. The Operator searches a curated
        knowledge base and cites sources by filename.
      </p>
    </div>
  );
}

function placeholderFor(variant: "global" | "listing") {
  return variant === "listing"
    ? "Ask about this deal — multiples, fit, concerns, or general ETA mechanics…"
    : "Ask about SBA loans, deal structure, due diligence, transition…";
}

function agentLabel(agent: RoutedAgent): string {
  switch (agent) {
    case "operator":
      return "Operator";
    case "analyst":
      return "Analyst";
    case "clarify":
      return "Router (clarify)";
    case "out_of_scope":
      return "Router (out of scope)";
  }
}
