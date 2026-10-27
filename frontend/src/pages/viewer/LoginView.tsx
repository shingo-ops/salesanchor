/** ① ログイン */
import { useState } from "react";
import type { FormEvent } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { ViewerApiError, login } from "./api";
import type { ViewerLoginResponse } from "./types";

/** ログイン失敗 → 画面に出す文。キーは t("…") の直書き（i18n 検査が読めるように） */
export function loginErrorMessage(t: TFunction, err: unknown): string {
  if (err instanceof ViewerApiError) {
    if (err.status === 422) return t("viewer.error.validation");
    switch (err.detail) {
      case "forbidden_origin":
        return t("viewer.error.forbidden_origin");
      case "viewer_too_many_attempts":
        return t("viewer.error.viewer_too_many_attempts");
      case "viewer_invalid_credentials":
        return t("viewer.error.viewer_invalid_credentials");
      case "viewer_suspended":
        return t("viewer.error.viewer_suspended");
      case "viewer_trial_expired":
        return t("viewer.error.viewer_trial_expired");
      default:
        break;
    }
  }
  return t("viewer.error.generic");
}

interface LoginViewProps {
  onLoggedIn: (res: ViewerLoginResponse) => void;
  /** 503（準備中）のとき ④ へ */
  onPreparing: () => void;
  /** 「パスワードを忘れた」→ 再発行画面へ */
  onForgot: () => void;
  /** 「申込」→ 申込画面へ */
  onSignup: () => void;
}

export function LoginView({ onLoggedIn, onPreparing, onForgot, onSignup }: LoginViewProps) {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onLoggedIn(await login(email.trim(), password));
    } catch (err) {
      if (err instanceof ViewerApiError && (err.status === 503 || err.detail === "pending")) {
        onPreparing();
      } else {
        setError(loginErrorMessage(t, err));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="viewer-login" onSubmit={submit} data-testid="viewer-login">
      <h1 className="viewer-login__title">{t("viewer.login.title")}</h1>
      <TextField
        label={t("viewer.login.email")}
        type="email"
        autoComplete="username"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        fullWidth
      />
      <TextField
        label={t("viewer.login.password")}
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        fullWidth
      />
      {error && (
        <p className="viewer-login__error" role="alert" data-testid="viewer-login-error">
          {error}
        </p>
      )}
      <Button type="submit" fullWidth loading={busy} disabled={busy}>
        {t("viewer.login.submit")}
      </Button>
      <Button type="button" variant="secondary" fullWidth onClick={onForgot} data-testid="viewer-login-forgot">
        {t("viewer.login.forgot")}
      </Button>
      <Button type="button" variant="secondary" fullWidth onClick={onSignup} data-testid="viewer-login-signup">
        {t("viewer.login.signup")}
      </Button>
    </form>
  );
}
