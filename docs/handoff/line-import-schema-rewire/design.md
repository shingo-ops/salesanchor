# Phase 5 追補設計 — line-import-schema-rewire

**対象ADR**: ADR-156（商品分類ツリーと共用マスタ分離。Step 4/5 のスキーマ移行対象にパイプラインテーブルを含む）
**recon**: docs/handoff/line-import-schema-rewire/recon.md
**日付**: 2026-09-22
**担当**: implementer（本番障害の緊急復旧）

---

## 障害と原因（事実）

- 2026-09-21 16:52、PR #3628（`migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`）が
  マージされ、`tenant_004.source_messages` / `supplier_channels` / `import_jobs` /
  `import_job_messages` / `extraction_jobs` 等をDROP（ADR-156 Step 5/5、public 移行完了後の後片付け）。
- `backend/app/services/tcg_line_import_svc.py` だけが `from app.tcg_config import TCG_SCHEMA`
  （既定値 `tenant_004`）のままで、DROP 済みテーブルへの読み書きを継続していたため、
  17:01:43 以降 `POST /api/v1/tcg/line-devices/import` が HTTP 500 を返し続けた。
- 同時期に public 移行された他15モジュール（`backend/app/routers/tcg_line_import.py:56` 等）は
  すでに `TCG_SCHEMA = "public"` へのモジュール内直接定義に書き換え済みで、本モジュールのみ書き換え漏れ。

## 外部・過去事例の参照と我々への応用

**過去事例（同リポジトリ）**: `backend/app/routers/tcg_line_import.py:54-56` および
`backend/app/services/tcg_import_progress.py:13-15` で採用済みのパターン
（`# Step 4/5: TCG テーブルは public スキーマに移行済み。` コメント + モジュール内で
`TCG_SCHEMA = "public"` を直接定義し `app.tcg_config` の import を外す）を、そのまま
tcg_line_import_svc.py に適用した。新規パターンの考案はしていない。

---

## 変更内容

### backend/app/services/tcg_line_import_svc.py

1. モジュール docstring 冒頭の
   `TCG解析システムは tenant_004 専用スキーマ。全 SQL は tenant_004. で修飾する。`
   （事実誤り）を
   `Step 4/5: TCG テーブルは public スキーマに移行済み。全 SQL は public. で修飾する。`
   に修正。
2. `from app.tcg_config import TCG_SCHEMA` を削除し、他15モジュールと同じ形の
   モジュール内定数定義に置換:
   ```python
   # Step 4/5: TCG テーブルは public スキーマに移行済み。
   # テスト互換性のため TCG_SCHEMA 属性を維持する（monkeypatch.setattr 対象）。
   TCG_SCHEMA = "public"
   ```
3. `{TCG_SCHEMA}.<table>` を使う既存SQL文字列・`public.suppliers` への直書きINSERTは
   一切変更していない（`{TCG_SCHEMA}` が `"public"` を指すようになるだけ）。

### backend/tests/test_tcg_line_import.py（テスト側の tenant_004 前提を是正）

修正前は本番SQLが `tenant_004.` 前提のまま3件ハードコードされており、
`TCG_SCHEMA = "public"` 化後はいずれも失敗した（作業3で実測、後述）。

1. `from app.tcg_config import TCG_SCHEMA as _SCHEMA` →
   `from app.services.tcg_line_import_svc import TCG_SCHEMA as _SCHEMA`
   （テストが検証すべきは「サービスが実際に使うスキーマ」であり、`tcg_config` の既定値ではない）
2. `"INSERT INTO tenant_004.source_messages" in s` のハードコード3箇所を
   `"INSERT INTO public.source_messages" in s` に修正
   （`test_import_zero_unresolved_writes_source_messages`,
   `test_import_unresolved_auto_creates_supplier_and_writes_source_messages`,
   `test_import_partial_unresolved_auto_creates_and_writes_all`）。

`test_tcg_line_import.py:516` のコメント（旧migration `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql`
への言及）はテストの合否に影響しない説明コメントのため変更していない。

---

## テーブル実在確認（5件・作業1の停止条件クリア）

| `{TCG_SCHEMA}.<table>` | public 実在確認 |
|---|---|
| supplier_channels | `migrations/20260921_110000_pipeline_tables_public.sql:9` |
| source_messages | `migrations/20260921_110000_pipeline_tables_public.sql:19` |
| extraction_jobs | `migrations/20260921_110000_pipeline_tables_public.sql:78` |
| import_job_messages | `migrations/20260921_110000_pipeline_tables_public.sql:57` |
| import_jobs | `migrations/20260921_110000_pipeline_tables_public.sql:39` |

存在しないテーブルはゼロ。作業1の「勝手に判断せず報告して停止」条件には該当しなかった。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| tcg_line_import_svc.py が `app.tcg_config` を import しなくなる | `grep -n "from app.tcg_config" backend/app/services/tcg_line_import_svc.py` → ヒットなし |
| `TCG_SCHEMA` が `"public"` に固定される | `grep -n 'TCG_SCHEMA = "public"' backend/app/services/tcg_line_import_svc.py` → 1件ヒット |
| docstring の tenant_004 専用記述が消える | `grep -n "tenant_004 専用スキーマ" backend/app/services/tcg_line_import_svc.py` → ヒットなし |
| LINE取込関連ユニットテストが全件成功 | `pytest backend/tests/test_tcg_line_import.py backend/tests/test_line_import_admin.py backend/tests/test_line_import_devices.py backend/tests/test_tcg_line_android_api.py backend/tests/test_tcg_line_android_parser.py backend/tests/test_tcg_config.py backend/tests/test_tcg_schema_qualification.py backend/tests/test_tcg_gemini_extraction.py backend/tests/test_line_source_names.py -q` → 200 passed（実測、後述） |
| 静的スキーマ修飾チェック（AST）が通る | `pytest backend/tests/test_tcg_schema_qualification.py -q` → 実測 pass |
| 本番デプロイ後、LINE取込APIが200で応答する | デプロイ後 `POST /api/v1/tcg/line-devices/import` を実インポートで確認（本PRのスコープ外・デプロイ後PO確認事項） |

