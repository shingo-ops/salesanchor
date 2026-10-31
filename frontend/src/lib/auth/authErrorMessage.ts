/**
 * 自社 API（/api/v1/auth/*）の誤りをエンドユーザー向けの文言に変換する（ADR-027: 文言は t()）。
 * 口（context）と状態コードから文言キーを 1 つ選ぶ。detail は決まった識別子のときだけ読み、本文の文章は読まない。
 * Firebase 用の firebaseErrorMessage.ts は便6 まで残す。
 */

export type AuthErrorContext = "login" | "resetRequest" | "resetConfirm" | "passwordChange" | "passkey";

interface StatusLike {
  status: number;
  /** SelfAuthError.detail（識別子または null） */
  detail?: string | null;
  /** ApiError.responseDetail（FastAPI の detail そのまま。入力検査の 422 では配列） */
  responseDetail?: unknown;
}

function isStatusLike(err: unknown): err is StatusLike {
  return typeof err === "object" && err !== null && typeof (err as { status?: unknown }).status === "number";
}

function detailOf(err: StatusLike): string | null {
  if (typeof err.detail === "string") return err.detail;
  if (typeof err.responseDetail === "string") return err.responseDetail;
  return null;
}

export function authErrorMessage(err: unknown, t: (key: string) => string, context: AuthErrorContext): string {
  if (!isStatusLike(err)) return t("authError.default");
  const detail = detailOf(err);

  // パスキーの口: パスワードの話（invalidCredentials など）を画面に出さない
  if (context === "passkey") {
    switch (err.status) {
      case 401:
        return t("authError.passkeyFailed");
      case 400:
        return detail === "challenge_expired" ? t("authError.passkeyExpired") : t("authError.passkeyFailed");
      case 409:
        if (detail === "passkey_exists") return t("authError.passkeyExists");
        if (detail === "passkey_limit") return t("authError.passkeyLimit");
        break;
      case 503:
        return t("authError.unavailable");
    }
  }

  switch (err.status) {
    case 401:
      return t("authError.invalidCredentials");
    case 403:
      return t("authError.forbiddenOrigin");
    case 404:
      return t("authError.unavailable");
    case 429:
      return t("authError.tooManyAttempts");
    case 400:
      if (context === "resetConfirm") return t("authError.resetLinkInvalid");
      if (context === "passwordChange") return t("authError.currentPasswordWrong");
      return t("authError.default");
    case 422:
      if (detail === "password_too_short") return t("authError.passwordTooShort");
      if (detail === "password_too_long") return t("authError.passwordTooLong");
      if (detail === "password_too_common") return t("authError.passwordTooCommon");
      return t("authError.validation");
    default:
      return t("authError.default");
  }
}
