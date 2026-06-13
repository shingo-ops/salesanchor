import { useState, FormEvent, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../contexts/AuthContext";
import { firebaseErrorMessage } from "../../lib/firebaseErrorMessage";

type Mode = "signIn" | "reset";

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
      setError(firebaseErrorMessage(err, t));
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
      setError(firebaseErrorMessage(err, t));
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
                <input
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
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-forgot-link"
                  onClick={switchToReset}
                >
                  {t("login.forgotPassword")}
                </button>
              </div>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? t("login.signingIn") : t("login.signIn")}
              </button>
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
                  <input
                    id="reset-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? t("login.sendingEmail") : t("login.sendResetEmail")}
                </button>
              </form>
            )}
            <button type="button" className="login-back-link" onClick={switchToSignIn}>
              {t("login.backToLogin")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
