# design: login-ux-phase1

> 作成日: 2026-06-14
> ADR参照: ADR-023, ADR-027, ADR-032, ADR-138
> recon参照: docs/handoff/login-ux-phase1/recon.md

---

## KGI と受け入れ基準

| # | KGI | 受け入れ基準 | 検証方法 |
|---|-----|------------|---------|
| 1 | パスワード再設定メール送信 | 「パスワードをお忘れの方」リンク押下 → 再設定モードへ遷移 → メール入力 → 送信ボタン → 成功メッセージ表示 | Playwright: login.spec.ts |
| 2 | ログイン後に元ページへ戻る | `/crm/leads` に未ログインでアクセス → ログイン → `/crm/leads` に戻る | Playwright: login.spec.ts |
| 3 | ログイン済みで `/login` を開くと自動遷移 | 認証済みセッションで `/login` → `useEffect` で `/` へ replace navigate | Playwright: login.spec.ts |
| 4 | Firebase 生エラー非表示 | 既存 `firebaseErrorMessage()` を再設定フローにも適用 | 既実装済み・spec で確認 |
| 5 | スマホでフォームが崩れない | `@media (max-width: 767px)` で `.login-card` padding 削減 | Playwright screenshot / 手動 |

---

## 外部・過去事例の参照と我々への応用

Firebase Authentication の `sendPasswordResetEmail` は公式 SDK に用意済みの標準 API であり、外部事例を参照するまでもなく確立した実装パターンが存在する。
- Firebase 公式: `sendPasswordResetEmail(auth, email)` を try/catch で囲み、成功時に成功 UI・失敗時にエラー表示
- 一般的 UX パターン: ログインフォーム内に「パスワードを忘れた方」リンクを設け、同一カード内でモード切替（別ページへの遷移は不要）
- Firebase sendPasswordResetEmail はメールアドレスが存在しない場合でも成功を返す（列挙攻撃対策）→ 我々もこの挙動をそのまま利用（エラーにしない）

---

## 実装方針

### AuthContext.tsx — sendPasswordReset 追加

```tsx
import { sendPasswordResetEmail } from "firebase/auth";

// AuthContextType に追加
sendPasswordReset: (email: string) => Promise<void>;

// 実装
const sendPasswordReset = async (email: string) => {
  await sendPasswordResetEmail(auth, email);
};
```

### ProtectedRoute.tsx — from state 付与

```tsx
import { Navigate, useLocation } from "react-router-dom";

const location = useLocation();
// 変更前: <Navigate to="/login" replace />
// 変更後:
<Navigate to="/login" state={{ from: location }} replace />
```

### LoginPage.tsx — 3機能追加

**モード管理:**
```tsx
type Mode = "signIn" | "reset";
const [mode, setMode] = useState<Mode>("signIn");
const [resetSent, setResetSent] = useState(false);
```

**KGI-3: ログイン済みリダイレクト:**
```tsx
const { user, loading: authLoading, signIn, sendPasswordReset } = useAuth();
const location = useLocation();
const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

useEffect(() => {
  if (!authLoading && user) {
    navigate(from, { replace: true });
  }
}, [authLoading, user, navigate, from]);
```

**KGI-2: ログイン後に from へ遷移:**
```tsx
// handleSubmit 成功後
navigate(from, { replace: true });
```

**KGI-1: パスワード再設定フォーム:**
```tsx
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
```

### i18n キー追加（ADR-027 準拠）

ja.json / en.json の `login` セクションに以下を追加:

| キー | 日本語 | 英語 |
|------|--------|------|
| `login.forgotPassword` | パスワードをお忘れの方 | Forgot your password? |
| `login.resetPassword` | パスワード再設定 | Reset password |
| `login.sendResetEmail` | 再設定メールを送信 | Send reset email |
| `login.sendingEmail` | 送信中... | Sending... |
| `login.resetEmailSent` | 再設定メールを送信しました。メールをご確認ください。 | Password reset email sent. Please check your inbox. |
| `login.backToLogin` | ログイン画面に戻る | Back to sign in |

### pages-layout.css — スタイル追加

```css
/* パスワード再設定リンク */
.login-forgot-link {
  display: block;
  text-align: right;
  font-size: var(--font-sm);
  color: var(--accent);
  margin-top: var(--space-1);
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
  text-decoration: underline;
}
.login-forgot-link:hover { color: var(--accent-hover); }

/* 再設定成功メッセージ */
.login-success-message {
  background: var(--success-bg);
  color: var(--success-text);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-size: var(--font-sm);
  margin-bottom: var(--space-4);
}

/* 戻るリンク */
.login-back-link {
  display: block;
  text-align: center;
  font-size: var(--font-sm);
  color: var(--accent);
  margin-top: var(--space-4);
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
  text-decoration: underline;
  width: 100%;
}
.login-back-link:hover { color: var(--accent-hover); }

/* KGI-5: モバイル対応 */
@media (max-width: 767px) {
  .login-card {
    padding: var(--space-6);
    border-radius: 0;
    box-shadow: none;
    border-top: 3px solid var(--accent);
    min-height: 100vh;
  }
}
```

---

## 弊害・トレードオフ

| 懸念 | 対処 |
|------|------|
| `useEffect` による `/login` → `/` 遷移がチラつく | `authLoading` が `true` の間はリダイレクトしない（既存 `loading-screen` が表示されるため問題なし） |
| `from` state が存在しない場合（直接 /login アクセス） | `?? "/"` でフォールバック |
| Firebase の sendPasswordResetEmail はメール不存在でも成功を返す | 意図的（メールアドレス列挙攻撃対策）。成功メッセージは「送信しました」のまま |
| scene1-dashboard.spec.ts のログインテストへの影響 | 既存3要素（メールアドレス・パスワード・ログインボタン）は変わらないため影響なし |

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `frontend/src/contexts/AuthContext.tsx` | `sendPasswordReset` 追加 |
| `frontend/src/components/ProtectedRoute.tsx` | `useLocation` + `state={{ from: location }}` |
| `frontend/src/pages/login/LoginPage.tsx` | 再設定モード・from リダイレクト・ログイン済みチェック |
| `frontend/src/locales/ja.json` | login セクションに 6 キー追加 |
| `frontend/src/locales/en.json` | 同上（英語） |
| `frontend/src/pages-layout.css` | 再設定 UI スタイル + モバイル対応 |
| `frontend/tests-e2e/login.spec.ts` | 新規作成（KGI 1-3 の Playwright テスト） |
| `docs/handoff/login-ux-phase1/recon.md` | 本 recon |
| `docs/handoff/login-ux-phase1/design.md` | 本 design |
