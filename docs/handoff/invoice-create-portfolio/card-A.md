# card: 便A 関税の額の表2つと請求書の5列を作る（invoice-create-portfolio）

状態: カード発行（Opus、2026-11-13）。PO の設計承認と実装承認は 2026-11-13「1,（２）決済手数料を合計に足す仕組みは、今回は作りません。別の作業に回します。→次便で」と、同じ日の常設の指示「…確立したなら進める。…PRマージ、デプロイまで完走させてくれ。」（design.md 第8版・審査 APPROVE）。第9版（2026-11-14）: PO が振込先を版で持つ案を「1,」で選んだ（ADR-1078）。請求書の写しの2列（payment_method_snapshot・payment_account_number）を外し、請求書の列は5列になった。K21 は「請求書の表に写しと口座番号の列が無い」に変わった。
設計: docs/handoff/invoice-create-portfolio/design.md §3-3（関税）・§3-5（請求書の列・tenant.py・分類表）・§5 の便 A・§8 の K17・K21（第9版）・ADR-1078。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `73bf937a8` で行番号を測った（11694eaf6 で測った値を 2026-11-14 に 73bf937a8 で測り直し、変わっていない）。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
危険便か: はい（`migrations/` に新しい SQL を足し、毎回流れる分類表の SQL と `scripts/migration-guard/reference-allowlist.tsv`・`scripts/run_all_migrations.sh` を変える）。マージ前に Opus の審査役の APPROVE・CI 全通過・ADR-136 の GO 記録と直前のバックアップの確認を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 この便は「表と列を作るだけ」。計算・API・画面・PDF は便 B〜D で行う。値は入れない（ADR-155）。
- D2 会社ごとのスキーマに2表を作る: 関税の決まり `tenant_duty_rules`（国・送料の会社・有効期間・根拠の URL）と、その中身 `tenant_duty_rule_components`（関税・手数料などの率と下限・上限）。中身は決まりを外部キーで指し、決まりを消すと中身も消える（ON DELETE CASCADE）。関税の条件（DAP・DDU・DDP）の列は持たない（正本は tenant_settings.duty_incoterms だけ。design.md §3-3）。
- D3 設計 §3-3 の「note、is_active、created_at、updated_at」のとおり、関税の表に更新した人の列（updated_by_user_id）は作らない。
- D4 請求書 `invoices` に5列を足す: payment_method_id（INTEGER・外部キーなし。振込先の版の番号。ADR-1078）・tax_rate_percent（NUMERIC(5, 2)）・shipping_carrier（VARCHAR(50)）・shipping_service（VARCHAR(100)）・shipping_snapshot（JSONB）。どれも NULL 可（design.md §3-5）。振込先の写しと口座番号の列は作らない（第9版。口座番号は振込先の詳細の表だけに置く）。
- D5 新しい会社は backend/app/services/tenant.py で同じ形に作る。あわせて、移行だけで足してあって tenant.py に無い請求書の12列（ship_to_snapshot など。型は 20260604_160000・20260611_020000・20260612_131520 の移行と同じ）と、見積の明細・請求書の明細の hs_code を tenant.py に足す（design.md §2・recon §4-1）。
- D6 分類表（migrations/20261024_100300_create_ai_cloud_views.sql）に 11 列分の行を足す（請求書 3・関税の決まり 5・中身 3）。数・日付・真偽の型の列は型で通るので行を持たない。1151 を 1162 にする。元の表 docs/handoff/cloud-case-ai/stage1-column-class.tsv にも同じ 11 行を足す（design.md §3-5「SQL と元の表の両方」）。
- D7 分類表のファイルは reference-allowlist.tsv:7 に sha256 で登録されているので、同じ変更で sha256 と4列目を直す。4列目の最後に ` / invoice-create-portfolio card-A（分類11行追加）` を足す。
- D8 新しい2表は public の表を外部キーで指さないので、CI の手順（.github/workflows/）は変えない（前例の便2-2c1 は public.countries を指したので手順を足した）。
- D10 K21 は「請求書の表に振込先の写しと口座番号の列が無い」を §2-10 の試験 test_invoices_hold_no_payment_copy で確かめる。口座番号は振込先の詳細の表だけに残り、ADR-1061 決定9 の列名による隠し方がそのまま効く（ADR-1078）。関税の2表は個人の情報を持たないので ops_case.deny_tables に足さない。
- D9 移行の試験のテナント番号は 962（2026-11-13 に 11694eaf6、2026-11-14 に 73bf937a8 で backend・migrations・scripts を git grep して、試験と移行には 0 件。当たるのは backend/app/auth/data/common-passwords.txt と scripts/accuracy/llm_compare/README.md だけ）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（関税の表2つと請求書の列を作る。D1） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/invoice-create-portfolio-bin-a` を作る） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順8 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P2〜P12 は 11694eaf6 で実測し、2026-11-14 に 73bf937a8 で同じ値を確かめた。tenant.py の足す行の数は写しに §2-2 を当てて実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文。sha256 だけは手順4 で測った値を入れる） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-create-portfolio-A HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便A 関税の額の表2つと請求書の5列を作る の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/invoice-create-portfolio/card-A.md`（このカード）が枝に在る。
- P2 `ls migrations | sort | tail -1` が `20261113_100001_create_secretary_rules_down.sql`。
- P3 `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の値と `sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2` が、どちらも `472bfcd14f935118dadadb351601de91944964b031842ba9eee5f3d4d99fa6a6`。
- P4 `grep -c "1151"` が migrations/20261024_100300_create_ai_cloud_views.sql と backend/tests/ops/test_ai_cloud_views.py でそれぞれ 1。
- P5 `grep -c -E "tenant_duty|payment_method_snapshot|shipping_snapshot|tax_rate_percent|payment_account_number|shipping_service"` が backend/app/services/tenant.py・migrations/20261024_100300_create_ai_cloud_views.sql・backend/tests/rls_bootstrap.py でそれぞれ 0（`shipping_carrier` は注文・見積の表に既にあるので数えない。2026-11-13 審査の指摘で直した）。
- P6 `grep -c "962"` が backend/tests/rls_bootstrap.py と backend/tests/test_tenant_loop_migration_guard.py でそれぞれ 0。
- P7 `grep -c "    hs_code VARCHAR(20),"` が backend/app/services/tenant.py で 1（order_items の行だけ）。`grep -c "    subtotal NUMERIC(15, 2) NOT NULL,"` が 4。
- P8 `grep -c "ALTER TABLE {schema}.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY;"` が backend/app/services/tenant.py で 1。`grep -c "CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON {schema}.tenant_invoice_payment_wise"` が 1。
- P9 `wc -l < docs/handoff/cloud-case-ai/stage1-column-class.tsv` が 1058。`wc -l < scripts/run_all_migrations.sh` が 1272。
- P10 `tail -1 scripts/run_all_migrations.sh` が `# ADR-1077 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_100001_create_secretary_rules_down.sql`。
- P11 `sed -n 7p scripts/migration-guard/reference-allowlist.tsv | grep -c "secretary-rulebook card-bin1（分類5行追加）$"` が 1。
- P12 `ls migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql` が「無い」。`ls backend/tests/test_tenant_duty_rules_pg.py` も「無い」。

