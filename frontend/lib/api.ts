/**
 * Typed fetch wrapper for the Silvercurrent backend.
 *
 * Reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
 * Throws on non-2xx responses with a descriptive message.
 */

const DEFAULT_API_URL = "http://localhost:8000";

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;

export class ApiError extends Error {
  readonly status: number;
  readonly url: string;

  constructor(status: number, url: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.url = url;
  }
}

/**
 * GET `path` from the backend and parse the JSON body as `T`.
 *
 * `path` should start with `/` (e.g. `/api/health`). Throws `ApiError`
 * on non-2xx responses.
 */
export async function apiGet<T>(path: string): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(
      res.status,
      url,
      `GET ${url} failed: ${res.status} ${res.statusText}${body ? ` — ${body}` : ""}`,
    );
  }

  return (await res.json()) as T;
}
