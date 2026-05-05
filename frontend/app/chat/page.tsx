export default function ChatPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Global chat — Operator-leaning, no listing context. Routing lands in
          Phase 2.
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Conversation panel placeholder.
      </div>
    </div>
  );
}
