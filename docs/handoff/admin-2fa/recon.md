# 現状調査 — 管理者ログインの2段階の確認

> この文書は何か：管理者のログインに2段階の確認を足す前に、今のシステムと本番の状態を確かめた記録です。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)

**日付**: 2026-10-27
**調べた人**: 担当（Sonnet・読み取りのみ）／確かめた人: 設計パートナー（Opus・全文読了）
**基準**: origin/main（git fetch 後）。本番 DB は読み取り専用の道（ADR-1024）。メールアドレス・鍵・パスワードの値は書かない。

## 0. 既存 ADR の検索

- `git grep -i -e passkey -e webauthn -e totp -e "二段階" -e mfa origin/main -- docs/adr/` と `docs/adr/FEATURE-INDEX.md` を確認した。
- 該当: ADR-1013（docs/adr/ADR-1013-self-hosted-auth-and-passkey.md）。Decision 7「二段階認証（認証アプリ）は本 ADR の範囲外。次の便で任意設定として追加」（ADR-1013:30）。docs/handoff/auth-self-hosted-passkey/design.md:117,160,237 も同じ。
- 関連: ADR-1016（docs/adr/ADR-1016-realtime-change-signal-standard.md:15 即時反映は SSE 1本）、ADR-1008（人の正本は public.users）、ADR-1024（本番 DB の読み取りの道）、ADR-067（デザイントークン）、ADR-144（UI ガバナンス）、ADR-027（i18n）。
- 管理者に2段階を必須にする ADR は無い（grep 済み・該当なし）。

## 1. 「管理者」の定義（正本）

- super admin: `public.users.is_super_admin`（/Users/tanizawashingo/salesanchor/backend/app/models.py:33）。判定は `require_super_admin`（backend/app/auth/dependencies.py:516-541、:539 で偽なら 403）。
- 会社の管理者: `user_roles → roles.system_key` が owner / admin（backend/app/auth/system_roles.py:8-9,17-19 `is_tenant_admin`）。判定は backend/app/auth/dependencies.py:547 `get_user_system_keys`、:606 `require_tenant_admin`（:613「users.role は見ない」）。
- User モデルに role 列は無い（backend/app/models.py:22-37）。

## 2. 今のログインと2段階の判定

- 自社ログイン: backend/app/routers/auth.py:238-310（Origin 照合→IP 制限→users 引き→ロック判定→Argon2 照合→失敗10回で停止→成功で last_login 更新→アクセストークン＋refresh Cookie）。
- 自社トークンの amr（pwd か webauthn）: backend/app/auth/self_tokens.py:86-97。
- 発行は AUTH_PROVIDER=self のときだけ（backend/app/auth/self_tokens.py:20 既定 firebase）。
- MFA_REQUIRED: backend/app/auth/dependencies.py:39（既定 "true"）。Firebase 経路だけ（:222-229、`sign_in_second_factor`）。自社トークン経路（:207-209）では見ない。
- パスキーの置き場: `public.webauthn_credentials`（migrations/20261013_160000_add_self_hosted_auth_tables.sql:16-32）。API は未実装（routers/auth.py に passkey の口なし）。
- 6桁の秘密を置く列・表は無い。

## 3. 止めた人がログインできないこと（is_active）

- 自社トークン: backend/app/auth/dependencies.py:99 `not row.is_active` で 401。
- Firebase 経路: backend/app/auth/dependencies.py:238-247（is_active==True 付きで検索、無ければ 401）。キャッシュが当たっても :193-199 で DB を引き直す。
- 自社 login: backend/app/routers/auth.py:264。refresh: backend/app/auth/self_tokens.py:228。
- 生の出力: /tmp/CC報告ファイル/auth-2fa/is-active-check.txt（手元の控え）

## 4. 本番の管理者の人数（読み取り）

| 時刻（JST） | 有効な管理者 | 内訳 | パスキー登録 |
|---|---|---|---|
| 2026-10-27 23:01 | 5人 | super admin 2人（テスト管理者・PO 本人）、owner 5人、重複を除いて5人。admin ロールは0人 | 0件 |
| 2026-10-27 23:20 | 3人 | テスト管理者（test-corp）・PO 本人（highlife-jpn）・審査用（tenant-review） | 0件 |

- 23:01 と 23:20 の差は、使い道の分からない2人（test-tenant-2 と test-corp の owner）を PO の決定で止めたため（[deactivate-7-9/README.md](deactivate-7-9/README.md)）。
- 管理者の last_login は全員空。理由は未確認（今の Firebase ログインで更新されていない可能性があるが、確かめていない）。
- 文書（docs/handoff/neutralize-value-migrations-3c/recon.md:42）は super admin 3人と書くが、実測は2人。文書が古い。

## 5. 自動の点検への影響

