# recon: 新しい仕組みだけが読む仕入元ルールの欄を2つ足す

- 基準：origin/main = 9a2b06ecdff33a0bd43224e82962fe739defcfb2（git fetch 後。git show / git grep origin/main で確認）
- 元資料：/tmp/CC報告ファイル/v102/newcols/recon_raw.md
- 事実のみ。評価・提案は design.md に書く。社外秘の仕入元名・原文は書かない。

## 1. migration の作法
- migrations/20260924_030000_add_extraction_example_text.sql:1-2：`ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_example_text TEXT;`
- migrations/20260928_110000_create_extraction_shadow_tables.sql:9：`ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_ship_format TEXT;`
- migrations/20260924_010000_add_supplier_extraction_rules.sql:2-7：6列、すべて TEXT・IF NOT EXISTS
- 命名：backend/CLAUDE.md:50（migrations/YYYYMMDD_HHMMSS_description.sql）
- 追加のみの原則：backend/CLAUDE.md:41（カラム追加は許可）、:49
- 登録：scripts/run_all_migrations.sh:3-14（新マイグレーションは run_all_migrations.sh に追記）、:858-859 が書式の例、:800-804 が既存の extraction_* 列の登録
- .github/workflows/deploy.yml:205：deploy.yml への追記は不要と書かれている
- .github/workflows/migration-guard.yml:75-150（チェック2）：ファイル名 `^[0-9]{8}_[0-9]{6}_.*\.sql$` の強制、:119-139 で deploy.yml または run_all_migrations.sh への登録を確認
- .github/workflows/migration-test.yml:51-68：登録ファイルの存在点検（scripts/check-migration-registration-exists.sh）
- suppliers に ORM のモデルは無い（backend/app/models.py に suppliers を含む行は 0 件）。生 SQL で読み書き：backend/app/tasks/tcg_extraction.py:230-245、backend/app/routers/super_admin_suppliers.py:604-619, 688-695, 750-757
- 危険パス：scripts/check-process-artifacts.js:115-123（`/^migrations\//`・`/^scripts\//`、ADR-135）

## 2. ルールの読み込み経路
- backend/app/tasks/tcg_extraction.py:225-245 `_context_select_sql()`：8列＋ sc.supplier_id（:240）
- backend/app/tasks/tcg_extraction.py:248-254 `ExtractionContext`：raw_text, supplier_context, knowledge_links, supplier_id
- backend/app/tasks/tcg_extraction.py:257-296 `_build_extraction_context`：位置添字（row[2]〜row[9] が8列、:278 `supplier_id = row[10]`）、:273-274 `if any(v for v in extraction_rules.values()): supplier_context = extraction_rules`
- backend/tests/test_shadow_backfill.py:190-201：11要素のタプルで load_extraction_context を呼ぶ（位置添字に依存）
- 本番 v7：backend/app/tasks/tcg_extraction.py:348 → :399, :419-420 → backend/app/services/gemini_extraction_svc.py:810-844 → call_gemini_raw_copy（:468-）。:493 `_build_supplier_context_note(supplier_context or {}, ...)`、:495-501 で ship_format を v7 だけで末尾に足す
- 旧経路：backend/app/services/gemini_extraction_svc.py:405-407
- shadow：backend/app/tasks/tcg_extraction.py:563-579 → backend/app/services/extraction_shadow_svc.py:376-396（内部で call_gemini_raw_copy = v7）。必須鍵：extraction_shadow_svc.py:61-65、:74-78
- shadow_backfill：backend/app/tools/shadow_backfill.py:21, :112, :116-120（v7 と同じ経路）
- prompt_ab：backend/app/tools/prompt_ab.py:189-194（v7）、:462（v8 系 call_gemini_raw_copy_v8）、:312 `_SUPPLIER_FIELD_PATTERN`（`^extraction_[a-z_]+$`）、:352-366 `_supplier_context_with_rules`、:385-394（dry-run）

### 新2列を dict に足したとき v7 の指示書に入るか
- backend/app/services/gemini_extraction_svc.py:286-362 `_build_supplier_context_note` が dict から読む鍵は7つだけ：:313-319 label_map の5鍵、:326 extraction_order_pattern、:341-343 extraction_example_text。辞書を丸ごと出力する処理は無い
- ship_format はここでは読まず、:498 で v7 だけが別に読む
- 固定しているテスト：backend/tests/test_tcg_gemini_extraction.py:819-834、:836-879
- 副作用：tcg_extraction.py:273-274 は dict の値のどれかが真なら supplier_context を非 None にする。新2列を判定に含めると、新2列だけを持つ仕入元で None から非 None に変わる

