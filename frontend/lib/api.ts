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

async function request<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    method,
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
    ...init,
  });

  if (!res.ok) {
    const errBody = await res.text().catch(() => "");
    throw new ApiError(
      res.status,
      url,
      `${method} ${url} failed: ${res.status} ${res.statusText}${
        errBody ? ` — ${errBody}` : ""
      }`,
    );
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

/** GET a JSON resource. `path` should start with `/`. */
export function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>("GET", path, undefined, init);
}

/** POST a JSON body and return the parsed JSON response. */
export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

/** PATCH a JSON body and return the parsed JSON response. */
export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>("PATCH", path, body);
}

/** DELETE a resource. Returns `undefined` on the expected 204 response. */
export function apiDelete(path: string): Promise<void> {
  return request<void>("DELETE", path);
}
