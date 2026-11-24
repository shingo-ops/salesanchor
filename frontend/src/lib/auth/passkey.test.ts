import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mock = vi.hoisted(() => ({
  supported: true,
  startAuthentication: vi.fn(),
  startRegistration: vi.fn(),
  post: vi.fn(),
  get: vi.fn(),
  autofill: true,
  cancelCeremony: vi.fn(),
}));

vi.mock("@simplewebauthn/browser", () => ({
  browserSupportsWebAuthn: () => mock.supported,
  browserSupportsWebAuthnAutofill: async () => mock.autofill,
  startAuthentication: mock.startAuthentication,
  startRegistration: mock.startRegistration,
  WebAuthnAbortService: { cancelCeremony: mock.cancelCeremony },
  base64URLStringToBuffer: (s: string) => new TextEncoder().encode(s).buffer,
  bufferToBase64URLString: (b: ArrayBuffer) => `b64:${b.byteLength}`,
}));
vi.mock("../api", () => ({ api: { post: mock.post, get: mock.get } }));

import {
  autoRegisterPasskey,
  conditionalCreateSupported,
  immediateGetSupported,
  immediatePasskeyLogin,
  passkeyBrowserError,
  passkeySupported,
  registerPasskey,
  selfPasskeyLogin,
  startPasskeyAutofill,
} from "./passkey";
import { currentAccessToken, expireSession } from "./selfAuth";
import { registerDevSession } from "./devSessionSlot";
import { registerTestDevSession } from "../../test-utils/devSession";

let fetchMock: ReturnType<typeof vi.fn>;
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });

beforeEach(() => {
  registerDevSession(null);
  mock.supported = true;
  mock.startAuthentication.mockReset();
  mock.startRegistration.mockReset();
  mock.post.mockReset();
  mock.get.mockReset();
  mock.autofill = true;
  mock.cancelCeremony.mockReset();
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
    registerTestDevSession();
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

describe("conditionalCreateSupported", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("is false when getClientCapabilities is missing", async () => {
    vi.stubGlobal("PublicKeyCredential", {});
    expect(await conditionalCreateSupported()).toBe(false);
  });

  it("is true only when conditionalCreate is true", async () => {
    vi.stubGlobal("PublicKeyCredential", { getClientCapabilities: async () => ({ conditionalCreate: true }) });
    expect(await conditionalCreateSupported()).toBe(true);
    vi.stubGlobal("PublicKeyCredential", { getClientCapabilities: async () => ({ conditionalCreate: false }) });
    expect(await conditionalCreateSupported()).toBe(false);
  });

  it("is false when it throws", async () => {
    vi.stubGlobal("PublicKeyCredential", {
      getClientCapabilities: async () => {
        throw new Error("boom");
      },
    });
    expect(await conditionalCreateSupported()).toBe(false);
  });
});

describe("immediateGetSupported", () => {
  it("T1 is false without getClientCapabilities, true only when immediateGet is true, false when it throws", async () => {
    vi.stubGlobal("PublicKeyCredential", {});
    expect(await immediateGetSupported()).toBe(false);
    vi.stubGlobal("PublicKeyCredential", { getClientCapabilities: async () => ({ immediateGet: true }) });
    expect(await immediateGetSupported()).toBe(true);
    vi.stubGlobal("PublicKeyCredential", { getClientCapabilities: async () => ({ immediateGet: false }) });
    expect(await immediateGetSupported()).toBe(false);
    vi.stubGlobal("PublicKeyCredential", {
      getClientCapabilities: async () => {
        throw new Error("boom");
      },
    });
    expect(await immediateGetSupported()).toBe(false);
  });
});

describe("immediatePasskeyLogin", () => {
  const options = { challenge: "abc", rpId: "app.salesanchor.jp", timeout: 60000, userVerification: "preferred" };
  const buf = (n: number) => new Uint8Array(n).buffer;

  function stubOptionsAndVerify() {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/passkey/login/options"
          ? json(200, { challenge_id: "chal-9", options })
          : json(200, { access_token: "imm.tok.en", token_type: "bearer", expires_in: 900 }),
      ),
    );
  }

  it("T2 asks the browser with uiMode immediate and no allowCredentials/password, then verifies", async () => {
    stubOptionsAndVerify();
    const get = vi.fn().mockResolvedValue({
      id: "cred-1",
      rawId: buf(4),
      authenticatorAttachment: "platform",
      response: { authenticatorData: buf(3), clientDataJSON: buf(2), signature: buf(1), userHandle: null },
      getClientExtensionResults: () => ({}),
    });
    vi.stubGlobal("navigator", { credentials: { get } });

    await immediatePasskeyLogin();

    const arg = get.mock.calls[0][0];
    expect(arg.uiMode).toBe("immediate");
    expect(arg.publicKey.rpId).toBe("app.salesanchor.jp");
    expect("allowCredentials" in arg.publicKey).toBe(false);
    expect("password" in arg.publicKey).toBe(false);
    expect("password" in arg).toBe(false);
    const verifyBody = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(verifyBody.challenge_id).toBe("chal-9");
    expect(verifyBody.credential.id).toBe("cred-1");
    expect(currentAccessToken()).toBe("imm.tok.en");
  });

  it("T2 passes options extensions through when present", async () => {
    fetchMock.mockResolvedValue(
      json(200, { challenge_id: "c", options: { ...options, extensions: { appid: "x" } } }),
    );
    const get = vi.fn().mockRejectedValue(Object.assign(new Error("n"), { name: "NotAllowedError" }));
    vi.stubGlobal("navigator", { credentials: { get } });
    await expect(immediatePasskeyLogin()).rejects.toThrow();
    expect(get.mock.calls[0][0].publicKey.extensions).toEqual({ appid: "x" });
  });

  it("T2 NotAllowedError is thrown as is and verify is not called", async () => {
    stubOptionsAndVerify();
    const get = vi.fn().mockRejectedValue(Object.assign(new Error("none"), { name: "NotAllowedError" }));
    vi.stubGlobal("navigator", { credentials: { get } });

    await expect(immediatePasskeyLogin()).rejects.toMatchObject({ name: "NotAllowedError" });

    expect(fetchMock.mock.calls.map(([u]) => u)).toEqual(["/api/v1/auth/passkey/login/options"]);
    expect(currentAccessToken()).toBeNull();
  });
});

