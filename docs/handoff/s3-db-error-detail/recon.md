# recon — S3 例外の中身（SQL 文・入力値）を応答に出さない（db-error-detail）

**日付**: 2026-10-16　**基準**: origin/main 057e12b16（作業場所 HEAD と一致を確認）　**仕様書**: [docs/specs/db-error-detail/README.md](../../specs/db-error-detail/README.md)
**生出力**: /tmp/CC報告ファイル/s3-sql/（recon/、recon2/、pgcheck/、prod-baseline.txt、scope-60.tsv）

## 既存 ADR の検索結果

- `git grep -niE "exc\.orig|エラー応答|error response|detail.*例外|内部情報|情報漏" docs/adr docs/specs` → docs/adr は 0 行。docs/specs の 4 行（client-ip/ideal-state.md:10、tenant-rls/ideal-state.md:10、design-system/design.md:4213、design-system/component-ssot/page-title/design.md:15）はいずれも例外の応答内容と無関係（recon2/recon2.md §3）。
- docs/adr/FEATURE-INDEX.md にエラー応答・例外の中身に関する行は無い。
- 既存のコード上の正本: backend/app/routers/_utils.py:20 `handle_db_exceptions`。例外は logger.error（:41、:47）にだけ出し、応答は固定文言（:44、:50）。試験は backend/tests/test_db_exceptions.py。

## 1. 例外の中身を応答に入れている箇所

【事実】backend/app で、except 節の中の HTTPException / JSONResponse の detail・content に except の変数が入る箇所は 107 件（python ast で抽出。recon/g1-ast.tsv）。このうち DB 由来の中身が入りうるのは次の 59 件（scope-60.tsv。ファイル名は旧件数のまま）:

- `except IntegrityError` で `{exc.orig}` を入れる 409: 44 件
- `except Exception` で `{exc}`（erp.py のみ `{e}`）を入れる 500: 15 件（取り込みの確定 `*_IMPORT_COMMIT_ERROR` 6 種など。commit 中の DB 例外がそのまま入る）
- 59 件のうち super admin 専用（依存に require_super_admin）が 47 件。専用でないもの（各社の利用者が呼べる）は 12 件: IntegrityError 5 件（conditions.py:582、note_master.py:179・:217、payment_fee_settings.py:111・:150）と Exception 7 件（conditions.py:507、erp.py:154、note_master.py:399、product_categories.py:285、status_master.py:380、suppliers.py:498、units.py:339）。
- 残り 48 件（FedEx・Meta・LLM・PokeAPI・ValueError など外部 API や入力検査の文言）は DB の中身を含まないため対象外。

全 59 件の一覧は末尾の付録。

## 2. 例外の文字列に何が入るか（実物で確認）

【事実】本番と同じ版（sqlalchemy 2.0.38・asyncpg 0.31.0。backend/requirements.txt と一致）と PostgreSQL 16.15 を手元に使い捨てで立て、一意制約違反と外部キー違反を起こした（pgcheck/out.txt、pgcheck/check.py）。

| | str(exc.orig)（409 の 44 件が返す） | str(exc)（500 の 15 件が返す） |
|---|---|---|
| SQL 文 | 無し | 有り（`[SQL: INSERT INTO c (id, name, pid) VALUES ($1, $2, $3)]`） |
| 入力値 | 有り（`DETAIL:  キー (name)=(secret-val) はすでに存在します。`） | 有り（DETAIL と `[parameters: (2, 'secret-val', 1)]`） |
| 制約名・表名 | 有り（`c_name_key`、外部キーでは `"c"`・`"p"`） | 有り |

- `except Exception` で捕まえても型は sqlalchemy.exc.IntegrityError で、str(exc) は同じ。
- 使い捨て PG のメッセージは日本語ロケール。本番 PG のロケールは【未確認】（どの項目が入るかの判定には影響しない）。

## 3. 全体の例外ハンドラとログ

【事実】
- backend/app/main.py の exception_handler は 3 つ。OperationalError→503（:768-778）、SQLAlchemyError→500 固定文言（:782-789）、Exception→500 固定文言（:792-800）。未処理の例外は中身を返さない。FastAPI(...) に debug 引数なし（:195）。
- SQL をログに出す echo は backend/app/database.py:20・:73 で `ENVIRONMENT != "production"` のとき有効。本番は backend・celery とも ENVIRONMENT=production（2026-10-16 20:36 JST 実測、prod-baseline.txt）。
- 本番 backend ログ（11:33:40Z 起動以後の 28 行）に `[SQL:` 0 件・`[parameters:` 0 件、celery 24 時間で `[SQL:` 0 件（prod-baseline.txt）。

## 4. 59 件の except 節の形（recon2/table1_detail.md・table1_summary.tsv）

