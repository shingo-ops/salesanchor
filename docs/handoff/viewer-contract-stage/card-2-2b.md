# card: 便2-2b AI の読み取りの区分と都道府県47行の試験用の読み込み（ADR-1061）

状態: カード発行（Opus、2026-11-12）。PO の設計承認と実装承認は 2026-11-12「1、推測は禁止して…確立したなら進める。」（ideal-state 54。review.md「2026-11-12 PO の設計承認」）。
設計: docs/handoff/viewer-contract-stage/design.md §3-4（:180〜:185 都道府県の一覧・:281〜:292 隠す設定）・§8 の A30（一部）・A46。ADR-1061 決定9。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret・DB には触らない。PR は作らない（Opus が作る）。
基準: origin/main `6b086f13c`（便2-2a #5438 合流後）で行番号を測った。行番号がずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で停止）。
危険便か: はい（`migrations/` の毎回流れる SQL 4本と、`scripts/migration-guard/reference-allowlist.tsv` を変える）。マージ前に Opus の審査役の APPROVE・CI 全通過・ADR-136 の GO 記録と直前のバックアップの確認を必須にする（担当の作業ではない）。

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

## Opus の決めごと（このカードで固めたこと。根拠つき）

- D1 この便の目的は「便2-2a で作った public の9表を、AI の読み取りの道で正しく扱う」と「都道府県47行を試験で読めるようにする」の2つで、どちらも新しい表も新しい移行ファイルも作らない（card-2-2a.md D1 の分け方）。会社ごとの4表（発行元・振込先の一覧・銀行・Wise）と、その表の分類の行（'tenant_*'）は、表を作る便2-2c で一緒に足す。この便では、名前の一覧（ops_case.deny_tables）だけ先に5つ足す（名前だけの一覧なので表が無くても害が無い。design.md :282 の「個人情報の表の一覧」）。
- D2 列名の拒否の一覧（正規表現）は `^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$` にする（design.md :287）。直すのは (a) migrations/20261017_130100_create_ai_ro_views.sql:23 (b) migrations/20261024_100000_create_ai_cloud_meta.sql:76 (c) backend/app/ops/readonly_query.py:42 の3か所。試験の2ファイル（backend/tests/ops/test_ai_cloud_views.py:43・backend/tests/ops/test_ai_ro_views.py:30）は文字を持たず (c) を import する（design.md :288）。
- D3 今この新しい語に当たる列は tenant_carrier_credentials.account_number_encrypted だけで、これは既に `_encrypted$` で隠れている（design.md :286。2026-11-12 に origin/main 6b086f13c の migrations・backend/app・backend/tests を `git grep -i -E "account_number|\biban\b"` で読み直し、DB の列は増えていないことを確かめた）。足しても今見えている列は減らない。
- D4 (a)(b) は scripts/run_all_migrations.sh が毎回流す（ai_ro は最後の作り直し・(b) は :1199）。(c) は Mac の読み取りの道が結果の列を落とすときに使う。新しい移行ファイルは作らない（design.md :291）。(a)(b) は reference-allowlist.tsv に載っていない（登録は 20261024_100300 の1行だけ）。
- D5 分類表（migrations/20261024_100300_create_ai_cloud_views.sql）に 13 行（23 列）を足す。表ごとの理由:
  - 決まった値しか入らない列（CHECK の名前が付いている）: prefectures.code（ck_prefectures_code）・sa_contracts.status・sa_plan_features.feature_key・sa_plans.billing_interval・sa_plans.billing_type・viewer_invoice_lines.line_type・viewer_invoices.status → allow。理由の書き方は今ある行と同じ `値の決まり ck_xxx で値が限られる`。
  - 運営だけが入れる一覧の名前と記号（人や取引先の情報ではない）: prefectures.name_en・name_ja、sa_plans.code・name、sa_products.code・name → allow。理由は【名前を含む】で始める（:181 の pokemon_dex と同じ書き方）。
  - 請求書の宛先と発行元の写し・送り先のメール・誤りの文・ドライブの番号・請求書番号・明細の説明 → mask（理由は空。今ある mask の行と同じ）。
  - viewer_invoices.mail_sent_at は時刻の型で型として通るが、名前の見張り（"mail"）に当たるので、今ある :609 の並びと同じ「型で通る」行を置く。
  - 残りの列（数・日付・番号）は型で通り、名前の見張りにも当たらない（2026-11-12 に 20261112_150000 の列を1本ずつ照合）。tax_rates と viewer_invoice_number_seq は行が要らない。
