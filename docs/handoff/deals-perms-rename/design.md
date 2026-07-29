---
sprint: deals-perms-rename
title: deals.* 権限の本番DB削除とコード側クリーンアップ
親リンク: docs/specs/db-ssot/deal-removal/design.md
recon: docs/handoff/deals-perms-rename/recon.md
ADR: ADR-121（deals廃止段階）
date: 2026-07-29
---

# design.md — deals-perms-rename

## 素人向け1行説明

「案件管理」機能を廃止したあとも DB に残っていた「案件権限の設定データ」を削除し、新しいテナントでも作られないようにする。

---

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| `public.permissions` に deals.* 行が 0件 | dry-run で削除後件数=0 確認・本番適用後実測 |
| 全テナントの `role_permissions` に deals.* 付与が 0件 | CASCADE 自動削除・本番適用後実測 |
| 新規テナント作成時に deals.* 権限が作られない | migration 002 から deals.* 除去・tenant.py ロール付与から除去 |
| CI テストが既存不安定事象以外 PASS | pytest backend/tests/（deals.* 除去後） |
| frontend tsc build 成功 | npm run build |

---

## 変更内容

### DB 側（migration）

| ファイル | 変更内容 |
|------|---------|
| `migrations/20260729_170000_drop_deals_permissions.sql`（新規） | `DELETE FROM public.permissions WHERE key LIKE 'deals.%'`（CASCADE で role_permissions 70行も自動削除） |
| `scripts/run_all_migrations.sh`（末尾追記） | 上記 migration を登録 |

### コード側（新規テナント・テスト）

| ファイル | 変更内容 |
|------|---------|
| `migrations/002_add_permissions_master.sql:45-48` | deals.* 4行の INSERT 定義を除去（fresh setup 向け） |
| `backend/app/services/tenant.py:75` | `"deals.view", "deals.update"` を除去（マネージャー） |
| `backend/app/services/tenant.py:103` | `"deals.view", "deals.create", "deals.update"` を除去（営業） |
| `backend/app/services/tenant.py:127` | `"deals.view"` を除去（CS） |
| `backend/tests/conftest.py:1433` | `ALL_TEST_PERMISSIONS` から deals.* 4項目を除去 |
| `frontend/tests-e2e/utils/common-mocks.ts:21` | `"deals.view"` を除去 |

---

## 削除順序と安全性（前 recon 実測根拠）

1. `DELETE FROM public.permissions WHERE key LIKE 'deals.%'`（4行）
2. CASCADE → `role_permissions.permission_id` → 全テナント 70行 自動削除
3. role_permissions 以外に FK 参照テーブル: **0件**（実測済み）
4. deals.* をチェックするエンドポイント: **0件**（便C PR#3129 で削除済み）

手動で role_permissions を先に削除する必要はない（CASCADE で完結）。

---

## 外部事例欄

| 項目 | 内容 |
|------|------|
| 類似先行事例 | `migrations/079_remove_buddy_badges.sql`: buddy/badges 権限を同様に `DELETE FROM public.permissions WHERE resource IN (...)` で削除（CASCADE 実績あり） |

---

## 受入基準表

| # | 受入条件 | 検証方法 | 判定 |
|---|---------|---------|------|
| 1 | dry-run で deals.* 削除前=4行・削除後=0行・ROLLBACK で復帰 | 手順3生出力 | ○（dry-run済み） |
| 2 | migration 002 に deals.* INSERT なし | `grep "deals\." migrations/002_add_permissions_master.sql` → ヒットなし | ○ |
| 3 | tenant.py に deals.* 付与なし | `grep "deals\." backend/app/services/tenant.py` → ヒットなし | ○ |
| 4 | conftest.py に deals.* なし | `grep "deals\." backend/tests/conftest.py` → ヒットなし | ○ |
| 5 | E2E mock に deals.view なし | `grep "deals" frontend/tests-e2e/utils/common-mocks.ts` → ヒットなし | ○ |
| 6 | backend pytest PASS | 手順4生出力 | ○（実行済み） |
| 7 | frontend build 成功 | 手順4生出力 | ○（実行済み） |
| 8 | 本番 DB は本カードで変更しない | push なし・DR 別段 | ○ |

---

## 維持の仕組み欄

| リスク | 対策 |
|-------|------|
| deals.* が再追加される | migration 002 と tenant.py 両方から除去。再追加には両方変更が必要で目立つ |
| 新規テナントで deals.* が出現 | tenant.py から除去済み。migration 002 の deals.* INSERT も除去済み |
