/**
 * 動いている間の 401（自社ログインのときだけ）の扱い。
 * - /api/v1/auth/ で始まる口の 401 では refresh しない
 * - それ以外の口の 401 は refresh を 1 回送り、成功したら元の要求を 1 回だけ送り直す
 * - 送り直しも 401 なら、セッションを捨てる（ProtectedRoute がログイン画面へ移す）
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../firebase", () => ({ auth: { currentUser: null } }));
vi.mock("./provider", () => ({ isSelfAuth: () => true }));

import { api } from "../api";
import { adoptAccessToken, currentAccessToken, expireSession } from "./selfAuth";

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>;
let fetchMock: ReturnType<typeof vi.fn>;
let handler: Handler;

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });
const calls = (prefix: string) => fetchMock.mock.calls.filter(([url]) => String(url).startsWith(prefix));
const bearerOf = (call: unknown[]) => (call[1] as { headers: Record<string, string> }).headers.Authorization;

beforeEach(() => {
  expireSession();
  adoptAccessToken("tok-old", 900);
  fetchMock = vi.fn((url: string, init: RequestInit) => Promise.resolve(handler(url, init)));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  expireSession();
});

describe("401 handling (self login)", () => {
  it("401 on other endpoints: one refresh, then the original request is retried once with the new token", async () => {
    let first = true;
    handler = (url) => {
      if (url === "/api/v1/auth/refresh") return json(200, { access_token: "tok-new", token_type: "bearer", expires_in: 900 });
      if (first) {
        first = false;
        return json(401, { detail: "invalid token" });
      }
      return json(200, { ok: true });
    };

    await expect(api.post("/leads", { name: "x" })).resolves.toEqual({ ok: true });

    expect(calls("/api/v1/auth/refresh")).toHaveLength(1);
    const leads = calls("/api/v1/leads");
    expect(leads).toHaveLength(2);
    expect(bearerOf(leads[0])).toBe("Bearer tok-old");
    expect(bearerOf(leads[1])).toBe("Bearer tok-new");
    expect(currentAccessToken()).toBe("tok-new");
  });

  it("three concurrent calls that all get 401 cause only one refresh (K6)", async () => {
    let leftBeforeRefresh = 3;
    handler = (url) => {
      if (url === "/api/v1/auth/refresh") return json(200, { access_token: "tok-new", token_type: "bearer", expires_in: 900 });
      if (leftBeforeRefresh > 0) {
        leftBeforeRefresh -= 1;
        return json(401, { detail: "invalid token" });
      }
      return json(200, { ok: true });
    };

    await Promise.all([api.get("/a"), api.get("/b"), api.get("/c")]);

    expect(calls("/api/v1/auth/refresh")).toHaveLength(1);
  });

  it("retry also 401: drops the session and does not retry again", async () => {
    handler = (url) => {
      if (url === "/api/v1/auth/refresh") return json(200, { access_token: "tok-new", token_type: "bearer", expires_in: 900 });
      return json(401, { detail: "invalid token" });
    };

    await expect(api.post("/leads", {})).rejects.toMatchObject({ status: 401 });

    expect(calls("/api/v1/leads")).toHaveLength(2);
    expect(calls("/api/v1/auth/refresh")).toHaveLength(1);
    expect(currentAccessToken()).toBeNull();
  });

  it("refresh 401: drops the session and does not retry the original request", async () => {
    handler = (url) => {
      if (url === "/api/v1/auth/refresh") return json(401, { detail: "invalid_credentials" });
      return json(401, { detail: "invalid token" });
    };

    await expect(api.get("/leads")).rejects.toMatchObject({ status: 401 });

    expect(calls("/api/v1/leads")).toHaveLength(1);
    expect(currentAccessToken()).toBeNull();
  });

  it("401 on /auth/ endpoints does not refresh (no ping-pong)", async () => {
    handler = () => json(401, { detail: "invalid_credentials" });

    await expect(api.post("/auth/something", {})).rejects.toMatchObject({ status: 401 });

    expect(calls("/api/v1/auth/refresh")).toHaveLength(0);
    expect(calls("/api/v1/auth/something")).toHaveLength(1);
    // password/change・logout 以外の /auth/ の 401 ではセッションを捨てない
    expect(currentAccessToken()).toBe("tok-old");
  });

  it("401 on password/change and logout means the login ended: drop the session without refresh", async () => {
    handler = () => json(401, { detail: "invalid token" });

    await expect(api.post("/auth/password/change", {})).rejects.toMatchObject({ status: 401 });

    expect(calls("/api/v1/auth/refresh")).toHaveLength(0);
    expect(currentAccessToken()).toBeNull();

    adoptAccessToken("tok-again", 900);
    await expect(api.post("/auth/logout", {})).rejects.toMatchObject({ status: 401 });
    expect(calls("/api/v1/auth/refresh")).toHaveLength(0);
    expect(currentAccessToken()).toBeNull();
  });

  it("non-401 errors do not refresh", async () => {
    handler = () => json(400, { detail: "invalid_credentials" });

    await expect(api.post("/auth/password/change", {})).rejects.toMatchObject({ status: 400 });

    expect(calls("/api/v1/auth/refresh")).toHaveLength(0);
    expect(currentAccessToken()).toBe("tok-old");
  });

  it("401 on passkey register/list/delete endpoints: one refresh, then the request is retried once", async () => {
    for (const [method, path] of [
      ["post", "/auth/passkey/register/options"],
      ["get", "/auth/passkeys"],
    ] as const) {
      fetchMock.mockClear();
      adoptAccessToken("tok-old", 900);
      let first = true;
      handler = (url) => {
        if (url === "/api/v1/auth/refresh") return json(200, { access_token: "tok-new", token_type: "bearer", expires_in: 900 });
        if (first) {
          first = false;
          return json(401, { detail: "invalid token" });
        }
        return json(200, { ok: true });
      };

      await expect(method === "post" ? api.post(path, {}) : api.get(path)).resolves.toEqual({ ok: true });

      expect(calls("/api/v1/auth/refresh")).toHaveLength(1);
      expect(calls(`/api/v1${path}`)).toHaveLength(2);
    }
  });
});
