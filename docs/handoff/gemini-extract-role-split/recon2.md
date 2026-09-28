# recon2: PR-B/C/D 実装カード用詳細調査

起点: origin/main（fetch時点 SHA `4bad43a4dca6368ffa7370792a3c912e90bba52`。design.md 起点の `ae783c7f5` から進んでいたため origin-main2 に再抽出）
展開先: `scratchpad/origin-main2/`

## 1. Migration 規約

- 最新5件: `migrations/20260926_080000_create_extraction_prompt_config.sql`〜`migrations/20260927_130000_add_extraction_token_cost_columns.sql`（`ls migrations/ | sort | tail`で確認）
- ファイル名は YYYYMMDD_HHMMSS_description.sql 固定（`.github/workflows/migration-guard.yml:94-113` が正規表現 `^[0-9]{8}_[0-9]{6}_.*\.sql$` で強制。旧 `NNN_` 連番は失敗させる）
- 冪等パターン: `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`。テーブル存在チェック付きの `DO $$ ... IF EXISTS (SELECT 1 FROM pg_tables ...) ... $$` パターンも使われる（`migrations/20260926_010000_add_raw_product_code.sql` 全文）
- 新設テーブルは `public` スキーマ（`extraction_prompt_config` も `public`、tenant_idなし）。RLS は今回の対象テーブル（新設テーブル・suppliers列追加）双方とも tenant_id を持たない設計のため付与例なし（`suppliers` は既存 `tenant_id IS NULL` フィルタで運用者管理を表現）
- `scripts/run_all_migrations.sh` 末尾に `run_sql migrations/<file>` を追記するのが「新スタイル」。`.github/workflows/deploy.yml` への `< migrations/<file>` 追記でも可（旧スタイル）。**どちらか一方で migration-guard チェック2 を通過**（`.github/workflows/migration-guard.yml:113-125`）
- `.github/workflows/migration-guard.yml` チェック1: `backend/app/models.py` に新規 `Column(` が diff で追加された場合のみ発火し、`.github/workflows/deploy.yml` に `migrate_` を含む追記を要求
- **SQLAlchemy ORM 層**: `backend/app/models.py` を grep したが `supplier_prompts` / `extraction_prompt_config` の ORM 定義は無い。既存の `suppliers.extraction_*` 列も raw SQL (`text()`) で読み書きされており、ORM モデルを持たないテーブル運用が既定パターン。**PR-B の新設テーブル・新規列も models.py への追記は不要（既存パターン踏襲）** ※ただし models.py に新規 Column を足すなら migration-guard チェック1 が発火する点に注意
- `.github/workflows/schema-check.yml`（テナントスキーマ整合性チェック、Level 3）は `backend/app/models.py` / `migrations/` / `scripts/migrate_*` / `scripts/db/` / `scripts/setup_tenant.py` の変更で発火（`.github/workflows/schema-check.yml:33-40`）。新設テーブルが `public` スキーマでテナントスキーマと無関係でも、`migrations/` 配下の変更で自動的にジョブが走る（`scripts/setup_tenant.py` でテストテナント作成→`sync_tenant_schema.py --dry-run` 差分チェック）。今回はテナントスキーマに影響しない変更のはずだが、CIは必ず走る

## 2. env フラグの定義パターン／celery連鎖のフック点

- 中央 config/settings モジュールは無し。`TCG_AUTO_ANALYZE` / `TCG_AUTO_DISTRIBUTE` は使用箇所で直接 `os.environ.get("XXX", "").strip() == "1"` と読む（`backend/app/tasks/tcg_extraction.py:486`, `:496`）。**`EXTRACTION_SHADOW_ENABLED` も同パターンで実装するのが規約に沿う**（中央設定ファイルを新設する必要なし）
- 呼び出し連鎖: `_run_extraction()`（`backend/app/tasks/tcg_extraction.py:223`）→ Gemini抽出 → `extraction_jobs` 更新（`:461-480`）→ `if final_status == "done": if auto_analyze: analysis_stats = analyze_extraction_job(session, extraction_job_id)`（`:484-500`）
- シャドー実行のフック点: `backend/app/tasks/tcg_extraction.py:484-500` の `if final_status == "done":` ブロック内、`analyze_extraction_job` 呼び出し後（本番結果確定後）に `if os.environ.get("EXTRACTION_SHADOW_ENABLED", "").strip() == "1":` を追加し、同じ `raw_text` で v7 Gemini呼び出し＋判定を行い `extraction_shadow_results` に書く設計が自然。celery task自体は `extract_source_message_task`（`:550`）が `_run_extraction` の薄いラッパー
- `analyze_extraction_job` の実体: `backend/app/services/tcg_analyzer_svc.py`（import: `backend/app/tasks/tcg_extraction.py:31`）

