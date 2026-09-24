import type { Session, SignupInput } from "./types";

export const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const SESSION_KEY = "study-matcher:session:v1";
let session: Session | null = null;
try {
  session = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
} catch {
  /* Unavailable storage starts a fresh session. */
}
let refreshing: Promise<Session> | null = null;

export function getSession() {
  return session;
}
export function setSession(next: Session | null) {
  session = next;
  try {
    if (next) sessionStorage.setItem(SESSION_KEY, JSON.stringify(next));
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* The in-memory session still works when storage is unavailable. */
  }
  window.dispatchEvent(new Event("study-session"));
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
  token?: string,
): Promise<T> {
  if (!API_URL)
    throw new ApiError(
      "Account mode is not connected yet. You can explore the demo instead.",
      0,
    );
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(75_000),
    });
  } catch {
    throw new ApiError(
      "The server is taking a moment to wake up or could not be reached. Please try again.",
      0,
    );
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item: { msg?: string }) => item.msg || "Invalid value")
              .join(". ")
          : "Something went wrong. Please try again.";
    throw new ApiError(message, response.status);
  }
  return data as T;
}

export async function refreshSession(): Promise<Session> {
  if (refreshing) return refreshing;
  const previous = session;
  if (!previous) throw new ApiError("Please sign in again.", 401);
  refreshing = request<Session>("/auth/refresh", "POST", {
    refresh_token: previous.refresh_token,
  })
    .then((next) => {
      // A late refresh must not restore a session after sign-out or another login.
      if (session !== previous)
        throw new ApiError(
          "Your session has changed. Please sign in again.",
          401,
        );
      setSession(next);
      return next;
    })
    .catch((error) => {
      if (
        session === previous &&
        error instanceof ApiError &&
        [400, 401, 403].includes(error.status)
      )
        setSession(null);
      throw error;
    })
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  if (!session) throw new ApiError("Please sign in again.", 401);
  if (session.expires_at * 1000 < Date.now() + 30_000) await refreshSession();
  try {
    return await request<T>(path, method, body, session?.access_token);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    const next = await refreshSession();
    return request<T>(path, method, body, next.access_token);
  }
}

export async function login(nyu_email: string, password: string) {
  const next = await request<Session>("/auth/login", "POST", {
    nyu_email,
    password,
  });
  setSession(next);
  return next.user;
}
export function signup(input: SignupInput) {
  return request("/auth/signup", "POST", input);
}

export async function socketUrl(roomId: string) {
  if (!session) throw new ApiError("Please sign in again.", 401);
  if (session.expires_at * 1000 < Date.now() + 30_000) await refreshSession();
  const url = new URL(`${API_URL}/ws/rooms/${encodeURIComponent(roomId)}`);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("token", session!.access_token);
  return url.toString();
}

export function requestPasswordReset(email: string) {
  return request("/auth/password-reset/request", "POST", { email });
}

export function confirmPasswordReset(new_password: string, token: string) {
  return request(
    "/auth/password-reset/confirm",
    "POST",
    { new_password },
    token,
  );
}
