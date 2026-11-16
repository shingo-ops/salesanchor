# card: 便2-2c1 発行元の会社情報と振込先の表を作る（ADR-1061）

状態: カード発行（Opus、2026-11-12）。PO の設計承認と実装承認は 2026-11-12「1、推測は禁止して…確立したなら進める。」（ideal-state 54。review.md「2026-11-12 PO の設計承認」）。
設計: docs/handoff/viewer-contract-stage/design.md §3-4（発行元の会社情報・振込先・請求書の発行元区分・海外用の保存フォルダ）・§8。ADR-1061。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `81f0f031e`（便2-2b #5446 合流後）で行番号を測った。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
危険便か: はい（`migrations/` に新しい SQL を足し、毎回流れる分類表の SQL と `scripts/migration-guard/reference-allowlist.tsv`・`scripts/run_all_migrations.sh` を変える）。マージ前に Opus の審査役の APPROVE・CI 全通過・ADR-136 の GO 記録と直前のバックアップの確認を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 この便は「表と列を作るだけ」。画面・API・請求書の出し分けは便2-2c2 と便2-2c3 で行う。値は入れない（ADR-155）。
- D2 会社ごとのスキーマに4表を作る: 発行元の会社情報 `tenant_issuer_profiles`（国内用・海外用の 2 行まで）・振込先の一覧 `tenant_invoice_payment_methods`・銀行の詳細 `tenant_invoice_payment_bank`・Wise の詳細 `tenant_invoice_payment_wise`。詳細の表は一覧の (id, tenant_id, method_type) を外部キーで指し、銀行の行に Wise の詳細が付かない形にする。一覧の行を消すと詳細も消える（ON DELETE CASCADE）。
- D3 請求書 `invoices` に発行元区分 `issuer_region`（domestic / overseas・NULL 可）を足す。public の Drive 設定 `tenant_google_drive_config` に海外用フォルダ `overseas_folder_id` を足す。
- D4 新しい会社は backend/app/services/tenant.py の `_TENANT_TABLES_SQL`・`_RLS_ENABLE_SQL`・`_RLS_POLICY_SQL` で同じ形に作る（移行ファイルと tenant.py の形が同じことは新しい PG 試験が確かめる）。
- D5 発行元の表は public.countries と public.prefectures を外部キーで指す。そのため、試験の土台（backend/tests/rls_bootstrap.py の `_PG_AFTER_TENANTS_MIGRATIONS`）に国の表・閲覧者の表・便2-2a の public 9表の移行を足す（tenant.py がテナントを作る前に在る必要がある）。CI の schema-check と migration-test にも同じ前提の手順を足す（便2-2b 改訂1 の教訓）。
- D6 分類表（migrations/20261024_100300_create_ai_cloud_views.sql）に 33 列分を足す（会社ごとの 11 行 32 列と、public の Drive 設定の行に 1 列）。口座番号 `bank_account_number` と `iban` は列名の拒否の一覧（便2-2b）に当たって読めないので行を持たない。区分の列（CHECK の名前が付いている）は allow、通貨は文字の形の決まりだけなので mask（先例 `accuracy_gold_versions.gold_version`）、ほかの文字の列は mask。1109 を 1142 にする。
- D7 分類表のファイルは reference-allowlist.tsv:7 に sha256 で登録されているので、同じ変更で sha256 と4列目を直す。4列目の最後に ` / viewer-contract-stage card-2-2c1（分類33行追加）` を足す。
- D8 public の表の許可リスト（.github/workflows/migration-guard.yml の PUBLIC_TABLES）に `countries` が無い（2026-11-12 に 81f0f031e で 0 件）。土台の試験で国の表を作るので足す。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（発行元の会社情報と振込先の表と列を作る。D1） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/viewer-contract-bin2-2c1` を作る） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順8 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P2〜P12 は 81f0f031e で実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文。sha256 だけは手順4 で測った値を入れる） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED viewer-contract-bin2-2c1 HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便2-2c1 発行元の会社情報と振込先の表を作る の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/viewer-contract-stage/card-2-2c1.md`（このカード）が枝に在る。
- P2 `ls migrations | sort | tail -1` が `20261112_150000_create_viewer_contract_public_tables.sql`。
- P3 `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の値と `sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2` が、どちらも `444ad4bb1b196f4b57f98e866a20eeafddc6d20a739b6bbabd01345263393125`。
- P4 `grep -c "1109"` が migrations/20261024_100300_create_ai_cloud_views.sql と backend/tests/ops/test_ai_cloud_views.py でそれぞれ 1。
- P5 `grep -c -E "tenant_issuer_profiles|tenant_invoice_payment|issuer_region|overseas_folder_id"` が backend/app/services/tenant.py・migrations/20261024_100300_create_ai_cloud_views.sql・backend/tests/rls_bootstrap.py でそれぞれ 0。
- P6 `grep -c "963"` が backend/tests/rls_bootstrap.py と backend/tests/test_tenant_loop_migration_guard.py でそれぞれ 0。
- P7 `grep -c "    void_reason VARCHAR(500),"` が backend/app/services/tenant.py で 1。`grep -c "CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)"` が 1。
- P8 `grep -c "ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;"` が backend/app/services/tenant.py で 2。`grep -c "CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory"` が 2。
- P9 `grep -c ' countries"' .github/workflows/migration-guard.yml` が 0。`grep -c 'viewer_invoice_lines"$' .github/workflows/migration-guard.yml` が 1。
- P10 `grep -c "変更 SQL を 1回目実行（実行可否・構文チェック）" .github/workflows/migration-test.yml` が 1。`grep -c "Create customer statuses master" .github/workflows/schema-check.yml` が 1。
- P11 `grep -c "run_sql migrations/20261112_150000_create_viewer_contract_public_tables.sql" scripts/run_all_migrations.sh` が 1。
- P12 `ls migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql` が「無い」（exit 2）。`ls backend/tests/test_tenant_issuer_tables_pg.py` も「無い」。

## 1. 触るファイル

1. migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql（新規）
2. backend/app/services/tenant.py（4か所に足す）
3. migrations/20261024_100300_create_ai_cloud_views.sql（説明1行・分類の行1行を直し、11行を足す）
4. scripts/migration-guard/reference-allowlist.tsv（7行目の sha256 と4列目）
5. scripts/run_all_migrations.sh（2行足す）
6. .github/workflows/migration-test.yml（手順を1つ足す）
7. .github/workflows/schema-check.yml（手順を1つ足す）
8. .github/workflows/migration-guard.yml（1語足す）
9. backend/tests/rls_bootstrap.py（2か所）
10. backend/tests/test_tenant_loop_migration_guard.py（2か所）
11. backend/tests/ops/test_ai_cloud_views.py（数1か所と試験1本）
12. backend/tests/test_tenant_issuer_tables_pg.py（新規）

触らない: docs/ 全部・frontend/・backend/app のほかのファイル・migrations のほかのファイル・.github/workflows のほかのファイル（特に workflow-lint.yml）。

## 2. 変更

### 2-1. migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql（新規。全文）

```sql
-- viewer-contract-stage 2-2c1: 発行元の会社情報と振込先の表 4 つ、請求書の発行元区分の列、海外用の保存フォルダの列を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/viewer-contract-stage/design.md §3-4（ADR-1061）
-- 中身（各テナントのスキーマ）:
--   tenant_issuer_profiles           発行元の会社情報（国内用・海外用の 2 行まで）
--   tenant_invoice_payment_methods   振込先の一覧（銀行・Wise）
--   tenant_invoice_payment_bank      銀行振込先の詳細
--   tenant_invoice_payment_wise      Wise 振込先の詳細
--   invoices.issuer_region           請求書がどちらの発行元で出たか（domestic / overseas）
-- 中身（public）:
--   tenant_google_drive_config.overseas_folder_id   海外用の保存フォルダの番号
-- ADR-155: 構造変更のみ。値は入れない。
-- GRANT は ALTER DEFAULT PRIVILEGES（20260605_040000）で自動付与される。
-- 新しい会社のスキーマは backend/app/services/tenant.py の _TENANT_TABLES_SQL で同じ形に作る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP TABLE IF EXISTS <tenant>.tenant_invoice_payment_wise;
--   DROP TABLE IF EXISTS <tenant>.tenant_invoice_payment_bank;
--   DROP TABLE IF EXISTS <tenant>.tenant_invoice_payment_methods;
--   DROP TABLE IF EXISTS <tenant>.tenant_issuer_profiles;
--   ALTER TABLE <tenant>.invoices DROP CONSTRAINT IF EXISTS chk_invoices_issuer_region;
--   ALTER TABLE <tenant>.invoices DROP COLUMN IF EXISTS issuer_region;
--   ALTER TABLE public.tenant_google_drive_config DROP COLUMN IF EXISTS overseas_folder_id;

