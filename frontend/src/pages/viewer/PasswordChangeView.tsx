/** ② パスワードの変更（初回の強制 / 本人が選んだとき） */
import { useState } from "react";
import type { FormEvent } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { TextField } from "../../components/TextField";
import { ViewerApiError, changePassword, readToken } from "./api";

/** 変更失敗 → 画面に出す文。キーは t("…") の直書き（i18n 検査が読めるように） */
export function passwordChangeErrorMessage(t: TFunction, err: unknown): string {
  if (err instanceof ViewerApiError) {
    if (err.status === 429) return t("viewer.error.viewer_too_many_attempts");
    switch (err.detail) {
      case "viewer_invalid_current_password":
        return t("viewer.error.viewer_invalid_current_password");
      case "password_too_short":
        return t("viewer.error.password_too_short");
      case "password_too_long":
        return t("viewer.error.password_too_long");
      case "password_too_common":
        return t("viewer.error.password_too_common");
      case "password_same_as_current":
        return t("viewer.error.password_same_as_current");
      default:
        break;
    }
  }
  return t("viewer.error.generic");
}

interface PasswordChangeViewProps {
  /** true の間は「戻る」を出さない（変更しないと先へ進めない） */
  forced: boolean;
  /** 成功。新しいトークンは保存済みで、親が在庫表を読み込む */
  onDone: (newToken: string) => void;
  onBack: () => void;
  onLogout: () => void;
}

export function PasswordChangeView({ forced, onDone, onBack, onLogout }: PasswordChangeViewProps) {
  const { t } = useTranslation();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      setError(t("viewer.passwordChange.mismatch"));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await changePassword(readToken() ?? "", current, next);
      onDone(res.access_token);
    } catch (err) {
      setError(passwordChangeErrorMessage(t, err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="viewer-login" onSubmit={submit} data-testid="viewer-password-change">
      <h1 className="viewer-login__title">{t("viewer.passwordChange.title")}</h1>
      {forced && <p data-testid="viewer-password-forced">{t("viewer.passwordChange.forced")}</p>}
      <TextField
        label={t("viewer.passwordChange.current")}
        type="password"
        autoComplete="current-password"
        value={current}
        onChange={(e) => setCurrent(e.target.value)}
        required
        fullWidth
      />
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
        <p className="viewer-login__error" role="alert" data-testid="viewer-password-error">
          {error}
        </p>
      )}
      <Button type="submit" fullWidth loading={busy} disabled={busy}>
        {t("viewer.passwordChange.submit")}
      </Button>
      {!forced && (
        <Button type="button" variant="secondary" fullWidth onClick={onBack} data-testid="viewer-password-back">
          {t("viewer.passwordChange.back")}
        </Button>
      )}
      {forced && (
        <Button type="button" variant="secondary" fullWidth onClick={onLogout} data-testid="viewer-password-logout">
          {t("viewer.logout")}
        </Button>
      )}
    </form>
  );
}