describe("startPasskeyAutofill", () => {
  const options = { challenge: "abc", rpId: "app.salesanchor.jp" };
  const credential = { id: "cred", response: {} };

  function stubFetch() {
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === "/api/v1/auth/passkey/login/options"
          ? json(200, { challenge_id: "chal-a", options })
          : json(200, { access_token: "auto.tok.en", token_type: "bearer", expires_in: 900 }),
      ),
    );
  }

  it("T3 calls startAuthentication with useBrowserAutofill, then verify", async () => {
    stubFetch();
    mock.startAuthentication.mockResolvedValue(credential);

    await startPasskeyAutofill(() => false);

    expect(mock.startAuthentication).toHaveBeenCalledWith({ optionsJSON: options, useBrowserAutofill: true });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ challenge_id: "chal-a", credential });
    expect(currentAccessToken()).toBe("auto.tok.en");
  });

  it("T3 stale at the entrance: no request at all, AbortError", async () => {
    stubFetch();
    await expect(startPasskeyAutofill(() => true)).rejects.toMatchObject({ name: "AbortError" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("T3 stale after options: startAuthentication is not called, AbortError", async () => {
    stubFetch();
    let calls = 0;
    await expect(startPasskeyAutofill(() => ++calls >= 2)).rejects.toMatchObject({ name: "AbortError" });
    expect(mock.startAuthentication).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("T3 stale after startAuthentication: verify is not called, AbortError", async () => {
    stubFetch();
    mock.startAuthentication.mockResolvedValue(credential);
    let calls = 0;
    await expect(startPasskeyAutofill(() => ++calls >= 3)).rejects.toMatchObject({ name: "AbortError" });
    expect(mock.startAuthentication).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(currentAccessToken()).toBeNull();
  });

  it("T3 options fails (429): AbortError, startAuthentication and verify are not called", async () => {
    fetchMock.mockResolvedValue(json(429, { detail: "too many" }));

    await expect(startPasskeyAutofill(() => false)).rejects.toMatchObject({ name: "AbortError" });

    expect(mock.startAuthentication).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(currentAccessToken()).toBeNull();
  });
});

describe("autoRegisterPasskey", () => {
  const named = (name: string) => {
    const e = new Error(name);
    e.name = name;
    return e;
  };

  beforeEach(() => {
    mock.post.mockImplementation((path: string) =>
      Promise.resolve(path.endsWith("/options") ? { challenge_id: "c1", options: { challenge: "x" } } : {}),
    );
  });

  it("created: options with auto, conditional registration, then verify", async () => {
    mock.startRegistration.mockResolvedValue({ id: "cred" });
    expect(await autoRegisterPasskey()).toBe("created");
    expect(mock.post).toHaveBeenCalledWith("/auth/passkey/register/options", { auto: true });
    expect(mock.startRegistration).toHaveBeenCalledWith({ optionsJSON: { challenge: "x" }, useAutoRegister: true });
    expect(mock.post).toHaveBeenCalledWith("/auth/passkey/register/verify", {
      challenge_id: "c1",
      credential: { id: "cred" },
      label: "",
    });
  });

  it("InvalidStateError is exists", async () => {
    mock.startRegistration.mockRejectedValue(named("InvalidStateError"));
    expect(await autoRegisterPasskey()).toBe("exists");
  });

  it("NotAllowedError is not_allowed", async () => {
    mock.startRegistration.mockRejectedValue(named("NotAllowedError"));
    expect(await autoRegisterPasskey()).toBe("not_allowed");
  });

  it("other errors are failed", async () => {
    mock.startRegistration.mockRejectedValue(new Error("other"));
    expect(await autoRegisterPasskey()).toBe("failed");
  });

  it("gives up after 10 seconds", async () => {
    vi.useFakeTimers();
    try {
      mock.startRegistration.mockReturnValue(new Promise(() => {}));
      const pending = autoRegisterPasskey();
      await vi.advanceTimersByTimeAsync(10_000);
      expect(await pending).toBe("failed");
    } finally {
      vi.useRealTimers();
    }
  });
});