## 1. 触るファイル

1. migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql（新規）
2. backend/app/services/tenant.py（6か所に足す）
3. migrations/20261024_100300_create_ai_cloud_views.sql（説明1行を直し、分類の行を7行足す）
4. scripts/migration-guard/reference-allowlist.tsv（7行目の sha256 と4列目）
5. docs/handoff/cloud-case-ai/stage1-column-class.tsv（11行足す）
6. scripts/run_all_migrations.sh（最後に2行足す）
7. backend/tests/rls_bootstrap.py（1か所）
8. backend/tests/test_tenant_loop_migration_guard.py（2か所）
9. backend/tests/ops/test_ai_cloud_views.py（数1か所と試験1本）
10. backend/tests/test_tenant_duty_rules_pg.py（新規）

触らない: 上の 5 以外の docs/ 全部・frontend/・backend/app のほかのファイル・migrations のほかのファイル・.github/workflows の全部（特に workflow-lint.yml）。

## 2. 変更

### 2-1. migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql（新規。全文）

```sql
-- invoice-create-portfolio 便A: 関税の額の表 2 つと、請求書の 5 列を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/invoice-create-portfolio/design.md §3-3（関税）・§3-5（請求書の列）
-- 中身（各テナントのスキーマ）:
--   tenant_duty_rules              関税の決まり（行き先の国・送料の会社・有効期間・根拠の URL。DDP のときに使う）
--   tenant_duty_rule_components    関税の決まりの中身（関税・手数料などの率と下限・上限）
--   invoices.payment_method_id         請求書で案内した振込先の版の番号（外部キーなし。版は消えない。ADR-1078）
--   invoices.tax_rate_percent          使った消費税の率
--   invoices.shipping_carrier          送料の会社
--   invoices.shipping_service          送料のサービス名
--   invoices.shipping_snapshot         送料の元の額・元の通貨・換算の率・出どころ
-- 関税の条件（DAP・DDU・DDP）の正本は tenant_settings.duty_incoterms だけ。この表には条件の列を持たない。
-- ADR-155: 構造変更のみ。値は入れない。
-- GRANT は ALTER DEFAULT PRIVILEGES（20260605_040000）で自動付与される。
-- 新しい会社のスキーマは backend/app/services/tenant.py の _TENANT_TABLES_SQL で同じ形に作る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP TABLE IF EXISTS <tenant>.tenant_duty_rule_components;
--   DROP TABLE IF EXISTS <tenant>.tenant_duty_rules;
--   ALTER TABLE <tenant>.invoices DROP COLUMN IF EXISTS payment_method_id, DROP COLUMN IF EXISTS tax_rate_percent,
--     DROP COLUMN IF EXISTS shipping_carrier,
--     DROP COLUMN IF EXISTS shipping_service, DROP COLUMN IF EXISTS shipping_snapshot;

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
            'CREATE TABLE IF NOT EXISTS %I.tenant_duty_rules (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                destination_country_code CHAR(2) NOT NULL,
                carrier VARCHAR(50),
                label TEXT NOT NULL,
                effective_from DATE NOT NULL,
                effective_to DATE,
                source_url TEXT NOT NULL,
                note TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_duty_rules_country CHECK (destination_country_code ~ ''^[A-Z]{2}$''),
                CONSTRAINT chk_tenant_duty_rules_carrier CHECK (carrier IS NULL OR (carrier = lower(btrim(carrier)) AND carrier <> '''')),
                CONSTRAINT chk_tenant_duty_rules_label CHECK (btrim(label) <> ''''),
                CONSTRAINT chk_tenant_duty_rules_source_url CHECK (btrim(source_url) <> ''''),
                CONSTRAINT chk_tenant_duty_rules_period CHECK (effective_to IS NULL OR effective_to >= effective_from)
            )',
            r.nspname, tid
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_tenant_duty_rules_country_carrier ON %I.tenant_duty_rules (destination_country_code, carrier)',
            r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_duty_rule_components (
                id SERIAL PRIMARY KEY,
                rule_id INTEGER NOT NULL REFERENCES %I.tenant_duty_rules(id) ON DELETE CASCADE,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                sort_order INTEGER NOT NULL DEFAULT 0,
                label TEXT NOT NULL,
                base VARCHAR(30) NOT NULL,
                rate_pct NUMERIC(8, 4) NOT NULL,
                min_amount NUMERIC(14, 2),
                max_amount NUMERIC(14, 2),
                amount_currency CHAR(3),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_duty_rule_components_label CHECK (btrim(label) <> ''''),
                CONSTRAINT chk_tenant_duty_rule_components_base CHECK (base IN (''subtotal'', ''subtotal_shipping'', ''subtotal_shipping_prior'')),
                CONSTRAINT chk_tenant_duty_rule_components_rate CHECK (rate_pct >= 0),
                CONSTRAINT chk_tenant_duty_rule_components_amounts CHECK ((min_amount IS NULL OR min_amount >= 0) AND (max_amount IS NULL OR max_amount >= 0) AND (min_amount IS NULL OR max_amount IS NULL OR min_amount <= max_amount)),
                CONSTRAINT chk_tenant_duty_rule_components_currency CHECK (amount_currency IS NULL OR amount_currency ~ ''^[A-Z]{3}$''),
                CONSTRAINT chk_tenant_duty_rule_components_currency_required CHECK ((min_amount IS NULL AND max_amount IS NULL) OR amount_currency IS NOT NULL)
            )',
            r.nspname, r.nspname, tid
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_tenant_duty_rule_components_rule_id ON %I.tenant_duty_rule_components (rule_id)',
            r.nspname
        );

        EXECUTE format('ALTER TABLE %I.tenant_duty_rules ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_duty_rule_components ENABLE ROW LEVEL SECURITY', r.nspname);

        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rules_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_duty_rules_tenant_isolation ON %I.tenant_duty_rules USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rule_components_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_duty_rule_components_tenant_isolation ON %I.tenant_duty_rule_components USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;

        IF to_regclass(format('%I.invoices', r.nspname)) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS payment_method_id INTEGER', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS tax_rate_percent NUMERIC(5, 2)', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS shipping_carrier VARCHAR(50)', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS shipping_service VARCHAR(100)', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS shipping_snapshot JSONB', r.nspname);
            EXECUTE format('COMMENT ON COLUMN %I.invoices.payment_method_id IS %L', r.nspname, '請求書で案内した振込先の版の番号（振込先の一覧の id。版は消えない。外部キーは張らない。PayPal は NULL）');
            EXECUTE format('COMMENT ON COLUMN %I.invoices.tax_rate_percent IS %L', r.nspname, '計算に使った消費税の率（パーセント。日本宛のときだけ）');
            EXECUTE format('COMMENT ON COLUMN %I.invoices.shipping_snapshot IS %L', r.nspname, '送料の元の額・元の通貨・換算の率・出どころ（calculate / quote / none）');
        END IF;

        EXECUTE format('COMMENT ON TABLE %I.tenant_duty_rules IS %L', r.nspname, '関税の決まり。関税の条件が DDP のときに、行き先の国と送料の会社ごとに請求する額の決まり');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rules.carrier IS %L', r.nspname, '送料の会社（小文字・前後の空白なし）。NULL はどの会社でも');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rules.source_url IS %L', r.nspname, '額の根拠の URL（空は不可）');
        EXECUTE format('COMMENT ON TABLE %I.tenant_duty_rule_components IS %L', r.nspname, '関税の決まりの中身（関税・手数料など）。sort_order の順に計算する');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rule_components.base IS %L', r.nspname, 'subtotal=小計 / subtotal_shipping=小計+送料 / subtotal_shipping_prior=小計+送料+前の中身の合計');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rule_components.amount_currency IS %L', r.nspname, '下限・上限の通貨（英大文字3字。下限か上限があるときは必須）');
        RAISE NOTICE 'duty rule tables and invoice columns created/verified for schema: %', r.nspname;
    END LOOP;
END $$;
```