- D6 分類表のファイルは reference-allowlist.tsv:7 に sha256 で登録されているので、同じ変更で sha256 と4列目（決めごとの記録）を直す。4列目の最後に ` / viewer-contract-stage card-2-2b（分類23行追加）` を足す（先例: 末尾の `status-ssot-contact-company card-bin1（分類3行追加）`）。
- D7 分類表の行数の試験（backend/tests/ops/test_ai_cloud_views.py:484）と冒頭の説明（20261024_100300:3）の 1086 を 1109 にする（1086＋23）。
- D8 新しい列が分類されていることは、今ある「本番の順に近い DB で流して漏れが無い」試験（:693 の ai_job の試験）と同じ形の試験を1本足して CI で確かめる。加えて、請求書の表の8列が mask、status と mail_sent_at が pass で作られたことを build_columns で確かめる。
- D9 都道府県47行の正本は docs/handoff/viewer-contract-stage/data/prefectures.sql（Opus がこのカードと一緒に置いた。JIS X 0401 と 47行すべて照合済み）。試験は backend/tests/seed_data.py の新しい関数がこのファイルをそのまま読む（先例: :62〜:64 の customer_statuses_seed_sql）。値を Python に書かない。
- D10 A30 のうち「試験の seed で47行」「frontend/src に北海道が0件」をこの便で確かめる。「API が47行を返す」は都道府県の口を作る便2-2c で確かめる。
- D11 本番への47行の投入は、この便の本番反映の後に Opus が「1回だけのデータの変更」（DRY-RUN → COMMIT）で行う（design.md :182・:523）。担当の作業ではない。
- D12 ADR-1061 は Opus がこのカードと同じ docs の PR で Accepted に上げる（決定9 は「本 ADR が Accepted になったときに効く」と書かれているため。ADR-1061:8）。根拠は PO の設計承認（2026-11-12、ideal-state 54）。担当の作業ではない。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は担当が作らない（Opus が作る） | ○（冒頭・§5） |
| 3 | 報告の宛先と生出力の扱い | ○（§5。完了報告の本文に各手順の出力を tail の範囲でそのまま貼る） |
| 4 | 1便1目的 | ○（便2-2a の9表を AI の読み取りの道で正しく扱う。都道府県の正本の読み込みは同じ表の試験の準備。D1） |
| 5 | 既存ブランチへの追記ではない | ○（このカードが main に入った後、Opus が origin/main から新しい実装の枝 `release/viewer-contract-bin2-2b` を作る） |
| 6 | 書式は実例で示した | ○（§2 に変更前・変更後の全文） |
| 7 | 合格基準を出力まで縛った | ○（§3 の各手順の期待） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（手順8 の `git status --short` と `git diff --stat`） |
| 9 | 出力量に上限のないコマンドを使わない | ○（すべて tail か wc） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§4・§5・末尾） |
| 11 | 期待値は実測から | ○（P2〜P9 は 6b086f13c で実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§4） |
| 13 | 委任文の定型4点 | ○（§6） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない（commit は git log で確かめる） | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。プレースホルダを残さない | ○（§2 は全文。sha256 だけは手順4 で測った値を入れる） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED viewer-contract-bin2-2b HEAD=`（続けて `git rev-parse HEAD` の 40 桁）。2 行目に「本報告はカード 便2-2b AI の読み取りの区分と都道府県47行の試験用の読み込み の実行結果である」と書く。

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 `docs/handoff/viewer-contract-stage/card-2-2b.md`（このカード）が枝に在る。
- P2 `ls migrations | sort | tail -1` が `20261112_150000_create_viewer_contract_public_tables.sql`。
- P3 `grep -c "private_key|credential';"` が migrations/20261017_130100_create_ai_ro_views.sql と migrations/20261024_100000_create_ai_cloud_meta.sql でそれぞれ 1。`grep -c 'private_key|credential")' backend/app/ops/readonly_query.py` が 1。
- P4 `grep -c "private_key|credential"` が backend/tests/ops/test_ai_cloud_views.py と backend/tests/ops/test_ai_ro_views.py でそれぞれ 1。
- P5 `grep -c "1086"` が migrations/20261024_100300_create_ai_cloud_views.sql と backend/tests/ops/test_ai_cloud_views.py でそれぞれ 1。
- P6 `grep -c -E "'(prefectures|sa_contracts|sa_plan_features|sa_plans|sa_products|viewer_invoice_lines|viewer_invoices)'" migrations/20261024_100300_create_ai_cloud_views.sql` が 0。
- P7 `grep -c "('viewer_billing_profiles', '請求先（宛名・住所・電話）');" migrations/20261031_210000_create_ops_case.sql` が 1。
- P8 `grep -c "^  ('" docs/handoff/viewer-contract-stage/data/prefectures.sql` が 47。
- P9 `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の値と `sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2` が、どちらも `f7543436f6345b02b8ac73f0e9c31b05bc67b48772243cf3b43fb6037f4e4929`。

## 1. 触るファイル

1. migrations/20261017_130100_create_ai_ro_views.sql（1行）
2. migrations/20261024_100000_create_ai_cloud_meta.sql（1行）
3. backend/app/ops/readonly_query.py（2行）
4. migrations/20261024_100300_create_ai_cloud_views.sql（説明1行と分類13行）
5. scripts/migration-guard/reference-allowlist.tsv（7行目の sha256 と4列目）
6. migrations/20261031_210000_create_ops_case.sql（名前の一覧に5行）
7. backend/tests/ops/test_ai_cloud_views.py
8. backend/tests/ops/test_ai_ro_views.py
9. backend/tests/ops/test_deny_column_regex_sync.py（新規）
10. backend/tests/ops/test_ops_case_db.py
11. backend/tests/seed_data.py
12. backend/tests/test_viewer_contract_public_tables_pg.py
13. backend/tests/test_prefectures_seed.py（新規）

触らない: docs/ 全部（正本の prefectures.sql も変えない）・scripts/run_all_migrations.sh（新しい移行ファイルは無い）・.github/・frontend/・backend/app のほかのファイル・migrations のほかのファイル。

## 2. 変更

### 2-1. migrations/20261017_130100_create_ai_ro_views.sql（:23）

変更前:
```
  deny constant text := '^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential';
```
変更後:
```
  deny constant text := '^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$';
```

### 2-2. migrations/20261024_100000_create_ai_cloud_meta.sql（:76）

変更前と変更後は 2-1 と同じ文（字下げも同じ2文字）。

### 2-3. backend/app/ops/readonly_query.py（:41〜:42）

変更前:
```
# ai_ro ビュー生成（migrations/*_create_ai_ro_views.sql）の拒否リストと同じ正規表現
DENY_COLUMN_RE = re.compile(r"^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential")
```
変更後:
```
# 列名の拒否リストの正本（ADR-1061 決定9）。migrations/20261017_130100_create_ai_ro_views.sql と
# migrations/20261024_100000_create_ai_cloud_meta.sql の deny は同じ文字（backend/tests/ops/test_deny_column_regex_sync.py が確かめる）
DENY_COLUMN_RE = re.compile(
    r"^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential|account_number|^iban$"
)
```

