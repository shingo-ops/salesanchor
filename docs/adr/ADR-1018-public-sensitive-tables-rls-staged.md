# ADR-1018: public の機微 11 表への RLS は段階導入し、表ごとに型を決める

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（PO の承認: KGI と段階導入 2026-10-15 チャット「y」、段階③の案 C と認証トークン 3 表に RLS を付けない方針 2026-10-16 チャット「y」。段階①〜③は 2026-10-16 までに本番反映済み） |
| 作成日 | 2026-10-15 |
| 起案 | Claude Opus（設計）。PO 2026-10-15 09:04「着手して」（監査指摘 S1） |
| 関連 | ADR-145、ADR-072、ADR-131、ADR-1013、ADR-135、ADR-136 |
| 根拠 | docs/specs/tenant-rls/README.md、docs/specs/tenant-rls/kgi.md（KGI の判定）、docs/handoff/s1-rls-permissions/recon.md、docs/handoff/s1-rls-permissions/design.md、docs/handoff/s1-rls-stage3a/design.md、docs/handoff/s1-rls-stage3b/design.md、docs/handoff/s1-rls-stage3c/design.md |

---

## Context

- 2026-10-15 の監査で、public スキーマの機微 11 表（users, tenants, auth_refresh_tokens, password_reset_tokens, webauthn_credentials, permissions, tenant_google_calendar_config, tenant_google_drive_config, tenant_paypal_config, registration_tokens, suppliers）に RLS が無いことを本番 DB で確認した。守りは SQL の `WHERE tenant_id` だけ。
- アプリ・Celery は本番で salesanchor_app（rolsuper f / rolbypassrls f）で接続しており、RLS は効く。migration 実行役 jarvis は superuser。
- 認証前（会社が未確定）に引く表に会社別 RLS を付けると全ログインが止まる。ADR-1013 は認証系の表に RLS を付けていない。
- `migrations/20260605_030000_create_salesanchor_app_role.sql` が毎デプロイ全表に SELECT/INSERT/UPDATE/DELETE を再付与するため、表単位の REVOKE は次のデプロイで戻る。

## Decision

1. 3 段階で導入し、1 段階ずつ「適用 → 本番確認 → 次」で進める。
   - 段階①: permissions（全社共通の権限マスタ）。読取は全行、書込は `app.is_operator='true'` のみ（app_fx_rates と同じ型）。
   - 段階②: suppliers・tenant_google_calendar_config・tenant_google_drive_config。会社別の型。文脈を張らずに書く経路（super_admin_suppliers.py、OAuth callback）を先に直す。
     - 2026-10-16 追記：段階②は 2 便に分ける。②a＝Google 2 表（tenant_carrier_credentials と同じ「自社行のみ」の型。OAuth 戻り先で set_tenant_context を張り、commit 後に同表を読む経路で reset_tenant_context を呼ぶ）。②b＝suppliers（共通行 tenant_id NULL があるため products と同じ型。運用者の書込経路に app.is_operator を張ってから適用）。理由：suppliers は共通行 288 行と書込経路が多く、Google 2 表（計 1 行）と一緒に入れると不具合の切り分けができないため。
   - 段階③: tenants・tenant_paypal_config・認証系 5 表。RLS を付けるか、付けずに代わりの守りにするかを PO と決めてから設定する。
     - 2026-10-16 追記（PO「y」）：案 C＝書込・削除だけ DB で止め、読取は全行可のままにする。理由：この 4 表はログイン前・会社未確定の時点で読まれるため、読取を会社別に絞るとログインと招待が止まる。3 便に分けた。便A＝tenant_paypal_config・registration_tokens（PR #4354）、便B＝tenants（作成・変更・削除は運営文脈のときだけ。PR #4379）、便C＝users（作成・変更・削除は自社の会社文脈か運営文脈のときだけ。ログイン・パスワード再設定・言語/テーマ変更・登録は users の書込直前だけ会社文脈を張る。PR #4381）。
     - 認証トークン 3 表（auth_refresh_tokens・password_reset_tokens・webauthn_credentials）は RLS を付けない（Decision 6）。
2. 守りは RLS（ポリシー）で行い、表単位 REVOKE は使わない（毎デプロイの再付与で戻るため）。
3. ENABLE と FORCE の両方を付ける。ポリシーは冪等（`DROP POLICY IF EXISTS` → `CREATE POLICY`）にする。
4. migration-guard チェック 8 では、POLICY 文を構造 DDL として許可する（値を書く文ではないため）。この許可は PO 確認後に入れる。
5. 訂正注記：ADR-145 の「bypassrls=t でも強制される」趣旨の記述は PostgreSQL 公式（docs/16/ddl-rowsecurity: "Superusers and roles with the BYPASSRLS attribute always bypass the row security system"）と食い違う。superuser・BYPASSRLS 役は FORCE でも素通りする。FORCE が効くのは所有者が一般役の場合。
6. 認証トークン 3 表（auth_refresh_tokens・password_reset_tokens・webauthn_credentials）には RLS を付けない（PO 2026-10-16「y」）。
   - 理由：この 3 表はログイン前・会社未確定の時点で、トークンのハッシュ一致で 1 行を引く（backend/app/auth/self_tokens.py:198・:207・:244、backend/app/routers/auth.py:444）。会社別 RLS を付けると全ログインとパスワード再設定が止まる。
   - 代わりの守り（コードの行で確認済み 2026-10-16）:
     - 生トークンを保存しない：sha256 のハッシュだけを token_hash 列に入れる（self_tokens.py:141-142、INSERT は :171-177 と auth.py:412-415）。token_hash は UNIQUE と長さ CHECK 付き（migrations/20261013_160000_add_self_hosted_auth_tables.sql:51,55,57,71,79,80）。
     - 期限：refresh 30 日（self_tokens.py:24,166）、アクセストークン 900 秒（:23）、再設定 30 分・招待 72 時間（migration :60）。照合 SQL に `expires_at > :now`（self_tokens.py:198、auth.py:444）。
     - 1 回限りと失効：再設定は `used_at IS NULL` の UPDATE で 1 回だけ（auth.py:443-445）、新しい申請で未使用分を失効（auth.py:404-405）。refresh は使うたびに旧トークンを失効（self_tokens.py:197-199）、再利用を見つけたら同じ系列を全失効（:207-215）、ログアウトで失効（:243-244）、パスワード再設定で本人の全 refresh を失効（auth.py:476-477）。
     - webauthn_credentials は公開鍵（COSE）と credential_id・sign_count だけで、秘密鍵の列は無い（migration :16-32）。2026-10-16 時点でこの表を読み書きする backend/app のコードは 0 件。
   - 2026-10-16 時点の本番：3 表とも relrowsecurity=f・ポリシー 0（意図どおり）。

## Consequences

- アプリの SQL に書き忘れや注入があっても、DB が他社行・書込を拒否する範囲が段階ごとに広がる。
- 将来アプリから permissions を書く機能を作る場合は、`app.is_operator` を立てる経路に限る。
- 段階②・③は、アプリ側の文脈付与の改修が先に必要。
- 戻し方は各段階の design.md に記す（ポリシー削除と RLS 無効化の SQL＋Revert PR）。

## 代替案

- 11 表を一度に適用：認証系でログインが全停止する危険があり、原因の切り分けもできないため不採用。
- 表単位 REVOKE：毎デプロイの再付与で戻るため不採用。
- ガード回避（行分割・EXECUTE 文字列で表名を隠す）：ゲートの迂回になるため不採用。
