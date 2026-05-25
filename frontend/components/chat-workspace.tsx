"use client";

import { useCallback, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ChatPanel } from "@/components/chat-panel";
import { Button } from "@/components/ui/button";
import { apiDelete, apiGet } from "@/lib/api";
import type { ChatTurn, Conversation } from "@/lib/chat";
import { cn } from "@/lib/utils";

type ChatWorkspaceProps = {
  initialConversations: Conversation[];
  /** Full scope string of the active conversation, or null when none is selected. */
  activeScope: string | null;
  initialActiveTurns: ChatTurn[];
};

export function ChatWorkspace({
  initialConversations,
  activeScope,
  initialActiveTurns,
}: ChatWorkspaceProps) {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>(
    initialConversations,
  );
  const [pending, startTransition] = useTransition();

  const refreshConversations = useCallback(async () => {
    try {
      const fresh = await apiGet<Conversation[]>("/api/chat/conversations");
      setConversations(fresh);
    } catch {
      // Non-fatal — the rail stays stale until the next interaction.
    }
  }, []);

  function navigateToScope(scope: string | null) {
    startTransition(() => {
      router.push(scope ? `/chat?scope=${encodeURIComponent(scope)}` : "/chat");
    });
  }

  function newChat() {
    // crypto.randomUUID is available in all modern browsers + Node 19+.
    const newScope = `chat:${crypto.randomUUID()}`;
    navigateToScope(newScope);
  }

  async function deleteScope(scope: string) {
    if (
      !confirm(
        `Delete this conversation? Removes all messages for "${shortTitle(
          conversations.find((c) => c.scope === scope)?.title ?? scope,
        )}".`,
      )
    ) {
      return;
    }
    try {
      await apiDelete(`/api/chat?scope=${encodeURIComponent(scope)}`);
    } catch {
      alert("Couldn't delete the conversation. Backend reachable?");
      return;
    }
    // Optimistic local update so the rail responds instantly.
    setConversations((prev) => prev.filter((c) => c.scope !== scope));
    if (scope === activeScope) {
      const next = conversations.find((c) => c.scope !== scope) ?? null;
      navigateToScope(next?.scope ?? null);
    } else {
      router.refresh();
    }
  }

  async function clearActive() {
    if (!activeScope) return;
    if (!confirm("Clear all messages in this conversation? Cannot be undone.")) {
      return;
    }
    try {
      await apiDelete(`/api/chat?scope=${encodeURIComponent(activeScope)}`);
    } catch {
      alert("Couldn't clear the conversation. Backend reachable?");
      return;
    }
    setConversations((prev) => prev.filter((c) => c.scope !== activeScope));
    router.refresh();
  }

  return (
    <div className="flex flex-1 min-h-0 gap-4">
      <aside className="flex w-64 shrink-0 flex-col gap-2 rounded-lg border border-border bg-card/30 p-3">
        <Button
          type="button"
          size="sm"
          onClick={newChat}
          disabled={pending}
          className="w-full"
        >
          + New chat
        </Button>
        <div className="-mx-1 flex-1 overflow-y-auto px-1">
          {conversations.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs italic text-muted-foreground">
              No conversations yet.
            </p>
          ) : (
            <ul className="flex flex-col gap-1">
              {conversations.map((c) => (
                <ConversationItem
                  key={c.scope}
                  conversation={c}
                  active={c.scope === activeScope}
                  onSelect={() => navigateToScope(c.scope)}
                  onDelete={() => deleteScope(c.scope)}
                />
              ))}
            </ul>
          )}
        </div>
      </aside>

      <section className="flex min-h-0 flex-1 flex-col gap-3">
        {activeScope ? (
          <>
            <div className="flex items-center justify-between gap-3">
              <p className="truncate text-sm text-muted-foreground">
                {conversations.find((c) => c.scope === activeScope)?.title ??
                  "New chat"}
              </p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={clearActive}
              >
                Clear
              </Button>
            </div>
            <div className="flex min-h-0 flex-1 flex-col">
              <ChatPanel
                scope={activeScope}
                initialTurns={initialActiveTurns}
                variant="global"
                onAfterSend={refreshConversations}
              />
            </div>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            <p className="font-medium">No conversation selected</p>
            <p className="max-w-sm text-xs">
              Start a new chat or pick one from the list. Ask about SBA loans,
              deal structure, due diligence, or transition — the Operator
              searches a curated ETA knowledge base before answering.
            </p>
            <Button type="button" onClick={newChat}>
              + New chat
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}

function ConversationItem({
  conversation,
  active,
  onSelect,
  onDelete,
}: {
  conversation: Conversation;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <li className="group relative">
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-1.5 pr-8 text-left transition-colors",
          active
            ? "bg-muted text-foreground"
            : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
        )}
        aria-current={active ? "true" : undefined}
      >
        <span className="line-clamp-2 text-xs leading-snug">
          {conversation.title}
        </span>
        <span className="text-[10px] text-muted-foreground/70">
          {conversation.turn_count}{" "}
          {conversation.turn_count === 1 ? "turn" : "turns"} ·{" "}
          {new Date(conversation.last_at).toLocaleDateString()}
        </span>
      </button>
      <button
        type="button"
        onClick={onDelete}
        aria-label="Delete conversation"
        className="absolute right-1 top-1.5 hidden h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-background hover:text-foreground group-hover:flex"
      >
        ×
      </button>
    </li>
  );
}

function shortTitle(s: string): string {
  return s.length > 40 ? s.slice(0, 39) + "…" : s;
}