【事実】
- except 内で自分の例外をログに出しているのは 1 件（buyback_prices.py:692 の logger.exception）。58 件は出していない（erp.py:152 の logger.exception は erp_sync_logs 更新失敗の別の例外用）。
- rollback を呼ぶのは 57 件（buyback_prices.py:691、erp.py:144 は呼ばない。erp.py は except 内で erp_sync_logs を更新して commit する）。
- `logger = logging.getLogger` があるのは buyback_prices.py:43 と erp.py:37 の 2 ファイル。残り 26 ファイルには logging の import も無い。
- detail の前置きは 3 種: 制約違反系（「重複または制約違反」「制約違反」「重複または FK 違反」「重複」「同じ区分・表示名のマスタが既に存在します」「種別コードが重複しています」）、取り込み系（`*_IMPORT_COMMIT_ERROR` 6 種）、その他（「再マッチング中にエラーが発生しました」「ERP エクスポート失敗」「更新エラー」）。

## 5. 文言への依存

【事実】
- frontend/src・gas・scripts・backend/tests で、59 件の detail の文言・接頭辞を比較・分岐に使う箇所は 0 件（recon2 §2）。
- frontend/src/lib/api.ts:101-107・:185-190 が detail を ApiError.message にし、各マスタ画面の保存処理が err.message をそのまま表示する（例 ConditionsMasterPanel.tsx:214、NoteMasterPanel.tsx:172）。＝今は SQL・入力値・制約名が画面に出る。
- 取り込み確定の画面 6 つ（例 UnitImportPage.tsx:63）は status で分け、detail は使わない。

## 6. 機械で守る仕組みと試験

【事実】
- exc.orig・str(e) を応答に入れることを検査する試験・lint は 0 件。ruff は E/F/W/I のみ（backend/pyproject.toml:16-21）。
- AST で backend/app を全走査する試験の手本: backend/tests/test_time_handling.py:30-50（rglob と除外集合）、backend/tests/test_tcg_mirror.py:56-80（ast.walk と `assert not found`）。
- 重複で 409 を API 経由で確かめる試験は backend/tests/test_super_admin_unit_ignore_phrases.py:107-120 の 1 件（scope の #50 super_admin_unit_ignore_phrases の作成）。`requires_pg`（:25-29、RLS_ADMIN_DATABASE_URL と RLS_TEST_DATABASE_URL が要る）で、CI の test.yml は postgres:16 と RLS_* を設定する（.github/workflows/test.yml:122-123、:223、:225）。この試験が CI で実際に走っているか（skip されていないか）は【未確認】→ 実装 PR の CI ログで確かめる。

## 付録: 対象 59 件

