import { useState, FormEvent, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../contexts/AuthContext";
import { firebaseErrorMessage } from "../../lib/firebaseErrorMessage";
import { authErrorMessage } from "../../lib/auth/authErrorMessage";
import type { AuthErrorContext } from "../../lib/auth/authErrorMessage";
import { isSelfAuth } from "../../lib/auth/provider";
import {
  autoRegisterPasskey,
  conditionalCreateSupported,
  getPasskeyPrompt,
  passkeyBrowserError,
  passkeySupported,
  registerPasskey,
  skipPasskeyPrompt,
} from "../../lib/auth/passkey";
import { Button } from "../../components/Button";
import { Modal } from "../../components/Modal";
import { Stack } from "../../components/Stack";
import { TextFieldControl } from "../../components/TextField";
import { PasswordFieldControl } from "../../components/PasswordField";
import { TextLink } from "../../components/TextLink";

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
  // ログイン直後のパスキー登録（ADR-1013 便6）。処理中・案内中は自動遷移させない
  const [enrolling, setEnrolling] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [promptBusy, setPromptBusy] = useState(false);
  const { signIn, signInWithPasskey, sendPasswordReset, user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from =
    (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  // KGI-3: ログイン済みユーザーはアプリ本体へ自動遷移
  useEffect(() => {
    if (!authLoading && user && !enrolling && !promptOpen) {
      navigate(from, { replace: true });
    }
  }, [authLoading, user, navigate, from, enrolling, promptOpen]);

  // パスワードでログインした直後: 裏で作る → できなければ案内。どこで失敗しても必ず元の画面へ進む
  const afterPasswordSignIn = async () => {
    try {
      if (!passkeySupported()) return navigate(from, { replace: true });
      const status = await getPasskeyPrompt();
      if (status.can_auto && (await conditionalCreateSupported())) {
        const result = await autoRegisterPasskey();
        // 作れた・登録済みなら案内は要らない。断られた・失敗・打ち切りは案内へ進む
        if (result === "created" || result === "exists") return navigate(from, { replace: true });
      }
      if (status.show_prompt) {
        setPromptOpen(true);
        return;
      }
    } catch {
      // 登録の案内はログインを止めない
    }
    navigate(from, { replace: true });
  };

  const finishPrompt = () => {
    setPromptOpen(false);
    setEnrolling(false);
    navigate(from, { replace: true });
  };

  const handlePromptRegister = async () => {
    setPromptBusy(true);
    try {
      await registerPasskey("");
    } catch {
      // 取り消し・失敗でもログインは続ける
    }
    setPromptBusy(false);
    finishPrompt();
  };

  const handlePromptSkip = async () => {
    if (promptBusy) return;
    setPromptBusy(true);
    try {
      await skipPasskeyPrompt();
    } catch {
      // 記録に失敗してもログインは続ける
    }
    setPromptBusy(false);
    finishPrompt();
  };

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setEnrolling(true);
    try {
      await signIn(email, password);
    } catch (err) {
      // KGI-4: Firebase の生エラー文字列を i18n キー経由に変換
      setError(loginErrorMessage(err, t, "login"));
      setEnrolling(false);
      setLoading(false);
      return;
    }
    try {
      // KGI-2: ログイン後に元ページへ戻る（自社ログインでは先にパスキー登録の案内を挟む）
      await afterPasswordSignIn();
    } finally {
      setLoading(false);
    }
  };

  const handlePasskeySignIn = async () => {
    setError("");
    setLoading(true);
    try {
      await signInWithPasskey();
      navigate(from, { replace: true });
    } catch (err) {
      setError(
        passkeyBrowserError(err) === "cancelled"
          ? t("authError.passkeyCancelled")
          : authErrorMessage(err, t, "passkey"),
      );
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
            <Stack gap="3">
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
                <PasswordFieldControl
                  variant="login"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
                <div className="login-forgot-row">
                  <TextLink onClick={switchToReset}>
                    {t("login.forgotPassword")}
                  </TextLink>
                </div>
              </div>
              <Button loading={loading} variant="primary" size="auth" shape="pill" fullWidth type="submit" disabled={loading}>
                {t("login.signIn")}
              </Button>
            </form>
            {passkeySupported() && (
              <Button
                loading={loading}
                variant="outline"
                size="auth"
                shape="pill"
                fullWidth
                type="button"
                disabled={loading}
                onClick={() => void handlePasskeySignIn()}
              >
                {t("login.signInWithPasskey")}
              </Button>
            )}
            </Stack>
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
                <Button loading={loading} variant="primary" size="auth" shape="pill" fullWidth type="submit" disabled={loading}>
                  {t("login.sendResetEmail")}
                </Button>
              </form>
            )}
            <TextLink onClick={switchToSignIn}>
              {t("login.backToLogin")}
            </TextLink>
          </>
        )}
      </div>
      <Modal
        open={promptOpen}
        size="sm"
        title={t("login.passkeyPromptTitle")}
        onClose={() => void handlePromptSkip()}
        footer={
          <>
            <Button variant="secondary" disabled={promptBusy} onClick={() => void handlePromptSkip()}>
              {t("login.passkeyPromptSkip")}
            </Button>
            <Button variant="primary" disabled={promptBusy} onClick={() => void handlePromptRegister()}>
              {t("login.passkeyPromptRegister")}
            </Button>
          </>
        }
      >
        <p>{t("login.passkeyPromptBody")}</p>
      </Modal>
    </div>
  );
}