| 仕組み | ログインの通り方 | 2段階必須の影響 | 根拠 |
|---|---|---|---|
| FedEx smoke | 固定トークン。MFA を通らない | 無し | backend/app/auth/dependencies.py:148-170 |
| 設計図書サイト smoke | Basic 認証 | 無し | .github/workflows/deploy.yml:127-138 |
| deploy 後 smoke | DB 直 | 無し | scripts/smoke_test_post_deploy.sh:52-88 |
| qa-smoke | tenant 6 の qa-admin で Firebase 実ログイン | 対象になれば壊れる。ただし本番の tenant 6 の owner は審査用1人だけで、qa-admin がオーナーとして本番にいる形跡は無い。直近5回中3回すでに失敗。ADR-1013 便6 で置き換え予定（ADR-1013:43） | .github/workflows/qa-smoke.yml:23-33; scripts/qa/seed-tenant.sql:101-112 |

## 6. 承認の知らせを届ける道

| 道 | 今あるもの | 無いもの | 根拠 |
|---|---|---|---|
| 開いている画面に出す | SSE 1本 `GET /api/v1/events/stream` | 宛先は会社単位と全体だけ。人単位の宛先が無い | docs/adr/ADR-1016-realtime-change-signal-standard.md:15,60; backend/app/routers/realtime_events.py:58-105; backend/app/realtime/publisher.py:19-21; backend/app/realtime/hub.py:28-30; frontend/src/lib/realtime/RealtimeProvider.tsx:81 |
| スマホの通知 | 無い（serviceWorker・pywebpush・VAPID・PushManager・webmanifest の grep 0件） | 全部 | iPhone はホーム画面に追加が必要・iOS 16.4 以降（https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/） |
| メール | 送信部品 backend/app/services/auth_mail.py:73-93、設定 backend/app/services/mail_config.py:28-35（4つそろわないと送らずログのみ） | 本番で送れる状態か未確認（PO の画面作業待ち docs/handoff/auth-self-hosted-passkey/card-b3.md §8 ②） | .github/workflows/deploy.yml:355-359 |

- 新しい機器を覚える表・cookie は無い。`auth_refresh_tokens.user_agent_hash` は「記録と検知だけ、拒否には使わない」（migrations/20261013_160000_add_self_hosted_auth_tables.sql:68-93）。
- 生の出力: /tmp/CC報告ファイル/auth-2fa/notify-channels.txt（手元の控え）

## 7. 暗号化と部品

- 暗号化の既存部品: backend/app/services/encryption.py:100 `encrypt` / :121 `decrypt`（Fernet・鍵 METADATA_FERNET_KEY :39）。起動時の確認 backend/app/main.py:146,164-168。
- 読み取りの道は `_encrypted` で終わる列を読まない（backend/app/ops/readonly_query.py:42 DENY_COLUMN_RE）。
- 依存: backend/requirements.txt:24 cryptography==48.0.1。pyotp・webauthn・qrcode は requirements.txt・frontend/package.json に無い（grep 0件）。
- 外部の版（2026-10-27 読み取り）: webauthn 3.0.1 は cryptography>=49 を要求し両立しない。2.8.0 は cryptography>=46 で両立（PyPI JSON requires_dist）。pyotp 2.10.0（MIT）。@simplewebauthn/browser 14.0.0（MIT・依存0）。qrcode.react 4.2.0（ISC・依存0・SVG）。

## 8. 画面の金型

- 使える金型: Button（frontend/src/components/Button.tsx:40）、TextFieldControl（frontend/src/components/TextField.tsx:43、variant login :35、InputHTMLAttributes を継承 :37）、Modal（frontend/src/components/Modal.tsx:36）、Callout（frontend/src/components/Callout.tsx:25）、Card（frontend/src/components/Card.tsx:27）、LoadingBlock（frontend/src/components/loading/）。
- 無い金型: QR コードの表示、6桁専用の分割枠（components を otp/code/pin/digit で grep して該当なし）。
- 新設の決まり: docs/CC_UI_GOVERNANCE.md:9-15（PO 許可後に Xxx.tsx＋Xxx.css（var() のみ）＋Xxx.stories.tsx）。

## 9. 外部の決まり（2026-10-27 公式ページ直読み。Context7 は月の上限で使えなかった）

- NIST SP 800-63B-4（2025-08-26）3.2.5: 手で打つ OTP は「フィッシングに強い」と見なしてはならない（SHALL NOT）。付録B: 同期型パスキーは AAL2 まで可。https://pages.nist.gov/800-63-4/sp800-63b.html
- OWASP MFA Cheat Sheet: 強い方式から弱い方式への格下げを防ぐ／要素の変更は既存の要素で再確認／OTP は1回限り・回数制限。https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
- Google のログイン確認: いつもと違う入り方のとき、パソコンの画面の番号とスマホの番号を合わせる確認を出すことがある。https://support.google.com/accounts/answer/7026266
- 押すだけの承認の弱さ: 2022年の Uber への侵入は、承認の通知を何度も送り押させる手口だったとセキュリティ会社の記事が書く（https://centrexit.com/mfa-fatigue-uber-breach-2022/）。Uber 自身の公式発表は未確認。
