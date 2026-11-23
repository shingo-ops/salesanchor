# パスキーの自動の候補 — 現在地（recon）

- 起点: origin/main bef5a7a8b（2026-11-24）。ブランチ release/passkey-autofill-first
- 読んだ人: Claude Opus（設計担当）。推測は書かない。未確認は §6 にまとめる。
- KGI: docs/specs/auth-login/kgi.md「KGI 追加 — パスキーの自動の候補」（PO 承認 2026-11-24 チャット「1」）

## §1 既存 ADR の検索

| 検索 | 結果 |
|---|---|
| `git grep -il "passkey\|webauthn" -- docs/adr` | ADR-1013・ADR-1017・ADR-1018・ADR-1048・ADR-1083・ADR-1084・ADR-138・FEATURE-INDEX・README |
| docs/adr/FEATURE-INDEX.md:48 | 「ログイン / パスキー / WebAuthn …」の正本は **ADR-1013**、仕様は docs/specs/auth-login |
| docs/adr/FEATURE-INDEX.md:51 | 新しい機械の承認は ADR-1055（パスキーは承認なしで入れる＝What 5） |
| docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:20-30 | パスキーは自社サーバー。RP ID は app.salesanchor.jp（5b・変えるには新 ADR）。ログイン情報は public.users にだけぶら下げる（2） |

→ 本件はサーバー・表・RP ID を変えない。ADR-1013 の範囲内の画面の変更で、新しい ADR は要らない（design.md §3 で判断）。

## §2 画面側（frontend）

| 場所 | 事実 |
|---|---|
| /Users/tanizawashingo/worktrees/salesanchor/release-passkey-autofill-first/frontend/package.json:80 | `"@simplewebauthn/browser": "14.0.0"` |
| frontend/src/lib/auth/passkey.ts:27-35 | `selfPasskeyLogin()` = options 取得 → `startAuthentication({ optionsJSON })` → verify → `adoptAccessToken` |
| frontend/src/lib/auth/passkey.ts:22-24 | `passkeySupported()` = 開発用ログインでない かつ `browserSupportsWebAuthn()` |
| frontend/src/lib/auth/passkey.ts:52-57 | `passkeyBrowserError` は `err.name` で NotAllowedError→cancelled を判定 |
| frontend/src/lib/auth/passkey.ts:63-75 | `conditionalCreateSupported()` が `PublicKeyCredential.getClientCapabilities()` を読む型（今回の `immediateGet` の見本） |
| frontend/src/pages/login/LoginPage.tsx:235-250 | `handlePasskeySignIn` = `signInWithPasskey()` → `navigate(from)`、失敗は cancelled なら `authError.passkeyCancelled`、他は `authErrorMessage(err, t, "passkey")` |
| frontend/src/pages/login/LoginPage.tsx:394-402 | メール欄は `TextFieldControl`（variant="login"・id="email"・`autoComplete="email"`） |
| frontend/src/pages/login/LoginPage.tsx:424-437 | 「顔・指紋でログイン」ボタン（`Button` variant="outline"）。`passkeySupported()` のときだけ出す |
| frontend/src/pages/login/LoginPage.tsx:451-458 | 再設定画面のメール欄（`autoComplete="email"`）。今回は触らない |
| frontend/src/contexts/AuthContext.tsx:106-109 | `signInWithPasskey` は開発用ログインなら何もしない、他は `selfPasskeyLogin()` |
| frontend/src/components/TextField.tsx:43-56 | `TextFieldControl` は `...rest` を `<input>` へそのまま渡す（autoComplete は通る） |
| frontend/src/components/Callout.tsx:24-31 | 案内の金型。variant info は role="status" |
| frontend/src/locales/ja.json:705-709・765-769 | login.signInWithPasskey ほか・authError.passkey* の文言 |
| frontend/src/pages/login/LoginPage.test.tsx:18-20・319-374 | passkey は vi.mock。ボタンの試験は 3 本 |
| frontend/src/lib/auth/passkey.test.ts:11-16 | `@simplewebauthn/browser` と api を vi.mock |