## 3. プロンプトのバージョン選択（v7を足す設計）

- `extraction_prompt_config` は `prompt_key` (`base_extraction` / `work_id_extraction`) × `is_active` で管理（`backend/app/services/gemini_extraction_svc.py:91-137` `_load_db_prompts()`）。DB必須・フォールバックなし（未登録なら `RuntimeError`）
- version文字列は別モジュール `backend/app/services/tcg_work_reference.py:13-18` で管理: `WORK_ID_PROMPT_VERSION = "raw-extraction-v6-rawcode-p1"` と `WORK_ID_PROMPT_VERSIONS` / `PRODUCT_ID_PROMPT_VERSIONS` / `RAW_CODE_PROMPT_VERSIONS` の frozenset群。**v7を足す場合はここに新しい定数と frozenset エントリを追加**し、`backend/app/services/gemini_extraction_svc.py` 側は `prompt_key` ベース（`shadow_extraction` 等の新規 prompt_key）で分離するのが既存規約に整合。既存の `base_extraction`/`work_id_extraction` テキストを書き換える方式ではなく、新規 `prompt_key` 行を **migration 内 INSERT** で追加する形になる（既存2行の初期データがどう投入されたかは migration に痕跡なし＝**未確認**、恐らく手動運用画面 `frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx` 経由。v7は再現性のため migration の INSERT ... ON CONFLICT で入れるのが安全）
- `call_gemini_extraction()`（`backend/app/services/gemini_extraction_svc.py:318-407`）が `db_base_prompt` / `db_work_id_prompt` を都度DBから取得し `full_prompt` を組み立てる。シャドー用に第3のプロンプト（v7）を使う場合、この関数に `prompt_key` 引数を足すか、専用の別関数を新設する設計判断が必要（**未確認・設計判断待ち**）

## 4. block_delimiter / status_keyword の現在の使われ方

- `backend/app/services/gemini_extraction_svc.py:296-311` `_build_supplier_context_note()` 内、`knowledge_links` 引数（`supplier_knowledge_links` + `knowledge_rules` 結合行）から `category` ごとにフィルタしてプロンプトに埋め込む:
  - `block_delimiter` → 「商品ブロックの区切り記号: ...」（:304-306）
  - `skip_condition` → 「以下のキーワードを含むブロックは出力対象外」（:307-308）
  - `status_keyword` → 「ステータス判定: 「kw」→norm」（:309-311）
- 取得元: `backend/app/tasks/tcg_extraction.py:285-304` で `supplier_knowledge_links` × `knowledge_rules` を `is_active=TRUE` 条件でJOINして取得し `knowledge_links` として渡す
- Python側でのこれ以外の用途は grep 上見当たらず（プロンプト注入専用）
- UI: 仕入元知識リンクの編集は `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx`（knowledgeLinks 関連 state, `:217-290`付近でCRUD）。API: `GET/POST/DELETE /super-admin/suppliers/{supplier_id}/knowledge-links[...]`（`SupplierExtractionRulesPage.tsx:218,246,258,285`）。バックエンドのknowledge-links関連ルーターは `backend/app/routers/super_admin_suppliers.py`（`supplier_knowledge_links`検索が必要、行番号は本ファイルの別セクション＝未確認・追加grep要）

## 5. supplier_prompts 全参照（削除PRの対象リスト）

バックエンド:
- `backend/app/routers/super_admin_suppliers.py:49-50`（import `SupplierPromptResponse`, `SupplierPromptUpdate`）
- `backend/app/routers/super_admin_suppliers.py:600-667`（`GET /super-admin/suppliers/{supplier_id}/prompt` と `PUT /super-admin/suppliers/{supplier_id}/prompt`。ADR-085 コメントブロック含む。SQLは `public.supplier_prompts` に直接アクセス）
- `backend/app/schemas/central_masters.py:388-408`付近（`SupplierPromptResponse` / `SupplierPromptUpdate` クラス定義、コメント「ADR-085: 仕入先別 Gemini プロンプト (public.supplier_prompts)」）

フロントエンド:
- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:142`（`GET /super-admin/suppliers/${supplierId}/prompt`）
- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:157`（`PUT /super-admin/suppliers/${promptSupplierId}/prompt`）
- 同ファイル内、プロンプト編集フォーム一式（フェッチ・保存ハンドラ・関連state）— 行範囲は要精査（**未確認**、142/157周辺の関数ブロックごと削除想定）