---

## 実測値（作業3のテスト実行結果）

実行環境: このworktree上、依存関係が揃っている別worktree
（`/root/worktrees/salesanchor/release-mobile-dev-environment/.venv`, Python 3.12.14,
pytest 8.3.5）の venv を使用。ローカルに CI 用 PostgreSQL がないため `_pg` サフィックスの
統合テスト（`GITHUB_ACTIONS=true` を前提とする disposable DB テスト）は対象外。

- 修正前（tcg_line_import_svc.py 修正後・テスト未修正の状態）:
  `pytest backend/tests/test_tcg_line_import.py ... -q --no-cov`
  → `4 failed, 119 passed`
  失敗4件はいずれも `AssertionError`:
  - `test_source_message_insert_before_update_supersede`:
    `INSERT INTO source_messages が呼ばれなかった`（`_SCHEMA` が `tcg_config` 由来の
    `tenant_004` のままで、実SQLの `public.source_messages` と不一致）
  - `test_import_zero_unresolved_writes_source_messages`,
    `test_import_unresolved_auto_creates_supplier_and_writes_source_messages`,
    `test_import_partial_unresolved_auto_creates_and_writes_all`:
    いずれも `"INSERT INTO tenant_004.source_messages" in s` のハードコード比較に失敗
- テスト側修正後:
  `pytest backend/tests/test_tcg_line_import.py backend/tests/test_line_import_admin.py backend/tests/test_line_import_devices.py backend/tests/test_tcg_line_android_api.py backend/tests/test_tcg_line_android_parser.py -q --no-cov`
  → `123 passed`
  `pytest backend/tests/test_tcg_config.py backend/tests/test_tcg_gemini_extraction.py backend/tests/test_tcg_schema_qualification.py backend/tests/test_line_source_names.py -q --no-cov`
  → `77 passed`
  リポジトリ全体の `tcg` / `line_import` キーワードテスト:
  `pytest backend/tests/ -k "tcg or line_import" -q --no-cov`
  → `1179 passed, 74 skipped, 446 errors`（全 error は `_pg` テストの
  `AssertionError: Disposable CI PostgreSQL required` — `GITHUB_ACTIONS` 環境変数を
  前提とするゲートで、ローカル実行環境の制約によるもの。本PRの変更とは無関係と判断）

---

## 弊害・トレードオフ

- `backend/app/tcg_config.py` はそのまま残置（他の未移行8モジュールが引き続き参照するため）。
  今回の tcg_line_import_svc.py 修正で tcg_config.py 自体は不要にならない。
- テスト互換性のため `TCG_SCHEMA` をモジュール属性として維持しているが、これは既存15モジュールと
  同じ設計であり新規の弊害ではない。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | tcg_line_import_svc.py の import と docstring を public 化 | implementer |
| 2 | 参照5テーブルの public 実在確認 | implementer |
| 3 | 残存8モジュールの調査（修正はしない） | implementer |
| 4 | LINE取込関連テスト実行・tenant_004前提の3箇所を修正 | implementer |
| 5 | recon.md / design.md 作成 | implementer |
| 6 | push（PR作成は親セッション） | implementer |

---

## 継続

- **完了後の監視**: デプロイ後、`POST /api/v1/tcg/line-devices/import` の実インポートで
  200 応答・`source_messages` への INSERT を確認すること（PO確認事項）。
- **次フェーズへの引き継ぎ**: 作業2で判明した残存8モジュール（`backend/app/line_import_admin.py`,
  `backend/app/routers/tcg_product_import.py`, `backend/app/services/tcg_product_detail_svc.py`,
  `backend/app/services/tcg_product_import_svc.py`, `backend/app/services/tcg_product_master_svc.py`,
  `backend/app/services/tcg_product_roundtrip_svc.py`, `backend/app/services/tcg_work_comparison_svc.py`,
  `backend/app/tasks/tcg_mirror.py`）はいずれも同じ理由（tenant_004パイプラインテーブルDROP）で
  壊れていることを確認済み。詳細は `docs/handoff/line-import-schema-rewire/recon.md` の
  一覧表を参照し、別PRで同一パターン（`TCG_SCHEMA = "public"` へのモジュール内直接定義）を
  適用すること。加えて `backend/app/services/tcg_product_import_svc.py` の `tcg_major_categories` /
  `tcg_product_categories` 参照（`LOOKUP_TABLES`）は、パイプラインDROPとは別の
  `migrations/20260921_130000_drop_tenant004_master_copies.sql` によっても壊れている
  可能性があり、そちらも合わせて調査が必要。

## 維持の仕組み

守り手: `backend/tests/test_tcg_schema_qualification.py` の `TARGETS` リストに
`backend/app/services/tcg_line_import_svc.py` が既に登録されており（`import_jobs`,
`source_messages`, `supplier_channels`, `extraction_jobs`）、静的AST解析で
「`{TCG_SCHEMA}.` / `public.` のどちらでもない裸のテーブル参照」を今後もCIで検出する。
`backend/tests/test_tcg_config.py::test_tcg_line_import_svc_uses_configured_schema` は
`monkeypatch.setattr(svc, "TCG_SCHEMA", ...)` でモジュール属性を直接差し替える方式のため、
`TCG_SCHEMA` の定義元を import からモジュール内定数に変えても引き続き有効。