### 2-4. migrations/20261024_100300_create_ai_cloud_views.sql（5か所）

(1) :3

変更前:
```
-- 1) 分類表 ai_cloud_meta.column_class を空にして下の 1086 行を入れ直す（このファイルが正本。行の足し引きはこの SQL の変更で行う）。
```
変更後:
```
-- 1) 分類表 ai_cloud_meta.column_class を空にして下の 1109 行を入れ直す（このファイルが正本。行の足し引きはこの SQL の変更で行う）。
```

(2) :182 の行の後ろに2行足す。

変更前:
```
  ('public','pokemon_dex',ARRAY['region'],'allow','共用マスタ（運営が入れる一覧）。作品の地方区分'),
  ('public','product_attribute_masters',ARRAY['attribute'],'mask',''),
```
変更後:
```
  ('public','pokemon_dex',ARRAY['region'],'allow','共用マスタ（運営が入れる一覧）。作品の地方区分'),
  ('public','prefectures',ARRAY['code'],'allow','値の決まり ck_prefectures_code で値が限られる（JIS X 0401 の 01〜47）'),
  ('public','prefectures',ARRAY['name_en','name_ja'],'allow','【名前を含む】共用マスタ（運営だけが入れる一覧）。都道府県の名前（実在の人ではない）'),
  ('public','product_attribute_masters',ARRAY['attribute'],'mask',''),
```

(3) :222 の行の後ろに6行足す。

変更前:
```
  ('public','rule_test_runs',ARRAY['state'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
  ('public','source_messages',ARRAY['raw_sha256','raw_text'],'mask',''),
```
変更後:
```
  ('public','rule_test_runs',ARRAY['state'],'mask','値の決まりが無く自由に入る列のため伏せる（初期は最小）'),
  ('public','sa_contracts',ARRAY['status'],'allow','値の決まり ck_sa_contracts_status で値が限られる'),
  ('public','sa_plan_features',ARRAY['feature_key'],'allow','値の決まり ck_sa_plan_features_feature_key で値が限られる'),
  ('public','sa_plans',ARRAY['billing_interval'],'allow','値の決まり ck_sa_plans_billing_interval で値が限られる（NULL か month・year）'),
  ('public','sa_plans',ARRAY['billing_type'],'allow','値の決まり ck_sa_plans_billing_type で値が限られる'),
  ('public','sa_plans',ARRAY['code','name'],'allow','【名前を含む】運営だけが入れる一覧。自社の売り物のプランの記号と名前（人や取引先の情報ではない）'),
  ('public','sa_products',ARRAY['code','name'],'allow','【名前を含む】運営だけが入れる一覧。自社の売り物の商材の記号と名前（人や取引先の情報ではない）'),
  ('public','source_messages',ARRAY['raw_sha256','raw_text'],'mask',''),
```

(4) :310 の行の後ろに4行足す。

変更前:
```
  ('public','viewer_discord_config',ARRAY['guild_id','reception_channel_id','staff_role_id','ticket_category_id'],'mask',''),
  ('public','viewer_login_events',ARRAY['client_ip'],'mask',''),
```
変更後:
```
  ('public','viewer_discord_config',ARRAY['guild_id','reception_channel_id','staff_role_id','ticket_category_id'],'mask',''),
  ('public','viewer_invoice_lines',ARRAY['description'],'mask',''),
  ('public','viewer_invoice_lines',ARRAY['line_type'],'allow','値の決まり ck_viewer_invoice_lines_line_type で値が限られる'),
  ('public','viewer_invoices',ARRAY['bill_to_snapshot','drive_error','drive_file_id','drive_web_link','invoice_number','issuer_snapshot','mail_error','mail_to'],'mask',''),
  ('public','viewer_invoices',ARRAY['status'],'allow','値の決まり ck_viewer_invoices_status で値が限られる'),
  ('public','viewer_login_events',ARRAY['client_ip'],'mask',''),
```

(5) :609 の行の後ろに1行足す。

変更前:
```
  ('public','quantity_units',ARRAY['display_order'],'allow','数・日付・uuid・真偽の型で文字を持たない（型で通る。名前の見張りに当たるため行を置く）'),
  ('public','weight_classes',ARRAY['display_order'],'allow','数・日付・uuid・真偽の型で文字を持たない（型で通る。名前の見張りに当たるため行を置く）'),
```
変更後:
```
  ('public','quantity_units',ARRAY['display_order'],'allow','数・日付・uuid・真偽の型で文字を持たない（型で通る。名前の見張りに当たるため行を置く）'),
  ('public','viewer_invoices',ARRAY['mail_sent_at'],'allow','数・日付・uuid・真偽の型で文字を持たない（型で通る。名前の見張りに当たるため行を置く）'),
  ('public','weight_classes',ARRAY['display_order'],'allow','数・日付・uuid・真偽の型で文字を持たない（型で通る。名前の見張りに当たるため行を置く）'),
```

### 2-5. scripts/migration-guard/reference-allowlist.tsv（7行目の2か所。手順4 で 2-4 の後に行う）

(1) 2列目の sha256: 変更前 `f7543436f6345b02b8ac73f0e9c31b05bc67b48772243cf3b43fb6037f4e4929` → 変更後は手順4 の `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` が出した 64 文字。Edit ツールで置き換える（タブは触らない）。

(2) 行の最後:

変更前:
```
status-ssot-contact-company card-bin1（分類3行追加）
```
変更後:
```
status-ssot-contact-company card-bin1（分類3行追加） / viewer-contract-stage card-2-2b（分類23行追加）
```