i18n（ja.json、`knowledge.*` 名前空間）:
- `frontend/src/locales/ja.json:2443` `"promptSection": "仕入先別 解析プロンプト（使用保留中）"`
- `:2444` `"promptHelp"`
- `:2445` `"promptPlaceholder"`
- en.json 側の対応キーは未grep（**未確認**、ja.jsonと同一キー必須のADR-027規約により同名キーが存在するはず）

テスト: `backend/tests/`, `frontend/` 配下を `supplier_prompts`/`SupplierPrompt` でgrepしたが**ヒット0件**（専用テストは存在しない）

DBテーブル本体（削除対象・PR-B）: `public.supplier_prompts`（DROP TABLE、GO #PR番号必須・不可逆操作）

## 6. 仕入元ルール編集フォーム（extraction_ship_format を足す場所）

- ページ: `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx`（914行）。既存 `extraction_price_format`/`qty_format`/`order_pattern`/`default_unit`/`state_format`/`notes`/`example_text` の7フィールドをフォームで編集（型定義 `:39-45`、フォーム初期値 `:77-93`、編集値マッピング `:98-104`）
- 使用金型: `TextField`(`:17`), `Select`/`SelectControl`(`:18`), `Textarea`(`:19`), `Button`(`:20`), `DataTable`(`:15`), `Badge`(`:16`), `PageLayout`(`:14`) — すべて `frontend/src/components/` 配下の既存金型。生要素なし
- 保存API呼び出し: `api.patch`(推定、要目視) 相当の呼び出しが `:427` 付近で `/super-admin/suppliers/${selectedSupplier.supplier_id}/extraction-rules` へ
- バックエンド:
  - `GET /super-admin/suppliers/extraction-overview`（`super_admin_suppliers.py:768-819`）
  - `GET /super-admin/suppliers/{supplier_id}/extraction-rules`（`:822-872`）
  - `PATCH /super-admin/suppliers/{supplier_id}/extraction-rules`（`:875-923`、`_EXTRACTION_RULE_UPDATABLE` セット `:757-765` に列を追加するだけで動的UPDATE文に反映される設計）
  - 定数 `_EXTRACTION_RULE_COLS`（`:751-755`）・`_EXTRACTION_RULE_UPDATABLE`（`:757-765`）に `extraction_ship_format` を追加すれば GET/PATCH 両方に自動反映
  - スキーマ: `backend/app/schemas/central_masters.py` の `SupplierExtractionRulesResponse`（`:410-421`）と `SupplierExtractionRulesUpdate`（`:424-432`、`Field(default=None, max_length=...)` パターン）に `extraction_ship_format` フィールド追加要

## 7. NeedsReviewListPage のタブ機構／関連金型

- 現状 `frontend/src/pages/super-admin/NeedsReviewListPage.tsx` は **Tabs金型を使っていない**。`status_tab: "NEEDS_REVIEW"` というクエリパラメータで `GET /api/v1/tcg/analysis-results?status_tab=...` を叩き、結果を `DataTable`（`:11`,`:168`）に描画するだけの単一ビュー
- タブ金型は既存: `frontend/src/components/Tabs.tsx`（+`Tabs.css`+`frontend/src/components/Tabs.stories.tsx`）。`variant="underline"|"pill"`, `size="sm"|"md"`, `items: {key,label,count?,icon?,disabled?}[]` props（`frontend/src/components/Tabs.tsx:1-40`のJSDoc/型定義より）。カードDでは既存タブ無しのページに新規で `<Tabs>` を導入し、既存ビュー（NEEDS_REVIEW）とシャドー結果ビューを切り替える設計になる
- 関連金型一覧（`frontend/src/components/` 直下、拡張子省略）: `Badge`, `Button`, `Card`, `ContentToolbar`, `DataTable`, `Modal`/`ConfirmModal`, `PageLayout`, `Select`, `Tabs`, `TextField`（grep追加、Textareaも存在）
- `docs/CC_UI_GOVERNANCE.md`（ADR-144）要旨（原文引用）:
  > 1. `components/` に金型があるか先に確認する（`<Select>`/`<TextField>`/`<SearchBar>`/`<Tabs>`/`<OverflowTabs>` 等）
  > 2. あれば必ずそれを使う（独自実装を重複させない）
  > 3. 無ければ実装しない・止めて報告する（PO許可を得てから登録してから使う）
  > 禁止: 生`<select>`、生`<input type="text"|"search"|省略>`、自作タブ（className に `tab` 語を含む div/nav 等）、色直値インライン、生px数値インラインスタイル
  > 例外コメント書式（両方必須）: `{/* ui-allow: <理由> (#<課題番号>) */}`。番号は GitHub Issue、仮番`#0`禁止

