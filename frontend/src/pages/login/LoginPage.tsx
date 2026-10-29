import { useState, FormEvent, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../contexts/AuthContext";
import { firebaseErrorMessage } from "../../lib/firebaseErrorMessage";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import type { AuthErrorContext } from "../../lib/auth/authErrorMessage";
import { isSelfAuth } from "../../lib/auth/provider";
import { Button } from "../../components/Button";
import { TextFieldControl } from "../../components/TextField";

type Mode = "signIn" | "reset";

// 自社ログインのときは自社 API の応答から、Firebase のときは Firebase のエラーコードから文言を作る
function loginErrorMessage(err: unknown, t: (key: string) => string, context: AuthErrorContext): string {
  return isSelfAuth() ? authErrorMessage(err, t, context) : firebaseErrorMessage(err, t);
}

export default function LoginPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<Mode>("signIn");
  const [resetSent, setResetSent] = useState(false);
  const { signIn, sendPasswordReset, user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from =
    (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  // KGI-3: ログイン済みユーザーはアプリ本体へ自動遷移
  useEffect(() => {
    if (!authLoading && user) {
      navigate(from, { replace: true });
    }
  }, [authLoading, user, navigate, from]);

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signIn(email, password);
      // KGI-2: ログイン後に元ページへ戻る
      navigate(from, { replace: true });
    } catch (err) {
      // KGI-4: Firebase の生エラー文字列を i18n キー経由に変換
      setError(loginErrorMessage(err, t, "login"));
    } finally {
      setLoading(false);
    }
  };

  // KGI-1: パスワード再設定メール送信
  const handleReset = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await sendPasswordReset(email);
      setResetSent(true);
    } catch (err) {
      setError(loginErrorMessage(err, t, "resetRequest"));
    } finally {
      setLoading(false);
    }
  };

  const switchToReset = () => {
    setMode("reset");
    setError("");
    setResetSent(false);
  };

  const switchToSignIn = () => {
    setMode("signIn");
    setError("");
    setResetSent(false);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="sr-only">Sales Anchor</h1>
        <img
          src="/logo.png"
          alt=""
          aria-hidden="true"
          className="login-logo"
        />

        {mode === "signIn" ? (
          <>
            <p className="login-subtitle">{t("login.signIn")}</p>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSignIn}>
              <div className="form-group">
                <label htmlFor="email">{t("login.email")}</label>
                <TextFieldControl
                  variant="login"
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              <div className="form-group">
                <label htmlFor="password">{t("login.password")}</label>
                <TextFieldControl
                  variant="login"
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
                <Button type="button" variant="secondary" size="sm" onClick={switchToReset}>
                  {t("login.forgotPassword")}
                </Button>
              </div>
              <Button loading={loading} variant="primary" size="lg" fullWidth type="submit" disabled={loading}>
                {t("login.signIn")}
              </Button>
            </form>
          </>
        ) : (
          <>
            <p className="login-subtitle">{t("login.resetPassword")}</p>
            {resetSent && (
              <div className="login-success-message">{t("login.resetEmailSent")}</div>
            )}
            {error && <div className="error-message">{error}</div>}
            {!resetSent && (
              <form onSubmit={handleReset}>
                <div className="form-group">
                  <label htmlFor="reset-email">{t("login.email")}</label>
                  <TextFieldControl
                    variant="login"
                    id="reset-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>
                <Button loading={loading} variant="primary" size="lg" fullWidth type="submit" disabled={loading}>
                  {t("login.sendResetEmail")}
                </Button>
              </form>
            )}
            <Button type="button" variant="secondary" size="sm" onClick={switchToSignIn}>
              {t("login.backToLogin")}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
