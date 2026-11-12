# card: 便2-2a 契約と請求書の public の9表・税率の口と画面（ADR-1061）

状態: カード発行（Opus、2026-11-12）。PO の設計承認と実装承認は 2026-11-12「1、推測は禁止して…確立したなら進める。」（ideal-state 54。review.md「2026-11-12 PO の設計承認」）。
改訂（Opus、2026-11-12）: §2-8 の試験の判定 8 か所を、jest-dom の判定（toHaveTextContent・toBeInTheDocument）から、既存の試験と同じ `.textContent` と `toContain`・`toBeTruthy` へ直した。理由: frontend に jest-dom が入っておらず、1回目の実装が手順8の tsc で TS2339 ×8 で止まったため（`frontend/src/test-setup.ts` は jest-dom を読まない。先例 `frontend/src/pages/super-admin/ViewerAccountsPage.test.tsx:70`）。 2回目の改訂: §2-8 の欄の探し方 4 か所に `{ exact: false }` を足した。理由: 必須欄はラベルの後ろに `*` が付き（`frontend/src/components/TextField.tsx:88`〜:90）、完全一致では見つからず、2回目の実装が手順8の vitest で 2 件落ちたため（画面に名前の付いた欄はこの 2 つだけ）。
設計: docs/handoff/viewer-contract-stage/design.md §3-4（public の表・tax_rates・RLS :297〜:310）・§3-4b（/super-admin/tax-rates）・§3-4d（税率の画面の置き場）・§8 の A14・A15・A31。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `9747e2cf1`（#5431 合流後）で行番号を測った（審査の時点 4a8893528 までの間は docs だけの変更で、変更前の文はすべて一致することを審査役が確かめた）。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
危険便か: はい（`migrations/` と本番 `scripts/run_all_migrations.sh` を含む。CI の `.github/workflows/migration-guard.yml` の許可一覧も1行変える）。マージ前に Opus の審査役の APPROVE・CI 全通過・ADR-136 の GO 記録と直前のバックアップの確認を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 便2-2 をさらに分ける。2-2a＝public の9表（形だけ）と税率の口・画面。2-2b＝AI の読み取りの区分（ai_cloud の見せない列・ops_case の個人情報の一覧・deny の正規表現 3 か所と A46）と都道府県 47 行の試験用の読み込み。2-2c＝会社ごとの4表と会社情報のページ。理由: 1便1目的（design-partner.md §5.5 の4）。2-2a は「表が在り、書けるのは運営の印のときだけ」と「税率を PO が画面で入れられる」で閉じる。
- D2 移行で行を入れない。税率の最初の行（10.00・2019-10-01）は本番反映の後に PO が画面で足す（design.md §3-4 tax_rates の2行目・ADR-1007 決定1）。都道府県 47 行は 2-2b 以降（design.md :182）。商材とプランは便2b の画面で PO が入れる。
- D3 新しい列は AI の読み取りでは既定で見せない（migrations/20261024_100300_create_ai_cloud_views.sql の作りで、区分の無い列は見せない側）。区分は 2-2b で付ける。請求書を作る便3 は 2-2b より前に出さない。
- D4 書き込みは `set_operator_context`／`reset_operator_context`（backend/app/auth/dependencies.py:454・:471）で、ハンドラの中だけ印を張り finally で戻す（先例: backend/app/routers/super_admin_suppliers.py:60〜:75 の `_operator_writes`）。backend/app/tasks/fx_rate_updater.py:70 の形は写さない。
- D5 印が接続に残らない根拠: backend/app/database.py:33（pool_reset_on_return=None）と :37〜:52（ADR-1070。返すたびに rollback → RESET ALL → commit）。PostgreSQL の SET は commit 後は接続に残り、rollback で取り消される（Context7 /websites/postgresql の sql-set.html で確かめた）。commit の後の `SET app.is_operator = ''` は commit されないまま返却時に rollback されるが、続く RESET ALL で消える。
- D6 税率の追加の決まり（design.md §3-4 tax_rates の5行目）: 表が空でないとき、適用日が「今ある最も新しい行の適用日以前」または「今日（日本時間）以前」なら 422 `tax_rate.effective_from_invalid`。表が空のときだけ過去の日付も通す。同じ日付が同時に2つ来たときは一意の制約で止め 409 `tax_rate.effective_from_taken`。
- D7 税率の削除の決まり（同 4行目）: 適用日が今日（日本時間）以前の行は 409 `tax_rate.not_deletable`。無い id は 404 `tax_rate.not_found`。消した行数が1でなければ RuntimeError で止める（A31 の処理の動き）。過去の行を直す口は作らない（PUT・PATCH なし）。
- D8 A15 の前半（適用日以降の請求書だけ変わる・発行済みは変わらない）は請求書を作る便3 で確かめる。この便は A15 の後半（422 と 409）と A14・A31 を確かめる。
- D9 A31 の DB の動きは CI の salesanchor_app（test.yml:193〜:219 で作る。超管理者でも RLS 素通りでもないことを試験の中で確かめる）で9表それぞれ確かめる。処理の動きは、この便で UPDATE か DELETE を持つ処理＝税率の削除だけ。
- D10 A14（名簿を消すと請求書と契約の viewer_account_id が NULL）は CI で確かめる。CI の表の持ち主は超管理者なので、本番の持ち主での動きは本番反映の後に Opus が読み取り専用の鍵で表の持ち主と rolsuper を読んで記録する（担当の作業ではない）。
- D11 sa_products.seller_tenant_id は ON DELETE RESTRICT（発行元の会社を消すと商材の発行元が分からなくなるため止める）。users を指す列は ON DELETE SET NULL。明細と機能は親と一緒に消える（CASCADE）。
- D12 paid_at は DATE（入金を確かめた日。時刻は持たない）。明細の amount_jpy の符号は便3 で決める（この便では CHECK を付けない）。
- D13 migration-guard.yml のチェック8（共用マスタの名前を値の行に書かない）に当たらないよう、新しい移行の COMMENT ON は1行に書き、他の行には共用マスタの表の名前を単語で書かない（sa_products は `\b` の切れ目が無いので当たらない）。手順5 で `scripts/check-migration-value-writes.py` を流して確かめる。
- D14 .github/workflows/migration-test.yml は変えない。前提の表 public.tenants（:192）・public.users（:203）・public.viewer_accounts（:928）が既に在り、権限は `IF EXISTS (pg_roles…)` で囲むので役割が無くても通る。
- D15 金額は円の整数（BIGINT）。税率は NUMERIC(5,2)（0.00〜100.00）。API は税率を文字列の10進（例 "10.00"）で返し、画面は文字列のまま見せる（小数の誤差を作らない）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（public の9表と、それに書く最初の口＝税率。D1） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/viewer-contract-bin2-2a` を作る。その枝にはこのカードだけが載っている） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順9 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P2〜P6 は 9747e2cf1 で実測。新しい表の名前が0件であることも実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED viewer-contract-bin2-2a HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便2-2a 契約と請求書の public の9表・税率の口と画面 の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/viewer-contract-stage/card-2-2a.md`（このカード）が枝に在る。
- P2 `ls migrations | sort | tail -1` が `20261112_130000_add_viewer_contracting_status.sql`。
- P3 `tail -1 scripts/run_all_migrations.sh` が `run_sql migrations/20261112_130000_add_viewer_contracting_status.sql`。
- P4 `git grep -n -E "sa_products|sa_plans|sa_plan_features|sa_contracts|tax_rates|viewer_invoices|viewer_invoice_lines|viewer_invoice_number_seq|public\.prefectures" -- migrations backend/app frontend/src .github | wc -l` が 0。
- P5 `grep -c 'path="tax-rates"' frontend/src/App.tsx` が 1、`grep -c "TaxRatesPage" frontend/src/App.tsx` が 0。
- P6 `grep -c "staff_join_invites customer_statuses\"" .github/workflows/migration-guard.yml` が 1。

## 1. 触るファイル

1. migrations/20261112_140000_create_viewer_contract_public_tables.sql（新規）
2. scripts/run_all_migrations.sh
3. .github/workflows/migration-guard.yml（PUBLIC_TABLES の1行だけ）
4. backend/app/routers/super_admin_tax_rates.py（新規）
5. backend/app/main.py
6. backend/tests/test_viewer_contract_public_tables_pg.py（新規）
7. frontend/api-contract/openapi.json（手順6 の生成だけで変える。手で書かない）
8. frontend/src/pages/super-admin/TaxRatesPage.tsx（新規）
9. frontend/src/pages/super-admin/TaxRatesPage.test.tsx（新規）
10. frontend/src/App.tsx
11. frontend/src/locales/ja.json
12. frontend/src/locales/en.json

触らない: これ以外のすべて。特に `.github/workflows/migration-test.yml`（D14）・`deploy.yml`・`migrations/20261024_100300_create_ai_cloud_views.sql`（D3。2-2b）・`backend/app/tasks/fx_rate_updater.py`（D4）・`frontend/src/components/`（金型は変えない）・`frontend/src/pages/super-admin/settings/settingsNav.ts`（並びは変えない。design.md §3-4d）・既存の migration。

## 2. 変更

### 2-1. migrations/20261112_140000_create_viewer_contract_public_tables.sql（新規。Write ツールで下の全文を書く）