## 3. 新しい仕組みの組み立て
- backend/app/services/gemini_raw_copy_v8.py:94-108 `build_supplier_note_v8`（:102 で v7 と同じ `_build_supplier_context_note` を呼ぶ。:104-107 で ship_format を末尾に足す）
- backend/app/services/gemini_raw_copy_v8.py:111-117 `build_prompt_v8`：prompt_text ＋ note ＋ 「原文:」＋ 原文
- 使用者：gemini_raw_copy_v8.py:114, :184、backend/app/tools/prompt_ab.py:44-45, :386, :462、backend/tests/test_gemini_raw_copy_v8.py
- v9 / v10 / v101 は build_prompt_v8 を使わず v8 の補助関数だけを使う：gemini_raw_copy_v9.py:15、gemini_raw_copy_v10.py:14、gemini_raw_copy_v101.py:18-19。v102 は専用ファイルが無く prompt_ab.py:385 で build_prompt_v8 を通る
- 本番（tcg_extraction.py）から v8 系を呼ぶ箇所は無い。呼び出しは prompt_ab.py のみ

## 4. API とスキーマ
- backend/app/schemas/central_masters.py:393-405 `SupplierExtractionRulesResponse`、:408-416 `SupplierExtractionRulesUpdate`（max_length：5000 / 50000 / 100）
- backend/app/routers/super_admin_suppliers.py:604-608 `_EXTRACTION_RULE_COLS`、:610-619 `_EXTRACTION_RULE_UPDATABLE`、:639-646 has_extraction_rules（6列の OR。example_text・ship_format は含まない）、:688-695 GET の SELECT、:716-727 GET の詰め替え、:747-757 PATCH の UPDATE、:767-777 PATCH の詰め替え
- 認可：super_admin_suppliers.py:625, :679, :733 `Depends(require_super_admin)`
- OpenAPI：frontend/api-contract/openapi.json。生成は `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`（.github/workflows/api-contract-check.yml:31-35）、差分検査は同 :50-55。Python は 3.12（同 :16-19）、依存は backend/requirements.txt（同 :27-29）
- frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx は generated 型を使わず、ページ内で interface を手書き（:37-48）

## 5. 画面
- frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:7-8（ADR-027・ADR-144 の注記）
- 欄の並び：:37-48（interface）、:77-86（RulesFormState）、:88-97（emptyForm）、:99-110（detailToForm）、:421-430（handleSave の payload）
- 描画：:774-805（Textarea ×3：extraction_notes、example_text、ship_format）
- 部品の import：:10-23（Textarea は frontend/src/components/Textarea）
- 文言：frontend/src/locales/ja.json:5054 から supplierExtractionRules。:5122-5123 が shipFormat / shipFormatHelper。en.json も同じ行番号
- 機械検査：frontend/package.json:27 `check:i18n-missing-keys`、scripts/check-ui-governance.js（ADR-144）

## 6. テスト
- backend/tests/conftest.py:47-70 `_PUBLIC_SUPPLIERS_DDL`（:56-63 に8列）
- backend/tests/test_gemini_raw_copy_v8.py:40-48 `_CTX`、:55-86
- backend/tests/test_prompt_ab.py:22-26, :746-749, :843-994
- backend/tests/test_tcg_gemini_extraction.py:741-751, :819-879
- backend/tests/test_shadow_backfill.py:190-201
- extraction-rules エンドポイントの API テストは見つからなかった（git grep "extraction-rules" backend/tests → 該当なし）
- extraction_layout_rules / extraction_hard_cases という名前は docs・backend・frontend/src に既存の出現なし

## 7. ADR・GO の決まり
- docs/adr/FEATURE-INDEX.md に仕入元ルールを直接指す行は無い（:18 は在庫・商品マスタ・仕入元 → ADR-099 / ADR-093 / ADR-014）
- 関連：docs/adr/ADR-085-supplier-prompts.md、docs/adr/ADR-014-inventory-management.md、docs/adr/ADR-045-migration-055-deploy-automation.md、docs/adr/ADR-1004
- ADR-135：main へのマージ ＝ 本番投入可。migrations/・scripts/ は危険パス（CLAUDE.md「ブランチ運用ルール」）
- ADR-136：docs/adr/ADR-136-cc-bot-github-identity.md（GO 手順）。同名番号の別 ADR：docs/adr/ADR-136-company-stats-ssot.md
- 関連する過去の設計：docs/handoff/extraction-example-text/、docs/handoff/gemini-extract-role-split/、docs/handoff/gemini-supplier-rules-file/、docs/handoff/gemini-omit-supplier-field/、docs/handoff/gemini-v102/

## 8. 手元の openapi 生成で分かった事実（本 PR の作業中）
- 手元の python3（3.14.3）では、変更前の origin/main でも openapi.json との差が 652 行出る（環境差）
- CI と同じ Python 3.12 に backend/requirements.txt を入れて生成すると、変更前の origin/main との差は 0 行
- その環境で本 PR の変更を生成した差は 46 行（2列 × Response・Update の2スキーマ）
