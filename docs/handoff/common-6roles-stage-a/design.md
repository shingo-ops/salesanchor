# Design — 共通6ロール標準化 段階A

recon: docs/handoff/common-6roles-stage-a/recon.md  
対象ADR: ADR-147

## 変更概要

`DEFAULT_ROLES`（`backend/app/services/tenant.py`）を5ロールから6ロール体制へ更新し、既存テナント揃えスクリプトを新規作成する。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| DEFAULT_ROLES にマネージャー・仕入れ・発送が定義されている | `grep "マネージャー\|仕入れ\|発送" backend/app/services/tenant.py` |
| 仕入れ・発送の permissions に `reports.view` が含まれる | コードレビューで直接確認 |
| スクリプト `--tenant-id` 未指定で終了・usage 表示 | `python scripts/migrate_6roles_stage_a.py` → argparse エラー |
| tenant_004 対象時に `--yes-production` 未指定で中断 | コードレビュー: `_PRODUCTION_TENANT_IDS = {4}` + sys.exit(1) |
| 適用前後の roles/user_roles 件数をログ出力する | コードレビュー: `_count_roles()` before/after ログ |
| 改名は name のみ UPDATE（権限・user_roles は変更しない） | コードレビュー: UPDATE 文が `SET name = :new_name` のみ |
| 冪等性: 2回実行しても重複作成・エラーなし | seed の ON CONFLICT DO UPDATE 設計 |

## 外部・過去事例の参照と我々への応用

一般的な SaaS 製品では職能別 RBAC（Shopify: Staff/Limited permissions、Salesforce: Standard Profiles）を採用し、「誰でも全機能」ではなく業務フローに合った権限粒度を提供する。今回の仕入れ・発送ロール追加はこれに倣い、物流担当者が必要な画面（在庫・発注・出荷）のみアクセスできる最小権限設計とした。

## 実施手順

1. `DEFAULT_ROLES` 更新 + スクリプト新規作成（本 PR）
2. develop マージ後、VPS でスクリプト実行（tenant_006 → tenant_004 の順）

## 非適用範囲

- `migrations/` への変更なし（スクリプト方式）
- `deploy.yml` への変更なし
- 本番（tenant_004）への適用は Shingo GO 後に手動実行
