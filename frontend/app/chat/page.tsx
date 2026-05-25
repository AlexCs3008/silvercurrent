import { ChatWorkspace } from "@/components/chat-workspace";
import { ApiError, apiGet } from "@/lib/api";
import type { ChatTurn, Conversation } from "@/lib/chat";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ scope?: string }>;

export default async function ChatPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { scope: requestedScope } = await searchParams;

  let conversations: Conversation[] = [];
  let fetchError: string | null = null;
  try {
    conversations = await apiGet<Conversation[]>("/api/chat/conversations");
  } catch (err) {
    fetchError =
      err instanceof ApiError
        ? `Backend returned ${err.status}: ${err.message}`
        : err instanceof Error
          ? err.message
          : "Could not load conversations.";
  }

  // Resolve the active scope: explicit ?scope= wins, else most-recent
  // conversation, else null (empty state). A requested scope that doesn't
  // appear in the list yet is still active — happens right after "+ New chat"
  // before the first message lands.
  const activeScope: string | null =
    requestedScope ??
    (conversations.length > 0 ? conversations[0].scope : null);

  let initialActiveTurns: ChatTurn[] = [];
  if (activeScope) {
    try {
      initialActiveTurns = await apiGet<ChatTurn[]>(
        `/api/chat?scope=${encodeURIComponent(activeScope)}`,
      );
    } catch {
      // Brand-new scopes simply return []; any other failure degrades to empty
      // and the chat panel will surface send errors itself.
      initialActiveTurns = [];
    }
  }

  return (
    // h-[calc(100vh-4rem)] caps the page to the viewport (minus main's py-8
    // padding) so the inner flex column can constrain its scrolling child.
    // Without a height ceiling, flex-1 + overflow-y-auto on the message
    // scroller would let the page grow indefinitely instead of scrolling.
    <div className="flex h-[calc(100vh-4rem)] min-h-0 flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          General ETA conversations. The Router dispatches each message to the
          Operator (knowledge-base answers) or, when relevant, the Analyst.
        </p>
      </div>

      {fetchError ? (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <p className="font-medium">Couldn’t load conversations.</p>
          <p className="mt-1 font-mono text-xs">{fetchError}</p>
          <p className="mt-2 text-xs">
            Make sure the backend is running on{" "}
            <code className="font-mono">localhost:8000</code>.
          </p>
        </div>
      ) : (
        <ChatWorkspace
          initialConversations={conversations}
          activeScope={activeScope}
          initialActiveTurns={initialActiveTurns}
        />
      )}
    </div>
  );
}
