import { useState, FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { ButtonLink } from "../../components/ButtonLink";
import { Callout } from "../../components/Callout";
import { PasswordFieldControl } from "../../components/PasswordField";
import { selfConfirmPasswordReset } from "../../lib/auth/selfAuth";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";

/**
 * パスワード再設定・初回設定ページ（ADR-1013）。メールのリンク `/reset-password?token=` から来る。
 * ログイン不要。成功しても自動ログインはせず、ログイン画面へのリンクを出す。
 */
export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [form, setForm] = useState({ next: "", confirm: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.next !== form.confirm) {
      setError(t("resetPasswordPage.mismatch"));
      return;
    }
    setSaving(true);
    try {
      await selfConfirmPasswordReset(token, form.next);
      setDone(true);
      setForm({ next: "", confirm: "" });
    } catch (err) {
      setError(authErrorMessage(err, t, "resetConfirm"));
    } finally {
      setSaving(false);
    }
  };

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [k]: e.target.value }));

  return (
    <PageLayout titleText={t("resetPasswordPage.title")} subtitleKey="resetPasswordPage.subtitle">
      {!token ? (
        <Callout variant="warning" title={t("resetPasswordPage.missingTokenTitle")}>
          {t("resetPasswordPage.missingTokenBody")}
        </Callout>
      ) : done ? (
        <>
          <Callout variant="info" title={t("resetPasswordPage.doneTitle")}>
            {t("resetPasswordPage.doneBody")}
          </Callout>
          <ButtonLink to="/login" variant="primary">
            {t("resetPasswordPage.goToLogin")}
          </ButtonLink>
        </>
      ) : (
        <form onSubmit={handleSubmit}>
          <p>{t("resetPasswordPage.hint")}</p>
          <div className="form-group">
            <label htmlFor="reset_new_password">{t("resetPasswordPage.newPassword")}</label>
            <PasswordFieldControl
              id="reset_new_password"
              value={form.next}
              onChange={set("next")}
              autoComplete="new-password"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="reset_confirm_password">{t("resetPasswordPage.confirmPassword")}</label>
            <PasswordFieldControl
              id="reset_confirm_password"
              value={form.confirm}
              onChange={set("confirm")}
              autoComplete="new-password"
              required
            />
          </div>
          {error && (
            <Callout variant="warning" title={t("resetPasswordPage.errorTitle")}>
              {error}
            </Callout>
          )}
          <Button loading={saving} variant="primary" size="md" type="submit" disabled={saving}>
            {t("resetPasswordPage.submit")}
          </Button>
        </form>
      )}
    </PageLayout>
  );
}
