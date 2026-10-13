# ADR-1013: ログインの判定を Firebase から自社サーバーへ移し、パスキー（顔・指紋）でのログインを足す

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（PO 2026-10-13 チャット「y」で設計と KGI を承認。実装は便ごとに実装カードと PO の実装承認を経る） |
| 作成日 | 2026-10-13 |
| 起案 | Claude Opus（設計担当） + しんごさん（PO：方針・発行方式・範囲の決定） |
| 関連 | Supersedes ADR-138（Firebase 専一）。ADR-032（Firebase 認証ドメイン）と ADR-023（3 層同期・提案）は便6 完了時に Superseded とする。ADR-1008（人の正本）、ADR-1007（migration 構造のみ）、ADR-127、ADR-136、ADR-144 |
| 根拠 | docs/handoff/auth-self-hosted-passkey/recon.md、docs/handoff/auth-self-hosted-passkey/design.md、docs/specs/auth-login/ |

---

## Context

- ログインは Firebase Authentication が全部受け持ち、自社 DB にパスワードは無い（ADR-138・2026-06-12）。
- PO は顔・指紋（パスキー）でのログインを足したい（2026-10-13）。Firebase の公式ドキュメントにパスキーの本番提供は無い（firebase-tools PR #10636 本文で "private preview"）。
- 本番の実物（2026-10-13 読み取り）: 使用中ユーザー 10 人・Firebase 登録 12 人（両方にいるのは 9 人）、二段階認証は本番で無効（MFA_REQUIRED=false）、自社のメール送信設定は無い。
- 全 API の認証は `get_current_user` 1 本を通り、ユーザーとは email で紐づいている。テナントは DB の user.tenant_id で決まる。

## Decision

1. パスワードの照合・ログイン後のトークンの発行と失効・パスワード再設定メール・パスキーを自社サーバー（FastAPI＋PostgreSQL）で持つ。
2. ログイン情報は人の正本 public.users.id にだけぶら下げる（users の 4 列と、子表 webauthn_credentials・password_reset_tokens・auth_refresh_tokens）。人の名簿は増やさない。
3. パスワードは Argon2id で保管する。長さ 15〜64 文字、漏洩・常用一覧の照合あり、定期変更なし。口座単位で 10 回失敗すると 15 分止める。
3b. パスワードを入れる新しい列の名前は password_argon2_hash とする（password_hash にしない）。`scripts/run_all_migrations.sh` は毎デプロイ登録済み migration を全件やり直し、409 行目で `migrations/20260612_150000_drop_password_hash.sql`（DROP COLUMN IF EXISTS password_hash）が毎回走るため、同じ名前の列は毎デプロイ消えるから（2026-10-13 便1 調査）。
4. 移行時は、既存パスワードを Firebase から持ち出さず、使用中の全員に新しいパスワードを発行する。平文は PO の Mac のファイルにだけ書き出す（PO 2026-10-13）。
5. 移行後の再設定は、本人がメールのリンクで行う（PO 2026-10-13「n」）。メールは salesanchor.jp のアドレスから自社サーバーが送る。新しく作るユーザーにも、同じ仕組みで「初回設定メール」を送る（使い捨て鍵の表は再設定と共用）。
5b. ログイン関連の API は、画面のオリジン（app.salesanchor.jp）以外から呼ばれたら拒否する。パスキーの RP ID は app.salesanchor.jp とする（PO 2026-10-13「y」）。後から変えると登録済みのパスキーが全部使えなくなるため、変更には新しい ADR を要する。
6. 切替はスイッチ（AUTH_PROVIDER）で行い、Firebase のユーザー削除は最後の便で PO の GO を取ってから行う。
7. 二段階認証（認証アプリ）は本 ADR の範囲外とし、次の便で任意設定として追加する（PO 2026-10-13）。

## Why

- パスワードは Firebase、パスキーは自社、という分け方では、ログイン情報が 2 か所に分かれ、PO の「データを分散させない」に反する。
- Firebase のパスキー対応は提供時期が公表されておらず、計画に組めない。
- 既存パスワードの持ち出し（Firebase の scrypt 互換）は、Firebase の署名鍵を本番に置く必要があり、照合部品も非公式。使用中は 10 人なので、新しく発行する方が安全で単純。
- ADR-138 が削除した理由は「照合に使わない保管は攻撃面を増やすだけ」だった。本 ADR では照合に使うので、保管する理由がある。保管方式は OWASP の第一選択（Argon2id）とする。

## Consequences

- 自社で守る範囲が増える（パスワード保管・口座ロック・再設定メール・秘密 2 種 AUTH_JWT_SECRET と SMTP 資格情報）。
- 切替日に使用中の全員のパスワードが変わる。PO が配布する。
- Firebase に依存する運用スクリプト・CI・監視（qa-smoke・rotate-qa-firebase・snapshot・smoke）は便6 で置き換える。
- 戻し方: 便4 までは AUTH_PROVIDER=firebase に戻せば元どおり。Firebase のユーザー削除（便6）だけは戻せない。