### 2-6. migrations/20261031_210000_create_ops_case.sql（:102。名前の一覧の最後）

変更前:
```
        ('viewer_billing_profiles', '請求先（宛名・住所・電話）');
```
変更後:
```
        ('viewer_billing_profiles', '請求先（宛名・住所・電話）'),
        ('viewer_invoices', '閲覧者の請求書（宛先と発行元の写し・送り先のメール）'),
        ('tenant_issuer_profiles', '請求書の発行元（会社名・住所・電話・登録番号）'),
        ('tenant_invoice_payment_methods', '請求書の振込先の一覧'),
        ('tenant_invoice_payment_bank', '振込先の銀行口座'),
        ('tenant_invoice_payment_wise', '振込先の Wise 口座');
```

### 2-7. backend/tests/ops/test_ai_cloud_views.py（4か所）

(1) import（:21〜:22）

変更前:
```
import pytest

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
```
変更後:
```
import pytest

from app.ops.readonly_query import DENY_COLUMN_RE

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
```

(2) :43

変更前:
```
_DENY_RE = re.compile(r"^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential")
```
変更後:
```
_DENY_RE = DENY_COLUMN_RE  # 正本は backend/app/ops/readonly_query.py（ADR-1061 A46）
```

(3) :484

変更前:
```
    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1086
```
変更後:
```
    assert _rows(pg, "SELECT count(*) FROM ai_cloud_meta.column_class")[0][0] == n0 == 1109
```

(4) `def test_t10_detects_added_columns(pg):`（:739）の直前（ai_job の試験の終わりの空行2つの後ろ）に、次をそのまま足す（最後に空行2つ）。

```python
# ADR-1061 便2-2b: 契約と請求書の public の9表の23列に column_class の行があることを名前で確かめる。
_VIEWER_ACCOUNTS_SQL = "20261016_150000_add_viewer_accounts.sql"
_VIEWER_CONTRACT_SQL = "20261112_150000_create_viewer_contract_public_tables.sql"
_VIEWER_CONTRACT_TABLES = {
    "prefectures", "sa_products", "sa_plans", "sa_plan_features", "sa_contracts", "tax_rates",
    "viewer_invoices", "viewer_invoice_number_seq", "viewer_invoice_lines",
}  # fmt: skip
_VIEWER_INVOICE_MASKED = {
    "bill_to_snapshot", "drive_error", "drive_file_id", "drive_web_link",
    "invoice_number", "issuer_snapshot", "mail_error", "mail_to",
}  # fmt: skip
_VIEWER_CONTRACT_CLASSIFIED = (
    {("prefectures", c) for c in ("code", "name_en", "name_ja")}
    | {("sa_contracts", "status"), ("sa_plan_features", "feature_key")}
    | {("sa_plans", c) for c in ("billing_interval", "billing_type", "code", "name")}
    | {("sa_products", c) for c in ("code", "name")}
    | {("viewer_invoice_lines", c) for c in ("description", "line_type")}
    | {("viewer_invoices", c) for c in _VIEWER_INVOICE_MASKED | {"status", "mail_sent_at"}}
)


def test_t10_viewer_contract_columns_are_classified_on_bootstrapped_db(cluster):
    """本番の migration 順に近い DB に便2-2a の migration を流し、23列に column_class の行があり、9表に分類の漏れが無い。

    流す順: bootstrap → 閲覧者の名簿 → 便2-2a（2回・冪等）→ ai_cloud の分類。
    請求書の表の8列は mask、status と mail_sent_at は pass で作られる。専用の DB を作り、終わったら消す。"""
    from sqlalchemy.ext.asyncio import create_async_engine

    assert len(_VIEWER_CONTRACT_CLASSIFIED) == 23
    assert len(_VIEWER_CONTRACT_TABLES) == 9
    name, conn = _new_db(cluster.control, "ai_cloud_t10_vcontract")
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
        c.execute(_read(_VIEWER_ACCOUNTS_SQL))
        c.execute(_read(_VIEWER_CONTRACT_SQL))
        c.execute(_read(_VIEWER_CONTRACT_SQL))  # 冪等
        c.execute(_read(_CREATE_SQL))
        rows = _rows(
            conn, "SELECT table_name, column_name FROM ai_cloud_meta.column_class WHERE schema_pattern = 'public'"
        )
        have = {(r[0], r[1]) for r in rows}
        missing = _VIEWER_CONTRACT_CLASSIFIED - have
        assert missing == set(), f"column_class に行が無い: {sorted(missing)}"

        gaps = [g for g in _classification_gaps(conn) if g[1] in _VIEWER_CONTRACT_TABLES]
        assert gaps == [], f"分類の漏れ（表名・列名）: {[(g[1], g[2]) for g in gaps]}"

        modes = dict(
            _rows(conn, "SELECT column_name, mode FROM ai_cloud_meta.build_columns WHERE source = 'public.viewer_invoices'")
        )
        for col in sorted(_VIEWER_INVOICE_MASKED):
            assert modes[col] == "mask", col
        assert modes["status"] == "pass"
        assert modes["mail_sent_at"] == "pass"
    finally:
        conn.close()
        cur = cluster.control.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
```

### 2-8. backend/tests/ops/test_ai_ro_views.py（3か所）

(1) :12〜:18

変更前:
```
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
```
変更後:
```
import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from app.ops.readonly_query import DENY_COLUMN_RE
```

(2) :30

変更前:
```
_DENY_RE = re.compile(r"^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential")
```
変更後:
```
_DENY_RE = DENY_COLUMN_RE  # 正本は backend/app/ops/readonly_query.py（ADR-1061 A46）
```

(3) ファイルの最後（`test_one_uncreatable_table_does_not_stop_other_views` の後ろ）に、空行2つを置いて次を足す。

