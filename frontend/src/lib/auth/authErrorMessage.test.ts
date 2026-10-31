import { describe, expect, it } from "vitest";
import { authErrorMessage } from "./authErrorMessage";
import type { AuthErrorContext } from "./authErrorMessage";
import { SelfAuthError } from "./selfAuth";
import { ApiError } from "../api";

// t は「キーをそのまま返す」ので、どのキーを選んだかを確かめられる
const t = (key: string) => key;
const msg = (err: unknown, context: AuthErrorContext = "login") => authErrorMessage(err, t, context);

describe("authErrorMessage", () => {
  it("401 is the single login error message", () => {
    expect(msg(new SelfAuthError(401, "invalid_credentials"))).toBe("authError.invalidCredentials");
  });

  it("403, 404 and 429", () => {
    expect(msg(new SelfAuthError(403, "forbidden_origin"))).toBe("authError.forbiddenOrigin");
    expect(msg(new SelfAuthError(404, null))).toBe("authError.unavailable");
    expect(msg(new SelfAuthError(429, "too_many_attempts"))).toBe("authError.tooManyAttempts");
  });

  it("400 uses a different key per endpoint", () => {
    expect(msg(new SelfAuthError(400, "invalid_or_expired_token"), "resetConfirm")).toBe("authError.resetLinkInvalid");
    expect(msg(new ApiError("invalid_credentials", 400, "invalid_credentials"), "passwordChange")).toBe(
      "authError.currentPasswordWrong",
    );
    expect(msg(new SelfAuthError(400, null), "login")).toBe("authError.default");
  });

  it("422 uses one key per detail identifier", () => {
    expect(msg(new SelfAuthError(422, "password_too_short"), "resetConfirm")).toBe("authError.passwordTooShort");
    expect(msg(new SelfAuthError(422, "password_too_long"), "resetConfirm")).toBe("authError.passwordTooLong");
    expect(msg(new ApiError("password_too_common", 422, "password_too_common"), "passwordChange")).toBe(
      "authError.passwordTooCommon",
    );
  });

  it("validation 422 (array detail) and unknown identifiers share one message", () => {
    expect(msg(new ApiError("HTTP 422", 422, [{ msg: "x" }]))).toBe("authError.validation");
    expect(msg(new SelfAuthError(422, "something_else"))).toBe("authError.validation");
  });

  it("other statuses and network failures share one message", () => {
    expect(msg(new SelfAuthError(500, null))).toBe("authError.default");
    expect(msg(new TypeError("Failed to fetch"))).toBe("authError.default");
    expect(msg(undefined)).toBe("authError.default");
  });

  it("never shows detail prose on screen", () => {
    const out = msg(new SelfAuthError(500, "internal secret text"));
    expect(out).toBe("authError.default");
  });

  it("passkey context never shows the password message", () => {
    expect(msg(new SelfAuthError(401, "invalid_credentials"), "passkey")).toBe("authError.passkeyFailed");
    expect(msg(new SelfAuthError(400, "challenge_expired"), "passkey")).toBe("authError.passkeyExpired");
    expect(msg(new ApiError("passkey_invalid", 400, "passkey_invalid"), "passkey")).toBe("authError.passkeyFailed");
    expect(msg(new ApiError("passkey_exists", 409, "passkey_exists"), "passkey")).toBe("authError.passkeyExists");
    expect(msg(new ApiError("passkey_limit", 409, "passkey_limit"), "passkey")).toBe("authError.passkeyLimit");
    expect(msg(new SelfAuthError(503, "unavailable"), "passkey")).toBe("authError.unavailable");
    expect(msg(new SelfAuthError(429, "too_many_attempts"), "passkey")).toBe("authError.tooManyAttempts");
  });

  it("existing contexts are unchanged by the passkey context", () => {
    expect(msg(new SelfAuthError(401, null), "login")).toBe("authError.invalidCredentials");
    expect(msg(new SelfAuthError(400, null), "passwordChange")).toBe("authError.currentPasswordWrong");
    expect(msg(new SelfAuthError(409, "passkey_exists"), "login")).toBe("authError.default");
  });
});