### 2-2. backend/app/services/tenant.py（6か所。どれも足すだけで、消す行は無い）

`{{2}}` などの二重の波かっこはこのファイルの書き方なのでそのまま写す。説明の行（`--` で始まる行）に `;` と波かっこを入れない。

(a) 見積の明細の表。`    subtotal NUMERIC(15, 2) NOT NULL,` は4か所にあるので、後ろの行と組で探す。変更前（1か所だけ・:856〜:860）:
```
    subtotal NUMERIC(15, 2) NOT NULL,
    sort_order INTEGER DEFAULT 0
);

-- 請求書ヘッダー
```
変更後（1行目と2行目の間に1行足す）:
```
    subtotal NUMERIC(15, 2) NOT NULL,
    hs_code VARCHAR(20),
    sort_order INTEGER DEFAULT 0
);

-- 請求書ヘッダー
```

(b) 請求書の表。変更前（1か所だけ・:888〜:889）:
```
    issuer_region VARCHAR(20) CONSTRAINT chk_invoices_issuer_region CHECK (issuer_region IN ('domestic', 'overseas')),
    notes TEXT,
```
変更後（2行の間に 19 行足す）:
```
    issuer_region VARCHAR(20) CONSTRAINT chk_invoices_issuer_region CHECK (issuer_region IN ('domestic', 'overseas')),
    -- 移行で全テナントに入っている列（20260604_160000・20260611_020000・20260612_131520）を新しいテナントにも作る
    ship_to_snapshot JSONB,
    bill_to_snapshot JSONB,
    issue_mode VARCHAR(20),
    duty_amount NUMERIC(15, 2),
    duty_policy_snapshot JSONB,
    fx_rate_snapshot JSONB,
    paypal_order_id TEXT,
    paypal_approval_url TEXT,
    payment_fee NUMERIC(15, 2),
    paypal_invoicer_view_url TEXT,
    paypal_copy_pdf BYTEA,
    paypal_copy_pdf_at TIMESTAMPTZ,
    -- invoice-create-portfolio 便A: 案内した支払い先・使った税率・選んだ送料（移行 20261113_120000 と同じ形）
    payment_method_id INTEGER,
    tax_rate_percent NUMERIC(5, 2),
    shipping_carrier VARCHAR(50),
    shipping_service VARCHAR(100),
    shipping_snapshot JSONB,
    notes TEXT,
```

(c) 請求書の明細の表。変更前（1か所だけ・:910〜:914）:
```
    subtotal NUMERIC(15, 2) NOT NULL,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS {schema}.order_items (
```
変更後（1行目と2行目の間に1行足す）:
```
    subtotal NUMERIC(15, 2) NOT NULL,
    hs_code VARCHAR(20),
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS {schema}.order_items (
```

