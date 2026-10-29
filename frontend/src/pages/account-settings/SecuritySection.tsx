import { useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  EmailAuthProvider,
  reauthenticateWithCredential,
  updatePassword,
} from "../../lib/firebase-auth";
import { auth } from "../../lib/firebase";
import { firebaseErrorMessage } from "../../lib/firebaseErrorMessage";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import { isSelfAuth } from "../../lib/auth/provider";
import { adoptAccessToken } from "../../lib/auth/selfAuth";
import { api } from "../../lib/api";
import { ACCOUNT_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { Button } from "../../components/Button";
import { TextFieldControl } from "../../components/TextField";

export default function SecuritySection() {
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
    const selfMode = isSelfAuth();
    // 自社ログインの長さ・よく使われるパスワードの決まりは backend が判定する（422 の識別子を文言にする）
    if (!selfMode && form.next.length < 8) {
      setError(t("accountSettings.passwordTooShort"));
      return;
    }

    if (selfMode) {
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
      } catch (err) {
        setError(authErrorMessage(err, t, "passwordChange"));
      } finally {
        setChanging(false);
      }
      return;
    }

    const user = auth.currentUser;
    if (!user || !user.email) {
      setError(t("firebaseError.default"));
      return;
    }

    setChanging(true);
    try {
      const cred = EmailAuthProvider.credential(user.email, form.current);
      await reauthenticateWithCredential(user as never, cred as never);
      await updatePassword(user as never, form.next);
      setSuccess(true);
      setForm({ current: "", next: "", confirm: "" });
    } catch (err) {
      setError(firebaseErrorMessage(err, t));
    } finally {
      setChanging(false);
    }
  };

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [k]: e.target.value }));

  return (
    <section className="account-settings-section">
      <div className="account-settings-section-title">
        <ACCOUNT_ICONS.security size={ICON.md} aria-hidden="true" />
        {t("accountSettings.sectionSecurity")}
      </div>

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
    </section>
  );
}