## 8. キーワード登録API（既存パターン／新設exclude API用の型）

- 既存 `search-keywords` エンドポイント: `POST /api/v1/tcg/products/{product_id}/search-keywords`（`backend/app/routers/tcg_product_master.py:247-263`）。`Depends(require_super_admin)` で認証（super admin限定、`backend/app/routers/tcg_product_master.py:9-11` コメントにも「tenant_004専用」と明記）
- 実装本体: `add_search_keyword(db, *, product_id, new_keyword)`（`backend/app/services/tcg_product_master_svc.py:474-530`）
  - `new_keyword.strip()` が空なら `ValueError("SEARCH_KEYWORD_EMPTY")`
  - `products` テーブルを `FOR UPDATE` でロック確認、無ければ `SEARCH_KEYWORD_PRODUCT_NOT_FOUND`
  - 既存キーワードと重複なら `{"ok": False, "code": "KEYWORD_ALREADY_EXISTS"}`
  - `product_search_keywords` に `position = MAX+1` でINSERT
- **新設の exclude-keyword 単体追加API**は上記関数を鏡写しにして `product_exclude_keywords` テーブル（`backend/app/services/tcg_product_master_svc.py:436-451`にバルクINSERT実装あり、単体版は無し）に対して作る設計が自然。ルーターに `POST /tcg/products/{product_id}/exclude-keywords` を追加し、`add_search_keyword`と対の `add_exclude_keyword` サービス関数を新設する形

## 9. i18n ファイルパスと命名規約

- `frontend/src/locales/ja.json` / 対の `frontend/src/locales/en.json`（パス確認: ja側のみ実読、en側は場所推定=`frontend/src/locales/en.json`だが本セッションでは開いていない＝**未確認**）
- キー命名: super-adminページは `"知識"名前空間 knowledge.*`（例 `knowledge.promptSection`）のようにページ機能単位でオブジェクトをネストし、camelCaseキーを使う規約（既存 `promptSection`/`promptHelp`/`promptPlaceholder`/`rulesSection`/`aliasesSection`等から）。ADR-027によりja/en同一キー必須、ハードコード日本語禁止

## 10. PG テスト fixture パターン

- 命名規約: 実PostgreSQL必須のテストは test_*_pg.py（例: `backend/tests/test_tcg_extraction_record_integrity_pg.py`, `backend/tests/test_tcg_product_import_atomicity_pg.py` 他、grep該当10件以上）
- 共有conftestの`engine`fixtureは無し。**各テストファイルが自前で定義**（`backend/tests/test_super_admin_suppliers.py:19-33`の例）:
  ```python
  TEST_PG_URL = os.getenv("TEST_PG_URL")
  pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not TEST_PG_URL, reason="実 PostgreSQL 環境が必要 (TEST_PG_URL 未設定)。")]

  @pytest.fixture
  async def engine():
      from sqlalchemy.ext.asyncio import create_async_engine
      eng = create_async_engine(TEST_PG_URL, echo=False)
      yield eng
      await eng.dispose()
  ```
- _pg.py サフィックスのファイル名自体が命名規約（grep該当が全て_pg.py）。非PGテストと同居する `backend/tests/test_super_admin_suppliers.py` のように _pg.py サフィックスなしでも `TEST_PG_URL` skipif パターンを使う例もある（両方存在、統一名称ではなく「実DB必須テストは`TEST_PG_URL`スキップガード必須」が本質規約）

## 未確認・要追加調査

1. `extraction_prompt_config` の初期2行（base_extraction/work_id_extraction）がどう投入されたか（migrationに痕跡なし＝手動 or 別スクリプト、v7追加時のINSERT方式の参考にできず）
2. `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx` 内のプロンプト編集フォームの正確な行範囲（142/157周辺のstate/JSX含む削除対象全体）
3. `frontend/src/locales/en.json` 側の対応キー（ja.jsonとの1:1確認は未実施）
4. `supplier_knowledge_links` CRUDルーターの正確な行番号（`backend/app/routers/super_admin_suppliers.py`内、本調査では knowledge-links の具体的GET/POST/DELETE実装箇所まで行番号を特定できていない）
5. v7プロンプトの`prompt_key`命名・DB投入方式（新規キー名、`is_active`運用、シャドー専用に分離するか既存2キーと並存させるか）はPR-C設計時にArchitect判断が必要