DO $$
DECLARE
    r RECORD;
    tid INT;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        tid := regexp_replace(r.nspname, '\D', '', 'g')::INT;

        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_issuer_profiles (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                region VARCHAR(20) NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                website VARCHAR(255),
                country_code CHAR(2) NOT NULL REFERENCES public.countries(code),
                postal_code VARCHAR(10),
                prefecture_code CHAR(2) REFERENCES public.prefectures(code),
                state_region TEXT,
                city TEXT NOT NULL,
                address1 TEXT NOT NULL,
                address2 TEXT,
                phone VARCHAR(16),
                is_invoice_registered BOOLEAN NOT NULL DEFAULT FALSE,
                registration_number VARCHAR(14),
                updated_by_user_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_tenant_issuer_profiles_tenant_region UNIQUE (tenant_id, region),
                CONSTRAINT chk_tenant_issuer_profiles_region CHECK (region IN (''domestic'', ''overseas'')),
                CONSTRAINT chk_tenant_issuer_profiles_company_name CHECK (btrim(company_name) <> ''''),
                CONSTRAINT chk_tenant_issuer_profiles_city CHECK (btrim(city) <> ''''),
                CONSTRAINT chk_tenant_issuer_profiles_address1 CHECK (btrim(address1) <> ''''),
                CONSTRAINT chk_tenant_issuer_profiles_jp_address CHECK (country_code <> ''JP'' OR (postal_code IS NOT NULL AND postal_code ~ ''^[0-9]{7}$'' AND prefecture_code IS NOT NULL AND state_region IS NULL)),
                CONSTRAINT chk_tenant_issuer_profiles_foreign_address CHECK (country_code = ''JP'' OR (prefecture_code IS NULL AND (postal_code IS NULL OR postal_code ~ ''^[0-9A-Za-z -]{1,10}$''))),
                CONSTRAINT chk_tenant_issuer_profiles_phone CHECK (phone IS NULL OR (country_code = ''JP'' AND phone ~ ''^[0-9]{10,11}$'') OR (country_code <> ''JP'' AND phone ~ ''^\+[0-9]{6,15}$'')),
                CONSTRAINT chk_tenant_issuer_profiles_registration CHECK ((is_invoice_registered AND registration_number IS NOT NULL AND registration_number ~ ''^T[0-9]{13}$'') OR (NOT is_invoice_registered AND registration_number IS NULL))
            )',
            r.nspname, tid
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_invoice_payment_methods (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                region VARCHAR(20) NOT NULL,
                method_type VARCHAR(10) NOT NULL,
                display_name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                updated_by_user_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type),
                CONSTRAINT chk_tenant_invoice_payment_methods_region CHECK (region IN (''domestic'', ''overseas'')),
                CONSTRAINT chk_tenant_invoice_payment_methods_method_type CHECK (method_type IN (''bank'', ''wise'')),
                CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> '''')
            )',
            r.nspname, tid
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_invoice_payment_bank (
                payment_method_id INTEGER PRIMARY KEY,
                method_type VARCHAR(10) NOT NULL DEFAULT ''bank'',
                tenant_id INTEGER NOT NULL DEFAULT %s,
                account_holder TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                bank_branch TEXT NOT NULL,
                bank_account_type TEXT NOT NULL,
                bank_account_number TEXT NOT NULL,
                swift_code TEXT,
                bank_address TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_invoice_payment_bank_method_type CHECK (method_type = ''bank''),
                CONSTRAINT chk_tenant_invoice_payment_bank_required CHECK (btrim(account_holder) <> '''' AND btrim(bank_name) <> '''' AND btrim(bank_branch) <> '''' AND btrim(bank_account_type) <> '''' AND btrim(bank_account_number) <> ''''),
                CONSTRAINT fk_tenant_invoice_payment_bank_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES %I.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
            )',
            r.nspname, tid, r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_invoice_payment_wise (
                payment_method_id INTEGER PRIMARY KEY,
                method_type VARCHAR(10) NOT NULL DEFAULT ''wise'',
                tenant_id INTEGER NOT NULL DEFAULT %s,
                account_holder TEXT NOT NULL,
                wise_currency CHAR(3) NOT NULL,
                wise_email VARCHAR(255) NOT NULL,
                iban TEXT,
                swift_bic TEXT,
                bank_name TEXT,
                bank_address TEXT,
                note TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_invoice_payment_wise_method_type CHECK (method_type = ''wise''),
                CONSTRAINT chk_tenant_invoice_payment_wise_currency CHECK (wise_currency ~ ''^[A-Z]{3}$''),
                CONSTRAINT chk_tenant_invoice_payment_wise_required CHECK (btrim(account_holder) <> '''' AND btrim(wise_email) <> ''''),
                CONSTRAINT fk_tenant_invoice_payment_wise_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES %I.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
            )',
            r.nspname, tid, r.nspname
        );

        EXECUTE format('ALTER TABLE %I.tenant_issuer_profiles ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_bank ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY', r.nspname);

        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_issuer_profiles_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_issuer_profiles_tenant_isolation ON %I.tenant_issuer_profiles USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_methods_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_invoice_payment_methods_tenant_isolation ON %I.tenant_invoice_payment_methods USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_bank_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_invoice_payment_bank_tenant_isolation ON %I.tenant_invoice_payment_bank USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_wise_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON %I.tenant_invoice_payment_wise USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;

        IF to_regclass(format('%I.invoices', r.nspname)) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS issuer_region VARCHAR(20)', r.nspname);
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_invoices_issuer_region' AND conrelid = to_regclass(format('%I.invoices', r.nspname))) THEN
                EXECUTE format('ALTER TABLE %I.invoices ADD CONSTRAINT chk_invoices_issuer_region CHECK (issuer_region IN (''domestic'', ''overseas''))', r.nspname);
            END IF;
            EXECUTE format('COMMENT ON COLUMN %I.invoices.issuer_region IS %L', r.nspname, '請求書を出した発行元の区分（domestic=国内用 / overseas=海外用。NULL は区分を付ける前の請求書）');
        END IF;

        EXECUTE format('COMMENT ON TABLE %I.tenant_issuer_profiles IS %L', r.nspname, '発行元の会社情報。国内用と海外用の 2 行まで（ADR-1061）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.region IS %L', r.nspname, 'domestic=国内用 / overseas=海外用');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.country_code IS %L', r.nspname, '国の2文字コード（国マスタの code）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.prefecture_code IS %L', r.nspname, '都道府県の2桁コード（日本のときだけ必須）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.state_region IS %L', r.nspname, '海外の州・地域（日本のときは空）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.registration_number IS %L', r.nspname, '適格請求書の登録番号 T+13桁（登録しているときだけ）');
        EXECUTE format('COMMENT ON TABLE %I.tenant_invoice_payment_methods IS %L', r.nspname, '請求書に載せる振込先の一覧（銀行・Wise）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_invoice_payment_methods.method_type IS %L', r.nspname, 'bank=銀行振込 / wise=Wise');
        EXECUTE format('COMMENT ON TABLE %I.tenant_invoice_payment_bank IS %L', r.nspname, '銀行振込先の詳細（振込先の一覧 1 行に 1 行）');
        EXECUTE format('COMMENT ON TABLE %I.tenant_invoice_payment_wise IS %L', r.nspname, 'Wise 振込先の詳細（振込先の一覧 1 行に 1 行）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_invoice_payment_wise.wise_currency IS %L', r.nspname, '受け取る通貨の記号（英大文字3字）');
        RAISE NOTICE 'issuer and payment tables created/verified for schema: %', r.nspname;
    END LOOP;
END $$;

DO $$
BEGIN
    IF to_regclass('public.tenant_google_drive_config') IS NOT NULL THEN
        ALTER TABLE public.tenant_google_drive_config ADD COLUMN IF NOT EXISTS overseas_folder_id TEXT;
        COMMENT ON COLUMN public.tenant_google_drive_config.overseas_folder_id IS '海外用の請求書・見積書を保存する Google ドライブのフォルダの番号（NULL は国内用と同じフォルダ）';
    END IF;
END $$;
```

### 2-2. backend/app/services/tenant.py（4か所。どれも足すだけで、消す行は無い）

(a) 請求書の表。変更前（1か所だけ・:887〜:888）:
```
    void_reason VARCHAR(500),
    notes TEXT,
```
変更後（2行の間に1行足す）:
```
    void_reason VARCHAR(500),
    issuer_region VARCHAR(20) CONSTRAINT chk_invoices_issuer_region CHECK (issuer_region IN ('domestic', 'overseas')),
    notes TEXT,
```

(b) `_TENANT_TABLES_SQL` の最後。変更前（1か所だけ・:1209〜:1211）:
```
    CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)
);
"""
```
変更後（`);` と `"""` の間に、空行で始まる次の 90 行を足す。`{{7}}` などの二重の波かっこと `\\+` はこのファイルの書き方なのでそのまま写す）:
```
    CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)
);

-- ADR-1061 2-2c1: 発行元の会社情報（国内用・海外用の 2 行まで）
CREATE TABLE IF NOT EXISTS {schema}.tenant_issuer_profiles (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    region VARCHAR(20) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    website VARCHAR(255),
    country_code CHAR(2) NOT NULL REFERENCES public.countries(code),
    postal_code VARCHAR(10),
    prefecture_code CHAR(2) REFERENCES public.prefectures(code),
    state_region TEXT,
    city TEXT NOT NULL,
    address1 TEXT NOT NULL,
    address2 TEXT,
    phone VARCHAR(16),
    is_invoice_registered BOOLEAN NOT NULL DEFAULT FALSE,
    registration_number VARCHAR(14),
    updated_by_user_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_issuer_profiles_tenant_region UNIQUE (tenant_id, region),
    CONSTRAINT chk_tenant_issuer_profiles_region CHECK (region IN ('domestic', 'overseas')),
    CONSTRAINT chk_tenant_issuer_profiles_company_name CHECK (btrim(company_name) <> ''),
    CONSTRAINT chk_tenant_issuer_profiles_city CHECK (btrim(city) <> ''),
    CONSTRAINT chk_tenant_issuer_profiles_address1 CHECK (btrim(address1) <> ''),
    CONSTRAINT chk_tenant_issuer_profiles_jp_address CHECK (country_code <> 'JP' OR (postal_code IS NOT NULL AND postal_code ~ '^[0-9]{{7}}$' AND prefecture_code IS NOT NULL AND state_region IS NULL)),
    CONSTRAINT chk_tenant_issuer_profiles_foreign_address CHECK (country_code = 'JP' OR (prefecture_code IS NULL AND (postal_code IS NULL OR postal_code ~ '^[0-9A-Za-z -]{{1,10}}$'))),
    CONSTRAINT chk_tenant_issuer_profiles_phone CHECK (phone IS NULL OR (country_code = 'JP' AND phone ~ '^[0-9]{{10,11}}$') OR (country_code <> 'JP' AND phone ~ '^\\+[0-9]{{6,15}}$')),
    CONSTRAINT chk_tenant_issuer_profiles_registration CHECK ((is_invoice_registered AND registration_number IS NOT NULL AND registration_number ~ '^T[0-9]{{13}}$') OR (NOT is_invoice_registered AND registration_number IS NULL))
);

-- ADR-1061 2-2c1: 請求書に載せる振込先の一覧（銀行・Wise）
CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_methods (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    region VARCHAR(20) NOT NULL,
    method_type VARCHAR(10) NOT NULL,
    display_name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by_user_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type),
    CONSTRAINT chk_tenant_invoice_payment_methods_region CHECK (region IN ('domestic', 'overseas')),
    CONSTRAINT chk_tenant_invoice_payment_methods_method_type CHECK (method_type IN ('bank', 'wise')),
    CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> '')
);

-- ADR-1061 2-2c1: 銀行振込先の詳細（振込先の一覧 1 行に 1 行）
CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_bank (
    payment_method_id INTEGER PRIMARY KEY,
    method_type VARCHAR(10) NOT NULL DEFAULT 'bank',
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    account_holder TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    bank_branch TEXT NOT NULL,
    bank_account_type TEXT NOT NULL,
    bank_account_number TEXT NOT NULL,
    swift_code TEXT,
    bank_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_invoice_payment_bank_method_type CHECK (method_type = 'bank'),
    CONSTRAINT chk_tenant_invoice_payment_bank_required CHECK (btrim(account_holder) <> '' AND btrim(bank_name) <> '' AND btrim(bank_branch) <> '' AND btrim(bank_account_type) <> '' AND btrim(bank_account_number) <> ''),
    CONSTRAINT fk_tenant_invoice_payment_bank_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
);

-- ADR-1061 2-2c1: Wise 振込先の詳細（振込先の一覧 1 行に 1 行）
CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_wise (
    payment_method_id INTEGER PRIMARY KEY,
    method_type VARCHAR(10) NOT NULL DEFAULT 'wise',
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    account_holder TEXT NOT NULL,
    wise_currency CHAR(3) NOT NULL,
    wise_email VARCHAR(255) NOT NULL,
    iban TEXT,
    swift_bic TEXT,
    bank_name TEXT,
    bank_address TEXT,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_invoice_payment_wise_method_type CHECK (method_type = 'wise'),
    CONSTRAINT chk_tenant_invoice_payment_wise_currency CHECK (wise_currency ~ '^[A-Z]{{3}}$'),
    CONSTRAINT chk_tenant_invoice_payment_wise_required CHECK (btrim(account_holder) <> '' AND btrim(wise_email) <> ''),
    CONSTRAINT fk_tenant_invoice_payment_wise_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
);
"""
```

(c) `_RLS_ENABLE_SQL` の最後。`ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;` は2か所（:1260 と :1263）にあるので、前の行の説明と組で探す。変更前（1か所だけ・:1262〜:1264）:
```
-- D-2: A在庫（ADR SA-04/05）
ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;
"""
```
変更後:
```
-- D-2: A在庫（ADR SA-04/05）
ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;
-- ADR-1061 2-2c1: 発行元の会社情報と振込先
ALTER TABLE {schema}.tenant_issuer_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_invoice_payment_methods ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_invoice_payment_bank ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY;
"""
```

(d) `_RLS_POLICY_SQL` の最後。own_inventory のポリシーの文は2か所（:1329 と :1487）にあるので、`END $$` と組で探す。変更前（1か所だけ・:1487〜:1490）:
```
        CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
END $$
```
変更後（`    END IF;` と `END $$` の間に 17 行足す）:
```
        CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- ADR-1061 2-2c1: 発行元の会社情報と振込先 — ポリシー名は migration 20261112_160000 と同じ
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_issuer_profiles_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_issuer_profiles_tenant_isolation ON {schema}.tenant_issuer_profiles
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_methods_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_invoice_payment_methods_tenant_isolation ON {schema}.tenant_invoice_payment_methods
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_bank_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_invoice_payment_bank_tenant_isolation ON {schema}.tenant_invoice_payment_bank
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_wise_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON {schema}.tenant_invoice_payment_wise
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
END $$
```

### 2-3. migrations/20261024_100300_create_ai_cloud_views.sql（4か所）

(1) :3

変更前:
```
-- 1) 分類表 ai_cloud_meta.column_class を空にして下の 1109 行を入れ直す（このファイルが正本。行の足し引きはこの SQL の変更で行う）。
```
変更後:
```
-- 1) 分類表 ai_cloud_meta.column_class を空にして下の 1142 行を入れ直す（このファイルが正本。行の足し引きはこの SQL の変更で行う）。
```

(2) :290（Drive 設定の行に海外用フォルダを足す）

変更前:
```
  ('public','tenant_google_drive_config',ARRAY['account_email','folder_id'],'mask',''),
```
変更後:
```
  ('public','tenant_google_drive_config',ARRAY['account_email','folder_id','overseas_folder_id'],'mask',''),
```

(3) :441 の行の後ろに1行足す。

変更前:
```
  ('tenant_*','invoices',ARRAY['issue_mode'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
  ('tenant_*','invoices',ARRAY['notes'],'mask',''),
```
変更後:
```
  ('tenant_*','invoices',ARRAY['issue_mode'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
  ('tenant_*','invoices',ARRAY['issuer_region'],'allow','値の決まり chk_invoices_issuer_region で値が限られる'),
  ('tenant_*','invoices',ARRAY['notes'],'mask',''),
```

(4) :593 の行の後ろに10行足す。

変更前:
```
  ('tenant_*','tenant_commission_settings',ARRAY['commission_rates'],'mask',''),
  ('tenant_*','tenant_meta_config',ARRAY['granted_scopes','instagram_business_account_id','instagram_username','notes','page_id','page_name','subscribed_fields'],'mask',''),
```
変更後:
```
  ('tenant_*','tenant_commission_settings',ARRAY['commission_rates'],'mask',''),
  ('tenant_*','tenant_invoice_payment_bank',ARRAY['account_holder','bank_account_type','bank_address','bank_branch','bank_name','swift_code'],'mask',''),
  ('tenant_*','tenant_invoice_payment_bank',ARRAY['method_type'],'allow','値の決まり chk_tenant_invoice_payment_bank_method_type で値が限られる'),
  ('tenant_*','tenant_invoice_payment_methods',ARRAY['display_name'],'mask',''),
  ('tenant_*','tenant_invoice_payment_methods',ARRAY['method_type'],'allow','値の決まり chk_tenant_invoice_payment_methods_method_type で値が限られる'),
  ('tenant_*','tenant_invoice_payment_methods',ARRAY['region'],'allow','値の決まり chk_tenant_invoice_payment_methods_region で値が限られる'),
  ('tenant_*','tenant_invoice_payment_wise',ARRAY['account_holder','bank_address','bank_name','note','swift_bic','wise_email'],'mask',''),
  ('tenant_*','tenant_invoice_payment_wise',ARRAY['method_type'],'allow','値の決まり chk_tenant_invoice_payment_wise_method_type で値が限られる'),
  ('tenant_*','tenant_invoice_payment_wise',ARRAY['wise_currency'],'mask','値の決まりが値の一覧でなく文字の形だけのため伏せる（初期は最小）'),
  ('tenant_*','tenant_issuer_profiles',ARRAY['address1','address2','city','company_name','country_code','email','phone','postal_code','prefecture_code','registration_number','state_region','website'],'mask',''),
  ('tenant_*','tenant_issuer_profiles',ARRAY['region'],'allow','値の決まり chk_tenant_issuer_profiles_region で値が限られる'),
  ('tenant_*','tenant_meta_config',ARRAY['granted_scopes','instagram_business_account_id','instagram_username','notes','page_id','page_name','subscribed_fields'],'mask',''),
```

### 2-4. scripts/migration-guard/reference-allowlist.tsv（7行目。手順4 で行う）

(1) 2列目の `444ad4bb1b196f4b57f98e866a20eeafddc6d20a739b6bbabd01345263393125` を、手順4 で測った 2-3 の後の sha256（64 文字）に置き換える。
(2) 4列目（行の最後）の `viewer-contract-stage card-2-2b（分類23行追加）` を `viewer-contract-stage card-2-2b（分類23行追加） / viewer-contract-stage card-2-2c1（分類33行追加）` に置き換える。タブの数は変えない（列は4つのまま）。

### 2-5. scripts/run_all_migrations.sh（:1265 の後ろに2行足す）

変更前:
```
run_sql migrations/20261112_150000_create_viewer_contract_public_tables.sql
```
変更後:
```
run_sql migrations/20261112_150000_create_viewer_contract_public_tables.sql
# ADR-1061 便2-2c1: 発行元の会社情報と振込先の4表・請求書の発行元区分・Drive の海外用フォルダを作る（形だけ・行なし・冪等）
run_sql migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql
```

### 2-6. .github/workflows/migration-test.yml（手順を1つ足す）

変更前（この行は1か所だけ。81f0f031e で :1410）:

          - name: 変更 SQL を 1回目実行（実行可否・構文チェック）

この行の直前に、次の10行（最後は空行）を足す:

          - name: 変更 SQL の前提の移行を先に実行（国と都道府県の表）
            if: steps.detect.outputs.has_sql_changes == 'true' && contains(steps.detect.outputs.changed_sql, 'migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql')
            run: |
              # 20261112_160000 は public.countries（20260621_010000）と public.prefectures（20261112_150000）を外部キーで指すので、本番と同じ順で先に作る
              for sqlfile in migrations/20260621_010000_create_countries_master.sql migrations/20261112_150000_create_viewer_contract_public_tables.sql; do
                echo "▶ $sqlfile を前提として実行中..."
                psql -h localhost -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -f "$sqlfile"
                echo "✅ $sqlfile 成功"
              done

（上の表示は本文の字下げとして全体に4文字の空白が付いている。ファイルに入れるときは各行の先頭4文字を除く。つまり `- name:` は6文字、`if:` と `run: |` は8文字、`#` と `for` と `done` は10文字、`echo` と `psql` は12文字の空白で始まる。すぐ上にある「変更 SQL の前提の移行を先に実行（会社と連絡先の状態の表）」の手順と同じ形。）

### 2-7. .github/workflows/schema-check.yml（手順を1つ足す）

変更前（この行は1か所だけ。81f0f031e で :171）:

          # public.permissions に最低限のデータを seed する（migration 042 の依存）

この行の直前に、次の13行（最後は空行）を足す:

          # public.countries と public.prefectures（tenant_NNN.tenant_issuer_profiles の外部キーの参照先・ADR-1061 便2-2c1）
          # 新しい会社の作り方（tenant.py）が参照するので、テナントを作る前に本物の migration で作る（行は入れない）
          - name: Create countries and prefectures masters
            env:
              PGPASSWORD: testpass
            run: |
              psql -h localhost -U jarvis -d jarvis_schema_check_db -v ON_ERROR_STOP=1 \
                -f migrations/20260621_010000_create_countries_master.sql
              psql -h localhost -U jarvis -d jarvis_schema_check_db -v ON_ERROR_STOP=1 \
                -f migrations/20261016_150000_add_viewer_accounts.sql
              psql -h localhost -U jarvis -d jarvis_schema_check_db -v ON_ERROR_STOP=1 \
                -f migrations/20261112_150000_create_viewer_contract_public_tables.sql

（字下げは 2-6 と同じく表示の4文字を除く。`#` と `- name:` は6文字、`env:` と `run: |` は8文字、`PGPASSWORD:` と `psql` は10文字、`-f` は12文字。すぐ上の「Create customer statuses master」の手順と同じ形。）

### 2-8. .github/workflows/migration-guard.yml（:228 の行の最後）

変更前（行の最後の部分。この並びは1か所だけ）:
```
viewer_invoices viewer_invoice_number_seq viewer_invoice_lines"
```
変更後:
```
viewer_invoices viewer_invoice_number_seq viewer_invoice_lines countries"
```

### 2-9. backend/tests/rls_bootstrap.py（2か所）

(1) :41〜:44

変更前:
```
_PG_AFTER_TENANTS_MIGRATIONS = (
    "20261106_190000_create_public_channel_masters.sql",
    "20261112_120000_create_public_customer_statuses.sql",
)
```
変更後:
```
_PG_AFTER_TENANTS_MIGRATIONS = (
    "20261106_190000_create_public_channel_masters.sql",
    "20261112_120000_create_public_customer_statuses.sql",
    # ADR-1061 便2-2c1: 発行元の会社情報が public.countries と public.prefectures を外部キーで指す。
    # prefectures を作る 20261112_150000 は public.viewer_accounts（20261016_150000）を指すので、この順で流す
    "20260621_010000_create_countries_master.sql",
    "20261016_150000_add_viewer_accounts.sql",
    "20261112_150000_create_viewer_contract_public_tables.sql",
)
```

(2) :183 の行の後ろに1行足す。

変更前:
```
    "20261106_150000_add_discord_role_link_tables.sql": 1,
```
変更後:
```
    "20261106_150000_add_discord_role_link_tables.sql": 1,
    "20261112_160000_create_tenant_issuer_and_payment_tables.sql": 1,
```

### 2-10. backend/tests/test_tenant_loop_migration_guard.py（2か所）

(1) `rls_bootstrap.py` の組の集合の最後（:50）。`"20261106_150000_add_discord_role_link_tables.sql",` の行はこのファイルに1か所だけ（:105 は `frozenset({...})` の中で行の形が違う）。

変更前:
```
                "20261106_150000_add_discord_role_link_tables.sql",
            }
        ),
```
変更後:
```
                "20261106_150000_add_discord_role_link_tables.sql",
                "20261112_160000_create_tenant_issuer_and_payment_tables.sql",
            }
        ),
```

(2) :102〜:106 の組の後ろに5行足す。

変更前:
```
    "test_discord_role_link_ddl.py": (
        "scoped",
        "",
        frozenset({"20261106_150000_add_discord_role_link_tables.sql"}),
    ),
```
変更後:
```
    "test_discord_role_link_ddl.py": (
        "scoped",
        "",
        frozenset({"20261106_150000_add_discord_role_link_tables.sql"}),
    ),
    "test_tenant_issuer_tables_pg.py": (
        "scoped",
        "",
        frozenset({"20261112_160000_create_tenant_issuer_and_payment_tables.sql"}),
    ),
```

### 2-11. backend/tests/ops/test_ai_cloud_views.py（2か所）

(1) :486

変更前:
```
    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1109
```
変更後:
```
    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1142
```

(2) `def test_t10_detects_added_columns(pg):`（:815。1か所だけ）の行の直前に、次の文と空行2つを足す（この文の最後の行の後ろに空行2つ、その次が `def test_t10_detects_added_columns(pg):`）。

```python
# ADR-1061 便2-2c1: 発行元の会社情報と振込先のテナントの4表・請求書の発行元区分・Drive の海外用フォルダに column_class の行があることを名前で確かめる。
_ISSUER_TABLES = {
    "tenant_issuer_profiles", "tenant_invoice_payment_methods",
    "tenant_invoice_payment_bank", "tenant_invoice_payment_wise",
}  # fmt: skip
_ISSUER_CLASSIFIED = (
    {("tenant_issuer_profiles", c) for c in (
        "address1", "address2", "city", "company_name", "country_code", "email", "phone",
        "postal_code", "prefecture_code", "registration_number", "state_region", "website", "region",
    )}
    | {("tenant_invoice_payment_methods", c) for c in ("display_name", "method_type", "region")}
    | {("tenant_invoice_payment_bank", c) for c in (
        "account_holder", "bank_account_type", "bank_address", "bank_branch", "bank_name", "swift_code", "method_type",
    )}
    | {("tenant_invoice_payment_wise", c) for c in (
        "account_holder", "bank_address", "bank_name", "note", "swift_bic", "wise_email", "method_type", "wise_currency",
    )}
    | {("invoices", "issuer_region")}
)  # fmt: skip


def test_t10_issuer_columns_are_classified_on_bootstrapped_db(cluster):
    """新しい会社の作り方（tenant.py）で作ったテナントに、便2-2c1 の 32 列の column_class の行があり、4表と請求書の発行元区分に分類の漏れが無い。

    口座番号（bank_account_number）と IBAN（iban）は名前の決まりで読めない列なので分類の行を持たない。
    public の Drive 設定の海外用フォルダ（overseas_folder_id）の行もあることを確かめる。専用の DB を作り、終わったら消す。"""
    from sqlalchemy.ext.asyncio import create_async_engine

    assert len(_ISSUER_CLASSIFIED) == 32
    name, conn = _new_db(cluster.control, "ai_cloud_t10_issuer")
    try:
        c = conn.cursor()
        c.execute(_read(_AI_READER_SQL))
        c.execute(_read(_ROLE_SQL))
        c.execute(_read(_META_SQL))
        url = _psycopg_url(ADMIN_PG_URL, name).replace("postgresql://", "postgresql+asyncpg://", 1)
        from tests.rls_bootstrap import bootstrap_tenant_schema

        async def build():
            eng = create_async_engine(url)
            try:
                await bootstrap_tenant_schema(eng, 1)
            finally:
                await eng.dispose()

        asyncio.run(build())
        c.execute(_read(_CREATE_SQL))
        rows = _rows(
            conn, "SELECT table_name, column_name FROM ai_cloud_meta.column_class WHERE schema_pattern = 'tenant_*'"
        )
        have = {(r[0], r[1]) for r in rows}
        missing = _ISSUER_CLASSIFIED - have
        assert missing == set(), f"column_class に行が無い: {sorted(missing)}"
        drive = _rows(
            conn,
            "SELECT 1 FROM ai_cloud_meta.column_class WHERE schema_pattern = 'public'"
            " AND table_name = 'tenant_google_drive_config' AND column_name = 'overseas_folder_id'",
        )
        assert len(drive) == 1

        gaps = [
            g for g in _classification_gaps(conn)
            if g[1] in _ISSUER_TABLES or (g[1] == "invoices" and g[2] == "issuer_region")
        ]  # fmt: skip
        assert gaps == [], f"分類の漏れ（表名・列名）: {[(g[1], g[2]) for g in gaps]}"
    finally:
        conn.close()
        cur = cluster.control.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
```

### 2-12. backend/tests/test_tenant_issuer_tables_pg.py（新規。全文）

```python
"""ADR-1061 便2-2c1: 発行元の会社情報と振込先の表 4 つ・請求書の発行元区分の列の構造と決まりの試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に表 4 つと列が含まれ、移行ファイルが登録され、値を入れない。
- PG（CI で実行）: 新テナントを作った形（tenant.py）と、表と列を消して移行ファイルを 2 回流した形が同じ。
  決まり（CHECK・一意・外部キー・消したときの連鎖）が設計どおりに効く。試験の中で入れた行は最後に戻す。
  ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（test_discord_role_link_ddl.py と同じ形）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.services import tenant as tenant_service
from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
    tenant_schema_lock,
)
from tests.seed_data import country_seed_sql, prefectures_seed_sql

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261112_160000_create_tenant_issuer_and_payment_tables.sql"
# 試験・移行のどこにも無い 963 を使う（2026-11-12 に origin/main で git grep して 0 件）
_TENANT_ID = 963
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_TABLES = (
    "tenant_issuer_profiles",
    "tenant_invoice_payment_methods",
    "tenant_invoice_payment_bank",
    "tenant_invoice_payment_wise",
)


def _block(sql: str, marker: str) -> str:
    """marker の直後から、最初の '\\n);' までを返す（表の列定義）。"""
    marker = "CREATE TABLE IF NOT EXISTS " + marker
    assert sql.count(marker) == 1, marker
    body = sql.split(marker)[1]
    return body[: body.index("\n);")]


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def test_tenant_ddl_has_issuer_and_payment_tables():
    sql = tenant_service._TENANT_TABLES_SQL
    invoices = _block(sql, "{schema}.invoices (")
    assert (
        "issuer_region VARCHAR(20) CONSTRAINT chk_invoices_issuer_region"
        " CHECK (issuer_region IN ('domestic', 'overseas')),"
    ) in invoices

    profiles = _block(sql, "{schema}.tenant_issuer_profiles (")
    assert "country_code CHAR(2) NOT NULL REFERENCES public.countries(code)," in profiles
    assert "prefecture_code CHAR(2) REFERENCES public.prefectures(code)," in profiles
    assert "CONSTRAINT uq_tenant_issuer_profiles_tenant_region UNIQUE (tenant_id, region)," in profiles
    for name in ("jp_address", "foreign_address", "phone", "registration"):
        assert f"CONSTRAINT chk_tenant_issuer_profiles_{name} CHECK" in profiles

    methods = _block(sql, "{schema}.tenant_invoice_payment_methods (")
    assert "CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type)," in methods

    for kind in ("bank", "wise"):
        detail = _block(sql, f"{{schema}}.tenant_invoice_payment_{kind} (")
        assert f"method_type VARCHAR(10) NOT NULL DEFAULT '{kind}'," in detail
        assert (
            f"CONSTRAINT fk_tenant_invoice_payment_{kind}_method FOREIGN KEY (payment_method_id, tenant_id, method_type)"
            " REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE"
        ) in detail

    for table in _TABLES:
        assert f"ALTER TABLE {{schema}}.{table} ENABLE ROW LEVEL SECURITY;" in tenant_service._RLS_ENABLE_SQL
        assert f"CREATE POLICY {table}_tenant_isolation ON {{schema}}.{table}" in tenant_service._RLS_POLICY_SQL


def test_migration_file_exists_and_is_registered():
    migration = _REPO_ROOT / "migrations" / _MIGRATION
    assert migration.is_file()
    body = migration.read_text(encoding="utf-8")
    for table in _TABLES:
        assert f"CREATE TABLE IF NOT EXISTS %I.{table} (" in body
        assert f"ALTER TABLE %I.{table} ENABLE ROW LEVEL SECURITY" in body
        assert f"CREATE POLICY {table}_tenant_isolation ON %I.{table}" in body
    assert "ADD COLUMN IF NOT EXISTS issuer_region VARCHAR(20)" in body
    assert "ALTER TABLE public.tenant_google_drive_config ADD COLUMN IF NOT EXISTS overseas_folder_id TEXT;" in body
    runner = (_REPO_ROOT / "scripts" / "run_all_migrations.sh").read_text(encoding="utf-8")
    lines = [line for line in runner.splitlines() if line.startswith("run_sql ")]
    assert lines.count(f"run_sql migrations/{_MIGRATION}") == 1


def test_migration_writes_no_values():
    """ADR-155: 構造変更のみ（INSERT INTO / UPDATE 表 / DELETE FROM を含まない。ON DELETE CASCADE は外部キーの決まり）。"""
    body = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    code = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("--")
    ).upper()
    for word in ("INSERT INTO", "UPDATE %I", "UPDATE PUBLIC.", "DELETE FROM"):
        assert word not in code


async def _shape(conn) -> dict:
    tables = list(_TABLES)
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable, column_default, character_maximum_length"
            " FROM information_schema.columns"
            " WHERE table_schema = :s AND (table_name = ANY(:t)"
            " OR (table_name = 'invoices' AND column_name = 'issuer_region'))"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    constraints = await conn.execute(
        text(
            "SELECT c.relname, con.conname, pg_get_constraintdef(con.oid)"
            " FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND (c.relname = ANY(:t) OR con.conname = 'chk_invoices_issuer_region')"
            " ORDER BY c.relname, con.conname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    policies = await conn.execute(
        text(
            "SELECT tablename, policyname, qual FROM pg_policies"
            " WHERE schemaname = :s AND tablename = ANY(:t) ORDER BY tablename, policyname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    rls = await conn.execute(
        text(
            "SELECT c.relname, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t) ORDER BY c.relname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    return {
        "columns": [tuple(row) for row in columns.all()],
        "constraints": [tuple(row) for row in constraints.all()],
        "policies": [tuple(row) for row in policies.all()],
        "rls": [tuple(row) for row in rls.all()],
    }


_JP = {
    "region": "domestic",
    "company_name": "試験商事",
    "country_code": "JP",
    "postal_code": "1000001",
    "prefecture_code": "13",
    "city": "千代田区",
    "address1": "千代田1-1",
    "phone": "0312345678",
    "is_invoice_registered": True,
    "registration_number": "T1234567890123",
}
_US = {
    "region": "overseas",
    "company_name": "Test Trading",
    "country_code": "US",
    "postal_code": "10001",
    "prefecture_code": None,
    "state_region": "NY",
    "city": "New York",
    "address1": "1 Main St",
    "phone": "+12125550100",
    "is_invoice_registered": False,
    "registration_number": None,
}


async def _insert_profile(conn, row: dict) -> None:
    cols = ", ".join(row)
    vals = ", ".join(f":{k}" for k in row)
    await conn.execute(text(f"INSERT INTO {_SCHEMA}.tenant_issuer_profiles ({cols}) VALUES ({vals})"), row)


async def _expect_error(conn, sql: str, params: dict, code: str) -> None:
    sp = await conn.begin_nested()
    with pytest.raises(DBAPIError) as exc_info:
        await conn.execute(text(sql), params)
    await sp.rollback()
    assert _sqlstate(exc_info.value) == code, sql


async def _expect_profile_error(conn, row: dict, code: str) -> None:
    cols = ", ".join(row)
    vals = ", ".join(f":{k}" for k in row)
    await _expect_error(conn, f"INSERT INTO {_SCHEMA}.tenant_issuer_profiles ({cols}) VALUES ({vals})", row, code)


async def _check_rules(conn) -> None:
    """決まりが効くことを確かめる。呼び出し側の取引は最後に戻す（行を残さない）。"""
    # rls_bootstrap.bootstrap_tenant_schema と同じ流し方（取引の中・運営の印は取引の中だけ）
    await conn.exec_driver_sql(country_seed_sql())
    await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
    await conn.exec_driver_sql(prefectures_seed_sql())
    await conn.execute(text("SELECT set_config('app.is_operator', '', true)"))

    await _insert_profile(conn, _JP)  # 国内用の正しい形は入る
    # 海外用の区分はまだ空なので、次の失敗は一意の決まりではなく、それぞれの決まりで起きる
    other = {**_JP, "region": "overseas"}
    await _expect_profile_error(conn, {**other, "phone": "03-1234-5678"}, "23514")  # 日本の電話は数字だけ
    await _expect_profile_error(conn, {**other, "prefecture_code": None}, "23514")  # 日本は都道府県が要る
    await _expect_profile_error(conn, {**other, "postal_code": "100-0001"}, "23514")  # 日本の郵便番号は7桁の数字
    await _expect_profile_error(conn, {**_US, "prefecture_code": "13"}, "23514")  # 海外に都道府県は入らない
    await _expect_profile_error(conn, {**_US, "phone": "12125550100"}, "23514")  # 海外の電話は + から
    await _expect_profile_error(conn, {**other, "is_invoice_registered": False}, "23514")  # 登録なしに番号は入らない
    await _expect_profile_error(conn, {**other, "registration_number": None}, "23514")  # 登録ありは番号が要る
    await _expect_profile_error(conn, {**other, "region": "asia"}, "23514")  # 区分は国内用・海外用だけ
    await _expect_profile_error(conn, {**_US, "country_code": "ZZ"}, "23503")  # 国の一覧に無い国
    await _insert_profile(conn, _US)  # 海外用の正しい形は入る
    await _expect_profile_error(conn, {**_JP}, "23505")  # 同じ区分は1行まで

    method_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_methods (region, method_type, display_name)"
        " VALUES (:region, :method_type, :display_name) RETURNING id"
    )
    bank_id = (await conn.execute(text(method_sql), {"region": "domestic", "method_type": "bank", "display_name": "銀行"})).scalar_one()
    wise_id = (await conn.execute(text(method_sql), {"region": "overseas", "method_type": "wise", "display_name": "Wise"})).scalar_one()
    await _expect_error(conn, method_sql, {"region": "domestic", "method_type": "paypal", "display_name": "x"}, "23514")

    bank_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_bank"
        " (payment_method_id, account_holder, bank_name, bank_branch, bank_account_type, bank_account_number)"
        " VALUES (:id, 'シケン', '試験銀行', '本店', '普通', '1234567')"
    )
    wise_sql = (
        f"INSERT INTO {_SCHEMA}.tenant_invoice_payment_wise (payment_method_id, account_holder, wise_currency, wise_email)"
        " VALUES (:id, 'Test', :cur, 'pay@example.com')"
    )
    await conn.execute(text(bank_sql), {"id": bank_id})
    await _expect_error(conn, wise_sql, {"id": bank_id, "cur": "USD"}, "23503")  # 銀行の行に Wise の詳細は付かない
    await _expect_error(conn, bank_sql, {"id": wise_id}, "23503")  # Wise の行に銀行の詳細は付かない
    await _expect_error(conn, wise_sql, {"id": wise_id, "cur": "jpy"}, "23514")  # 通貨は英大文字3字
    await conn.execute(text(wise_sql), {"id": wise_id, "cur": "USD"})

    await conn.execute(text(f"DELETE FROM {_SCHEMA}.tenant_invoice_payment_methods WHERE id = :id"), {"id": bank_id})
    left = await conn.execute(
        text(f"SELECT count(*) FROM {_SCHEMA}.tenant_invoice_payment_bank WHERE payment_method_id = :id"), {"id": bank_id}
    )
    assert left.scalar_one() == 0  # 振込先を消すと詳細も消える


@pytest.mark.skipif(
    not ADMIN_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_new_tenant_shape_equals_migration_and_rules_hold():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    try:
        async with tenant_schema_lock(admin_engine, _TENANT_ID):
            try:
                schema_name = await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
                assert schema_name == _SCHEMA
                async with admin_engine.connect() as conn:
                    before = await _shape(conn)  # 新しい会社の作り方（tenant.py）で作った形
                assert len(before["rls"]) == 4
                assert all(row[1] for row in before["rls"])
                assert len(before["policies"]) == 4
                # 表と列を消してから、全テナントを回す正本をこの試験のテナントだけに絞って 2 回流す
                async with admin_engine.begin() as conn:
                    for table in reversed(_TABLES):
                        await conn.execute(text(f"DROP TABLE {_SCHEMA}.{table}"))
                    await conn.execute(text(f"ALTER TABLE {_SCHEMA}.invoices DROP COLUMN issuer_region"))
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 1 回目
                    await _apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)  # 2 回目（冪等）
                async with admin_engine.connect() as conn:
                    after = await _shape(conn)
                assert before == after

                conn = await admin_engine.connect()
                try:
                    trans = await conn.begin()
                    try:
                        await _check_rules(conn)
                    finally:
                        await trans.rollback()
                finally:
                    await conn.close()
            finally:
                async with public_bootstrap_lock(admin_engine):
                    async with admin_engine.begin() as conn:
                        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    finally:
        await admin_engine.dispose()


def test_migration_is_scoped_to_own_tenant():
    from tests.rls_bootstrap import _scope_tenant_migration

    sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    scoped = _scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2c1 && git log --oneline -1 | tail -1
    cd ~/sa && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
  期待: 2行目 `is-ancestor exit=0`。1 なら `BLOCKED: 手順1 is-ancestor`（取り込みは Opus が行う）。

手順2 実装前点検 P1〜P12 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/viewer-contract-stage/card-2-2c1.md | tail -1
    cd ~/sa && ls migrations | sort | tail -1
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | tail -1
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2
    cd ~/sa && grep -c "1109" migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py | tail -2
    cd ~/sa && grep -c -E "tenant_issuer_profiles|tenant_invoice_payment|issuer_region|overseas_folder_id" backend/app/services/tenant.py migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/rls_bootstrap.py | tail -3
    cd ~/sa && grep -c "963" backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py | tail -2
    cd ~/sa && grep -c "    void_reason VARCHAR(500)," backend/app/services/tenant.py
    cd ~/sa && grep -c "CONSTRAINT chk_reserved_le_physical CHECK (reserved_qty <= physical_qty)" backend/app/services/tenant.py
    cd ~/sa && grep -c "ALTER TABLE {schema}.own_inventory ENABLE ROW LEVEL SECURITY;" backend/app/services/tenant.py
    cd ~/sa && grep -c "CREATE POLICY own_inventory_tenant_isolation ON {schema}.own_inventory" backend/app/services/tenant.py
    cd ~/sa && grep -c ' countries"' .github/workflows/migration-guard.yml
    cd ~/sa && grep -c 'viewer_invoice_lines"$' .github/workflows/migration-guard.yml
    cd ~/sa && grep -c "変更 SQL を 1回目実行（実行可否・構文チェック）" .github/workflows/migration-test.yml
    cd ~/sa && grep -c "Create customer statuses master" .github/workflows/schema-check.yml
    cd ~/sa && grep -c "run_sql migrations/20261112_150000_create_viewer_contract_public_tables.sql" scripts/run_all_migrations.sh
    cd ~/sa && ls migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql backend/tests/test_tenant_issuer_tables_pg.py 2>&1 | tail -2
  期待: 3行目 `20261112_150000_create_viewer_contract_public_tables.sql`。4行目と5行目の値は `444ad4bb1b196f4b57f98e866a20eeafddc6d20a739b6bbabd01345263393125`。6行目は2ファイルとも `:1`。7行目は3ファイルとも `:0`。8行目は2ファイルとも `:0`。9行目 1。10行目 1。11行目 2。12行目 2。13行目 0。14行目 1。15行目 1。16行目 1。17行目 1。18行目は2つとも「No such file or directory」。

手順3 §2 の変更をする（2-1、2-2、2-3、2-5 から 2-12 の順。2-4 は手順4 で行う。新規の2ファイルは Write ツール、それ以外は Edit ツールで行う）

手順4 許可一覧の sha256 を直す（2-3 の後）
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | tail -1
  出た 64 文字で §2-4 の(1)を Edit ツールで置き換え、§2-4 の(2)も Edit ツールで行う。その後:
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | awk -F'\t' '{print NF}'
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | grep -c "card-2-2c1（分類33行追加）$"
  期待: 1行目は sha256sum と同じ 64 文字。2行目 4（列の数が変わっていない）。3行目 1。

手順5 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    cd ~ && python3.12 --version 2>&1 | tail -1
    cd ~ && python3.12 -m venv ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python --version 2>&1 | tail -1
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
    cd ~ && ~/venv312/bin/ruff --version | tail -1
  手順5 の python3.12 が無いときだけ、1行目と2行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）。
    cd ~ && uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    cd ~ && ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順6 形と数
    cd ~/sa && ~/venv312/bin/ruff check backend/app/services/tenant.py backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/ops/test_ai_cloud_views.py backend/tests/test_tenant_issuer_tables_pg.py 2>&1 | tail -10
    cd ~/sa && ~/venv312/bin/python -c "import ast; ast.parse(open('backend/app/services/tenant.py').read()); print('tenant.py ok')" 2>&1 | tail -1
    cd ~/sa && ~/venv312/bin/python -c "import yaml; [yaml.safe_load(open('.github/workflows/' + n)) for n in ('migration-test.yml', 'schema-check.yml', 'migration-guard.yml')]; print('yaml ok')" 2>&1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py repo > ~/vw-repo.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-repo.txt
    cd ~/sa && git diff -U0 migrations/20261024_100300_create_ai_cloud_views.sql | grep -c "^+  ('tenant_\*'"
    cd ~/sa && git diff -U0 migrations/20261024_100300_create_ai_cloud_views.sql | grep -c "^-  ('"
    cd ~/sa && git diff -U0 migrations/20261024_100300_create_ai_cloud_views.sql | grep -c "^+  ('public'"
    cd ~/sa && grep -c "1142" migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py | tail -2
    cd ~/sa && git diff -U0 backend/app/services/tenant.py | grep -c "^-"
    cd ~/sa && git diff -U0 backend/app/services/tenant.py | grep -c "^+"
    cd ~/sa && grep -c "CREATE TABLE IF NOT EXISTS {schema}.tenant_i" backend/app/services/tenant.py
    cd ~/sa && grep -c "run_sql migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql" scripts/run_all_migrations.sh
  期待（上から順に）: ruff は `All checks passed!`／`tenant.py ok`／`yaml ok`／値の書き込みの検査は `exit=0`／11（足した会社ごとの分類の行）／1（直した Drive の行の古い形）／1（直した Drive の行の新しい形）／2ファイルとも `:1`／1（消した行は無いので、当たるのは見出しの `--- a/backend/app/services/tenant.py` の1行だけ）／114（足した行 113 と `+++ b/` の1行）／4／1。
  repo の検査が exit=0 でなかったら、最後の 10 行を貼って `BLOCKED: value-writes`。

手順7 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_tenant_issuer_tables_pg.py tests/test_tenant_loop_migration_guard.py 2>&1 | tail -15
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/ops/test_ai_cloud_views.py 2>&1 | tail -15
  期待: 1本目は failed 0・error 0 で、passed に test_tenant_issuer_tables_pg.py の単体4件を含む（PG の1件は skipped でよい）。2本目は failed 0・error 0（skipped は出てよい）。

手順8 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -20
    cd ~/sa && git diff --stat | tail -20
  期待: §1 の 12 ファイルだけ（新規の2ファイルは `??` で各1行）。

手順9 記録と送り出し
    cd ~/sa && git add migrations/20261112_160000_create_tenant_issuer_and_payment_tables.sql backend/app/services/tenant.py migrations/20261024_100300_create_ai_cloud_views.sql scripts/migration-guard/reference-allowlist.tsv scripts/run_all_migrations.sh .github/workflows/migration-test.yml .github/workflows/schema-check.yml .github/workflows/migration-guard.yml backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/ops/test_ai_cloud_views.py backend/tests/test_tenant_issuer_tables_pg.py && git status --short | tail -20
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(tenant): create issuer profile and invoice payment tables per tenant (ADR-1061 bin2-2c1)" && git log --oneline -1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py diff origin/main HEAD --check all > ~/vw-diff.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-diff.txt
    cd ~/sa && git push origin release/viewer-contract-bin2-2c1 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-contract-bin2-2c1 -2 | tail -2
  `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。3行目の diff 検査が exit=0 でなかったら push せずに最後の 10 行を貼って `BLOCKED: value-writes`。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - 手順1 の is-ancestor が 0 でない・P1〜P12 のどれかが外れた → `BLOCKED: 手順1` か `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 手順4 の期待が外れた → 出力を貼って `BLOCKED: allowlist`。
  - 値の書き込みの検査（手順6・手順9）が失敗した → 最後の 10 行を貼って `BLOCKED: value-writes`。移行の文を直さない。
  - 手順6 の数の期待が外れた → 出力を貼って `BLOCKED: 手順6`。
  - 手順7 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - 手順7 で skipped が出る → そのまま書く（実 PostgreSQL の試験は CI で動く）。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED viewer-contract-bin2-2c1 HEAD=…`。2 行目: 「本報告はカード 便2-2c1 発行元の会社情報と振込先の表を作る の実行結果である」。
- 手順1・2・4・5・6・7・8・9 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の2ファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

END OF CARD
