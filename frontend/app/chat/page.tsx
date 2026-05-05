import { ChatPanel } from "@/components/chat-panel";
import { ApiError, apiGet } from "@/lib/api";
import { type ChatTurn } from "@/lib/chat";

export const dynamic = "force-dynamic";

const SCOPE = "global";

export default async function ChatPage() {
  let initialTurns: ChatTurn[] = [];
  let fetchError: string | null = null;
  try {
    initialTurns = await apiGet<ChatTurn[]>(`/api/chat?scope=${SCOPE}`);
  } catch (err) {
    fetchError =
      err instanceof ApiError
        ? `Backend returned ${err.status}: ${err.message}`
        : err instanceof Error
          ? err.message
          : "Could not load chat history.";
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Operator agent — global scope. Searches the curated ETA knowledge
          base before answering and cites sources by filename.
        </p>
      </div>

      {fetchError ? (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <p className="font-medium">Couldn’t load chat history.</p>
          <p className="mt-1 font-mono text-xs">{fetchError}</p>
          <p className="mt-2 text-xs">
            Make sure the backend is running on{" "}
            <code className="font-mono">localhost:8000</code>.
          </p>
        </div>
      ) : (
        <ChatPanel scope={SCOPE} initialTurns={initialTurns} />
      )}
    </div>
  );
}
