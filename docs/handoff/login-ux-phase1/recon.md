# recon: login-ux-phase1

> 作成日: 2026-06-14
> 担当: Hikky-dev (Claude Code)
> worktree: feature/morimoto/login-ux-phase1

---

## 1. 既存 ADR 検索結果

git grep で "login|password.reset|forgot.password" を docs/adr/ 検索。docs/adr/FEATURE-INDEX.md 参照。

| ADR | 内容 | 関連度 |
|-----|------|--------|
| ADR-023 | Firebase Auth スタッフライフサイクル3層同期。password reset・MFA再設定フローは「対象外」として明示 | 参照のみ |
| ADR-032 | Firebase カスタム認証ドメイン（auth.salesanchor.jp）。ログイン UI 変更の前提環境 | 参照のみ |
| ADR-027 | 全 UI 文字列 t() 経由・ja.json / en.json キー同期必須 | 対応必須 |
| ADR-138 | password_hash 廃止決定。Firebase Auth が全担当。password_hash 復活禁止 | 制約（対象外確認） |

**パスワードリセット UI・ログイン後リダイレクト・ログイン済みチェックに関する既存 ADR は存在しない（grep 済み・該当なし）。**

---

## 2. 既存コード調査（file:line 根拠）

### LoginPage.tsx

- `frontend/src/pages/login/LoginPage.tsx:1-6` — import: useState, FormEvent, useNavigate, useTranslation, useAuth, firebaseErrorMessage
- `frontend/src/pages/login/LoginPage.tsx:9-14` — state: email, password, error, loading
- `frontend/src/pages/login/LoginPage.tsx:13` — signIn のみ useAuth から取得（sendPasswordReset 未実装）
- `frontend/src/pages/login/LoginPage.tsx:22` — ログイン成功後は navigate("/") で固定。from state 参照なし
- `frontend/src/pages/login/LoginPage.tsx:35` — ログイン済みチェックなし（/login へアクセスしても自動遷移しない）
- `frontend/src/pages/login/LoginPage.tsx:43` — UI: メール・パスワード・ボタンのみ。パスワード再設定リンクなし

### AuthContext.tsx

- `frontend/src/contexts/AuthContext.tsx:11-12` — import: signInWithEmailAndPassword, signOut のみ。sendPasswordResetEmail 未 import
- `frontend/src/contexts/AuthContext.tsx:15-19` — AuthContextType: user, loading, signIn, signOut の4フィールド。sendPasswordReset なし
- `frontend/src/contexts/AuthContext.tsx:29-33` — onAuthStateChanged でログイン状態管理（loading は初期 true）
- `frontend/src/contexts/AuthContext.tsx:36-38` — signIn: signInWithEmailAndPassword のみ

### ProtectedRoute.tsx

- `frontend/src/components/ProtectedRoute.tsx:5` — import: Navigate のみ。useLocation 未 import
- `frontend/src/components/ProtectedRoute.tsx:17-19` — 未ログイン時: Navigate to="/login" replace なし。state={{ from: location }} 未設定

### firebaseErrorMessage.ts

- `frontend/src/lib/firebaseErrorMessage.ts:39-42` — パスワードリセット系エラーコード既定義済み: auth/expired-action-code, auth/invalid-action-code, auth/requires-recent-login
- `frontend/src/lib/firebaseErrorMessage.ts:52-60` — firebaseErrorMessage(err, t) 実装済み。追加不要

### i18n（ja.json / en.json）

- `frontend/src/locales/ja.json:332-337` — login セクション: email, password, signIn, signingIn の4キー。再設定関連キーなし
- `frontend/src/locales/ja.json:2314-2325` — firebaseError セクション: 全エラーコード実装済み
- `frontend/src/locales/en.json:332-337` — 同構造（英語）

### CSS（pages-layout.css）

- `frontend/src/pages-layout.css:166-172` — .login-page: flex centering, min-height: 100vh
- `frontend/src/pages-layout.css:174-182` — .login-card: max-width var(--card-login-max-w) = 400px, padding var(--space-10) = 40px
- `frontend/src/pages-layout.css:210-215` — .login-subtitle スタイル済み
- レスポンシブ CSS なし（@media 未定義）。frontend/src/responsive.css に全 @media が集約（767px, 768px ブレークポイント）

### E2E テスト

- `frontend/tests-e2e/scene1-dashboard.spec.ts:89-96` — LoginPage の DOM 検証: getByLabel("メールアドレス"), getByLabel("パスワード"), getByRole("button", { name: "ログイン" })
- 既存 login.spec.ts なし（Glob で確認）

### tokens.css（CSS 変数）

- `frontend/src/tokens.css:303` — --card-login-max-w: 400px
- `frontend/src/tokens.css:100-112` — ブレークポイント: --breakpoint-mobile-max: 767px

---

## 3. 不明点

- なし。実装に必要な情報は全て揃っている。
