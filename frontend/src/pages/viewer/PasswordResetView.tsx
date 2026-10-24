/** ⑤ パスワードの再発行（メール申請 / メールのリンクから新パスワード設定） */
import { useState } from "react";
import type { FormEvent } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { TextField } from "../../components/TextField";
import { ViewerApiError, confirmPasswordReset, requestPasswordReset } from "./api";

/** 確定の失敗 → 画面に出す文（400 のリンク無効は別画面で扱う） */
export function passwordResetErrorMessage(t: TFunction, err: unknown): string {
  if (err instanceof ViewerApiError) {
    if (err.status === 429) return t("viewer.error.viewer_too_many_attempts");
    switch (err.detail) {
      case "password_too_short":
        return t("viewer.error.password_too_short");
      case "password_too_long":
        return t("viewer.error.password_too_long");
      case "password_too_common":
        return t("viewer.error.password_too_common");
      default:
        break;
    }
  }
  return t("viewer.error.generic");
}

interface PasswordResetViewProps {
  /** メールのリンクから来たときのトークン。無ければメール申請の画面 */
  token: string | null;
  onToLogin: () => void;
}

export function PasswordResetView({ token, onToLogin }: PasswordResetViewProps) {
  const { t } = useTranslation();
  const [activeToken, setActiveToken] = useState<string | null>(token);
  const [email, setEmail] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"form" | "sent" | "done" | "invalid">("form");

  const submitRequest = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await requestPasswordReset(email.trim());
      setStep("sent");
    } catch (err) {
      setError(passwordResetErrorMessage(t, err));
    } finally {
      setBusy(false);
    }
  };

  const submitConfirm = async (e: FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      setError(t("viewer.passwordChange.mismatch"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await confirmPasswordReset(activeToken ?? "", next);
      setStep("done");
    } catch (err) {
      if (err instanceof ViewerApiError && err.status === 400) {
        setStep("invalid");
      } else {
        setError(passwordResetErrorMessage(t, err));
      }
    } finally {
      setBusy(false);
    }
  };

  const sendAgain = () => {
    setActiveToken(null);
    setNext("");
    setConfirm("");
    setError(null);
    setStep("form");
  };

  if (step === "sent") {
    return (
      <div className="viewer-center" data-testid="viewer-reset-sent">
        <EmptyState
          title={t("viewer.reset.sentTitle")}
          description={t("viewer.reset.sentDescription")}
          action={
            <Button variant="secondary" onClick={onToLogin} data-testid="viewer-reset-to-login">
              {t("viewer.reset.backToLogin")}
            </Button>
          }
        />
      </div>
    );
  }

  if (step === "done") {
    return (
      <div className="viewer-center" data-testid="viewer-reset-done">
        <EmptyState
          title={t("viewer.reset.doneTitle")}
          description={t("viewer.reset.doneDescription")}
          action={
            <Button onClick={onToLogin} data-testid="viewer-reset-to-login">
              {t("viewer.reset.toLogin")}
            </Button>
          }
        />
      </div>
    );
  }

  if (step === "invalid") {
    return (
      <div className="viewer-center" data-testid="viewer-reset-invalid">
        <EmptyState
          title={t("viewer.reset.invalidTitle")}
          description={t("viewer.reset.invalidDescription")}
          action={
            <Button onClick={sendAgain} data-testid="viewer-reset-again">
              {t("viewer.reset.again")}
            </Button>
          }
        />
      </div>
    );
  }

  if (activeToken) {
    return (
      <form className="viewer-login" onSubmit={submitConfirm} data-testid="viewer-reset-new">
        <h1 className="viewer-login__title">{t("viewer.reset.newTitle")}</h1>
        <TextField
          label={t("viewer.passwordChange.new")}
          type="password"
          autoComplete="new-password"
          helperText={t("viewer.passwordChange.hint")}
          value={next}
          onChange={(e) => setNext(e.target.value)}
          required
          fullWidth
        />
        <TextField
          label={t("viewer.passwordChange.confirm")}
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
          fullWidth
        />
        {error && (
          <p className="viewer-login__error" role="alert" data-testid="viewer-reset-error">
            {error}
          </p>
        )}
        <Button type="submit" fullWidth loading={busy} disabled={busy}>
          {t("viewer.reset.submit")}
        </Button>
      </form>
    );
  }

  return (
    <form className="viewer-login" onSubmit={submitRequest} data-testid="viewer-reset-request">
      <h1 className="viewer-login__title">{t("viewer.reset.title")}</h1>
      <TextField
        label={t("viewer.login.email")}
        type="email"
        autoComplete="username"
        helperText={t("viewer.reset.emailHelp")}
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        fullWidth
      />
      {error && (
        <p className="viewer-login__error" role="alert" data-testid="viewer-reset-error">
          {error}
        </p>
      )}
      <Button type="submit" fullWidth loading={busy} disabled={busy}>
        {t("viewer.reset.send")}
      </Button>
      <Button type="button" variant="secondary" fullWidth onClick={onToLogin} data-testid="viewer-reset-back">
        {t("viewer.reset.backToLogin")}
      </Button>
    </form>
  );
}
