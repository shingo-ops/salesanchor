---
mode: handoff
---
# recon — S1 段階③便A（PayPal 設定・招待リンクの 2 表）

> この文書は何か：PayPal の接続設定（public.tenant_paypal_config）と顧客への招待リンク（public.registration_tokens）に「書込だけ RLS」を付ける前に、読み書きの全経路を行番号まで調べた記録です。

**日付**: 2026-10-16　**基準**: origin/main 5058a8bb0（fetch 後）
**調査**: Sonnet（読取のみ）＋ Opus 再確認　**生出力**: `/tmp/CC報告ファイル/s1-stage3/recon-paypal-regtoken/`（リポジトリ外）
**PO 決定**: 段階③は案 C（書込だけ RLS）— 2026-10-16 PO「y」（質問「書き換え・削除だけ DB で止めますか」への回答）

## 0. 既存 ADR・仕様

- ADR-1018（public 機微表の RLS 段階導入）Decision 1・段階③。docs/specs/tenant-rls/README.md。
- ADR-072（commit 直後に reset_tenant_context）。ADR-145（products の 4 ポリシーの手本）。
- 段階③草案: docs/handoff/s1-rls-stage3/design-draft.md。

## 1. 本番の現在地（2026-10-16 読取のみ）

| 表 | 行数 | RLS | ポリシー |
|---|---|---|---|
| tenant_paypal_config | 1 | f/f | 0 |
| registration_tokens | 5（全行 tenant 4） | f/f | 0 |

出典: /tmp/CC報告ファイル/s1-stage3/db-rls-flags.txt、db-policies.txt、db-counts 系。

## 2. 表の定義

- tenant_paypal_config: migrations/20260610_071110_add_paypal_config.sql:15-24。`tenant_id INTEGER NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE`（:17）。webhook_id は migrations/20260611_150000_add_paypal_webhook_id.sql:14-17。
- registration_tokens: migrations/20260604_080000_create_registration_tokens.sql:6-16。`tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE`（:8）。
- 【事実】両表とも tenant_id は NOT NULL＝共通行（tenant_id 空）は存在しえない。
- 【事実】この 2 表を参照する外部キーは他に無い（全リポジトリの参照一覧 grep_paypal.txt・grep_regtoken.txt に REFERENCES 行 0 件）。

## 3. 書込の全経路（origin/main）

| # | 書込 file:line | 呼出元 | 書込時の会社文脈 |
|---|---|---|---|
| W1 | backend/app/services/paypal_payments.py:94 INSERT…ON CONFLICT DO UPDATE（commit :114） | backend/app/routers/integrations.py:551（PUT /integrations/paypal/credentials） | あり（integrations.py:541 get_current_tenant → backend/app/auth/dependencies.py:309-316） |
| W2 | backend/app/services/paypal_payments.py:430 UPDATE webhook_id（commit :434） | backend/app/routers/integrations.py:562（同じ PUT の中、W1 の commit の後） | **不確実**。W1 の commit（paypal_payments.py:114）の後に文脈を張り直していない。張り直しは integrations.py:567（W2 の後） |
| W3 | backend/app/services/paypal_payments.py:119 DELETE（commit :122） | backend/app/routers/integrations.py:580（DELETE /integrations/paypal/credentials） | あり（integrations.py:575） |
| W4 | backend/app/services/registration_token.py:77 INSERT | backend/app/routers/registration_tokens.py:122（POST /registration-tokens、commit :142） | あり（registration_tokens.py:75 get_current_tenant） |
| W5 | backend/app/services/registration_token.py:157 UPDATE used_at | backend/app/routers/registration_tokens.py:349（POST /public/register、commit :351） | あり（:235 set_tenant_context。:236-348 の間は db.execute のみで commit 無し） |
| W6 | 同上 | backend/app/routers/registration_tokens.py:438（POST /public/register/address、commit :440） | あり（:388。間に commit 無し） |
| W7 | 同上 | backend/app/routers/registration_tokens.py:560（POST /public/register/change-billing、commit :562） | あり（:483。間に commit 無し） |
| W8 | 外部キー連鎖削除（ON DELETE CASCADE） | backend/app/routers/super_admin_tenants.py の物理削除（`DELETE FROM public.tenants` をアプリ接続 db で実行） | 運営画面。連鎖削除に RLS が掛かるかは下記 §5 |

- 【事実】W2 の危険: dependencies.py:404-408 のとおり、commit 後は別の接続が払い出されうる。文脈は `SET`（接続単位）なので、別接続では app.tenant_id が空か別会社の値のままになりうる。書込だけ RLS を付けると、W2 は「静かに 0 行」になりうる（UPDATE の USING 不一致は無言で除外。PostgreSQL docs/16/sql-createpolicy）。
- 【事実】運営（operator）文脈で 2 表に書く経路は無い。Celery・scripts からの参照も無い（全リポジトリ参照一覧に backend/app/tasks・scripts は run_all_migrations.sh 以外 0 件）。

## 4. 読取の全経路（書込だけ RLS では影響なし。SELECT ポリシーは全行可にする）

- paypal_payments.py:54（get_status）・:68（get_credentials）・:420（get_webhook_id）。get_credentials の呼出元 integrations.py:594/:632/:784/:914/:988、invoices.py:613。
- integrations.py:983 PayPal 不服申立 Webhook が全行を読む（会社文脈なし・設計どおり :913）。
- registration_token.py:125 verify_token（招待リンクを開いた時点・会社文脈なし）。
- SELECT…FOR UPDATE・UPDATE…RETURNING は 0 件。

## 5. PostgreSQL の仕様（公式 docs/16 を直接確認。Context7 は月間上限で利用不可）

- ddl-rowsecurity: 「Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security」。FORCE で所有者にも適用。
- sql-createpolicy: INSERT…ON CONFLICT DO UPDATE は SELECT ポリシーでも検査し、UPDATE 経路で既存行が USING を満たさなければ**エラー**（無言で避けない）。単独 UPDATE/DELETE の USING 不一致は**無言で 0 行**。WITH CHECK 不一致はエラー。
- 【未確認】外部キーの「連鎖削除（CASCADE）」自体が RLS を通らないことは、上の文言（checks・references）だけでは明記されていない → 試験で実測する（設計 §3 試験⑥）。

## 6. 試験・CI の前提

- backend/tests/conftest.py は SQLite 用定義あり（:991 tenant_paypal_config、:1319 registration_tokens）。RLS 試験は ②b と同じく実 PostgreSQL（backend/tests/test_suppliers_rls.py の型）。
- scripts/run_all_migrations.sh に 3 本とも登録済み（:297・:381・:384・:385）。.github/workflows/migration-test.yml に registration_tokens の最小定義（:616・:1581）。tenant_paypal_config は run_all_migrations.sh 経由で作られる。
- ②b の型: migrations/20261016_020000_add_suppliers_rls.sql（4 ポリシー）、`_operator_writes`（backend/app/routers/super_admin_suppliers.py:57-72）。