```python
def test_bank_account_number_and_iban_are_hidden(pg):
    """ADR-1061 決定9（A46）: 振込先の口座番号（bank_account_number・iban）は ai_ro に出ない。名前の列は出る。"""
    c = pg.cursor()
    _make_table(
        c,
        "tenant_003.tenant_invoice_payment_bank",
        [("id", "int"), ("bank_name", "text"), ("bank_account_number", "text")],
    )
    _make_table(
        c,
        "tenant_003.tenant_invoice_payment_wise",
        [("id", "int"), ("account_holder_name", "text"), ("iban", "text")],
    )
    _rebuild_views(pg)
    for view, want in (
        ("tenant_003__tenant_invoice_payment_bank", ["bank_name", "id"]),
        ("tenant_003__tenant_invoice_payment_wise", ["account_holder_name", "id"]),
    ):
        got = [
            r[0]
            for r in _rows(
                pg,
                "SELECT column_name FROM information_schema.columns"
                f" WHERE table_schema = 'ai_ro' AND table_name = '{view}' ORDER BY column_name",
            )
        ]
        assert got == want, view
```

### 2-9. backend/tests/ops/test_deny_column_regex_sync.py（新規。全文）

```python
"""ADR-1061 決定9・A46: 列名の拒否の一覧が3か所でそろっていることを確かめる（DB は使わない）。

正本は backend/app/ops/readonly_query.py の DENY_COLUMN_RE。SQL の2か所（ai_ro と ai_cloud を作る処理）は
Python から読めないので、ファイルの文字を読んで同じことを確かめる。試験の2ファイルは文字を自分で持たない。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.ops.readonly_query import DENY_COLUMN_RE

_ROOT = Path(__file__).resolve().parents[3]
_SQL_FILES = (
    "migrations/20261017_130100_create_ai_ro_views.sql",
    "migrations/20261024_100000_create_ai_cloud_meta.sql",
)
_TEST_FILES = (
    "backend/tests/ops/test_ai_cloud_views.py",
    "backend/tests/ops/test_ai_ro_views.py",
)
_DECL_RE = re.compile(r"deny constant text := '([^']*)';")


@pytest.mark.parametrize("rel", _SQL_FILES)
def test_sql_deny_list_is_same_as_python(rel):
    text = (_ROOT / rel).read_text("utf-8")
    assert _DECL_RE.findall(text) == [DENY_COLUMN_RE.pattern]


@pytest.mark.parametrize("rel", _TEST_FILES)
def test_test_files_import_instead_of_copying(rel):
    text = (_ROOT / rel).read_text("utf-8")
    assert "from app.ops.readonly_query import DENY_COLUMN_RE" in text
    assert "private_key|credential" not in text


@pytest.mark.parametrize(
    "column,hidden",
    [
        ("bank_account_number", True),
        ("iban", True),
        ("IBAN", True),
        ("password_hash", True),
        ("account_number_encrypted", True),
        ("account_holder_name", False),
        ("iban_note", False),
        ("bank_name", False),
    ],
)
def test_new_names_are_hidden_and_neighbours_are_not(column, hidden):
    assert bool(DENY_COLUMN_RE.search(column.lower())) is hidden
```

### 2-10. backend/tests/ops/test_ops_case_db.py（2か所）

(1) :629

変更前:
```
    assert _one(pg, "SELECT count(*) FROM ops_case.deny_tables") == 11
```
変更後:
```
    assert _one(pg, "SELECT count(*) FROM ops_case.deny_tables") == 16
```

(2) :656〜:664

変更前:
```
def test_deny_tables_has_eleven_names(pg):
    c = pg.cursor()
    c.execute("SELECT table_name FROM ops_case.deny_tables")
    got = {r[0] for r in c.fetchall()}
    assert got == {
        "users", "viewer_accounts", "auth_events", "auth_refresh_tokens", "password_reset_tokens",
        "registration_tokens", "viewer_login_events", "viewer_login_tokens", "webauthn_credentials",
        "tenant_carrier_credentials", "viewer_billing_profiles",
    }  # fmt: skip
```
変更後:
```
def test_deny_tables_has_sixteen_names(pg):
    c = pg.cursor()
    c.execute("SELECT table_name FROM ops_case.deny_tables")
    got = {r[0] for r in c.fetchall()}
    assert got == {
        "users", "viewer_accounts", "auth_events", "auth_refresh_tokens", "password_reset_tokens",
        "registration_tokens", "viewer_login_events", "viewer_login_tokens", "webauthn_credentials",
        "tenant_carrier_credentials", "viewer_billing_profiles",
        "viewer_invoices", "tenant_issuer_profiles", "tenant_invoice_payment_methods",
        "tenant_invoice_payment_bank", "tenant_invoice_payment_wise",
    }  # fmt: skip
```

### 2-11. backend/tests/seed_data.py（:64 の後ろ。customer_statuses_seed_sql と type_master_seed_sql の間）

変更前:
```
    return (Path(__file__).resolve().parents[2] / "docs" / "handoff" / "status-ssot-contact-company" / "insert-customer-statuses.sql").read_text("utf-8")


def type_master_seed_sql() -> str:
```
変更後:
```
    return (Path(__file__).resolve().parents[2] / "docs" / "handoff" / "status-ssot-contact-company" / "insert-customer-statuses.sql").read_text("utf-8")


def prefectures_seed_sql() -> str:
    """public.prefectures の47行。値は docs/handoff/viewer-contract-stage/data/prefectures.sql が正本（ここに値を書かない・ADR-1061）。
    書けるのは運営だけ。流す側が同じ取引の中で set_config('app.is_operator', 'true', true) を張る。"""
    return (Path(__file__).resolve().parents[2] / "docs" / "handoff" / "viewer-contract-stage" / "data" / "prefectures.sql").read_text("utf-8")


def type_master_seed_sql() -> str:
```