```sql
-- ADR-1061 便2-2a: 契約と請求書の public の9表を作る（形だけ。行は入れない）
-- 設計: docs/handoff/viewer-contract-stage/design.md §3-4・RLS :297〜:310
-- RLS: 9表とも ENABLE と FORCE。読むのは全行可、書くのは app.is_operator='true' のときだけ（ADR-1018 Decision 3。先例 20260628_170000_add_app_fx_rates.sql:51〜:63）
-- 冪等: 表と索引は IF NOT EXISTS。CHECK は表を作る文の中に書く（表が在れば文ごと飛ぶ）。方針は DROP POLICY IF EXISTS の後に作る
-- ロールバック: 表は残してコードが使わない（表を消すのは別便・PO GO）

BEGIN;

-- 都道府県（JIS X 0401 の 01〜47）。47行は別の1回だけのデータの変更で入れる（design.md :182）
CREATE TABLE IF NOT EXISTS public.prefectures (
    code CHAR(2) PRIMARY KEY,
    name_ja TEXT NOT NULL,
    name_en TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    CONSTRAINT ck_prefectures_code CHECK (code ~ '^(0[1-9]|[1-3][0-9]|4[0-7])$'),
    CONSTRAINT ck_prefectures_name_ja CHECK (char_length(btrim(name_ja)) BETWEEN 1 AND 20),
    CONSTRAINT ck_prefectures_name_en CHECK (char_length(btrim(name_en)) BETWEEN 1 AND 40)
);

-- 商材
CREATE TABLE IF NOT EXISTS public.sa_products (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    seller_tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
    default_payment_days INTEGER NOT NULL DEFAULT 3,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sa_products_code UNIQUE (code),
    CONSTRAINT ck_sa_products_code CHECK (code ~ '^[a-z0-9][a-z0-9_-]{0,49}$'),
    CONSTRAINT ck_sa_products_name CHECK (char_length(btrim(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_sa_products_default_payment_days CHECK (default_payment_days BETWEEN 1 AND 90)
);

-- プラン
CREATE TABLE IF NOT EXISTS public.sa_plans (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES public.sa_products(id) ON DELETE RESTRICT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    billing_type TEXT NOT NULL,
    billing_interval TEXT NULL,
    unit_price_jpy BIGINT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sa_plans_product_code UNIQUE (product_id, code),
    CONSTRAINT ck_sa_plans_code CHECK (code ~ '^[a-z0-9][a-z0-9_-]{0,49}$'),
    CONSTRAINT ck_sa_plans_name CHECK (char_length(btrim(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_sa_plans_billing_type CHECK (billing_type IN ('one_time', 'subscription')),
    CONSTRAINT ck_sa_plans_billing_interval CHECK (
        (billing_type = 'one_time' AND billing_interval IS NULL)
        OR (billing_type = 'subscription' AND billing_interval IN ('month', 'year'))
    ),
    CONSTRAINT ck_sa_plans_unit_price_jpy CHECK (unit_price_jpy >= 0)
);

-- プランに含む機能（この CHECK が機能の一覧の正本。design.md §3-4）
CREATE TABLE IF NOT EXISTS public.sa_plan_features (
    plan_id BIGINT NOT NULL REFERENCES public.sa_plans(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL,
    PRIMARY KEY (plan_id, feature_key),
    CONSTRAINT ck_sa_plan_features_feature_key CHECK (feature_key IN ('inventory_view', 'sheet_distribution'))
);

-- 契約（何を売ったかの記録。閲覧者の状態の正本は viewer_accounts.status）
CREATE TABLE IF NOT EXISTS public.sa_contracts (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES public.sa_plans(id) ON DELETE RESTRICT,
    viewer_account_id BIGINT NULL REFERENCES public.viewer_accounts(id) ON DELETE SET NULL,
    tenant_id INTEGER NULL REFERENCES public.tenants(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_sa_contracts_status CHECK (status IN ('in_progress', 'active', 'cancelled'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sa_contracts_open_viewer_plan
    ON public.sa_contracts (viewer_account_id, plan_id)
    WHERE status IN ('in_progress', 'active');

-- 税率（行を足すだけ。最初の行は本番反映の後に PO が画面で足す）
CREATE TABLE IF NOT EXISTS public.tax_rates (
    id BIGSERIAL PRIMARY KEY,
    rate_percent NUMERIC(5, 2) NOT NULL,
    effective_from DATE NOT NULL,
    created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tax_rates_effective_from UNIQUE (effective_from),
    CONSTRAINT ck_tax_rates_rate_percent CHECK (rate_percent >= 0 AND rate_percent <= 100)
);

-- 請求書
CREATE TABLE IF NOT EXISTS public.viewer_invoices (
    id BIGSERIAL PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    contract_id BIGINT NULL REFERENCES public.sa_contracts(id) ON DELETE SET NULL,
    viewer_account_id BIGINT NULL REFERENCES public.viewer_accounts(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    replaces_invoice_id BIGINT NULL REFERENCES public.viewer_invoices(id) ON DELETE SET NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    due_date DATE NOT NULL,
    paid_at DATE NULL,
    paid_confirmed_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    voided_at TIMESTAMPTZ NULL,
    subtotal_jpy BIGINT NOT NULL,
    discount_total_jpy BIGINT NOT NULL DEFAULT 0,
    taxable_jpy BIGINT NOT NULL,
    tax_rate_percent NUMERIC(5, 2) NOT NULL,
    tax_amount_jpy BIGINT NOT NULL,
    total_jpy BIGINT NOT NULL,
    bill_to_snapshot JSONB NOT NULL,
    issuer_snapshot JSONB NOT NULL,
    mail_to TEXT NULL,
    mail_sent_at TIMESTAMPTZ NULL,
    mail_error TEXT NULL,
    drive_file_id TEXT NULL,
    drive_web_link TEXT NULL,
    drive_saved_at TIMESTAMPTZ NULL,
    drive_error TEXT NULL,
    created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_viewer_invoices_invoice_number UNIQUE (invoice_number),
    CONSTRAINT ck_viewer_invoices_status CHECK (status IN ('issued', 'paid', 'voided')),
    CONSTRAINT ck_viewer_invoices_amounts_nonnegative CHECK (
        subtotal_jpy >= 0 AND discount_total_jpy >= 0 AND taxable_jpy >= 0
        AND tax_amount_jpy >= 0 AND total_jpy >= 0
    ),
    CONSTRAINT ck_viewer_invoices_discount_le_subtotal CHECK (discount_total_jpy <= subtotal_jpy),
    CONSTRAINT ck_viewer_invoices_taxable CHECK (taxable_jpy = subtotal_jpy - discount_total_jpy),
    CONSTRAINT ck_viewer_invoices_total CHECK (total_jpy = taxable_jpy + tax_amount_jpy),
    CONSTRAINT ck_viewer_invoices_tax_rate_percent CHECK (tax_rate_percent >= 0 AND tax_rate_percent <= 100)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_viewer_invoices_issued_contract
    ON public.viewer_invoices (contract_id)
    WHERE status = 'issued';

-- 請求書の番号の年ごとの採番
CREATE TABLE IF NOT EXISTS public.viewer_invoice_number_seq (
    year INTEGER PRIMARY KEY,
    last_number INTEGER NOT NULL,
    CONSTRAINT ck_viewer_invoice_number_seq_year CHECK (year BETWEEN 2000 AND 9999),
    CONSTRAINT ck_viewer_invoice_number_seq_last_number CHECK (last_number >= 0)
);

-- 請求書の明細（ADR-101 の2表に分ける形）
CREATE TABLE IF NOT EXISTS public.viewer_invoice_lines (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES public.viewer_invoices(id) ON DELETE CASCADE,
    line_type TEXT NOT NULL,
    description TEXT NOT NULL,
    amount_jpy BIGINT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT ck_viewer_invoice_lines_line_type CHECK (line_type IN ('item', 'discount')),
    CONSTRAINT ck_viewer_invoice_lines_description CHECK (char_length(btrim(description)) BETWEEN 1 AND 200)
);

COMMENT ON TABLE public.prefectures IS '都道府県（JIS X 0401 の 01〜47）。行は1回だけのデータの変更で入れる。ADR-1061';
COMMENT ON TABLE public.sa_products IS '運営が売る商材。発行元の会社 seller_tenant_id を持つ。ADR-1061';
COMMENT ON TABLE public.sa_plans IS '商材の料金プラン（税抜の円）。ADR-1061';
COMMENT ON TABLE public.sa_plan_features IS 'プランに含む機能。feature_key の CHECK が機能の一覧の正本。ADR-1061';
COMMENT ON TABLE public.sa_contracts IS '何を売ったかの記録。閲覧者の状態の判定には使わない（正本は viewer_accounts.status）。ADR-1061';
COMMENT ON TABLE public.tax_rates IS '消費税率。行を足すだけ。請求書は発行日に有効な行の率を写す。ADR-1061';
COMMENT ON TABLE public.viewer_invoices IS '閲覧者の請求書。金額・宛先・発行元は発行時点の写し。ADR-1061';
COMMENT ON TABLE public.viewer_invoice_number_seq IS '請求書の番号の年ごとの採番（SELECT … FOR UPDATE で進める）。ADR-1061';
COMMENT ON TABLE public.viewer_invoice_lines IS '請求書の明細（item＝品目／discount＝値引き）。ADR-1061';
COMMENT ON COLUMN public.sa_products.default_payment_days IS '既定の支払日数（1〜90。既定 3）';
COMMENT ON COLUMN public.sa_plans.billing_interval IS 'month／year。one_time のときは NULL';
COMMENT ON COLUMN public.sa_contracts.tenant_id IS '将来の導入支援用。今は常に NULL';
COMMENT ON COLUMN public.tax_rates.effective_from IS 'この日から使う（日本時間の日付）。一意';
COMMENT ON COLUMN public.viewer_invoices.taxable_jpy IS '課税対象＝小計−値引き（CHECK で止める）';
COMMENT ON COLUMN public.viewer_invoices.paid_at IS '入金を確かめた日（日付だけ）';

-- RLS（9表とも同じ形）
ALTER TABLE public.prefectures ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prefectures FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS prefectures_read ON public.prefectures;
CREATE POLICY prefectures_read ON public.prefectures FOR SELECT USING (true);
DROP POLICY IF EXISTS prefectures_write ON public.prefectures;
CREATE POLICY prefectures_write ON public.prefectures FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_products FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_products_read ON public.sa_products;
CREATE POLICY sa_products_read ON public.sa_products FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_products_write ON public.sa_products;
CREATE POLICY sa_products_write ON public.sa_products FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_plans FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_plans_read ON public.sa_plans;
CREATE POLICY sa_plans_read ON public.sa_plans FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_plans_write ON public.sa_plans;
CREATE POLICY sa_plans_write ON public.sa_plans FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_plan_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_plan_features FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_plan_features_read ON public.sa_plan_features;
CREATE POLICY sa_plan_features_read ON public.sa_plan_features FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_plan_features_write ON public.sa_plan_features;
CREATE POLICY sa_plan_features_write ON public.sa_plan_features FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_contracts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_contracts_read ON public.sa_contracts;
CREATE POLICY sa_contracts_read ON public.sa_contracts FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_contracts_write ON public.sa_contracts;
CREATE POLICY sa_contracts_write ON public.sa_contracts FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.tax_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_rates FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tax_rates_read ON public.tax_rates;
CREATE POLICY tax_rates_read ON public.tax_rates FOR SELECT USING (true);
DROP POLICY IF EXISTS tax_rates_write ON public.tax_rates;
CREATE POLICY tax_rates_write ON public.tax_rates FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.viewer_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viewer_invoices FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS viewer_invoices_read ON public.viewer_invoices;
CREATE POLICY viewer_invoices_read ON public.viewer_invoices FOR SELECT USING (true);
DROP POLICY IF EXISTS viewer_invoices_write ON public.viewer_invoices;
CREATE POLICY viewer_invoices_write ON public.viewer_invoices FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.viewer_invoice_number_seq ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viewer_invoice_number_seq FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS viewer_invoice_number_seq_read ON public.viewer_invoice_number_seq;
CREATE POLICY viewer_invoice_number_seq_read ON public.viewer_invoice_number_seq FOR SELECT USING (true);
DROP POLICY IF EXISTS viewer_invoice_number_seq_write ON public.viewer_invoice_number_seq;
CREATE POLICY viewer_invoice_number_seq_write ON public.viewer_invoice_number_seq FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.viewer_invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viewer_invoice_lines FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS viewer_invoice_lines_read ON public.viewer_invoice_lines;
CREATE POLICY viewer_invoice_lines_read ON public.viewer_invoice_lines FOR SELECT USING (true);
DROP POLICY IF EXISTS viewer_invoice_lines_write ON public.viewer_invoice_lines;
CREATE POLICY viewer_invoice_lines_write ON public.viewer_invoice_lines FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.prefectures, public.sa_products, public.sa_plans,
            public.sa_plan_features, public.sa_contracts, public.tax_rates, public.viewer_invoices,
            public.viewer_invoice_number_seq, public.viewer_invoice_lines TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.sa_products_id_seq, public.sa_plans_id_seq,
            public.sa_contracts_id_seq, public.tax_rates_id_seq, public.viewer_invoices_id_seq,
            public.viewer_invoice_lines_id_seq TO salesanchor_app;
    END IF;
END $$;

COMMIT;
```