(d) `_TENANT_TABLES_SQL` の最後。変更前（1か所だけ・:1300〜:1302）:
```
    CONSTRAINT fk_tenant_invoice_payment_wise_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
);
"""
```
変更後（`);` と `"""` の間に、空行で始まる次の 45 行を足す）:
```
    CONSTRAINT fk_tenant_invoice_payment_wise_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES {schema}.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
);

-- invoice-create-portfolio 便A: 関税の決まり（行き先の国・送料の会社ごと。DDP のときに使う）
CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rules (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    destination_country_code CHAR(2) NOT NULL,
    carrier VARCHAR(50),
    label TEXT NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    source_url TEXT NOT NULL,
    note TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_duty_rules_country CHECK (destination_country_code ~ '^[A-Z]{{2}}$'),
    CONSTRAINT chk_tenant_duty_rules_carrier CHECK (carrier IS NULL OR (carrier = lower(btrim(carrier)) AND carrier <> '')),
    CONSTRAINT chk_tenant_duty_rules_label CHECK (btrim(label) <> ''),
    CONSTRAINT chk_tenant_duty_rules_source_url CHECK (btrim(source_url) <> ''),
    CONSTRAINT chk_tenant_duty_rules_period CHECK (effective_to IS NULL OR effective_to >= effective_from)
);
CREATE INDEX IF NOT EXISTS idx_tenant_duty_rules_country_carrier ON {schema}.tenant_duty_rules (destination_country_code, carrier);

-- invoice-create-portfolio 便A: 関税の決まりの中身（関税・消費税・手数料など。率と下限・上限）
CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rule_components (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES {schema}.tenant_duty_rules(id) ON DELETE CASCADE,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    sort_order INTEGER NOT NULL DEFAULT 0,
    label TEXT NOT NULL,
    base VARCHAR(30) NOT NULL,
    rate_pct NUMERIC(8, 4) NOT NULL,
    min_amount NUMERIC(14, 2),
    max_amount NUMERIC(14, 2),
    amount_currency CHAR(3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_duty_rule_components_label CHECK (btrim(label) <> ''),
    CONSTRAINT chk_tenant_duty_rule_components_base CHECK (base IN ('subtotal', 'subtotal_shipping', 'subtotal_shipping_prior')),
    CONSTRAINT chk_tenant_duty_rule_components_rate CHECK (rate_pct >= 0),
    CONSTRAINT chk_tenant_duty_rule_components_amounts CHECK ((min_amount IS NULL OR min_amount >= 0) AND (max_amount IS NULL OR max_amount >= 0) AND (min_amount IS NULL OR max_amount IS NULL OR min_amount <= max_amount)),
    CONSTRAINT chk_tenant_duty_rule_components_currency CHECK (amount_currency IS NULL OR amount_currency ~ '^[A-Z]{{3}}$'),
    CONSTRAINT chk_tenant_duty_rule_components_currency_required CHECK ((min_amount IS NULL AND max_amount IS NULL) OR amount_currency IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_tenant_duty_rule_components_rule_id ON {schema}.tenant_duty_rule_components (rule_id);
"""
```

(e) `_RLS_ENABLE_SQL` の最後。変更前（1か所だけ・:1359〜:1360）:
```
ALTER TABLE {schema}.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY;
"""
```
変更後（2行の間に3行足す）:
```
ALTER TABLE {schema}.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY;
-- invoice-create-portfolio 便A: 関税の決まりの表2つ
ALTER TABLE {schema}.tenant_duty_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE {schema}.tenant_duty_rule_components ENABLE ROW LEVEL SECURITY;
"""
```

(f) `_RLS_POLICY_SQL` の最後。変更前（1か所だけ・:1600〜:1603）:
```
        CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON {schema}.tenant_invoice_payment_wise
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
END $$
```
変更後（`    END IF;` と `END $$` の間に 9 行足す）:
```
        CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON {schema}.tenant_invoice_payment_wise
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    -- invoice-create-portfolio 便A: 関税の決まりの表2つ — ポリシー名は migration 20261113_120000 と同じ
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rules_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_duty_rules_tenant_isolation ON {schema}.tenant_duty_rules
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rule_components_tenant_isolation' AND schemaname = '{schema_raw}') THEN
        CREATE POLICY tenant_duty_rule_components_tenant_isolation ON {schema}.tenant_duty_rule_components
            USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER);
    END IF;
END $$
```

### 2-3. migrations/20261024_100300_create_ai_cloud_views.sql（3か所）

(1) :3

変更前:
```
-- 1) 分類表 ai_cloud_meta.column_class を空にして下の 1151 行を入れ直す（このファイルが正本。行の足し引きはこの SQL の変更で行う）。
```
変更後:
```
-- 1) 分類表 ai_cloud_meta.column_class を空にして下の 1162 行を入れ直す（このファイルが正本。行の足し引きはこの SQL の変更で行う）。
```

(2) :451 の行の後ろに2行足す。

変更前:
```
  ('tenant_*','invoices',ARRAY['paypal_approval_url','paypal_copy_pdf','paypal_invoicer_view_url','paypal_order_id','pdf_url','ship_to_snapshot'],'mask',''),
  ('tenant_*','invoices',ARRAY['status'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
```
変更後:
```
  ('tenant_*','invoices',ARRAY['paypal_approval_url','paypal_copy_pdf','paypal_invoicer_view_url','paypal_order_id','pdf_url','ship_to_snapshot'],'mask',''),
  ('tenant_*','invoices',ARRAY['shipping_carrier','shipping_service'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
  ('tenant_*','invoices',ARRAY['shipping_snapshot'],'mask',''),
  ('tenant_*','invoices',ARRAY['status'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
```

(3) :600 の行の後ろに5行足す（`tenant_commission_settings` の `commission_rates` の行は1か所だけ）。

変更前:
```
  ('tenant_*','tenant_commission_settings',ARRAY['commission_rates'],'mask',''),
```
変更後:
```
  ('tenant_*','tenant_commission_settings',ARRAY['commission_rates'],'mask',''),
  ('tenant_*','tenant_duty_rule_components',ARRAY['amount_currency'],'mask','値の決まりが値の一覧でなく文字の形だけのため伏せる（初期は最小）'),
  ('tenant_*','tenant_duty_rule_components',ARRAY['base'],'allow','値の決まり chk_tenant_duty_rule_components_base で値が限られる'),
  ('tenant_*','tenant_duty_rule_components',ARRAY['label'],'mask',''),
  ('tenant_*','tenant_duty_rules',ARRAY['carrier','destination_country_code'],'mask','値の決まりが値の一覧でなく文字の形だけのため伏せる（初期は最小）'),
  ('tenant_*','tenant_duty_rules',ARRAY['label','note','source_url'],'mask',''),
```

### 2-4. scripts/migration-guard/reference-allowlist.tsv（7行目。手順4 で行う）

(1) 2列目の `472bfcd14f935118dadadb351601de91944964b031842ba9eee5f3d4d99fa6a6` を、手順4 で測った 2-3 の後の sha256（64 文字）に置き換える。
(2) 4列目（行の最後）の `secretary-rulebook card-bin1（分類5行追加）` を `secretary-rulebook card-bin1（分類5行追加） / invoice-create-portfolio card-A（分類11行追加）` に置き換える。タブの数は変えない（列は4つのまま）。

### 2-5. docs/handoff/cloud-case-ai/stage1-column-class.tsv（2か所に足す。列はタブ区切りの6列: schema_pattern・table・column・class・reason・data_type）

下の表示ではタブを `<TAB>` と書く。ファイルには本物のタブ文字を入れる（Edit ツールの文字列にタブを入れる）。reason が空の行は `mask<TAB><TAB>jsonb` のようにタブが2つ続く。

(1) `ship_to_snapshot` の行（:714）の後ろに3行足す。