### 2-12. backend/tests/test_viewer_contract_public_tables_pg.py（2か所）

(1) import（:20〜:21）

変更前:
```
from app.database import get_db
from tests.test_super_admin_viewers import _account, _api, _call, _make_user, _prepare
```
変更後:
```
from app.database import get_db
from tests.seed_data import prefectures_seed_sql
from tests.test_super_admin_viewers import _account, _api, _call, _make_user, _prepare
```

(2) ファイルの最後に、空行2つを置いて次を足す。

```python
@needs_ci_pg
def test_prefectures_seed_loads_47_rows_with_operator_flag(pg):  # noqa: F811
    """A30 の一部: 正本ファイルの47行は、運営の印があるときだけ入る。2回流しても47行のまま（冪等）。"""
    conn, _, async_url = pg
    _setup(conn, async_url)
    app_conn, _ = _app_conn_and_url(conn)
    try:
        acur = app_conn.cursor()
        with pytest.raises(psycopg2.Error) as exc_info:
            acur.execute(prefectures_seed_sql())
        assert exc_info.value.pgcode == "42501"
        app_conn.rollback()

        for _ in range(2):
            acur.execute("SELECT set_config('app.is_operator', 'true', true)")
            acur.execute(prefectures_seed_sql())
            app_conn.commit()

        acur.execute("SELECT count(*), min(code), max(code), count(DISTINCT sort_order) FROM public.prefectures")
        assert acur.fetchone() == (47, "01", "47", 47)
        acur.execute("SELECT name_ja, name_en FROM public.prefectures WHERE code = '13'")
        assert acur.fetchone() == ("東京都", "Tokyo")
        app_conn.rollback()
    finally:
        app_conn.close()
```

### 2-13. backend/tests/test_prefectures_seed.py（新規。全文）

```python
"""都道府県47行の正本ファイルの形を確かめる（ADR-1061 便2-2b。design.md §3-4・A30 の一部。DB は使わない）。

正本は docs/handoff/viewer-contract-stage/data/prefectures.sql の1ファイル。画面のコードに都道府県名を書かない。
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.seed_data import prefectures_seed_sql

_ROOT = Path(__file__).resolve().parents[2]
_SEED = _ROOT / "docs" / "handoff" / "viewer-contract-stage" / "data" / "prefectures.sql"
_ROW_RE = re.compile(r"^\s*\('(\d{2})',\s*'([^']+)',\s*'([^']+)',\s*(\d+)\),?$", re.M)
_FRONT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".json"}


def test_seed_file_has_47_rows_in_code_order():
    text = _SEED.read_text("utf-8")
    rows = _ROW_RE.findall(text)
    assert len(rows) == 47
    assert [r[0] for r in rows] == [f"{i:02d}" for i in range(1, 48)]
    assert all(int(r[3]) == int(r[0]) for r in rows)
    assert all(r[1].strip() and r[2].strip() for r in rows)
    assert text.count("INSERT INTO public.prefectures (code, name_ja, name_en, sort_order) VALUES") == 1
    assert "ON CONFLICT (code) DO NOTHING;" in text


def test_loader_reads_the_seed_file_as_is():
    assert prefectures_seed_sql() == _SEED.read_text("utf-8")


def test_frontend_source_has_no_prefecture_name():
    src = _ROOT / "frontend" / "src"
    assert src.is_dir()
    hits = [
        str(p.relative_to(_ROOT))
        for p in src.rglob("*")
        if p.is_file() and p.suffix in _FRONT_SUFFIXES and "北海道" in p.read_text("utf-8", errors="ignore")
    ]
    assert hits == []
```

## 3. 手順

手順1 枝を取る
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2b && git log --oneline -1 | tail -1

手順2 実装前点検 P1〜P9 を流し、結果をそのまま報告に貼る
    cd ~/sa && git rev-parse HEAD | tail -1
    cd ~/sa && ls docs/handoff/viewer-contract-stage/card-2-2b.md | tail -1
    cd ~/sa && ls migrations | sort | tail -1
    cd ~/sa && grep -c "private_key|credential';" migrations/20261017_130100_create_ai_ro_views.sql migrations/20261024_100000_create_ai_cloud_meta.sql | tail -2
    cd ~/sa && grep -c 'private_key|credential")' backend/app/ops/readonly_query.py
    cd ~/sa && grep -c "private_key|credential" backend/tests/ops/test_ai_cloud_views.py backend/tests/ops/test_ai_ro_views.py | tail -2
    cd ~/sa && grep -c "1086" migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py | tail -2
    cd ~/sa && grep -c -E "'(prefectures|sa_contracts|sa_plan_features|sa_plans|sa_products|viewer_invoice_lines|viewer_invoices)'" migrations/20261024_100300_create_ai_cloud_views.sql
    cd ~/sa && grep -c "('viewer_billing_profiles', '請求先（宛名・住所・電話）');" migrations/20261031_210000_create_ops_case.sql
    cd ~/sa && grep -c "^  ('" docs/handoff/viewer-contract-stage/data/prefectures.sql
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | tail -1
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2
  期待: 3行目 `20261112_150000_create_viewer_contract_public_tables.sql`。4行目は2ファイルとも `:1`。5行目 1。6行目は2ファイルとも `:1`。7行目は2ファイルとも `:1`。8行目 0。9行目 1。10行目 47。11行目と12行目の値は `f7543436f6345b02b8ac73f0e9c31b05bc67b48772243cf3b43fb6037f4e4929`。

手順3 §2 の変更をする（2-1 から 2-4、2-6 から 2-13 の順。2-5 は手順4 で行う。新規のファイルは Write ツール、それ以外は Edit ツールで行う）

