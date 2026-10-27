# 設計審査 — 管理者ログインの2段階の確認

> この文書は何か：設計書が実装に渡せる形になっているかを、設計者と同じ AI（Opus）が Architect の立場で確かめた記録です。独立した第二者の審査ではありません。

親: [design.md](design.md)

**日付**: 2026-10-27
**審査した人**: 設計パートナー（Opus・Architect 役。設計者と同一 AI）
**判定**: APPROVE（設計として合格。PO の実装承認・GO を兼ねない）

## 1. 照合した事実（origin/main・2026-10-27 fetch 後）

| 設計の記述 | 照合先 | 結果 |
|---|---|---|
| 管理者の判定の正本 | backend/app/auth/dependencies.py:516（require_super_admin）、:547（get_user_system_keys）、:606（require_tenant_admin）、backend/app/auth/system_roles.py:17 | 一致 |
| ログイン情報は子表 | docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:23（Decision 2） | 一致。user_totp・user_trusted_devices は子表 |
| 6桁は範囲外・任意 | ADR-1013:30（Decision 7） | 管理者についてだけ広げる。ADR-1048 に関係を明記 |
| refresh cookie の書き方 | backend/app/routers/auth.py:211-221（HttpOnly・Secure・SameSite strict） | いつもの機器の cookie を同じ書き方にそろえる |
| refresh で止めた人を拒否 | backend/app/auth/self_tokens.py:227-228 | 一致 |
| Redis に5分・1回限り | docs/handoff/auth-self-hosted-passkey/design.md:80 | 同じ置き方 |
| 暗号部品 | backend/app/services/encryption.py:100 | 一致 |
| 子表の GRANT・RLS なし | migrations/20261013_160000_add_self_hosted_auth_tables.sql:3,95-101 | 同じ形にする |
| メールが送れないときはログだけ | backend/app/services/mail_config.py:27-35 | 一致 |
| 6桁の入力枠 | frontend/src/components/TextField.tsx:43（InputHTMLAttributes を受ける :37） | 新しい金型は不要 |
| 金型の作法 | docs/CC_UI_GOVERNANCE.md:13-15 | QrCode は PO 許可済み（2026-10-27「1」） |
| cryptography の版 | backend/requirements.txt:24（48.0.1） | py_webauthn 2.8.0 で両立 |

照合の生出力: 手元の控え /tmp/CC報告ファイル/auth-2fa/design-linecheck.txt（134行）。

## 2. 観点ごとの判定

| 観点 | 判定 | 根拠 |
|---|---|---|
| データと配線を分散させない | 合格 | 管理者の判定は既存の関数、置き場は users の子表、知らせは既存 SSE 1本とメール部品、暗号は既存部品。新しい名簿・通り道・鍵なし |
| 金型とトークン | 合格 | 6桁は TextFieldControl、承認は Modal・Button。新設は QrCode だけで PO 許可済み・var() のみ・stories あり |
| 目標が数で測れる | 合格 | K1〜K7 に基準値（未測定はその旨）と測り方。K1 は本番読み取り、K2・K4 はログ行、K4・K5・K7 は自動試験、K6 は CI |
| 範囲がはっきりしている | 合格 | 対象と対象外（§4）、便 7a〜7d と危ない道（§5） |
| 閉め出しの防止 | 合格 | 既定 false の設定で入れ、K1=0 を数えてから PO の GO で切り替え。戻しは false |
| 外部の根拠 | 合格 | NIST・OWASP・Google は公式本文を 2026-10-27 に直接読んだ。Uber の件は記事のみで公式未確認と明記し、数値に使わない |

## 3. 審査で直した点

- 承認後のトークンを、依頼を出した機器だけが受け取れるようにした（依頼の id と機器の cookie を組にする。design.md §3-5 の2）。
- 設定だけのトークンには refresh cookie を出さないことを明記した（§3-2）。
- いつもの機器が1台も無い人は「パスワード＋6桁」で入れないことと、その時の道を明記した（§3-6）。

## 4. 未解決と、実装の便で最初に確かめること

| 事項 | 扱い |
|---|---|
| qrcode.react 4.2.0 に CSS 変数の色を渡せるか | 未確認。便7c の最初に確かめる。だめなら CSS で上書き、それも無理なら止めて相談（design.md §3-7） |
| メールが本番で送れるか | ADR-1013 便3 の PO の画面作業待ち。送れない間も画面の知らせで承認できる |
| 自動試験のファイル名 | 便7b の実装カードで決める |
| 全部を失くしたときの運用台本 | 便7b と同時に作る。本番データ変更の決まりに従う |
| 管理者の last_login が全員空の理由 | 未確認。本件の判定には使わないので設計に影響なし |

いずれも設計の芯（何を・どこに・どう測る）を変えない。実装に入るには、ADR-1013 便5（パスキー）の本番反映、PO の実装承認、便ごとの実装カードが要る。
