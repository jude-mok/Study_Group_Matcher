import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Session } from "./types";
import { demoUser } from "./demo";

const previous: Session = {
  access_token: "old",
  refresh_token: "refresh-old",
  expires_at: 0,
  user: demoUser,
};
const fresh: Session = {
  ...previous,
  access_token: "new",
  refresh_token: "refresh-new",
  expires_at: Math.floor(Date.now() / 1000) + 3600,
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("VITE_API_URL", "https://api.example.invalid");
  vi.stubGlobal("window", new EventTarget());
  const values = new Map<string, string>();
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => values.get(key) || null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("authenticated API client", () => {
  it("shares one refresh between simultaneous requests", async () => {
    const fetcher = vi.fn(async (url: string) =>
      url.endsWith("/auth/refresh") ? json(fresh) : json({ ok: true }),
    );
    vi.stubGlobal("fetch", fetcher);
    const client = await import("./api");
    client.setSession(previous);
    await Promise.all([client.api("/courses/"), client.api("/rooms")]);
    expect(
      fetcher.mock.calls.filter(([url]) => url.endsWith("/auth/refresh")),
    ).toHaveLength(1);
    expect(client.getSession()?.access_token).toBe("new");
  });
  it("does not restore a logged-out session after a late refresh", async () => {
    let resolve!: (response: Response) => void;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((done) => {
            resolve = done;
          }),
      ),
    );
    const client = await import("./api");
    client.setSession(previous);
    const pending = client.refreshSession();
    client.setSession(null);
    resolve(json(fresh));
    await expect(pending).rejects.toThrow(/session has changed/);
    expect(client.getSession()).toBeNull();
  });
  it("keeps the session when a sleeping server or network fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    const client = await import("./api");
    client.setSession(previous);
    await expect(client.refreshSession()).rejects.toThrow(/wake up/);
    expect(client.getSession()).toEqual(previous);
  });
  it("clears invalid credentials when refresh is rejected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json({ detail: "Invalid refresh token" }, 401)),
    );
    const client = await import("./api");
    client.setSession(previous);
    await expect(client.api("/rooms")).rejects.toThrow(/Invalid refresh token/);
    expect(client.getSession()).toBeNull();
  });
  it("formats validation errors and accepts empty delete responses", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        json({ detail: [{ msg: "End must follow start" }] }, 422),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetcher);
    const client = await import("./api");
    client.setSession(fresh);
    await expect(client.api("/schedules/", "POST", {})).rejects.toThrow(
      "End must follow start",
    );
    await expect(
      client.api("/schedules/one", "DELETE"),
    ).resolves.toBeUndefined();
  });
});