手順4 許可一覧の sha256 を直す（2-4 の後）
    cd ~/sa && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql | tail -1
  出た 64 文字で §2-5 の(1)を Edit ツールで置き換え、§2-5 の(2)も Edit ツールで行う。その後:
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | cut -f2
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | awk -F'\t' '{print NF}'
    cd ~/sa && sed -n 7p scripts/migration-guard/reference-allowlist.tsv | grep -c "card-2-2b（分類23行追加）$"
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
    cd ~/sa && ~/venv312/bin/ruff check backend/app/ops/readonly_query.py backend/tests/ops/test_ai_cloud_views.py backend/tests/ops/test_ai_ro_views.py backend/tests/ops/test_deny_column_regex_sync.py backend/tests/ops/test_ops_case_db.py backend/tests/seed_data.py backend/tests/test_viewer_contract_public_tables_pg.py backend/tests/test_prefectures_seed.py 2>&1 | tail -10
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py repo > ~/vw-repo.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-repo.txt
    cd ~/sa && grep -c "credential|account_number|^iban\$';" migrations/20261017_130100_create_ai_ro_views.sql migrations/20261024_100000_create_ai_cloud_meta.sql | tail -2
    cd ~/sa && grep -c 'credential|account_number|^iban\$"' backend/app/ops/readonly_query.py
    cd ~/sa && git diff -U0 migrations/20261024_100300_create_ai_cloud_views.sql | grep -c "^+  ('public'"
    cd ~/sa && git diff -U0 migrations/20261024_100300_create_ai_cloud_views.sql | grep -c "^-  ('"
    cd ~/sa && grep -c "1109" migrations/20261024_100300_create_ai_cloud_views.sql backend/tests/ops/test_ai_cloud_views.py | tail -2
    cd ~/sa && grep -c "'tenant_invoice_payment_wise', '振込先の Wise 口座');" migrations/20261031_210000_create_ops_case.sql
  期待（上から順に）: ruff は `All checks passed!`／値の書き込みの検査は `exit=0`／2ファイルとも `:1`／1／13（足した分類の行）／0（消した分類の行は無い）／2ファイルとも `:1`／1。
  repo の検査が exit=0 でなかったら、最後の 10 行を貼って `BLOCKED: value-writes`。

手順7 backend の試験（実 PostgreSQL の試験は CI だけで動く。ここでは skip と出てよい。failed と error は 0 であること）
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/test_prefectures_seed.py tests/ops/test_deny_column_regex_sync.py tests/test_seed_data.py 2>&1 | tail -15
    cd ~/sa/backend && ~/venv312/bin/python -m pytest -q -p no:cacheprovider tests/ops/test_ai_cloud_views.py tests/ops/test_ai_ro_views.py tests/ops/test_ops_case_db.py tests/test_viewer_contract_public_tables_pg.py 2>&1 | tail -15
  期待: 1本目は failed 0・error 0 で、passed に test_prefectures_seed.py の3件と test_deny_column_regex_sync.py の12件を含む。2本目は failed 0・error 0（skipped は出てよい）。

手順8 変えたファイルの名前と数
    cd ~/sa && git status --short | tail -20
    cd ~/sa && git diff --stat | tail -20
  期待: §1 の 13 ファイルだけ（新規の2ファイルは `??` で各1行）。

手順9 記録と送り出し
    cd ~/sa && git add migrations/20261017_130100_create_ai_ro_views.sql migrations/20261024_100000_create_ai_cloud_meta.sql backend/app/ops/readonly_query.py migrations/20261024_100300_create_ai_cloud_views.sql scripts/migration-guard/reference-allowlist.tsv migrations/20261031_210000_create_ops_case.sql backend/tests/ops/test_ai_cloud_views.py backend/tests/ops/test_ai_ro_views.py backend/tests/ops/test_deny_column_regex_sync.py backend/tests/ops/test_ops_case_db.py backend/tests/seed_data.py backend/tests/test_viewer_contract_public_tables_pg.py backend/tests/test_prefectures_seed.py && git status --short | tail -20
    cd ~/sa && git commit -q -m "feat(ai-read): hide account number and iban, classify viewer contract columns, load prefecture seed in tests (ADR-1061 bin2-2b)" && git log --oneline -1 | tail -1
    cd ~/sa && ~/venv312/bin/python scripts/check-migration-value-writes.py diff origin/main HEAD --check all > ~/vw-diff.txt 2>&1; echo "exit=$?"; tail -10 ~/vw-diff.txt
    cd ~/sa && git push origin release/viewer-contract-bin2-2b 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-contract-bin2-2b -2 | tail -2
  `git add` の後の status に §1 に無いファイルが出たら、commit せずに `BLOCKED: 範囲外のファイル` で停止する。3行目の diff 検査が exit=0 でなかったら push せずに最後の 10 行を貼って `BLOCKED: value-writes`。

## 4. 想定される分かれ道

- 停止する（その場で作業を停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P9 のどれかが外れた → `BLOCKED: P番号`。
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
- 1 行目: `RECEIVED viewer-contract-bin2-2b HEAD=…`。2 行目: 「本報告はカード 便2-2b AI の読み取りの区分と都道府県47行の試験用の読み込み の実行結果である」。
- 手順2・4・5・6・7・8・9 の出力（tail の範囲）をそのまま貼る。要約しない。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。待ちが要るものは Opus が見る（CI の結果など）。
- ファイルの編集は Edit ツールで行う（新規の2ファイルだけ Write ツール）。ヒアドキュメントで書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 改訂1（2026-11-12 Opus。審査役の REQUEST_CHANGES H1・H2 への対処）

この節は §1〜§6 を上書きしない。この節の作業だけを行う。§2 の変更は 108da716a で済んでいる。やり直さない。

