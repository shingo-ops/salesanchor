# KGI — テナント分離・RLS（tenant-rls）

> この文書は何か：「会社ごとのデータが他社に漏れない」を、○×で判定できる数字の目標に置き換えたものです。

親: [README.md](README.md)　／　あるべき姿: [ideal-state.md](ideal-state.md)

**状態: PO 承認済み（2026-10-15 22:10 頃、PO「y」）**。A 区分（`migrations/` を含む）のため PO 承認が必須ゲート（docs/STANDARD-WORKFLOW.md §1）。

## 背景（監査 2026-10-15 の事実）

本番 DB で、会社情報・ログイン情報を含む 11 表に RLS（データベース自身が「他社の行を見せない」仕組み）が無い。守りは各 SQL の `WHERE tenant_id` 1 行だけで、書き忘れや SQL 注入が 1 か所あれば全社分が漏れる。対象 11 表: users, tenants, auth_refresh_tokens, password_reset_tokens, webauthn_credentials, permissions, tenant_google_calendar_config, tenant_google_drive_config, tenant_paypal_config, registration_tokens, suppliers。

## KGI

| ID | 目標（○×で判定） | 判定方法 | 現在値（2026-10-15） |
|---|---|---|---|
| KGI-1 | 監査の 11 表すべてが「RLS 有効（ENABLE と FORCE）＋ポリシー 1 本以上」または「RLS を付けない理由と代わりの守りが ADR に記録済み」のどちらか。どちらでもない表が 0 | 本番 DB の `pg_class.relrowsecurity / relforcerowsecurity` と `pg_policies` 件数、ADR の記載 | 未対処 11 表 |
| KGI-2 | 各段階の適用後、ログイン・パスワード再設定・既存画面・夜間処理の失敗が 0 件（適用前と比べて増えない） | 適用後に本番でログイン成功を確認、該当画面の表示確認、アプリログのエラー件数を適用前後で比較 | 基準値は各段階の適用直前に取得 |
| KGI-3 | アプリの接続役（salesanchor_app）で、許されない読み書きを試すと DB が拒否する（各段階の対象表ごと） | 本番相当の DB で salesanchor_app として書き込み・他社行の読み取りを試すテストが CI で緑 | 0 表 |

## KPI（段階ごと）

| 段階 | 対象 | KPI |
|---|---|---|
| ① | permissions | salesanchor_app での INSERT/UPDATE/DELETE が拒否される。SELECT は全行（2026-10-15 時点 123 行）読める |
| ② | suppliers, tenant_google_calendar_config, tenant_google_drive_config | 他社の行が 0 行に見える。共通（tenant_id が空）の仕入先は全社で読める |
| ③ | tenants, tenant_paypal_config, users, auth_refresh_tokens, password_reset_tokens, webauthn_credentials, registration_tokens | 方針（RLS を付けるか、付けずに代わりの守りにするか）を別途 PO と決めてから設定 |

## 運用方針

- 変更は一度に 1 段階。各段階で「適用 → 本番確認 → 次の段階」。
- 各段階の本番適用は GO 記録が必要（ADR-135／ADR-136、委任は ADR-1003）。