## §3 サーバー側（読むだけ・変えない）

| 場所 | 事実 |
|---|---|
| backend/app/routers/auth.py:1106-1116 | `/passkey/login/options`: 画面の出元確認 → `check_auth_rate_limit(ip)`（読むだけ・数えない）→ 札を作り Redis へ |
| backend/app/cache.py:311-325 | `check_auth_rate_limit` は失敗回数を **読むだけ**（10 以上で True）。増やすのは `record_auth_failure`（:328） |
| backend/app/auth/passkeys.py:27 | `CHALLENGE_TTL_SECONDS = 300`（札は 5 分で消える） |
| backend/app/auth/passkeys.py:45-60 | 札は Redis に置き、verify で 1 回で消す（getdel）。DB の表は増えない |
| backend/app/auth/passkeys.py:76-77・84-87 | 登録は resident_key REQUIRED・UV REQUIRED。ログインの allow_credentials は空 |
| backend/app/middleware/audit.py:215-268 | 認証の口を通るたびに public.auth_events に 1 行（既存の表・既存の動き） |

→ 画面を開いたときに options を呼ぶと、auth_events に 1 行増える（今はボタンを押したときに増えている行と同じ種類）。表・列は増えない。

## §4 部品（@simplewebauthn/browser 14.0.0）の事実

出典: unpkg.com/@simplewebauthn/browser@14.0.0/esm/（2026-11-24 取得・scratchpad authreq/ext/swa/）

| 項目 | 事実 |
|---|---|
| 自動の候補 | `startAuthentication({ optionsJSON, useBrowserAutofill: true })`。`input[autocomplete$='webauthn']` が無いと投げる。`mediation='conditional'`・allowCredentials は空にする |
| 取り消し | 呼ぶたびに `WebAuthnAbortService.createNewAbortSignal()` で前の呼び出しを止める。`WebAuthnAbortService.cancelCeremony()` は公開（index.d.ts で export） |
| 止められた時 | `WebAuthnError`（name は元の誤りの name＝AbortError、code ERROR_CEREMONY_ABORTED） |
| immediate | 部品に `uiMode` の扱いは無い（startAuthentication.js の全文に無い）→ 直接 `navigator.credentials.get` を呼ぶ必要がある |
| 変換の道具 | `base64URLStringToBuffer`・`bufferToBase64URLString` は公開 |

## §5 ブラウザの事実（Chrome 公式・2026-11-24 取得）

出典: https://developer.chrome.com/docs/identity/immediate-ui-mode ・ https://developer.chrome.com/blog/webauthn-immediate-ui

- `navigator.credentials.get({ publicKey, uiMode: 'immediate' })`。Chrome 149 から。対応の見分けは `getClientCapabilities().immediateGet`。
- 押す操作から呼ぶ必要がある。押す操作を使い切らない。
- 「パスキーが無い」と「出た画面を閉じた」は、どちらも NotAllowedError（区別できない）。
- シークレット窓は常に NotAllowedError。allowCredentials が空でなければ NotAllowedError。
- signal で画面を閉じることはできない。
- Apple（WebKit）は反対の立場（Negative）。

## §6 未確認

- 自動の候補が待っている間に immediate の get を呼んだとき、Chrome がどう扱うか（公式の文が無い）。→ design.md §4-3 で「先に止めて、終わるのを待ってから呼ぶ」にする。
- options の通信の後でも「押す操作」が有効のままか（公式の文は「使い切らない」だけ）。→ 有効でなければ NotAllowedError になり、案内と「別の機械」の道が出る（壊れない）。P2 は PO の Mac の Chrome で確かめる。
- 3 台（Mac Chrome・iPhone Safari・Android Chrome）で本番の画面に候補が出るか。→ 反映後に PO の目視（P1）。
