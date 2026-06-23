# recon — inventory-aggregated-main

**仕事名**: inventory-aggregated-main
**日付**: 2026-06-24
**対象ADR**: ADR-099
**担当**: shingo-cc

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/inventory_aggregated.py:43` | `GET /inventory/aggregated` エンドポイント定義（tenant-scoped） |
| `backend/app/schemas/inventory_aggregated.py:32` | `InventoryAggregatedResponse` — tabs/rows ピボット応答スキーマ |
| `backend/app/services/inventory_aggregated_service.py:121` | `get_aggregated_inventory()` — 集計エントリポイント |
| `backend/app/main.py:55` | `inventory_aggregated` router の import 登録 |
| `backend/app/main.py:496` | `include_router(inventory_aggregated.router)` — `/api/v1` prefix で挿入 |
| `backend/tests/test_inventory_aggregated.py:403` | PG E2E: `test_aggregated_endpoint_returns_best_pick_rows` |
| `backend/tests/test_inventory_aggregated.py:461` | PG E2E: `test_aggregated_boundary_no_internal_fields` — 境界テスト |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | main の `_load_inventory_offers` が `raw_condition` を参照するか | `backend/tests/test_inventory_aggregated.py:144` fixture で bootstrap 確認 | ✅ 解消済み |
| 2 | PR #2537 に migration が混入していないか | `git diff --name-only origin/main..HEAD` = 5ファイル（migrations/ なし）で確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 実装は develop の PR #2514（`f4c20d5c`）から `git checkout` で正確コピー。手打ちなし。
- main の `_load_inventory_offers`（`inventory_search.py`）は `raw_condition` / `seal` / `search_cond` / `grade` / `damage` / `unit` を参照するため、テスト fixture の bootstrap loop に 3 migration を追加済み（commit `2c512798`・`6306097a`）。
- 新規 migration: ゼロ。既存エンドポイントへの影響: なし（追加のみ）。