変更前:
```
tenant_*<TAB>invoices<TAB>ship_to_snapshot<TAB>mask<TAB><TAB>jsonb
```
変更後:
```
tenant_*<TAB>invoices<TAB>ship_to_snapshot<TAB>mask<TAB><TAB>jsonb
tenant_*<TAB>invoices<TAB>shipping_carrier<TAB>mask<TAB>値の決まりが無く自由に入る列のため伏せる（初期は最小）<TAB>character varying
tenant_*<TAB>invoices<TAB>shipping_service<TAB>mask<TAB>値の決まりが無く自由に入る列のため伏せる（初期は最小）<TAB>character varying
tenant_*<TAB>invoices<TAB>shipping_snapshot<TAB>mask<TAB><TAB>jsonb
```

(2) `commission_rates` の行（:991。(1) の後は :994）の後ろに8行足す。

変更前:
```
tenant_*<TAB>tenant_commission_settings<TAB>commission_rates<TAB>mask<TAB><TAB>jsonb
```
変更後:
```
tenant_*<TAB>tenant_commission_settings<TAB>commission_rates<TAB>mask<TAB><TAB>jsonb
tenant_*<TAB>tenant_duty_rule_components<TAB>amount_currency<TAB>mask<TAB>値の決まりが値の一覧でなく文字の形だけのため伏せる（初期は最小）<TAB>character
tenant_*<TAB>tenant_duty_rule_components<TAB>base<TAB>allow<TAB>値の決まり chk_tenant_duty_rule_components_base で値が限られる<TAB>character varying
tenant_*<TAB>tenant_duty_rule_components<TAB>label<TAB>mask<TAB><TAB>text
tenant_*<TAB>tenant_duty_rules<TAB>carrier<TAB>mask<TAB>値の決まりが値の一覧でなく文字の形だけのため伏せる（初期は最小）<TAB>character varying
tenant_*<TAB>tenant_duty_rules<TAB>destination_country_code<TAB>mask<TAB>値の決まりが値の一覧でなく文字の形だけのため伏せる（初期は最小）<TAB>character
tenant_*<TAB>tenant_duty_rules<TAB>label<TAB>mask<TAB><TAB>text
tenant_*<TAB>tenant_duty_rules<TAB>note<TAB>mask<TAB><TAB>text
tenant_*<TAB>tenant_duty_rules<TAB>source_url<TAB>mask<TAB><TAB>text
```

### 2-6. scripts/run_all_migrations.sh（最後の行 :1272 の後ろに2行足す）

変更前（最後の行）:
```
# ADR-1077 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_100001_create_secretary_rules_down.sql
```
変更後:
```
# ADR-1077 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_100001_create_secretary_rules_down.sql
# invoice-create-portfolio 便A: 関税の額の表2つ・請求書の5列を作る（形だけ・行なし・冪等）
run_sql migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql
```
（ファイルの最後は改行で終わる形のままにする。）

### 2-7. backend/tests/rls_bootstrap.py（:190 の行の後ろに1行足す）

変更前:
```
    "20261112_160000_create_tenant_issuer_and_payment_tables.sql": 1,
}
```
変更後:
```
    "20261112_160000_create_tenant_issuer_and_payment_tables.sql": 1,
    "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql": 1,
}
```

### 2-8. backend/tests/test_tenant_loop_migration_guard.py（2か所）

(1) `rls_bootstrap.py` の組の集合の最後（:52）。

変更前:
```
                "20261112_160000_create_tenant_issuer_and_payment_tables.sql",
            }
```
変更後:
```
                "20261112_160000_create_tenant_issuer_and_payment_tables.sql",
                "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql",
            }
```

(2) :110〜:114 の組の後ろに5行足す。

変更前:
```
    "test_tenant_issuer_tables_pg.py": (
        "scoped",
        "",
        frozenset({"20261112_160000_create_tenant_issuer_and_payment_tables.sql"}),
    ),
```
変更後:
```
    "test_tenant_issuer_tables_pg.py": (
        "scoped",
        "",
        frozenset({"20261112_160000_create_tenant_issuer_and_payment_tables.sql"}),
    ),
    "test_tenant_duty_rules_pg.py": (
        "scoped",
        "",
        frozenset({"20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql"}),
    ),
```

### 2-9. backend/tests/ops/test_ai_cloud_views.py（2か所）

(1) :486

変更前:
```
    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1151
```
変更後:
```
    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1162
```

(2) `def test_t10_detects_added_columns(pg):`（:945。1か所だけ）の行の直前に、次の文と空行2つを足す（この文の最後の行の後ろに空行2つ、その次が `def test_t10_detects_added_columns(pg):`）。

```python
# invoice-create-portfolio 便A: 関税の決まりの2表・請求書の新しい列と tenant.py に足した列・明細の hs_code に分類の漏れが無いことを確かめる。
_DUTY_TABLES = {"tenant_duty_rules", "tenant_duty_rule_components"}
_DUTY_CLASSIFIED = {
    ("invoices", "shipping_snapshot"),
    ("invoices", "shipping_carrier"),
    ("invoices", "shipping_service"),
    ("tenant_duty_rule_components", "amount_currency"),
    ("tenant_duty_rule_components", "base"),
    ("tenant_duty_rule_components", "label"),
    ("tenant_duty_rules", "carrier"),
    ("tenant_duty_rules", "destination_country_code"),
    ("tenant_duty_rules", "label"),
    ("tenant_duty_rules", "note"),
    ("tenant_duty_rules", "source_url"),
}
_DUTY_CHECKED_COLUMNS = {
    ("invoices", c) for c in (
        "ship_to_snapshot", "bill_to_snapshot", "issue_mode", "duty_amount", "duty_policy_snapshot",
        "fx_rate_snapshot", "paypal_order_id", "paypal_approval_url", "payment_fee",
        "paypal_invoicer_view_url", "paypal_copy_pdf", "paypal_copy_pdf_at",
        "payment_method_id", "tax_rate_percent",
        "shipping_carrier", "shipping_service", "shipping_snapshot",
    )
} | {("quote_items", "hs_code"), ("invoice_items", "hs_code")}  # fmt: skip


def test_t10_duty_and_invoice_columns_are_classified_on_bootstrapped_db(cluster):
    """invoice-create-portfolio 便A: 新しい会社の作り方（tenant.py）で作ったテナントに 11 列の column_class の行があり、
    関税の2表と、請求書・明細に足した列に分類の漏れが無い。

    数・日付・真偽の型の列は型で通る。
    専用の DB を作り、終わったら消す。"""
    from sqlalchemy.ext.asyncio import create_async_engine

    assert len(_DUTY_CLASSIFIED) == 11
    assert len(_DUTY_CHECKED_COLUMNS) == 19
    name, conn = _new_db(cluster.control, "ai_cloud_t10_duty")
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
        missing = _DUTY_CLASSIFIED - have
        assert missing == set(), f"column_class に行が無い: {sorted(missing)}"

        gaps = [
            g for g in _classification_gaps(conn)
            if g[1] in _DUTY_TABLES or (g[1], g[2]) in _DUTY_CHECKED_COLUMNS
        ]  # fmt: skip
        assert gaps == [], f"分類の漏れ（表名・列名）: {[(g[1], g[2]) for g in gaps]}"
    finally:
        conn.close()
        cur = cluster.control.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
```

