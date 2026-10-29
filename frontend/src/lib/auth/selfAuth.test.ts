import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../firebase", () => ({ auth: { currentUser: null } }));
vi.mock("./provider", () => ({ isSelfAuth: () => true }));

import {
  adoptAccessToken,
  currentAccessToken,
  expireSession,
  getAccessToken,
  hasSession,
  readClaims,
  selfLogin,
  selfRefresh,
  SelfAuthError,
  subscribeSession,
} from "./selfAuth";

function jwt(claims: Record<string, unknown>): string {
  const enc = (o: unknown) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${enc({ alg: "HS256" })}.${enc(claims)}.sig`;
}

const tokenBody = (token: string) => ({ access_token: token, token_type: "bearer", expires_in: 900 });
const okJson = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  expireSession();
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  expireSession();
});

describe("selfAuth", () => {
  it("login stores the token in memory and notifies subscribers", async () => {
    fetchMock.mockImplementation(() => okJson(tokenBody("tok-1")));
    const listener = vi.fn();
    subscribeSession(listener);

    await selfLogin("a@example.com", "pw");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/auth/login");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin");
    expect(JSON.parse(init.body)).toEqual({ email: "a@example.com", password: "pw" });
    expect(currentAccessToken()).toBe("tok-1");
    expect(hasSession()).toBe(true);
    expect(listener).toHaveBeenCalled();
  });

  it("login 401 throws SelfAuthError (status and identifier detail)", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 })),
    );

    await expect(selfLogin("a@example.com", "bad")).rejects.toMatchObject({
      name: "SelfAuthError",
      status: 401,
      detail: "invalid_credentials",
    });
    expect(currentAccessToken()).toBeNull();
  });

  it("does not read an array detail (validation 422) as an identifier", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: [{ msg: "bad" }] }), { status: 422 })),
    );

    await expect(selfLogin("a", "b")).rejects.toMatchObject({ status: 422, detail: null });
  });

  it("three concurrent refresh calls send only one request (K6)", async () => {
    let release: (r: Response) => void = () => {};
    fetchMock.mockImplementation(
      () => new Promise<Response>((resolve) => { release = resolve; }),
    );

    const calls = [selfRefresh(), selfRefresh(), selfRefresh()];
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    release(new Response(JSON.stringify(tokenBody("tok-2")), { status: 200 }));

    await expect(Promise.all(calls)).resolves.toEqual(["tok-2", "tok-2", "tok-2"]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/auth/refresh");
  });

  it("refresh 401 drops the in-memory token", async () => {
    adoptAccessToken("old", 900);
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ detail: "invalid_credentials" }), { status: 401 })),
    );

    await expect(selfRefresh()).rejects.toBeInstanceOf(SelfAuthError);
    expect(currentAccessToken()).toBeNull();
  });

  it("simulated two tabs refresh one at a time via navigator.locks (K12)", async () => {
    // 同じ名前のロックを順番に取る簡易の navigator.locks
    let chain: Promise<unknown> = Promise.resolve();
    const lockOrder: string[] = [];
    vi.stubGlobal("navigator", {
      locks: {
        request: (name: string, cb: () => Promise<unknown>) => {
          lockOrder.push(name);
          const run = chain.then(cb);
          chain = run.catch(() => undefined);
          return run;
        },
      },
    });
    let inFlight = 0;
    let maxInFlight = 0;
    fetchMock.mockImplementation(async () => {
      inFlight += 1;
      maxInFlight = Math.max(maxInFlight, inFlight);
      await new Promise((r) => setTimeout(r, 5));
      inFlight -= 1;
      return new Response(JSON.stringify(tokenBody("tok")), { status: 200 });
    });

    // タブ A・タブ B の代わりに、モジュールを分けて読み込む
    vi.resetModules();
    const tabA = await import("./selfAuth");
    vi.resetModules();
    const tabB = await import("./selfAuth");
    await Promise.all([tabA.selfRefresh(), tabB.selfRefresh()]);

    expect(lockOrder).toEqual(["sa-auth-refresh", "sa-auth-refresh"]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(maxInFlight).toBe(1);
  });

  it("without navigator.locks the same tab still sends one request (B7)", async () => {
    vi.stubGlobal("navigator", {});
    fetchMock.mockImplementation(() => okJson(tokenBody("tok-3")));

    await expect(Promise.all([selfRefresh(), selfRefresh()])).resolves.toEqual(["tok-3", "tok-3"]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("getAccessToken reuses a fresh token and refreshes once when it is about to expire", async () => {
    adoptAccessToken("fresh", 900);
    await expect(getAccessToken()).resolves.toBe("fresh");
    expect(fetchMock).not.toHaveBeenCalled();

    adoptAccessToken("stale", 10);
    fetchMock.mockImplementation(() => okJson(tokenBody("renewed")));
    await expect(getAccessToken()).resolves.toBe("renewed");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("readClaims reads sub and email; a broken token is null", () => {
    expect(readClaims(jwt({ sub: "42", email: "a@example.com" }))).toEqual({ sub: "42", email: "a@example.com" });
    expect(readClaims(jwt({ sub: "42" }))).toBeNull();
    expect(readClaims("not-a-token")).toBeNull();
  });

  it("never puts the access token in browser storage (K3)", async () => {
    // 保存領域（Storage）への書き込みが 1 回も無いこと
    const local = vi.spyOn(Storage.prototype, "setItem");
    fetchMock.mockImplementation(() => okJson(tokenBody("tok-4")));

    await selfLogin("a@example.com", "pw");

    expect(local).not.toHaveBeenCalled();
    local.mockRestore();
  });
});
