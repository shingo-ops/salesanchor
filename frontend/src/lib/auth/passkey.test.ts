import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mock = vi.hoisted(() => ({
  self: true,
  supported: true,
  startAuthentication: vi.fn(),
  startRegistration: vi.fn(),
  post: vi.fn(),
}));

vi.mock("../firebase", () => ({ auth: { currentUser: null } }));
vi.mock("./provider", () => ({ isSelfAuth: () => mock.self }));
vi.mock("@simplewebauthn/browser", () => ({
  browserSupportsWebAuthn: () => mock.supported,
  startAuthentication: mock.startAuthentication,
  startRegistration: mock.startRegistration,
}));
vi.mock("../api", () => ({ api: { post: mock.post } }));

import { passkeyBrowserError, passkeySupported, registerPasskey, selfPasskeyLogin } from "./passkey";
import { currentAccessToken, expireSession } from "./selfAuth";

let fetchMock: ReturnType<typeof vi.fn>;
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });

beforeEach(() => {
  mock.self = true;
  mock.supported = true;
  mock.startAuthentication.mockReset();
  mock.startRegistration.mockReset();
  mock.post.mockReset();
  expireSession();
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  expireSession();
});

describe("passkeySupported", () => {
  it("is true only for self login on a supporting device", () => {
    expect(passkeySupported()).toBe(true);
    mock.supported = false;
    expect(passkeySupported()).toBe(false);
    mock.supported = true;
    mock.self = false;
    expect(passkeySupported()).toBe(false);
  });
});

describe("selfPasskeyLogin", () => {
  it("calls options, then the browser, then verify, and keeps the token in memory", async () => {
    const options = { challenge: "abc", rpId: "app.salesanchor.jp" };
    const credential = { id: "cred", response: {} };
    mock.startAuthentication.mockResolvedValue(credential);
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/passkey/login/options"
          ? json(200, { challenge_id: "chal-1", options })
          : json(200, { access_token: "tok.en.value", token_type: "bearer", expires_in: 900 }),
      ),
    );

    await selfPasskeyLogin();

    expect(fetchMock.mock.calls.map(([u]) => u)).toEqual([
      "/api/v1/auth/passkey/login/options",
      "/api/v1/auth/passkey/login/verify",
    ]);
    expect(mock.startAuthentication).toHaveBeenCalledWith({ optionsJSON: options });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ challenge_id: "chal-1", credential });
    expect(currentAccessToken()).toBe("tok.en.value");
  });

  it("does not call verify when the browser step is cancelled", async () => {
    mock.startAuthentication.mockRejectedValue(new Error("cancelled"));
    fetchMock.mockResolvedValue(json(200, { challenge_id: "chal-1", options: {} }));

    await expect(selfPasskeyLogin()).rejects.toThrow("cancelled");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(currentAccessToken()).toBeNull();
  });
});

describe("registerPasskey", () => {
  it("calls options, the browser, then verify with the label", async () => {
    const credential = { id: "cred" };
    mock.post.mockResolvedValueOnce({ challenge_id: "chal-2", options: { challenge: "x" } }).mockResolvedValueOnce({});
    mock.startRegistration.mockResolvedValue(credential);

    await registerPasskey("work iPhone");

    expect(mock.post).toHaveBeenNthCalledWith(1, "/auth/passkey/register/options", {});
    expect(mock.startRegistration).toHaveBeenCalledWith({ optionsJSON: { challenge: "x" } });
    expect(mock.post).toHaveBeenNthCalledWith(2, "/auth/passkey/register/verify", {
      challenge_id: "chal-2",
      credential,
      label: "work iPhone",
    });
  });
});

describe("passkeyBrowserError", () => {
  it("maps NotAllowedError to cancelled and InvalidStateError to exists", () => {
    const named = (name: string) => Object.assign(new Error("x"), { name });
    expect(passkeyBrowserError(named("NotAllowedError"))).toBe("cancelled");
    expect(passkeyBrowserError(named("InvalidStateError"))).toBe("exists");
    expect(passkeyBrowserError(named("Other"))).toBeNull();
    expect(passkeyBrowserError("string")).toBeNull();
  });
});
