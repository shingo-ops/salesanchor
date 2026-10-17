# KGI — テナント分離・RLS（tenant-rls）

> この文書は何か：「会社ごとのデータが他社に漏れない」を、○×で判定できる数字の目標に置き換えたものです。

親: [README.md](README.md)　／　あるべき姿: [ideal-state.md](ideal-state.md)

**状態: PO 承認済み（2026-10-15 22:10 頃、PO「y」）**。A 区分（`migrations/` を含む）のため PO 承認が必須ゲート（docs/STANDARD-WORKFLOW.md §1）。

## 背景（監査 2026-10-15 の事実）

本番 DB で、会社情報・ログイン情報を含む 11 表に RLS（データベース自身が「他社の行を見せない」仕組み）が無い。守りは各 SQL の `WHERE tenant_id` 1 行だけで、書き忘れや SQL 注入が 1 か所あれば全社分が漏れる。対象 11 表: users, tenants, auth_refresh_tokens, password_reset_tokens, webauthn_credentials, permissions, tenant_google_calendar_config, tenant_google_drive_config, tenant_paypal_config, registration_tokens, suppliers。

## KGI

| ID | 目標（○×で判定） | 判定方法 | 現在値（2026-10-16 17:30 JST） | 判定 |
|---|---|---|---|---|
| KGI-1 | 監査の 11 表すべてが「RLS 有効（ENABLE と FORCE）＋ポリシー 1 本以上」または「RLS を付けない理由と代わりの守りが ADR に記録済み」のどちらか。どちらでもない表が 0 | 本番 DB の `pg_class.relrowsecurity / relforcerowsecurity` と `pg_policies` 件数、ADR の記載 | 本番 DB（17:30）: RLS t/t＋ポリシーありが 8 表（permissions 2、suppliers 4、tenant_google_calendar_config 1、tenant_google_drive_config 1、tenant_paypal_config 4、registration_tokens 4、tenants 4、users 4）。RLS なしが 3 表（auth_refresh_tokens・password_reset_tokens・webauthn_credentials）で、理由と代わりの守りを ADR-1018 Decision 6 に記録。どちらでもない表 0 | ○ |
| KGI-2 | 各段階の適用後、ログイン・パスワード再設定・既存画面・夜間処理の失敗が 0 件（適用前と比べて増えない） | 適用後に本番でログイン成功を確認、該当画面の表示確認、アプリログのエラー件数を適用前後で比較 | 各段階の反映後に backend・Celery ログの 42501・row-level security・5xx を数えて 0 件（各 PR #4332・#4347・#4349・#4354・#4379・#4381 のコメント）。締めの再確認（17:30）: 現行コンテナ起動（07:44Z）以降の 42501・row-level security は backend・worker・beat とも 0、Traceback は worker の 1 件（接続を閉じるときの「Event loop is closed」。同じ処理は成功で終了し RLS と無関係）。便C 反映後の nginx 経由 /api/v1 応答は 200 が 18・401 が 7（401 はすべて閲覧ページ /api/v1/viewer/*）。**未観測**: 自社ログイン（ログイン操作・パスワード再設定）は本番でまだ使われておらず（auth_refresh_tokens の発行 0 件・last_login が全員 NULL）、ログイン成功を本番で確かめられない。画面の目視（ロール管理・Google 接続・PayPal 接続保存・招待リンク・運営画面の会社作成）も未実施。いずれも CI の実 PostgreSQL 試験では確認済み | 観測できた範囲では失敗 0（○）。ログイン成功と画面の目視は未観測のため最終判定は保留 |
| KGI-3 | アプリの接続役（salesanchor_app）で、許されない読み書きを試すと DB が拒否する（各段階の対象表ごと） | 本番相当の DB で salesanchor_app として書き込み・他社行の読み取りを試すテストが CI で緑 | main の Backend Tests（run 38863920549）が緑（6242 passed・69 skipped）。同じ run の PostgreSQL ログに `violates row-level security policy for table "<表>"` が RLS を付けた 8 表すべてで出ている（permissions 1、suppliers 1、tenant_google_calendar_config 1、tenant_google_drive_config 1、tenant_paypal_config 2、registration_tokens 2、tenants 3、users 3）＝試験が実際に走り DB が拒否した。試験の skip 条件は 6 ファイルとも接続先の環境変数が無いときだけ（例 backend/tests/test_users_rls.py:24-31） | ○（8 表） |

## KPI（段階ごと）

| 段階 | 対象 | KPI |
|---|---|---|
| ① | permissions | salesanchor_app での INSERT/UPDATE/DELETE が拒否される。SELECT は全行（2026-10-15 時点 123 行）読める |
| ② | suppliers, tenant_google_calendar_config, tenant_google_drive_config | 他社の行が 0 行に見える。共通（tenant_id が空）の仕入先は全社で読める |
| ③ | tenants, tenant_paypal_config, users, auth_refresh_tokens, password_reset_tokens, webauthn_credentials, registration_tokens | 方針（RLS を付けるか、付けずに代わりの守りにするか）を別途 PO と決めてから設定。→ 決定（PO 2026-10-16「y」）: 案 C＝書込・削除だけ DB で止め読取は全行可（tenants・tenant_paypal_config・users・registration_tokens）、認証トークン 3 表は RLS を付けない（ADR-1018 Decision 6） |

## 運用方針

- 変更は一度に 1 段階。各段階で「適用 → 本番確認 → 次の段階」。
- 各段階の本番適用は GO 記録が必要（ADR-135／ADR-136、委任は ADR-1003）。
