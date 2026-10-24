/** ⑥ 申込（フォーム / 申込コードと招待リンクの表示） */
import { useState } from "react";
import type { FormEvent } from "react";
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { Textarea } from "../../components/Textarea";
import { TextField } from "../../components/TextField";
import { ViewerApiError, signup } from "./api";
import type { ViewerSignupResponse } from "./types";

/** 申込の失敗 → 画面に出す文。ログインと同じキーを使う */
export function signupErrorMessage(t: TFunction, err: unknown): string {
  if (err instanceof ViewerApiError) {
    if (err.status === 422) return t("viewer.error.validation");
    if (err.status === 429) return t("viewer.error.viewer_too_many_attempts");
    if (err.detail === "forbidden_origin") return t("viewer.error.forbidden_origin");
  }
  return t("viewer.error.generic");
}

interface SignupViewProps {
  onToLogin: () => void;
}

export function SignupView({ onToLogin }: SignupViewProps) {
  const { t, i18n } = useTranslation();
  const [email, setEmail] = useState("");
  const [lineName, setLineName] = useState("");
  const [issue, setIssue] = useState("");
  const [website, setWebsite] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ViewerSignupResponse | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(
        await signup({
          email: email.trim(),
          line_name: lineName.trim(),
          inventory_issue: issue.trim(),
          website,
        }),
      );
    } catch (err) {
      setError(signupErrorMessage(t, err));
    } finally {
      setBusy(false);
    }
  };

  if (result) {
    const expires = new Date(result.expires_at).toLocaleString(i18n.language);
    return (
      <div className="viewer-center" data-testid="viewer-signup-done">
        <EmptyState
          title={t("viewer.signup.doneTitle")}
          description={t("viewer.signup.doneDescription")}
          action={
            <div className="viewer-signup__result">
              <p className="viewer-signup__code" data-testid="viewer-signup-code">
                {result.signup_code}
              </p>
              <p className="viewer-signup__note">{t("viewer.signup.expires", { time: expires })}</p>
              <p className="viewer-signup__note">{t("viewer.signup.onlyHere")}</p>
              {result.invite_url ? (
                <>
                  <Button
                    fullWidth
                    onClick={() => window.open(result.invite_url ?? "", "_blank", "noopener,noreferrer")}
                    data-testid="viewer-signup-invite"
                  >
                    {t("viewer.signup.openInvite")}
                  </Button>
                  <p className="viewer-signup__note" data-testid="viewer-signup-invite-url">
                    {result.invite_url}
                  </p>
                </>
              ) : (
                <p className="viewer-signup__note" role="status" data-testid="viewer-signup-invite-failed">
                  {t("viewer.signup.inviteFailed")}
                </p>
              )}
              <p className="viewer-signup__note">{t("viewer.signup.alreadyApplied")}</p>
              <Button variant="secondary" fullWidth onClick={onToLogin} data-testid="viewer-signup-to-login">
                {t("viewer.signup.backToLogin")}
              </Button>
            </div>
          }
        />
      </div>
    );
  }

  return (
    <form className="viewer-login" onSubmit={submit} data-testid="viewer-signup">
      <h1 className="viewer-login__title">{t("viewer.signup.title")}</h1>
      <TextField
        label={t("viewer.login.email")}
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        maxLength={254}
        required
        fullWidth
      />
      <TextField
        label={t("viewer.signup.lineName")}
        value={lineName}
        onChange={(e) => setLineName(e.target.value)}
        maxLength={100}
        required
        fullWidth
      />
      <Textarea
        label={t("viewer.signup.inventoryIssue")}
        helperText={t("viewer.signup.inventoryIssueHelp")}
        value={issue}
        onChange={(e) => setIssue(e.target.value)}
        maxLength={1000}
        fullWidth
      />
      {/* ui-allow: 申込のボット対策の隠し欄 (#4338) */}
      <input
        className="viewer-signup__trap"
        name="website"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        value={website}
        onChange={(e) => setWebsite(e.target.value)}
        data-testid="viewer-signup-website"
      />
      {error && (
        <p className="viewer-login__error" role="alert" data-testid="viewer-signup-error">
          {error}
        </p>
      )}
      <Button type="submit" fullWidth loading={busy} disabled={busy}>
        {t("viewer.signup.submit")}
      </Button>
      <Button type="button" variant="secondary" fullWidth onClick={onToLogin} data-testid="viewer-signup-back">
        {t("viewer.signup.backToLogin")}
      </Button>
    </form>
  );
}
