# ADR-147: 共通6ロール標準化（マネージャー・仕入れ・発送追加）

**ステータス**: Accepted  
**日付**: 2026-06-26  
**起案者**: Hikky-dev  
**承認者**: Shingo（shingo-ops）

---

## 背景

既存の5ロール体制（オーナー・システム管理者・リーダー・営業・CS）では、仕入れ・発送業務担当者に適切な権限セットを付与できない。また「リーダー」は職能を表さない汎用名称であり、マネジメント職能を表す「マネージャー」に統一することで UI の可読性を向上させる。

---

## 決定

全テナント共通の `DEFAULT_ROLES` を以下6ロール体制に更新する。

| ロール | priority | 変更種別 | 主な権限 |
|--------|----------|----------|---------|
| オーナー | 1000 | 変更なし | 全権限 |
| システム管理者 | 900 | 変更なし | system.manage 以外の全権限 |
| マネージャー | 500 | リーダーから改名 | leads/deals/teams/reports 等 |
| 仕入れ | 450 | **新規追加** | suppliers/purchase_orders/products |
| 発送 | 350 | **新規追加** | orders/shipping/products |
| 営業 | 300 | 変更なし | customers/leads/deals/orders |
| CS | 300 | 変更なし | customers/orders フォローアップ |

### 既存テナントへの適用方式

スクリプト `scripts/migrate_6roles_stage_a.py` により手動・冪等に適用する。

- `リーダー` が存在し `マネージャー` が存在しない → `UPDATE name` のみ（権限据え置き）
- `マネージャー` が既に存在する → スキップ
- `仕入れ担当` / `発送担当` → 同様に改名またはスキップ
- どちらも存在しない → `seed_system_roles` で新規 INSERT

スクリプトは `--tenant-id` 必須・本番（tenant_id=4）は `--yes-production` フラグ必須。CI 自動実行対象外（段階的手動適用）。

---

## 根拠

- `user_roles` は `role_id`（FK）参照のため、改名後もユーザー紐付けは自動維持される。
- `UNIQUE(tenant_id, name)` 制約により重複作成なし。
- `seed_system_roles` の `ON CONFLICT (tenant_id, name) DO UPDATE` により冪等性保証。

---

## 影響範囲

- `backend/app/services/tenant.py`: `DEFAULT_ROLES` 更新・docstring 更新
- `scripts/migrate_6roles_stage_a.py`: 新規作成
- `migrations/`: 変更なし（スクリプト方式）
- `deploy.yml`: 変更なし