### 2-10. backend/tests/test_tenant_duty_rules_pg.py（新規。全文）

```python
"""invoice-create-portfolio 便A: 関税の決まりの表 2 つ・請求書の 5 列の構造と決まりの試験。

- 単体（PostgreSQL 不要）: 新テナント用 DDL に表 2 つと請求書の列（移行だけにあった 12 列を含む）と明細の hs_code が含まれ、
  移行ファイルが登録され、値を入れない。請求書に振込先の写しと口座番号の列が無い（K21・ADR-1078）。
- PG（CI で実行）: 新テナントを作った形（tenant.py）と、表と列を消して移行ファイルを 2 回流した形が同じ。
  決まり（CHECK・外部キー・消したときの連鎖）が設計どおりに効き、別の会社の文脈では行が見えない（K17）。
  試験の中で入れた行と役割は最後に戻す。ゲートは CI が実際に設定する RLS_ADMIN_DATABASE_URL（前例 test_tenant_issuer_tables_pg.py と同じ形）。
"""
from __future__ import annotations

import datetime
import os
import uuid
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

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql"
# 試験・移行のどこにも無い 962 を使う（2026-11-13 に origin/main で git grep して試験・移行に 0 件）
_TENANT_ID = 962
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_TABLES = ("tenant_duty_rules", "tenant_duty_rule_components")
_NEW_INVOICE_COLUMNS = (
    "payment_method_id",
    "tax_rate_percent",
    "shipping_carrier",
    "shipping_service",
    "shipping_snapshot",
)
_OLD_INVOICE_COLUMNS = (
    "ship_to_snapshot JSONB,",
    "bill_to_snapshot JSONB,",
    "issue_mode VARCHAR(20),",
    "duty_amount NUMERIC(15, 2),",
    "duty_policy_snapshot JSONB,",
    "fx_rate_snapshot JSONB,",
    "paypal_order_id TEXT,",
    "paypal_approval_url TEXT,",
    "payment_fee NUMERIC(15, 2),",
    "paypal_invoicer_view_url TEXT,",
    "paypal_copy_pdf BYTEA,",
    "paypal_copy_pdf_at TIMESTAMPTZ,",
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


def test_tenant_ddl_has_duty_tables_and_invoice_columns():
    sql = tenant_service._TENANT_TABLES_SQL
    invoices = _block(sql, "{schema}.invoices (")
    for line in _OLD_INVOICE_COLUMNS:
        assert f"    {line}" in invoices, line
    for line in (
        "payment_method_id INTEGER,",
        "tax_rate_percent NUMERIC(5, 2),",
        "shipping_carrier VARCHAR(50),",
        "shipping_service VARCHAR(100),",
        "shipping_snapshot JSONB,",
    ):
        assert f"    {line}" in invoices, line
    assert "incoterm" not in invoices
    for items in ("{schema}.quote_items (", "{schema}.invoice_items ("):
        assert "    hs_code VARCHAR(20)," in _block(sql, items), items

    rules = _block(sql, "{schema}.tenant_duty_rules (")
    for name in ("country", "carrier", "label", "source_url", "period"):
        assert f"CONSTRAINT chk_tenant_duty_rules_{name} CHECK" in rules
    assert "incoterm" not in rules
    assert "updated_by_user_id" not in rules
    components = _block(sql, "{schema}.tenant_duty_rule_components (")
    assert "rule_id INTEGER NOT NULL REFERENCES {schema}.tenant_duty_rules(id) ON DELETE CASCADE," in components
    for name in ("label", "base", "rate", "amounts", "currency", "currency_required"):
        assert f"CONSTRAINT chk_tenant_duty_rule_components_{name} CHECK" in components

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
    for column in _NEW_INVOICE_COLUMNS:
        assert f"ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS {column} " in body
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


def test_invoices_hold_no_payment_copy():
    """K21（ADR-1078）: 請求書は振込先の版の番号だけを持つ。振込先の写しと口座番号の列は、新しい会社の DDL にも移行にも無い。"""
    invoices = _block(tenant_service._TENANT_TABLES_SQL, "{schema}.invoices (")
    body = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    for name in ("payment_method_snapshot", "payment_account_number", "account_number", "iban"):
        assert name not in invoices, name
        assert name not in body, name


def test_migration_is_scoped_to_own_tenant():
    from tests.rls_bootstrap import _scope_tenant_migration

    sql = (_REPO_ROOT / "migrations" / _MIGRATION).read_text(encoding="utf-8")
    scoped = _scope_tenant_migration(sql, _MIGRATION, _SCHEMA)
    assert scoped.count(f"AND nspname = '{_SCHEMA}'") == 1
    assert scoped != sql


async def _shape(conn) -> dict:
    tables = list(_TABLES)
    columns = await conn.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable, column_default,"
            " character_maximum_length, numeric_precision, numeric_scale"
            " FROM information_schema.columns"
            " WHERE table_schema = :s AND (table_name = ANY(:t)"
            " OR (table_name = 'invoices' AND column_name = ANY(:c)))"
            " ORDER BY table_name, column_name"
        ),
        {"s": _SCHEMA, "t": tables, "c": list(_NEW_INVOICE_COLUMNS)},
    )
    constraints = await conn.execute(
        text(
            "SELECT c.relname, con.conname, pg_get_constraintdef(con.oid)"
            " FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid"
            " JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = :s AND c.relname = ANY(:t)"
            " ORDER BY c.relname, con.conname"
        ),
        {"s": _SCHEMA, "t": tables},
    )
    indexes = await conn.execute(
        text(
            "SELECT tablename, indexname, indexdef FROM pg_indexes"
            " WHERE schemaname = :s AND tablename = ANY(:t) ORDER BY tablename, indexname"
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
        "indexes": [tuple(row) for row in indexes.all()],
        "policies": [tuple(row) for row in policies.all()],
        "rls": [tuple(row) for row in rls.all()],
    }


_RULE_SQL = (
    f"INSERT INTO {_SCHEMA}.tenant_duty_rules"
    " (destination_country_code, carrier, label, effective_from, effective_to, source_url)"
    " VALUES (:country, :carrier, :label, :from_date, :to_date, :url) RETURNING id"
)
_RULE_OK = {
    "country": "US",
    "carrier": "fedex",
    "label": "Duty",
    "from_date": datetime.date(2026, 1, 1),  # asyncpg は DATE に date 型が要る（文字列は DataError）
    "to_date": None,
    "url": "https://example.com/duty",
}
_COMPONENT_SQL = (
    f"INSERT INTO {_SCHEMA}.tenant_duty_rule_components"
    " (rule_id, label, base, rate_pct, min_amount, max_amount, amount_currency)"
    " VALUES (:rule_id, :label, :base, :rate, :min_amount, :max_amount, :currency)"
)


async def _expect_error(conn, sql: str, params: dict, code: str) -> None:
    sp = await conn.begin_nested()
    with pytest.raises(DBAPIError) as exc_info:
        await conn.execute(text(sql), params)
    await sp.rollback()
    assert _sqlstate(exc_info.value) == code, (sql, params)


async def _count(conn, table: str) -> int:
    return (await conn.execute(text(f"SELECT count(*) FROM {_SCHEMA}.{table}"))).scalar_one()


async def _check_rules(conn) -> None:
    """決まりと会社の分けが効くことを確かめる。呼び出し側の取引は最後に戻す（行と役割を残さない）。"""
    rule_id = (await conn.execute(text(_RULE_SQL), _RULE_OK)).scalar_one()
    # 送料の会社は小文字・前後の空白なし・空でない形だけ（K17・第8版）
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "carrier": "FedEx"}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "carrier": " fedex"}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "carrier": ""}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "country": "us"}, "23514")  # 国は英大文字2字
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "url": ""}, "23514")  # 根拠の URL は空にできない
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "url": "   "}, "23514")
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "label": "  "}, "23514")  # 名前は空にできない
    await _expect_error(conn, _RULE_SQL, {**_RULE_OK, "to_date": datetime.date(2025, 12, 31)}, "23514")  # 終わりは始まり以降

    ok = {"rule_id": rule_id, "label": "Duty", "base": "subtotal", "rate": 10, "min_amount": None, "max_amount": None, "currency": None}
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "base": "x"}, "23514")  # 基準は3つだけ
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "rate": -1}, "23514")  # 率は0以上
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "min_amount": 10, "max_amount": 5, "currency": "USD"}, "23514")  # 下限は上限以下
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "min_amount": 10}, "23514")  # 下限があれば通貨が要る
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "min_amount": 10, "currency": "usd"}, "23514")  # 通貨は英大文字3字
    await _expect_error(conn, _COMPONENT_SQL, {**ok, "rule_id": rule_id + 100000}, "23503")  # 無い決まりは指せない
    await conn.execute(text(_COMPONENT_SQL), {**ok, "min_amount": 1, "max_amount": 100, "currency": "USD"})

    # K17: 別の会社の文脈では、どちらの表も 0 行に見える（RLS を飛ばせない役割で確かめる）
    probe = f"duty_rls_probe_{uuid.uuid4().hex[:12]}"
    await conn.execute(text(f"CREATE ROLE {probe} NOLOGIN NOSUPERUSER NOBYPASSRLS"))
    await conn.execute(text(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO {probe}"))
    for table in _TABLES:
        await conn.execute(text(f"GRANT SELECT ON {_SCHEMA}.{table} TO {probe}"))
    await conn.execute(text(f"SET LOCAL ROLE {probe}"))
    await conn.execute(text("SELECT set_config('app.tenant_id', '961', true)"))
    assert [await _count(conn, t) for t in _TABLES] == [0, 0]
    await conn.execute(text(f"SELECT set_config('app.tenant_id', '{_TENANT_ID}', true)"))
    assert [await _count(conn, t) for t in _TABLES] == [1, 1]
    await conn.execute(text("RESET ROLE"))

    await conn.execute(text(f"DELETE FROM {_SCHEMA}.tenant_duty_rules WHERE id = :id"), {"id": rule_id})
    assert await _count(conn, "tenant_duty_rule_components") == 0  # 決まりを消すと中身も消える


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
                assert len(before["rls"]) == 2
                assert all(row[1] for row in before["rls"])
                assert len(before["policies"]) == 2
                assert len([c for c in before["columns"] if c[0] == "invoices"]) == 7
                # 表と列を消してから、全テナントを回す正本をこの試験のテナントだけに絞って 2 回流す
                async with admin_engine.begin() as conn:
                    for table in reversed(_TABLES):
                        await conn.execute(text(f"DROP TABLE {_SCHEMA}.{table}"))
                    for column in _NEW_INVOICE_COLUMNS:
                        await conn.execute(text(f"ALTER TABLE {_SCHEMA}.invoices DROP COLUMN {column}"))
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
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/invoice-create-portfolio-bin-a && git log --oneline -1 | tail -1
    cd ~/sa && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
  期待: 2行目 `is-ancestor exit=0`。1 なら `BLOCKED: 手順1 is-ancestor`（取り込みは Opus が行う）。

手順2 実装前点検 P1〜P12 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/invoice-create-portfolio/card-A.md | tail -1
    cd ~/sa && ls migrations | sort | tail -1
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | tail -1
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2
    cd ~/sa && grep -c "1151" migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py | tail -2
    cd ~/sa && grep -c -E "tenant_duty|payment_method_snapshot|shipping_snapshot|tax_rate_percent|payment_account_number|shipping_service" backend/app/services/tenant.py migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/rls_bootstrap.py | tail -3
    cd ~/sa && grep -c "962" backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py | tail -2
    cd ~/sa && grep -c "    hs_code VARCHAR(20)," backend/app/services/tenant.py
    cd ~/sa && grep -c "    subtotal NUMERIC(15, 2) NOT NULL," backend/app/services/tenant.py
    cd ~/sa && grep -c "ALTER TABLE {schema}.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY;" backend/app/services/tenant.py
    cd ~/sa && grep -c "CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON {schema}.tenant_invoice_payment_wise" backend/app/services/tenant.py
    cd ~/sa && wc -l < docs/handoff/cloud-case-ai/stage1-column-class.tsv
    cd ~/sa && wc -l < scripts/run_all_migrations.sh
    cd ~/sa && tail -1 scripts/run_all_migrations.sh
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | grep -c "secretary-rulebook card-bin1（分類5行追加）$"
    cd ~/sa && ls migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql backend/tests/test_tenant_duty_rules_pg.py 2>&1 | tail -2
  期待: 3行目 `20261113_100001_create_secretary_rules_down.sql`。4行目と5行目の値は `472bfcd14f935118dadadb351601de91944964b031842ba9eee5f3d4d99fa6a6`。6行目は2ファイルとも `:1`。7行目は3ファイルとも `:0`。8行目は2ファイルとも `:0`。9行目 1。10行目 4。11行目 1。12行目 1。13行目 1058。14行目 1272。15行目 `# ADR-1077 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261113_100001_create_secretary_rules_down.sql`。16行目 1。17行目は2つとも「No such file or directory」。

