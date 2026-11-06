import { useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import { adoptAccessToken } from "../../lib/auth/selfAuth";
import { api } from "../../lib/api";
import { Button } from "../../components/Button";
import { TextFieldControl } from "../../components/TextField";

interface PasswordChangeFormProps {
  /** パスワードを変えられたときに呼ぶ */
  onChanged?: () => void;
}

/** パスワード変更の欄（設定画面と、仮パスワードの変更ページで共用・ADR-1068） */
export default function PasswordChangeForm({ onChanged }: PasswordChangeFormProps) {
  const { t } = useTranslation();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [changing, setChanging] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(""); setSuccess(false);

    if (form.next !== form.confirm) {
      setError(t("accountSettings.passwordMismatch"));
      return;
    }
    // 長さ・よく使われるパスワードの決まりは backend が判定する（422 の識別子を文言にする）
    setChanging(true);
    try {
      const res = await api.post<{ access_token?: string | null; expires_in?: number | null }>(
        "/auth/password/change",
        { current_password: form.current, new_password: form.next },
      );
      // 他の端末の更新用トークンは失効するので、今の端末は応答の新しいトークンに入れ替える
      if (res.access_token && res.expires_in) adoptAccessToken(res.access_token, res.expires_in);
      setSuccess(true);
      setForm({ current: "", next: "", confirm: "" });
      onChanged?.();
    } catch (err) {
      setError(authErrorMessage(err, t, "passwordChange"));
    } finally {
      setChanging(false);
    }
  };

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [k]: e.target.value }));

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="current_password">{t("accountSettings.currentPassword")}</label>
        <TextFieldControl
          id="current_password"
          type="password"
          value={form.current}
          onChange={set("current")}
          autoComplete="current-password"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="new_password">{t("accountSettings.newPassword")}</label>
        <TextFieldControl
          id="new_password"
          type="password"
          value={form.next}
          onChange={set("next")}
          autoComplete="new-password"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="confirm_password">{t("accountSettings.confirmPassword")}</label>
        <TextFieldControl
          id="confirm_password"
          type="password"
          value={form.confirm}
          onChange={set("confirm")}
          autoComplete="new-password"
          required
        />
      </div>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="account-settings-success">{t("accountSettings.passwordChanged")}</div>}

      <div className="account-settings-actions">
        <Button loading={changing} variant="primary" size="md" type="submit" disabled={changing}>
          {t("accountSettings.changePassword")}
        </Button>
      </div>
    </form>
  );
}