### 7-1. 事実（Opus が確かめた）
- H1: CI の移行の試験は、変えた SQL を名前の順に素の DB で流す。最初の migrations/20261017_130100_create_ai_ro_views.sql:78 の `GRANT USAGE ON SCHEMA ai_ro TO ai_reader;` が `role "ai_reader" does not exist` で落ちた。ai_reader の役は migrations/20261017_130000_create_ai_reader_role.sql が作る（役が無ければ作り、あれば属性を確かめるだけ。何度流しても同じ結果）。.github/workflows/migration-test.yml には、この前提を先に流す手順が無い（同じ形の先例は「変更 SQL の前提の移行を先に実行（ai_cloud_meta・ai_reader_cloud）」の手順）。
- H2: guard-authoring/evaluation の error は scripts/run-guard-evaluation.js:25 の `git merge-base --is-ancestor base head` の失敗による。PR の宛先の main（730ed6a3a）が枝の HEAD（108da716a）の祖先でない（Opus の手元で exit=1 を確認）。main 側の先行2コミットは台帳だけ（#5445）。枝に origin/main を取り込めば直る。.github/workflows/migration-test.yml は scripts/check-guard-evaluations.js の管理対象ではない（評価の JSON は要らない）。

### 7-2. 触るファイル（改訂1）
- .github/workflows/migration-test.yml（手順を1つ足すだけ。消す行は無い）
- 取り込みのコミット（origin/main の取り込み。中身の変更はしない）

### 7-3. 変更
変更前（この行は1か所だけ。行番号は origin/main 730ed6a3a で 1330）:

          - name: 変更 SQL の前提の移行を先に実行（ai_cloud_meta・ai_reader_cloud）

この行の直前に、次の10行（最後は空行）を足す。字下げは今ある `- name:` の行と同じ6文字の空白:

          - name: 変更 SQL の前提の移行を先に実行（ai_reader）
            if: steps.detect.outputs.has_sql_changes == 'true' && contains(steps.detect.outputs.changed_sql, 'migrations/20261017_130100_create_ai_ro_views.sql')
            run: |
              # 20261017_130100 は 130000（ai_reader の役）が先に流れている前提（本番は役が先に在る）
              for sqlfile in migrations/20261017_130000_create_ai_reader_role.sql; do
                echo "▶ $sqlfile を前提として実行中..."
                psql -h localhost -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -f "$sqlfile"
                echo "✅ $sqlfile 成功"
              done

（上の表示は本文の字下げとして全体に4文字の空白が付いている。ファイルに入れるときは各行の先頭4文字を除く。つまり `- name:` は6文字、`if:` と `run: |` は8文字、`#` と `for` と `done` は10文字、`echo` と `psql` は12文字の空白で始まる。）

### 7-4. 手順（改訂1）
手順R1 枝を取り、main を取り込む
    cd ~ && git clone https://github.com/shingo-ops/salesanchor.git sa && cd sa && git checkout release/viewer-contract-bin2-2b && git log --oneline -1 | tail -1
    cd ~/sa && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git merge --no-edit origin/main 2>&1 | tail -3
    cd ~/sa && git merge-base --is-ancestor origin/main HEAD; echo "is-ancestor exit=$?"
    cd ~/sa && git diff --name-only HEAD~1 HEAD | tail -10
  期待: 2行目は衝突なし。3行目 `is-ancestor exit=0`。4行目は台帳（.claude-pipeline/ の下）だけ。衝突したら `git merge --abort` して `BLOCKED: merge`。

手順R2 変更前の行を確かめる
    cd ~/sa && grep -n "変更 SQL の前提の移行を先に実行（ai_cloud_meta・ai_reader_cloud）" .github/workflows/migration-test.yml | tail -3
    cd ~/sa && grep -c "20261017_130000_create_ai_reader_role" .github/workflows/migration-test.yml
  期待: 1行目は1件。2行目 0。外れたら `BLOCKED: R2`。

手順R3 7-3 の変更を Edit ツールで行い、確かめる
    cd ~/sa && grep -n -A9 "変更 SQL の前提の移行を先に実行（ai_reader）" .github/workflows/migration-test.yml | tail -12
    cd ~/sa && ~/venv312/bin/python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/migration-test.yml')); print('yaml ok')" 2>&1 | tail -1
    cd ~/sa && git diff --stat | tail -3
  期待: 1行目は 7-3 の10行と同じ並び（足した手順の次に ai_cloud_meta の手順が来る）。2行目 `yaml ok`（~/venv312 が無いときは §3 手順5 の1〜3行目で作り `pip install -q pyyaml` を足す）。3行目は `.github/workflows/migration-test.yml | 10 +` の1ファイルだけ。

手順R4 記録と送り出し
    cd ~/sa && git add .github/workflows/migration-test.yml && git status --short | tail -5
    cd ~/sa && git commit -q -m "ci(migration-test): create ai_reader role before running changed 20261017_130100 (ADR-1061 bin2-2b)" && git log --oneline -3 | tail -3
    cd ~/sa && git push origin release/viewer-contract-bin2-2b 2>&1 | tail -3
    cd ~/sa && git log --oneline origin/release/viewer-contract-bin2-2b -3 | tail -3
  status に migration-test.yml 以外が出たら commit せずに `BLOCKED: 範囲外のファイル`。push が拒まれたら force せずに `BLOCKED: push`。

### 7-5. 報告
1行目 `RECEIVED viewer-contract-bin2-2b-r1 HEAD=`（手順R1 の後の `git rev-parse HEAD` の40桁）。手順R1〜R4 の出力を tail の範囲でそのまま貼る。停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の3点。最後の行は `DONE` か `BLOCKED: 理由`。§6 の定型（sleep しない・PR を作らない・止められたら言い換えない）はこの改訂にも効く。

END OF CARD