| # | 箇所 | 関数 | except | super admin 専用 | except 内のログ | rollback |
|---|---|---|---|---|---|---|
| 1 | backend/app/routers/buyback_prices.py:693 | rematch_products | Exception | はい | 有り | 無し |
| 2 | backend/app/routers/conditions.py:507 | import_conditions_commit | Exception | いいえ | 無し | 有り |
| 3 | backend/app/routers/conditions.py:582 | create_condition_alias | IntegrityError | いいえ | 無し | 有り |
| 4 | backend/app/routers/erp.py:154 | export_invoices_for_erp | Exception | いいえ | 有り | 無し |
| 5 | backend/app/routers/note_master.py:179 | create_note_master | IntegrityError | いいえ | 無し | 有り |
| 6 | backend/app/routers/note_master.py:217 | update_note_master | IntegrityError | いいえ | 無し | 有り |
| 7 | backend/app/routers/note_master.py:399 | import_note_master_commit | Exception | いいえ | 無し | 有り |
| 8 | backend/app/routers/payment_fee_settings.py:111 | create_payment_fee_setting | IntegrityError | いいえ | 無し | 有り |
| 9 | backend/app/routers/payment_fee_settings.py:150 | update_payment_fee_setting | IntegrityError | いいえ | 無し | 有り |
| 10 | backend/app/routers/product_categories.py:285 | import_product_categories_commit | Exception | いいえ | 無し | 有り |
| 11 | backend/app/routers/product_masters.py:94 | create_attribute_master | IntegrityError | はい | 無し | 有り |
| 12 | backend/app/routers/product_masters.py:129 | update_attribute_master | IntegrityError | はい | 無し | 有り |
| 13 | backend/app/routers/status_master.py:380 | import_status_master_commit | Exception | いいえ | 無し | 有り |
| 14 | backend/app/routers/super_admin_aliases.py:130 | create_alias | IntegrityError | はい | 無し | 有り |
| 15 | backend/app/routers/super_admin_aliases.py:165 | update_alias | IntegrityError | はい | 無し | 有り |
| 16 | backend/app/routers/super_admin_condition_defs.py:88 | create_condition_def | IntegrityError | はい | 無し | 有り |
| 17 | backend/app/routers/super_admin_condition_defs.py:123 | update_condition_def | IntegrityError | はい | 無し | 有り |
| 18 | backend/app/routers/super_admin_conditions.py:223 | create_condition | IntegrityError | はい | 無し | 有り |
| 19 | backend/app/routers/super_admin_conditions.py:259 | update_condition | IntegrityError | はい | 無し | 有り |
| 20 | backend/app/routers/super_admin_conditions.py:424 | import_conditions_commit | Exception | はい | 無し | 有り |
| 21 | backend/app/routers/super_admin_conditions.py:480 | create_condition_alias | IntegrityError | はい | 無し | 有り |
| 22 | backend/app/routers/super_admin_dex.py:115 | create_dex | IntegrityError | はい | 無し | 有り |
| 23 | backend/app/routers/super_admin_link_templates.py:131 | upsert_link_template | IntegrityError | はい | 無し | 有り |
| 24 | backend/app/routers/super_admin_note_master.py:176 | create_note_master | IntegrityError | はい | 無し | 有り |
| 25 | backend/app/routers/super_admin_note_master.py:211 | update_note_master | IntegrityError | はい | 無し | 有り |
| 26 | backend/app/routers/super_admin_note_master.py:377 | import_note_master_commit | Exception | はい | 無し | 有り |
| 27 | backend/app/routers/super_admin_payment_fee_settings.py:105 | create_payment_fee_setting | IntegrityError | はい | 無し | 有り |
| 28 | backend/app/routers/super_admin_payment_fee_settings.py:140 | update_payment_fee_setting | IntegrityError | はい | 無し | 有り |
| 29 | backend/app/routers/super_admin_product_categories.py:151 | create_product_category | IntegrityError | はい | 無し | 有り |
| 30 | backend/app/routers/super_admin_product_categories.py:280 | import_product_categories_commit | Exception | はい | 無し | 有り |
| 31 | backend/app/routers/super_admin_product_categories.py:311 | update_product_category | IntegrityError | はい | 無し | 有り |
| 32 | backend/app/routers/super_admin_product_formats.py:82 | create_product_format | IntegrityError | はい | 無し | 有り |
| 33 | backend/app/routers/super_admin_product_formats.py:117 | update_product_format | IntegrityError | はい | 無し | 有り |
| 34 | backend/app/routers/super_admin_product_kinds.py:82 | create_product_kind | IntegrityError | はい | 無し | 有り |
| 35 | backend/app/routers/super_admin_product_kinds.py:117 | update_product_kind | IntegrityError | はい | 無し | 有り |
| 36 | backend/app/routers/super_admin_product_lines.py:82 | create_product_line | IntegrityError | はい | 無し | 有り |
| 37 | backend/app/routers/super_admin_product_lines.py:117 | update_product_line | IntegrityError | はい | 無し | 有り |
| 38 | backend/app/routers/super_admin_quantity_units.py:99 | create_quantity_unit | IntegrityError | はい | 無し | 有り |
| 39 | backend/app/routers/super_admin_quantity_units.py:134 | update_quantity_unit | IntegrityError | はい | 無し | 有り |
| 40 | backend/app/routers/super_admin_status_master.py:190 | create_status_master | IntegrityError | はい | 無し | 有り |
| 41 | backend/app/routers/super_admin_status_master.py:243 | update_status_master | IntegrityError | はい | 無し | 有り |
| 42 | backend/app/routers/super_admin_status_master.py:407 | import_status_master_commit | Exception | はい | 無し | 有り |
| 43 | backend/app/routers/super_admin_suppliers.py:167 | create_supplier | IntegrityError | はい | 無し | 有り |
| 44 | backend/app/routers/super_admin_suppliers.py:214 | update_supplier | IntegrityError | はい | 無し | 有り |
| 45 | backend/app/routers/super_admin_suppliers.py:542 | import_suppliers_commit | Exception | はい | 無し | 有り |
| 46 | backend/app/routers/super_admin_suppliers.py:599 | create_routing | IntegrityError | はい | 無し | 有り |
| 47 | backend/app/routers/super_admin_suppliers.py:792 | update_supplier_extraction_rules | Exception | はい | 無し | 有り |
| 48 | backend/app/routers/super_admin_tcg.py:94 | create_series | IntegrityError | はい | 無し | 有り |
| 49 | backend/app/routers/super_admin_tcg.py:194 | create_type | IntegrityError | はい | 無し | 有り |
| 50 | backend/app/routers/super_admin_unit_ignore_phrases.py:71 | create_unit_ignore_phrase | IntegrityError | はい | 無し | 有り |
| 51 | backend/app/routers/super_admin_unit_ignore_phrases.py:107 | update_unit_ignore_phrase | IntegrityError | はい | 無し | 有り |
| 52 | backend/app/routers/super_admin_units.py:162 | create_unit | IntegrityError | はい | 無し | 有り |
| 53 | backend/app/routers/super_admin_units.py:197 | update_unit | IntegrityError | はい | 無し | 有り |
| 54 | backend/app/routers/super_admin_units.py:276 | create_unit_alias | IntegrityError | はい | 無し | 有り |
| 55 | backend/app/routers/super_admin_units.py:423 | import_units_commit | Exception | はい | 無し | 有り |
| 56 | backend/app/routers/super_admin_weight_classes.py:82 | create_weight_class | IntegrityError | はい | 無し | 有り |
| 57 | backend/app/routers/super_admin_weight_classes.py:117 | update_weight_class | IntegrityError | はい | 無し | 有り |
| 58 | backend/app/routers/suppliers.py:498 | import_tenant_suppliers_commit | Exception | いいえ | 無し | 有り |
| 59 | backend/app/routers/units.py:339 | import_units_commit | Exception | いいえ | 無し | 有り |
