# 設計 — inventory-aggregated-main

**対象ADR**: ADR-099
**recon**: docs/handoff/inventory-aggregated-main/recon.md
**日付**: 2026-06-24
**担当**: shingo-cc

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本変更は develop の PR #2514 で実装・CI 緑・アーキ突合済みの機能を main へ 1テーマ直行するカービーアウトPRである。新規設計要素なし。既存ロジック（`aggregate_inventory_offers` / `_load_inventory_offers`）は改変しない。外部事例参照が不要な理由は「改変ゼロ、コピー移植のみ」という性質による。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `GET /api/v1/inventory/aggregated` が 200 を返し tabs/rows ピボットを含む | `pytest backend/tests/test_inventory_aggregated.py::test_aggregated_endpoint_returns_best_pick_rows` |
| category フィルタが機能する | `pytest backend/tests/test_inventory_aggregated.py::test_aggregated_endpoint_category_filter` |
| テナント応答に `supplier_name`/`reason`/`raw` が含まれない | `pytest backend/tests/test_inventory_aggregated.py::test_aggregated_boundary_no_internal_fields` |
| 既存 golden テスト（test_inventory_aggregation.py）が退行しない | CI backend-tests — 1928 passed / 0 failed（CI run #28061239951 確認済み） |
| `git diff --name-only origin/main..HEAD` に `migrations/` が含まれない | `git diff --name-only origin/main..HEAD \| grep -c migrations/` = 0 |

---

## 技術 How・KPI

- KPI: CI backend-tests 1928 passed / 0 failed（退行ゼロ）
- 技術選択: cherry-pick ではなく `git checkout <sha> -- <files>` でファイル単位コピー。理由: ツリー上の依存を含まないため conflict が発生しない。

---

## 弊害・トレードオフ

- migration ゼロのため rollback は `git revert` + deploy のみ。DB 状態変化なし。
- main の `_load_inventory_offers` が `raw_condition` を参照するため、テスト fixture に 3 migration bootstrap を追加。main 既存テストへの影響なし（別 fixture）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | develop PR #2514 の差分を `git checkout f4c20d5c` でコピー | shingo-cc |
| 2 | main.py への router 登録（import + include_router） | shingo-cc |
| 3 | テスト fixture の migration bootstrap 修正（2コミット） | shingo-cc |
| 4 | Draft PR #2537 作成・CI 緑確認 | shingo-cc |
| 5 | GO記録受領・SOP artifacts コミット | shingo-cc |
| 6 | un-draft → PO マージ → prod デプロイ | Shingo（PO） |

---

## 継続

- 完了後の監視: prod デプロイ後、`GET /api/v1/inventory/aggregated` の 200 応答を smoke チェック。
- 次フェーズへの引き継ぎ: products FK migration（`20260623_030000_add_products_tcg_type_fk.sql`）は別PR（develop→main）にて GO待ち。