### 2-2. scripts/run_all_migrations.sh（最後の2行の後ろに2行足す）

変更前（ファイルの最後の2行。P3）:
```bash
# ADR-1061 便2-1: 閲覧者の状態に contracting と履歴の操作4つを足す（CHECK の付け替え・足すだけ・冪等）
run_sql migrations/20261112_130000_add_viewer_contracting_status.sql
```

変更後:
```bash
# ADR-1061 便2-1: 閲覧者の状態に contracting と履歴の操作4つを足す（CHECK の付け替え・足すだけ・冪等）
run_sql migrations/20261112_130000_add_viewer_contracting_status.sql
# ADR-1061 便2-2a: 契約と請求書の public の9表を作る（形だけ・行なし・FORCE RLS・冪等）
run_sql migrations/20261112_140000_create_viewer_contract_public_tables.sql
```

ファイルの最後が変更前の2行でない（後ろに別の行がある）→ `BLOCKED: P3`。

### 2-3. .github/workflows/migration-guard.yml（:228 の PUBLIC_TABLES の値の最後だけ）

変更前（:228 の行の終わり）:
```
 channel_masters channel_master_tenant_settings staff_join_invites customer_statuses"
```

変更後:
```
 channel_masters channel_master_tenant_settings staff_join_invites customer_statuses prefectures sa_products sa_plans sa_plan_features sa_contracts tax_rates viewer_invoices viewer_invoice_number_seq viewer_invoice_lines"
```

この行の他の部分は1字も変えない。

### 2-4. backend/app/routers/super_admin_tax_rates.py（新規。全文）

```python
"""最高管理者の消費税率の API（ADR-1061 便2-2a。design.md §3-4 tax_rates・§3-4b・§8 A15・A31）。

GET    /api/v1/super-admin/tax-rates            一覧（適用日の新しい順）と今日（日本時間）
POST   /api/v1/super-admin/tax-rates            行を足す
DELETE /api/v1/super-admin/tax-rates/{rate_id}  まだ始まっていない行だけ消す

決まり:
- 足す行の適用日は、今ある最も新しい行の適用日より後で、かつ明日（日本時間）以降。表が空のときだけ過去の日付も通す。
- 適用日が今日（日本時間）以前の行は消せない。過去の行を直す口は作らない。
- public.tax_rates は FORCE RLS。書き込みは app.is_operator='true' のときだけ通る。印はハンドラの中だけ張り、
  finally で戻す（super_admin_suppliers.py の _operator_writes と同じ寿命。接続に残らない根拠は database.py の ADR-1070）。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_super_admin, reset_operator_context, set_operator_context
from app.database import get_db
from app.models import User
from app.services.time import JST

router = APIRouter(prefix="/super-admin/tax-rates", tags=["super-admin"])

_COLS = "id, rate_percent, effective_from, created_at"


class TaxRateOut(BaseModel):
    id: int
    rate_percent: Decimal = Field(description="消費税率（%）。例 10.00")
    effective_from: date = Field(description="この日から使う（日本時間の日付）")
    created_at: datetime


class TaxRateListOut(BaseModel):
    rates: list[TaxRateOut]
    today: date = Field(description="サーバーの今日（日本時間）。画面はこれより後の行だけに削除を出す")


class TaxRateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_percent: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    effective_from: date


def _today_jst() -> date:
    return datetime.now(JST).date()


def _sqlstate(exc: IntegrityError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


@router.get("", response_model=TaxRateListOut, dependencies=[Depends(require_super_admin)])
async def list_tax_rates(db: AsyncSession = Depends(get_db)) -> TaxRateListOut:
    rows = (
        await db.execute(text(f"SELECT {_COLS} FROM public.tax_rates ORDER BY effective_from DESC"))
    ).mappings().all()
    return TaxRateListOut(rates=[TaxRateOut(**row) for row in rows], today=_today_jst())


async def _latest_effective_from(db: AsyncSession) -> date | None:
    """今ある最も新しい適用日（表が空なら None）。"""
    return (await db.execute(text("SELECT max(effective_from) FROM public.tax_rates"))).scalar_one()


@router.post("", response_model=TaxRateOut, status_code=status.HTTP_201_CREATED)
async def create_tax_rate(
    body: TaxRateIn,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> TaxRateOut:
    today = _today_jst()
    latest = await _latest_effective_from(db)
    if latest is not None and (body.effective_from <= latest or body.effective_from <= today):
        raise HTTPException(status_code=422, detail="tax_rate.effective_from_invalid")
    try:
        await set_operator_context(db)
        row = (
            await db.execute(
                text(
                    "INSERT INTO public.tax_rates (rate_percent, effective_from, created_by_user_id) "
                    f"VALUES (:rate_percent, :effective_from, :user_id) RETURNING {_COLS}"
                ),
                {"rate_percent": body.rate_percent, "effective_from": body.effective_from, "user_id": user.id},
            )
        ).mappings().one()
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if _sqlstate(exc) == "23505":
            raise HTTPException(status_code=409, detail="tax_rate.effective_from_taken") from exc
        raise
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)
    return TaxRateOut(**row)


@router.delete(
    "/{rate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_super_admin)],
)
async def delete_tax_rate(rate_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    effective_from = (
        await db.execute(text("SELECT effective_from FROM public.tax_rates WHERE id = :id"), {"id": rate_id})
    ).scalar_one_or_none()
    if effective_from is None:
        raise HTTPException(status_code=404, detail="tax_rate.not_found")
    if effective_from <= _today_jst():
        raise HTTPException(status_code=409, detail="tax_rate.not_deletable")
    try:
        await set_operator_context(db)
        deleted = (
            await db.execute(text("DELETE FROM public.tax_rates WHERE id = :id"), {"id": rate_id})
        ).rowcount
        if deleted != 1:
            raise RuntimeError(f"tax_rates delete affected {deleted} rows")
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await reset_operator_context(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

### 2-5. backend/app/main.py（2か所）

(a) import の並び（:125〜:126）

変更前:
```python
    super_admin_suppliers,
    super_admin_tcg,