手順3 §2 の変更をする（2-1、2-2、2-3、2-5 から 2-10 の順。2-4 は手順4 で行う。新規の2ファイルは Write ツール、それ以外は Edit ツールで行う）

手順4 許可一覧の sha256 を直す（2-3 の後）
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | tail -1
  出た 64 文字で §2-4 の(1)を Edit ツールで置き換え、§2-4 の(2)も Edit ツールで行う。その後:
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | awk -F'\t' '{print NF}'
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | grep -c "invoice-create-portfolio card-A（分類11行追加）$"
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
    cd ~/sa && ~/venv312/bin/ruff check backend/app/services/tenant.py backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/ops/test_ai_cloud_views.py backend/tests/test_tenant_duty_rules_pg.py 2>&1 | tail -10
    cd ~/sa && ~/venv312/bin/python -c "import ast; ast.parse(open('backend/app/services/tenant.py').read()); print('tenant.py ok')" 2>&1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py repo > ~/vw-repo.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-repo.txt
    cd ~/sa && git diff -U0 migrations/20261024_100300_create_ai_cloud_views.sql | grep -c "^+  ('tenant_\*'"
    cd ~/sa && git diff -U0 migrations/20261024_100300_create_ai_cloud_views.sql | grep -c "^-  ('"
    cd ~/sa && grep -c "1162" migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py | tail -2
    cd ~/sa && git diff -U0 backend/app/services/tenant.py | grep -c "^-"
    cd ~/sa && git diff -U0 backend/app/services/tenant.py | grep -c "^+"
    cd ~/sa && grep -c "CREATE TABLE IF NOT EXISTS {schema}.tenant_duty_rule" backend/app/services/tenant.py
    cd ~/sa && grep -c "    hs_code VARCHAR(20)," backend/app/services/tenant.py
    cd ~/sa && wc -l < docs/handoff/cloud-case-ai/stage1-column-class.tsv
    cd ~/sa && git diff -U0 docs/handoff/cloud-case-ai/stage1-column-class.tsv | grep -c "^+tenant_\*"
    cd ~/sa && awk -F'\t' 'NF != 6' docs/handoff/cloud-case-ai/stage1-column-class.tsv | wc -l
    cd ~/sa && grep -c "run_sql migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql" scripts/run_all_migrations.sh
  期待（上から順に）: ruff は `All checks passed!`／`tenant.py ok`／値の書き込みの検査は `exit=0`／7（足した分類の行）／0（消した分類の行は無い）／2ファイルとも `:1`／1（消した行は無いので、当たるのは見出しの `--- a/backend/app/services/tenant.py` の1行だけ）／79（足した行 78 と `+++ b/` の1行）／2／3／1069／11／0（どの行も6列）／1。
  repo の検査が exit=0 でなかったら、最後の 10 行を貼って `BLOCKED: value-writes`。

