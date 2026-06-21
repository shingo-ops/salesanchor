# 設計 — migration-080-fix

**対象ADR**: ADR-135
**recon**: docs/handoff/migration-080-fix/recon.md
**日付**: 2026-06-22
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：git 未追跡ファイルの追跡化は標準的な git 操作であり、外部事例参照は不要と判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `Deploy to VPS` ワークフローが SUCCESS になる | CI 確認 |
| migration 080 が VPS で実行される | deploy ログの `migration 080` 行を確認 |
| 既存行が誤更新されない（冪等） | WHERE category IS NULL のみ更新（スクリプト内確認済み） |

---

## 技術 How・KPI

- **原因**: `scripts/migrate_20260620_080000_calendar_category_backfill.py` が `git add` されておらず VPS 側コンテナに存在しなかった
- **対応**: `git add scripts/migrate_20260620_080000_calendar_category_backfill.py` → commit → deploy
- **KPI**: デプロイ FAILURE → SUCCESS

---

## 弊害・トレードオフ

- migration 080 は冪等（`WHERE category IS NULL`）のため再実行で副作用なし
- `scripts/` パスは ADR-135 の管理対象（本番スクリプト）— PO 承認済み前提

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `scripts/migrate_20260620_080000_calendar_category_backfill.py` を git add → commit | Generator |
| 2 | PR 作成 → develop マージ → main → deploy | Generator |

---