```

変更後:
```python
    super_admin_suppliers,
    super_admin_tax_rates,  # ADR-1061 便2-2a: 消費税率
    super_admin_tcg,
```

(b) ルーターの登録（:580〜:582）

変更前:
```python
app.include_router(
    super_admin_tcg.router, prefix="/api/v1", tags=["super-admin"],
)
```

変更後:
```python
app.include_router(
    super_admin_tcg.router, prefix="/api/v1", tags=["super-admin"],
)
# ADR-1061 便2-2a: 消費税率（public.tax_rates）
app.include_router(
    super_admin_tax_rates.router, prefix="/api/v1", tags=["super-admin"],
)
```

### 2-6. backend/tests/test_viewer_contract_public_tables_pg.py（新規。全文）

```python
"""契約と請求書の public の9表と税率の API の試験（ADR-1061 便2-2a。design.md §8 A14・A15・A31）。

非 PG: 権限（403）と入力の形（422）。
PG（CI の使い捨て DB。pg fixture。書き込みはアプリの役割 salesanchor_app）: 9表の RLS（A31）・名簿を消したときの
SET NULL（A14）・税率の追加と削除の決まり（A15 の後半）・印が張られないときに処理が止まること（A31 の処理の動き）。
テストデータはすべて架空。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg2
import pytest
from sqlalchemy.engine import make_url

from app.database import get_db
from tests.test_super_admin_viewers import _account, _api, _call, _make_user, _prepare
from tests.test_super_admin_viewers import override_user as override_user  # noqa: F401  fixture
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture

needs_ci_pg = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true" or not os.getenv("RLS_TEST_DATABASE_URL"),
    reason="Disposable CI PostgreSQL service and app role required",
)

NEW_MIGRATION = "20261112_140000_create_viewer_contract_public_tables.sql"
BASE = "/api/v1/super-admin/tax-rates"

ROUTES = [
    ("GET", BASE, None),
    ("POST", BASE, {"rate_percent": "10.00", "effective_from": "2019-10-01"}),
    ("DELETE", f"{BASE}/1", None),
]


# ── 非 PG ─────────────────────────────────────────────────────


async def test_non_super_admin_gets_403_on_all_routes(override_user):  # noqa: F811
    override_user(_make_user(is_super_admin=False))
    for method, path, body in ROUTES:
        resp = await _call(method, path, body)
        assert resp.status_code == 403, (method, path)


@pytest.mark.parametrize(
    "body",
    [
        {"rate_percent": "100.01", "effective_from": "2030-01-01"},
        {"rate_percent": "-1", "effective_from": "2030-01-01"},
        {"rate_percent": "10.001", "effective_from": "2030-01-01"},
        {"rate_percent": "10.00", "effective_from": "2030-01-01", "extra": 1},
        {"rate_percent": "10.00"},
        {"effective_from": "2030-01-01"},
    ],
)
async def test_create_body_validation_422(override_user, body):  # noqa: F811
    from app.main import app

    async def _no_db():
        yield None

    override_user(_make_user(is_super_admin=True))
    app.dependency_overrides[get_db] = _no_db
    resp = await _call("POST", BASE, body)
    assert resp.status_code == 422


# ── PG 共通 ───────────────────────────────────────────────────


def _today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


def _app_conn_and_url(conn):
    """アプリの役割 salesanchor_app で同じ使い捨て DB へつなぐ（同期の接続と、API 用の非同期の URL）。"""
    app_url = make_url(os.environ["RLS_TEST_DATABASE_URL"]).set(database=conn.info.dbname)
    app_conn = psycopg2.connect(
        dbname=app_url.database, host=app_url.host, port=app_url.port,
        user=app_url.username, password=app_url.password,
    )
    return app_conn, app_url.set(drivername="postgresql+asyncpg")


def _setup(conn, async_url):
    cur = _prepare(conn, async_url, seed_templates=False)
    cur.execute((MIGRATIONS / NEW_MIGRATION).read_text())
    return cur


def _seed(cur):
    """管理者（RLS を通らない）で各表に1行ずつ入れる。"""
    cur.execute("INSERT INTO public.prefectures (code, name_ja, name_en, sort_order) VALUES ('13', '東京都', 'Tokyo', 13)")
    cur.execute("INSERT INTO public.sa_products (code, name, seller_tenant_id) VALUES ('p-1', 'test product', 999) RETURNING id")
    product_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO public.sa_plans (product_id, code, name, billing_type, unit_price_jpy) "
        "VALUES (%s, 'plan-1', 'test plan', 'one_time', 200000) RETURNING id",
        (product_id,),
    )
    plan_id = cur.fetchone()[0]
    cur.execute("INSERT INTO public.sa_plan_features (plan_id, feature_key) VALUES (%s, 'inventory_view')", (plan_id,))
    vid = _account(cur, "a31@example.com", "contracting", expires_in_days=3)
    cur.execute(
        "INSERT INTO public.sa_contracts (plan_id, viewer_account_id, status) VALUES (%s, %s, 'active') RETURNING id",
        (plan_id, vid),
    )
    contract_id = cur.fetchone()[0]
    cur.execute("INSERT INTO public.tax_rates (rate_percent, effective_from) VALUES (10.00, '2019-10-01')")
    cur.execute(
        "INSERT INTO public.viewer_invoices (invoice_number, contract_id, viewer_account_id, status, issued_at, due_date, "
        "subtotal_jpy, discount_total_jpy, taxable_jpy, tax_rate_percent, tax_amount_jpy, total_jpy, "
        "bill_to_snapshot, issuer_snapshot) "
        "VALUES ('INV-TEST-1', %s, %s, 'issued', now(), CURRENT_DATE + 3, 200000, 0, 200000, 10.00, 20000, 220000, "
        "'{}'::jsonb, '{}'::jsonb) RETURNING id",
        (contract_id, vid),
    )
    invoice_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO public.viewer_invoice_lines (invoice_id, line_type, description, amount_jpy, sort_order) "
        "VALUES (%s, 'item', 'line-1', 200000, 1)",
        (invoice_id,),
    )
    cur.execute("INSERT INTO public.viewer_invoice_number_seq (year, last_number) VALUES (2026, 1)")
    return vid


# 表ごとに: (表, 目印の列, 種の行の値, 2行目の値, 2行目を入れる文, UPDATE の SET)
TABLE_CASES = [
    ("prefectures", "code", "13", "14",
     "INSERT INTO public.prefectures (code, name_ja, name_en, sort_order) VALUES ('14', '神奈川県', 'Kanagawa', 14)",
     "sort_order = sort_order"),
    ("sa_products", "code", "p-1", "p-2",
     "INSERT INTO public.sa_products (code, name, seller_tenant_id) VALUES ('p-2', 'test product 2', 999)",
     "name = name"),
    ("sa_plans", "code", "plan-1", "plan-2",
     "INSERT INTO public.sa_plans (product_id, code, name, billing_type, unit_price_jpy) "
     "SELECT id, 'plan-2', 'test plan 2', 'one_time', 1000 FROM public.sa_products WHERE code = 'p-1'",
     "name = name"),
    ("sa_plan_features", "feature_key", "inventory_view", "sheet_distribution",
     "INSERT INTO public.sa_plan_features (plan_id, feature_key) "
     "SELECT id, 'sheet_distribution' FROM public.sa_plans WHERE code = 'plan-1'",
     "feature_key = feature_key"),
    ("sa_contracts", "status", "active", "cancelled",
     "INSERT INTO public.sa_contracts (plan_id, status) SELECT id, 'cancelled' FROM public.sa_plans WHERE code = 'plan-1'",
     "status = status"),
    ("tax_rates", "effective_from", "2019-10-01", "2030-01-01",
     "INSERT INTO public.tax_rates (rate_percent, effective_from) VALUES (8.00, '2030-01-01')",
     "rate_percent = rate_percent"),
    ("viewer_invoices", "invoice_number", "INV-TEST-1", "INV-TEST-2",
     "INSERT INTO public.viewer_invoices (invoice_number, status, issued_at, due_date, subtotal_jpy, "
     "discount_total_jpy, taxable_jpy, tax_rate_percent, tax_amount_jpy, total_jpy, bill_to_snapshot, issuer_snapshot) "
     "VALUES ('INV-TEST-2', 'voided', now(), CURRENT_DATE + 3, 1000, 0, 1000, 10.00, 100, 1100, '{}'::jsonb, '{}'::jsonb)",
     "mail_error = mail_error"),
    ("viewer_invoice_lines", "description", "line-1", "line-2",
     "INSERT INTO public.viewer_invoice_lines (invoice_id, line_type, description, amount_jpy, sort_order) "
     "SELECT id, 'item', 'line-2', 1000, 2 FROM public.viewer_invoices WHERE invoice_number = 'INV-TEST-1'",
     "sort_order = sort_order"),
    ("viewer_invoice_number_seq", "year", 2026, 2027,
     "INSERT INTO public.viewer_invoice_number_seq (year, last_number) VALUES (2027, 0)",
     "last_number = last_number"),
]


@needs_ci_pg
def test_public_tables_rls_and_viewer_delete_sets_null(pg):  # noqa: F811
    """A31（DB の動き。9表それぞれ）と A14（名簿を消すと請求書と契約の viewer_account_id が NULL）。"""
    conn, _, async_url = pg
    cur = _setup(conn, async_url)
    vid = _seed(cur)
    app_conn, _ = _app_conn_and_url(conn)
    try:
        acur = app_conn.cursor()
        acur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        assert acur.fetchone() == (False, False)
        app_conn.rollback()

        assert len(TABLE_CASES) == 9
        for table, key, seed_value, second_value, insert_sql, set_sql in TABLE_CASES:
            # 印なし: INSERT は RLS の誤り（42501）、UPDATE と DELETE は0行、読むのはできる
            with pytest.raises(psycopg2.Error) as exc_info:
                acur.execute(insert_sql)
            assert exc_info.value.pgcode == "42501", table
            app_conn.rollback()
            acur.execute(f"UPDATE public.{table} SET {set_sql} WHERE {key} = %s", (seed_value,))
            assert acur.rowcount == 0, table
            acur.execute(f"DELETE FROM public.{table} WHERE {key} = %s", (seed_value,))
            assert acur.rowcount == 0, table
            acur.execute(f"SELECT count(*) FROM public.{table} WHERE {key} = %s", (seed_value,))
            assert acur.fetchone()[0] == 1, table
            app_conn.rollback()

            # 印あり: 足す・直す・消すが通る
            acur.execute("SELECT set_config('app.is_operator', 'true', true)")
            acur.execute(insert_sql)
            assert acur.rowcount == 1, table
            acur.execute(f"UPDATE public.{table} SET {set_sql} WHERE {key} = %s", (seed_value,))
            assert acur.rowcount == 1, table
            acur.execute(f"DELETE FROM public.{table} WHERE {key} = %s", (second_value,))
            assert acur.rowcount == 1, table
            app_conn.commit()

        # A14: アプリの役割（印なし）で名簿の行を消す
        acur.execute("DELETE FROM public.viewer_accounts WHERE id = %s", (vid,))
        assert acur.rowcount == 1
        app_conn.commit()
    finally:
        app_conn.close()

    cur.execute("SELECT viewer_account_id, contract_id FROM public.viewer_invoices WHERE invoice_number = 'INV-TEST-1'")
    viewer_id, contract_id = cur.fetchone()
    assert viewer_id is None
    assert contract_id is not None
    cur.execute("SELECT viewer_account_id FROM public.sa_contracts WHERE id = %s", (contract_id,))
    assert cur.fetchone()[0] is None


def _api_or_error(url, method, path, body=None):
    """ASGITransport はアプリの例外をそのまま投げる。投げたときは 500 と誤りの文を返す。"""
    try:
        return _api(url, method, path, body).status_code, ""
    except Exception as exc:  # noqa: BLE001  試験の中で誤りの種類と文を確かめる
        return 500, f"{type(exc).__name__}: {exc}"


@needs_ci_pg
def test_tax_rate_api_rules_and_operator_flag(pg, monkeypatch):  # noqa: F811
    """A15 の後半（422・409 の2種・404）と A31 の処理の動き（印が張られないと止まり、行は変わらない）。"""
    conn, _, async_url = pg
    cur = _setup(conn, async_url)
    app_conn, app_async_url = _app_conn_and_url(conn)
    app_conn.close()
    today = _today_jst()
    tomorrow = today + timedelta(days=1)

    # 表が空のときだけ過去の日付が通る
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "10.00", "effective_from": "2019-10-01"})
    assert resp.status_code == 201, resp.text
    first = resp.json()
    assert Decimal(str(first["rate_percent"])) == Decimal("10.00")
    assert first["effective_from"] == "2019-10-01"
    cur.execute("SELECT created_by_user_id FROM public.tax_rates WHERE id = %s", (first["id"],))
    assert cur.fetchone()[0] == 999

    # 表が空でないとき: 今日以前・最新行以前は 422
    for value in (today.isoformat(), "2019-10-01", "2020-01-01"):
        resp = _api(app_async_url, "POST", BASE, {"rate_percent": "10.00", "effective_from": value})
        assert resp.status_code == 422, value
        assert resp.json()["detail"] == "tax_rate.effective_from_invalid"

    # 明日は通る。同じ日はもう一度は通らない（最新行以前）
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "8.00", "effective_from": tomorrow.isoformat()})
    assert resp.status_code == 201, resp.text
    future_id = resp.json()["id"]
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "8.00", "effective_from": tomorrow.isoformat()})
    assert resp.status_code == 422

    # 同時に2つ来たとき（前の確かめを素通りした）: 一意の制約で 409。行は増えない
    async def _no_latest(db):
        return None

    import app.routers.super_admin_tax_rates as tax_router

    real_latest = tax_router._latest_effective_from
    monkeypatch.setattr(tax_router, "_latest_effective_from", _no_latest)
    resp = _api(app_async_url, "POST", BASE, {"rate_percent": "8.00", "effective_from": tomorrow.isoformat()})
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == "tax_rate.effective_from_taken"
    monkeypatch.setattr(tax_router, "_latest_effective_from", real_latest)
    cur.execute("SELECT count(*) FROM public.tax_rates")
    assert cur.fetchone()[0] == 2

    # 一覧: 新しい順・今日は日本時間
    resp = _api(app_async_url, "GET", BASE)
    assert resp.status_code == 200
    data = resp.json()
    assert [r["effective_from"] for r in data["rates"]] == [tomorrow.isoformat(), "2019-10-01"]
    assert data["today"] == today.isoformat()

    # 削除: 始まった行は 409、無い id は 404、明日の行は 204
    resp = _api(app_async_url, "DELETE", f"{BASE}/{first['id']}")
    assert resp.status_code == 409
    assert resp.json()["detail"] == "tax_rate.not_deletable"
    resp = _api(app_async_url, "DELETE", f"{BASE}/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "tax_rate.not_found"
    resp = _api(app_async_url, "DELETE", f"{BASE}/{future_id}")
    assert resp.status_code == 204
    cur.execute("SELECT count(*) FROM public.tax_rates")
    assert cur.fetchone()[0] == 1

    # A31 処理の動き: 印を張る関数を空にすると、削除は0行で止まり、追加は RLS で止まる。行は変わらない
    cur.execute(
        "INSERT INTO public.tax_rates (rate_percent, effective_from) VALUES (10.00, %s) RETURNING id",
        (tomorrow + timedelta(days=1),),
    )
    later_id = cur.fetchone()[0]

    async def _no_flag(db):
        return None

    monkeypatch.setattr("app.routers.super_admin_tax_rates.set_operator_context", _no_flag)
    status_code, message = _api_or_error(app_async_url, "DELETE", f"{BASE}/{later_id}")
    assert status_code == 500
    assert message == "" or "affected 0 rows" in message, message
    cur.execute("SELECT count(*) FROM public.tax_rates WHERE id = %s", (later_id,))
    assert cur.fetchone()[0] == 1

    status_code, message = _api_or_error(
        app_async_url, "POST", BASE,
        {"rate_percent": "10.00", "effective_from": (tomorrow + timedelta(days=2)).isoformat()},
    )
    assert status_code == 500
    assert message == "" or "row-level security" in message, message
    cur.execute("SELECT count(*) FROM public.tax_rates")
    assert cur.fetchone()[0] == 2
```

### 2-7. frontend/src/pages/super-admin/TaxRatesPage.tsx（新規。全文）

```tsx
/**
 * /super-admin/settings/tax-rates — 消費税率の画面（ADR-1061 便2-2a。design.md §3-4 tax_rates・§3-4d）。
 *
 * - public.tax_rates の一覧（適用日の新しい順）と、行の追加・まだ始まっていない行の削除
 * - 足せるのは「明日以降で、いちばん新しい行より後の日付」（表が空のときだけ過去の日付も可。判定は API）
 * - 削除のボタンは、適用日がサーバーの今日（日本時間）より後の行にだけ出す
 * - is_super_admin=true のみ（Page 内で 403 ガード。API 側も require_super_admin）
 */
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import type { DataTableColumn } from "../../components/DataTable";
import { EmptyState } from "../../components/EmptyState";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import ConfirmModal from "../../components/ConfirmModal";
import { LoadingBlock } from "../../components/loading";

interface TaxRate {
  id: number;
  rate_percent: string;
  effective_from: string;
  created_at: string;
}

interface TaxRateList {
  rates: TaxRate[];
  today: string;
}

export default function TaxRatesPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [data, setData] = useState<TaxRateList | null>(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [ratePercent, setRatePercent] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TaxRate | null>(null);
  const [deleting, setDeleting] = useState(false);

  const errorText = useCallback(
    (err: unknown): string => {
      if (err instanceof ApiError) {
        if (err.responseDetail === "tax_rate.effective_from_invalid") return t("superAdmin.taxRates.errorDateInvalid");
        if (err.responseDetail === "tax_rate.effective_from_taken") return t("superAdmin.taxRates.errorDateTaken");
        if (err.responseDetail === "tax_rate.not_deletable") return t("superAdmin.taxRates.errorNotDeletable");
        if (err.responseDetail === "tax_rate.not_found") return t("superAdmin.taxRates.errorNotFound");
        if (err.status === 422) return t("superAdmin.taxRates.errorInput");
      }
      return t("superAdmin.taxRates.errorGeneric");
    },
    [t],
  );

  const load = useCallback(async () => {
    setFetching(true);
    try {
      setData(await api.get<TaxRateList>("/super-admin/tax-rates"));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setFetching(false);
    }
  }, [errorText]);

  useEffect(() => {
    if (!authLoading && isSuperAdmin) {
      void load();
    }
  }, [authLoading, isSuperAdmin, load]);

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await api.post<TaxRate>("/super-admin/tax-rates", {
        rate_percent: ratePercent,
        effective_from: effectiveFrom,
      });
      setRatePercent("");
      setEffectiveFrom("");
      setSuccess(t("superAdmin.taxRates.addSuccess"));
      await load();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setError("");
    setSuccess("");
    setDeleting(true);
    try {
      await api.delete(`/super-admin/tax-rates/${deleteTarget.id}`);
      setSuccess(t("superAdmin.taxRates.deleteSuccess"));
      setDeleteTarget(null);
      await load();
    } catch (err) {
      setDeleteTarget(null);
      setError(errorText(err));
    } finally {
      setDeleting(false);
    }
  };

  if (authLoading) {
    return <LoadingBlock />;
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminTaxRates">
        <div className="error-message" role="alert">
          {t("superAdmin.accessDenied")}
        </div>
      </PageLayout>
    );
  }

  const today = data?.today ?? "";
  const columns: DataTableColumn<TaxRate>[] = [
    { key: "effective_from", header: t("superAdmin.taxRates.effectiveFrom") },
    {
      key: "rate_percent",
      header: t("superAdmin.taxRates.ratePercent"),
      align: "right",
      renderCell: (row) => t("superAdmin.taxRates.ratePercentValue", { rate: row.rate_percent }),
    },
    {
      key: "actions",
      header: t("superAdmin.taxRates.actions"),
      renderCell: (row) =>
        row.effective_from > today ? (
          <Button
            variant="danger"
            size="sm"
            type="button"
            onClick={() => setDeleteTarget(row)}
            data-testid={`tax-rate-delete-${row.id}`}
          >
            {t("superAdmin.taxRates.deleteBtn")}
          </Button>
        ) : null,
    },
  ];

  return (
    <PageLayout navKey="nav.superAdminTaxRates" subtitleKey="superAdmin.taxRates.subtitle">
      <form onSubmit={handleAdd} data-testid="tax-rate-form">
        <ContentToolbar
          left={
            <Stack direction="row" gap="3">
              <TextField
                label={t("superAdmin.taxRates.ratePercent")}
                type="number"
                step="0.01"
                min="0"
                max="100"
                size="sm"
                required
                value={ratePercent}
                onChange={(e) => setRatePercent(e.target.value)}
              />
              <TextField
                label={t("superAdmin.taxRates.effectiveFrom")}
                type="date"
                size="sm"
                required
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
              />
            </Stack>
          }
          right={
            <Button
              variant="primary"
              size="sm"
              layoutClassName="field-h-md"
              type="submit"
              loading={saving}
              disabled={saving}
              data-testid="tax-rate-add-btn"
            >
              {t("superAdmin.taxRates.addBtn")}
            </Button>
          }
        />
      </form>
      {error && (
        <div className="error-message" role="alert" data-testid="tax-rate-error">
          {error}
        </div>
      )}
      {success && (
        <div className="success-message" role="status" data-testid="tax-rate-success">
          {success}
        </div>
      )}
      {fetching && data === null ? (
        <LoadingBlock />
      ) : (
        <DataTable<TaxRate>
          columns={columns}
          data={data?.rates ?? []}
          rowKey={(row) => String(row.id)}
          rowTestId={(row) => `tax-rate-row-${row.id}`}
          emptyState={<EmptyState title={t("superAdmin.taxRates.noData")} size="compact" />}
        />
      )}
      <ConfirmModal
        open={deleteTarget !== null}
        title={t("superAdmin.taxRates.deleteConfirmTitle")}
        message={t("superAdmin.taxRates.deleteConfirmMessage", {
          date: deleteTarget?.effective_from ?? "",
          rate: deleteTarget?.rate_percent ?? "",
        })}
        confirmLabel={t("superAdmin.taxRates.deleteBtn")}
        danger
        confirmLoading={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </PageLayout>
  );
}
```

### 2-8. frontend/src/pages/super-admin/TaxRatesPage.test.tsx（新規。全文）

```tsx
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import i18n from "../../i18n";
import TaxRatesPage from "./TaxRatesPage";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } };
});
vi.mock("../../hooks/useSuperAdmin", () => ({ useSuperAdmin: vi.fn() }));

const LIST = {
  today: "2026-11-12",
  rates: [
    { id: 2, rate_percent: "12.00", effective_from: "2027-04-01", created_at: "2026-11-12T00:00:00Z" },
    { id: 1, rate_percent: "10.00", effective_from: "2019-10-01", created_at: "2026-11-12T00:00:00Z" },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/super-admin/settings/tax-rates"]}>
      <Routes>
        <Route path="/super-admin/settings/tax-rates" element={<TaxRatesPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks();
  await i18n.changeLanguage("en");
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: true });
});

afterEach(() => {
  cleanup();
});

it("shows access denied for a non super admin and does not call the API", () => {
  vi.mocked(useSuperAdmin).mockReturnValue({ loading: false, isSuperAdmin: false });
  renderPage();
  expect((screen.getByRole("alert")).textContent).toContain(i18n.t("superAdmin.accessDenied"));
  expect(api.get).not.toHaveBeenCalled();
});

it("lists rates newest first and shows delete only for a rate that has not started", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  renderPage();
  expect((await screen.findByTestId("tax-rate-row-2")).textContent).toContain("12.00%");
  expect((screen.getByTestId("tax-rate-row-1")).textContent).toContain("10.00%");
  expect(screen.getByTestId("tax-rate-delete-2")).toBeTruthy();
  expect(screen.queryByTestId("tax-rate-delete-1")).toBeNull();
  expect(api.get).toHaveBeenCalledWith("/super-admin/tax-rates");
});

it("shows the empty state when there is no rate", async () => {
  vi.mocked(api.get).mockResolvedValue({ today: "2026-11-12", rates: [] });
  renderPage();
  expect(await screen.findByText(i18n.t("superAdmin.taxRates.noData"))).toBeTruthy();
});

it("sends the rate as a string and reloads after adding", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  vi.mocked(api.post).mockResolvedValue({ id: 3, rate_percent: "10.00", effective_from: "2028-01-01", created_at: "" });
  renderPage();
  await screen.findByTestId("tax-rate-row-2");
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.ratePercent"), { exact: false }), { target: { value: "10.00" } });
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.effectiveFrom"), { exact: false }), { target: { value: "2028-01-01" } });
  fireEvent.submit(screen.getByTestId("tax-rate-form"));
  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/super-admin/tax-rates", { rate_percent: "10.00", effective_from: "2028-01-01" }),
  );
  expect((await screen.findByTestId("tax-rate-success")).textContent).toContain(i18n.t("superAdmin.taxRates.addSuccess"));
  expect(api.get).toHaveBeenCalledTimes(2);
});

it("shows the date rule message when the API answers effective_from_invalid", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  vi.mocked(api.post).mockRejectedValue(new ApiError("x", 422, "tax_rate.effective_from_invalid"));
  renderPage();
  await screen.findByTestId("tax-rate-row-2");
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.ratePercent"), { exact: false }), { target: { value: "10" } });
  fireEvent.change(screen.getByLabelText(i18n.t("superAdmin.taxRates.effectiveFrom"), { exact: false }), { target: { value: "2026-11-12" } });
  fireEvent.submit(screen.getByTestId("tax-rate-form"));
  expect((await screen.findByTestId("tax-rate-error")).textContent).toContain(i18n.t("superAdmin.taxRates.errorDateInvalid"));
});

it("deletes a future rate after confirmation", async () => {
  vi.mocked(api.get).mockResolvedValue(LIST);
  vi.mocked(api.delete).mockResolvedValue(undefined);
  renderPage();
  fireEvent.click(await screen.findByTestId("tax-rate-delete-2"));
  const confirmButtons = await screen.findAllByRole("button", { name: i18n.t("superAdmin.taxRates.deleteBtn") });
  fireEvent.click(confirmButtons[confirmButtons.length - 1]);
  await waitFor(() => expect(api.delete).toHaveBeenCalledWith("/super-admin/tax-rates/2"));
  expect((await screen.findByTestId("tax-rate-success")).textContent).toContain(i18n.t("superAdmin.taxRates.deleteSuccess"));
});
```

### 2-9. frontend/src/App.tsx（2か所）

(a) import（:96）

変更前:
```tsx
import FxRatePage from "./pages/super-admin/FxRatePage";
```

変更後:
```tsx
import FxRatePage from "./pages/super-admin/FxRatePage";
import TaxRatesPage from "./pages/super-admin/TaxRatesPage";
```

(b) 道（:327〜:335。P5）

変更前:
```tsx
                      <Route
                        path="tax-rates"
                        element={
                          <ComingSoonPage
                            title={t("nav.superAdminTaxRates")}
                            description={t("superAdmin.settings.comingSoon")}
                          />
                        }
                      />
```

変更後:
```tsx
                      {/* 消費税率（ADR-1061 便2-2a） */}
                      <Route path="tax-rates" element={<TaxRatesPage />} />
```

ComingSoonPage の import は他の道（:258・:312・:339）が使うので消さない。

### 2-10. frontend/src/locales/ja.json（"fxRate" の塊の閉じの後ろ。:3060〜:3061）

変更前:
```json
      "rateJpy": "1 外貨 = N 円"
    },
    "inbound": {
```

変更後:
```json
      "rateJpy": "1 外貨 = N 円"
    },
    "taxRates": {
      "subtitle": "請求書に使う消費税率です。請求書は発行した日に効いている率で計算します。新しい率は明日以降の日付で足してください。",
      "effectiveFrom": "適用日",
      "ratePercent": "税率（%）",
      "ratePercentValue": "{{rate}}%",
      "actions": "操作",
      "addBtn": "追加",
      "addSuccess": "税率を追加しました。",
      "deleteBtn": "削除",
      "deleteSuccess": "税率を削除しました。",
      "deleteConfirmTitle": "税率の削除",
      "deleteConfirmMessage": "{{date}} から使う {{rate}}% の行を削除します。よろしいですか？",
      "noData": "まだ税率がありません。上の欄に率と適用日を入れて追加してください。",
      "errorDateInvalid": "この適用日では追加できません。いちばん新しい行より後で、明日以降の日付を選んでください。",
      "errorDateTaken": "同じ適用日の行がすでにあります。一覧を確認して、別の日付を選んでください。",
      "errorNotDeletable": "すでに始まった税率は削除できません。一覧を確認してください。",
      "errorNotFound": "この税率の行が見つかりません。画面を読み込み直して確認してください。",
      "errorInput": "入力の形が正しくありません。税率は 0〜100 で小数2桁まで、日付は必ず入れてください。",
      "errorGeneric": "税率の保存に失敗しました。しばらく待ってからもう一度お試しください。"
    },
    "inbound": {
```

### 2-11. frontend/src/locales/en.json（同じ場所。:3060〜:3061）

変更前:
```json
      "rateJpy": "1 Foreign = N JPY"
    },
    "inbound": {
```

変更後:
```json
      "rateJpy": "1 Foreign = N JPY"
    },
    "taxRates": {
      "subtitle": "Consumption tax rates used for invoices. An invoice uses the rate in effect on its issue date. Add a new rate with a date from tomorrow onward.",
      "effectiveFrom": "Effective from",
      "ratePercent": "Rate (%)",
      "ratePercentValue": "{{rate}}%",
      "actions": "Actions",
      "addBtn": "Add",
      "addSuccess": "Tax rate added.",
      "deleteBtn": "Delete",
      "deleteSuccess": "Tax rate deleted.",
      "deleteConfirmTitle": "Delete tax rate",
      "deleteConfirmMessage": "Delete the {{rate}}% rate effective from {{date}}?",
      "noData": "No tax rate yet. Enter a rate and an effective date above, then add it.",
      "errorDateInvalid": "This effective date cannot be added. Choose a date after the newest rate and from tomorrow onward.",
      "errorDateTaken": "A rate with the same effective date already exists. Check the list and choose another date.",
      "errorNotDeletable": "A rate that has already started cannot be deleted. Check the list.",
      "errorNotFound": "This tax rate was not found. Reload the page and check again.",
      "errorInput": "The input is not valid. Enter a rate from 0 to 100 with up to 2 decimals, and a date.",
      "errorGeneric": "Failed to save the tax rate. Please wait a moment and try again."
    },
    "inbound": {
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2a && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P6 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/viewer-contract-stage/card-2-2a.md | tail -1
    cd ~/sa && ls migrations | sort | tail -1
    cd ~/sa && tail -1 scripts/run_all_migrations.sh
    cd ~/sa && git grep -n -E "sa_products|sa_plans|sa_plan_features|sa_contracts|tax_rates|viewer_invoices|viewer_invoice_lines|viewer_invoice_number_seq|public\.prefectures" -- migrations backend/app frontend/src .github | wc -l
    cd ~/sa && grep -c 'path="tax-rates"' frontend/src/App.tsx
    cd ~/sa && grep -c "TaxRatesPage" frontend/src/App.tsx
    cd ~/sa && grep -c "staff_join_invites customer_statuses\"" .github/workflows/migration-guard.yml
  期待: 3行目 `20261112_130000_add_viewer_contracting_status.sql`・4行目 `run_sql migrations/20261112_130000_add_viewer_contracting_status.sql`・残りは順に 0・1・0・1。

手順3 §2 の変更をする（2-1 から 2-11 の順。新規のファイルは Write ツール、それ以外は Edit ツールで行う）

手順4 道具を入れる（本番と同じ Python 3.12 の venv を作業場所の外 ~/venv312 に作る。素の pip は見張り py312-guard が止めるので使わない）
    python3.12 --version 2>&1 | tail -1
    python3.12 -m venv ~/venv312 2>&1 | tail -3
    ~/venv312/bin/python --version 2>&1 | tail -1
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements.txt 2>&1 | tail -3
    cd ~/sa/backend && ~/venv312/bin/pip install -q -r requirements-dev.txt 2>&1 | tail -3
    ~/venv312/bin/ruff --version | tail -1
  python3.12 が無いときだけ、1行目と2行目の代わりに次を流す（それも失敗したら `BLOCKED: python3.12 なし`）:
    uv venv --python 3.12 ~/venv312 2>&1 | tail -3
    ~/venv312/bin/python -m ensurepip 2>&1 | tail -1

手順5 形
    cd ~/sa && ~/venv312/bin/ruff check backend/app/routers/super_admin_tax_rates.py backend/app/main.py backend/tests/test_viewer_contract_public_tables_pg.py 2>&1 | tail -10
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py repo 2>&1 | tail -10; echo "exit=$?"
    cd ~/sa && grep -c "^run_sql migrations/20261112_140000_create_viewer_contract_public_tables.sql" scripts/run_all_migrations.sh
    cd ~/sa && grep -c "customer_statuses prefectures sa_products sa_plans sa_plan_features sa_contracts tax_rates viewer_invoices viewer_invoice_number_seq viewer_invoice_lines\"" .github/workflows/migration-guard.yml
    cd ~/sa && grep -c "super_admin_tax_rates" backend/app/main.py
    cd ~/sa && grep -c "FORCE ROW LEVEL SECURITY" migrations/20261112_140000_create_viewer_contract_public_tables.sql
    cd ~/sa && grep -c '"taxRates": {' frontend/src/locales/ja.json frontend/src/locales/en.json | tail -2
  期待（上から順に）: ruff は `All checks passed!`／値の書き込みの検査は `exit=0`／1／1／2（import の行と `super_admin_tax_rates.router` の行）／9／`frontend/src/locales/ja.json:1` と `frontend/src/locales/en.json:1`。
  repo の検査が exit=0 でなかったら、最後の 10 行を貼って `BLOCKED: value-writes`。

手順6 API の形を作り直す（openapi.json は手で書かない）
    cd ~/sa/backend && ENVIRONMENT=test ~/venv312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json 2>&1 | tail -3
    cd ~/sa && git diff --stat frontend/api-contract/openapi.json | tail -3
    cd ~/sa && grep -c -E '^ *"/api/v1/super-admin/tax-rates(/\{rate_id\})?": \{' frontend/api-contract/openapi.json
  期待: diff は openapi.json の数十行。最後の grep は 2（道の見出しの行だけを数える。一覧と追加の道・削除の道）。

手順7 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_viewer_contract_public_tables_pg.py tests/test_super_admin_viewers.py 2>&1 | tail -15

手順8 frontend の点検と試験
    cd ~/sa/frontend && npm ci 2>&1 | tail -3
    cd ~/sa/frontend && npm run generate:api-types 2>&1 | tail -3
    cd ~/sa/frontend && npx tsc --noEmit 2>&1 | tail -15
    cd ~/sa/frontend && npm run check:all 2>&1 | tail -25
    cd ~/sa/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/super-admin/TaxRatesPage.test.tsx 2>&1 | tail -15
  期待: tsc は何も出ない。check:all は全部成功（最後に失敗の行が無い）。vitest は failed 0・6 passed。

手順9 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -20
    cd ~/sa && git diff --stat | tail -20
  期待: §1 の 12 ファイル（新規の5ファイルは `??` で各1行）だけ。frontend/src/api/generated の変化は git に載らない（追跡されていない）。

手順10 記録と送り出し
    cd ~/sa && git add migrations/20261112_140000_create_viewer_contract_public_tables.sql scripts/run_all_migrations.sh .github/workflows/migration-guard.yml backend/app/routers/super_admin_tax_rates.py backend/app/main.py backend/tests/test_viewer_contract_public_tables_pg.py frontend/api-contract/openapi.json frontend/src/pages/super-admin/TaxRatesPage.tsx frontend/src/pages/super-admin/TaxRatesPage.test.tsx frontend/src/App.tsx frontend/src/locales/ja.json frontend/src/locales/en.json && git status --short | tail -20
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py diff origin/main HEAD --check all 2>&1 | tail -10
    cd ~/sa && git commit -q -m "feat(viewer): add public contract and invoice tables with operator-only RLS and tax rate screen (ADR-1061 bin2-2a)" && git log --oneline -1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py diff origin/main HEAD --check all 2>&1 | tail -10; echo "exit=$?"
    cd ~/sa && git push origin release/viewer-contract-bin2-2a 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-contract-bin2-2a -2 | tail -2
  `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。2行目（commit 前の diff 検査）は HEAD に新規の移行がまだ無いので結果は見るだけ。commit の後の4行目が失敗したら push せずに最後の 10 行を貼って `BLOCKED: value-writes`。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P6 のどれかが外れた → `BLOCKED: P番号`。
  - §2 の変更前の文が見つからない・2 か所ある → `BLOCKED: ファイル名 変更前の文`。
  - 値の書き込みの検査（手順5・手順10）が失敗した → 最後の 10 行を貼って `BLOCKED: value-writes`。移行の文を直さない。
  - 手順6 の生成が失敗した → 最後の 3 行を貼って `BLOCKED: openapi`。
  - 手順7 で failed か error が 1 件でも出た → 試験を直さず最後の 15 行を貼って `BLOCKED: pytest`。ただしカードからの書き写し間違い（字・字下げ）が出力から分かるときだけ、カードの文に合わせて直してよい。直したら何をどう直したかを書く。
  - 手順8 の tsc・check:all・vitest が失敗した → 最後の 25 行を貼って `BLOCKED: frontend`。書き写し間違いの扱いは上と同じ。check:all の中の page-size・content-toolbar・stories など、画面の作りの決まりで止まったときも直さずに止める（金型の使い方は Opus が決める）。
  - push が拒まれた → 最後の 3 行を貼って `BLOCKED: push`（force はしない）。
- 記録して続ける（値を報告に書き、判定は Opus がする）:
  - ruff が I（並び順）だけを出した → `~/venv312/bin/ruff check --fix --select I` を同じファイルに流して、その結果を書く。I 以外を出したら `BLOCKED: ruff`。
  - 手順7 で skipped が出る → そのまま書く（実 PostgreSQL の試験は CI で動く）。
  - 手順8 の npm ci で警告（WARN）が出た → そのまま書く。

## 5. 報告の形

- 宛先: 完了報告の本文（クラウドの実行の最後の返事）。ファイルに書かない。
- 1 行目: `RECEIVED viewer-contract-bin2-2a HEAD=…`。2 行目: 「本報告はカード 便2-2a 契約と請求書の public の9表・税率の口と画面 の実行結果である」。
- 手順2・4・5・6・7・8・9・10 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の5ファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 改訂3（CI の赤2件の直し。§1〜§3 は済み。この改訂ではこの §7 だけを行う）

### 7-0. Opus の決めごと（根拠つき）

- 赤1: CI の pytest で `tests/test_realtime_topics.py::test_every_write_route_is_in_exactly_one_table` が `どちらの表にも無い書き込みルート: [('DELETE', '/api/v1/super-admin/tax-rates/{rate_id}'), ('POST', '/api/v1/super-admin/tax-rates')]` で落ちた（run 43137843774、1 failed・8804 passed）。新しい書き込みの口は backend/app/realtime/topics.py の WRITE_ROUTE_TOPICS か NO_SIGNAL_ROUTES のどちらか一方に載せる決まり（ADR-1016・同ファイル :4）。カードに入れ忘れた。税率は最高管理者だけの画面で、保存のあと画面が自分で読み直す（TaxRatesPage.tsx :94・:111 の `await load()`）。閲覧者の文面テンプレート（topics.py :143）と同じ扱いで NO_SIGNAL_ROUTES に載せる。
- 赤2（PR が衝突）: main に `migrations/20261112_140000_customer_status_fk.sql` が入った（main 0d58e6952）。刻印 20261112_140000 が本件の移行と重なる。migration-guard.yml の刻印重複の検査（main の :306〜:334）は、main に既にある刻印と同じ新規の移行を止める。本件の移行を 20261112_150000 に改名する（中身は1文字も変えない）。scripts/run_all_migrations.sh は main の2行の後ろに本件の2行を置く（刻印の順と実行の順が揃う）。

### 7-1. 触るファイル（この改訂で変わるのはこれだけ）

1. scripts/run_all_migrations.sh（衝突の解消と名前の付け替え）
2. migrations/20261112_140000_create_viewer_contract_public_tables.sql → migrations/20261112_150000_create_viewer_contract_public_tables.sql（git mv。中身は不変）
3. backend/tests/test_viewer_contract_public_tables_pg.py（:31 の1行）
4. backend/app/realtime/topics.py（:143 の後ろに2行）

main の取り込みで main 側のファイル（customer_status_fk の移行・試験・台帳など）が合流の記録に入るのは正しい。手で触らない。

### 7-2. 手順

手順A 枝を取り、先端を確かめる
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2a && git log --oneline -1 | tail -1
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com"
    cd ~/sa && grep -c "^## 7. 改訂3" docs/handoff/viewer-contract-stage/card-2-2a.md
  期待: 最後の grep は 1。

手順B main を取り込む（衝突は scripts/run_all_migrations.sh の1か所だけのはず）
    cd ~/sa && git fetch -q origin main && git merge --no-edit origin/main 2>&1 | tail -5
    cd ~/sa && git diff --name-only --diff-filter=U | tail -5
  期待: 2行目は `scripts/run_all_migrations.sh` だけ。ほかのファイルが出たら `git merge --abort` して `BLOCKED: 想定外の衝突`。
  scripts/run_all_migrations.sh の最後を Edit ツールで次の5行にする（衝突の印 `<<<<<<<`・`=======`・`>>>>>>>` の行を消し、main の2行を先、本件の2行を後ろにする。本件の行はこの時点で新しい名前にする）:

    run_sql migrations/20261112_130000_add_viewer_contracting_status.sql
    # 会社と連絡先の状態 便2: status 列を public.customer_statuses に外部キーで結び、旧 CHECK を外す（済みの領域は飛ばす・冪等）
    run_sql migrations/20261112_140000_customer_status_fk.sql
    # ADR-1061 便2-2a: 契約と請求書の public の9表を作る（形だけ・行なし・FORCE RLS・冪等）
    run_sql migrations/20261112_150000_create_viewer_contract_public_tables.sql

手順C 改名と2か所の変更
    cd ~/sa && git mv migrations/20261112_140000_create_viewer_contract_public_tables.sql migrations/20261112_150000_create_viewer_contract_public_tables.sql && ls migrations | grep -c "create_viewer_contract_public_tables"
  backend/tests/test_viewer_contract_public_tables_pg.py :31 を Edit ツールで
    変更前: NEW_MIGRATION = "20261112_140000_create_viewer_contract_public_tables.sql"
    変更後: NEW_MIGRATION = "20261112_150000_create_viewer_contract_public_tables.sql"
  backend/app/realtime/topics.py を Edit ツールで、次の1行（変更前の文）の直後に2行を足す:
    変更前の文（:143・この1行は変えない）:
    ("PUT", "/api/v1/super-admin/viewer-templates/{key}"): "閲覧者管理 段11: 文面テンプレートの本文を直すだけで画面更新の通知対象外（保存した画面は応答で差し替える）",
    足す2行（字下げは上の行と同じ空白4つ）:
    ("POST", "/api/v1/super-admin/tax-rates"): "消費税率 ADR-1061 便2-2a: 最高管理者だけが使う税率の追加で画面更新の通知対象外（保存した画面は自分で読み直す）",
    ("DELETE", "/api/v1/super-admin/tax-rates/{rate_id}"): "消費税率 ADR-1061 便2-2a: 最高管理者だけが使う税率の削除で画面更新の通知対象外（保存した画面は自分で読み直す）",

手順D 形の確かめ
    cd ~/sa && grep -c -E "^(<<<<<<<|=======|>>>>>>>)" scripts/run_all_migrations.sh
    cd ~/sa && tail -5 scripts/run_all_migrations.sh
    cd ~/sa && grep -c "20261112_140000_create_viewer_contract_public_tables" scripts/run_all_migrations.sh backend/tests/test_viewer_contract_public_tables_pg.py | tail -2
    cd ~/sa && grep -c "super-admin/tax-rates" backend/app/realtime/topics.py
    cd ~/sa && git diff --cached -M --stat HEAD -- migrations/ | tail -3
    cd ~/sa && ls migrations | grep "^20261112_" | tail -5
  期待: 0／上の5行と同じ／両方 :0／2／rename の1行（`=> 20261112_150000_...` で 0 の増減）／120000・130000・140000_customer_status_fk・150000_create_viewer の4行。

手順E 試験（道具は §3 手順4 と同じ ~/venv312 を作る）
    （§3 手順4 の6行をそのまま流す）
    cd ~/sa && ~/venv312/bin/ruff check backend/app/realtime/topics.py backend/tests/test_viewer_contract_public_tables_pg.py 2>&1 | tail -5
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_realtime_topics.py tests/test_viewer_contract_public_tables_pg.py 2>&1 | tail -15
  期待: ruff は `All checks passed!`。pytest は failed 0・error 0（実 PostgreSQL の試験は skipped でよい）。

手順F 記録と送り出し（合流の記録は1つ。改名と2か所は同じ合流の記録に入れる）
    cd ~/sa && git add scripts/run_all_migrations.sh backend/tests/test_viewer_contract_public_tables_pg.py backend/app/realtime/topics.py && git status --short | tail -20
    cd ~/sa && git commit -q --no-edit && git log --oneline -1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py diff origin/main HEAD --check all 2>&1 | tail -10; echo "exit=$?"
    cd ~/sa && git diff --name-only origin/main...HEAD | tail -20
    cd ~/sa && git push origin release/viewer-contract-bin2-2a 2>&1 | tail -3
  期待: status に出るのは main 側から来たファイル（M か A）と、7-1 の4つだけ。値の書き込みの検査は exit=0。4行目は本件の14ファイル（移行は 20261112_150000 の名前）に topics.py を足した15ファイルだけ。外れたら push せず `BLOCKED: 範囲`。

### 7-3. 分かれ道

- 衝突が run_all_migrations.sh 以外にも出た／手順D・E・F の期待が外れた → その場で止め、出力を貼って `BLOCKED: 手順の記号`。別のやり方を試さない。
- push が拒まれた → `BLOCKED: push`（force はしない）。
- 報告は §5 の形（1 行目は `RECEIVED viewer-contract-bin2-2a-rev3 HEAD=…`、手順A〜F の出力をそのまま貼る、最後は `DONE` か `BLOCKED: 理由`）。

END OF CARD