手順7 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_tenant_duty_rules_pg.py tests/test_tenant_loop_migration_guard.py 2>&1 | tail -15
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/ops/test_ai_cloud_views.py 2>&1 | tail -15
  期待: 1本目は failed 0・error 0 で、passed に test_tenant_duty_rules_pg.py の単体5件を含む（PG の1件は skipped でよい）。2本目は failed 0・error 0（skipped は出てよい）。

手順8 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -20
    cd ~/sa && git diff --stat | tail -20
  期待: §1 の 10 ファイルだけ（新規の2ファイルは `??` で各1行）。

手順9 記録と送り出し
    cd ~/sa && git add migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql backend/app/services/tenant.py migrations/20261024_100300_create_ai_cloud_views.sql scripts/migration-guard/reference-allowlist.tsv docs/handoff/cloud-case-ai/stage1-column-class.tsv scripts/run_all_migrations.sh backend/tests/rls_bootstrap.py backend/tests/test_tenant_loop_migration_guard.py backend/tests/ops/test_ai_cloud_views.py backend/tests/test_tenant_duty_rules_pg.py && git status --short | tail -20
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(tenant): create duty rule tables and invoice payment/tax/shipping columns per tenant (invoice-create-portfolio bin A)" && git log --oneline -1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py diff origin/main HEAD --check all > ~/vw-diff.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-diff.txt
    cd ~/sa && git push origin release/invoice-create-portfolio-bin-a 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/invoice-create-portfolio-bin-a -2 | tail -2
  `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。3行目の diff 検査が exit=0 でなかったら push せずに最後の 10 行を貼って `BLOCKED: value-writes`。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - 手順1 の is-ancestor が 0 でない・P1〜P12 のどれかが外れた → `BLOCKED: 手順1` か `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 手順4 の期待が外れた → 出力を貼って `BLOCKED: allowlist`。
  - 値の書き込みの検査（手順6・手順9）が失敗した → 最後の 10 行を貼って `BLOCKED: value-writes`。移行の文を直さない。
  - 手順6 の数の期待が外れた → 出力を貼って `BLOCKED: 手順6`。
  - 手順7 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ・タブ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - ruff が E501（行が長い）だけを出した → 直さずにそのまま書く（判定は Opus がする）。
  - 手順7 で skipped が出る → そのまま書く（実 PostgreSQL の試験は CI で動く）。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED invoice-create-portfolio-A HEAD=…`。2 行目: 「本報告はカード 便A 関税の額の表2つと請求書の5列を作る の実行結果である」。
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
