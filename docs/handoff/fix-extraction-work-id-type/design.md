# 設計: extraction_items.resolved_work_id 型修正

recon: `docs/handoff/fix-extraction-work-id-type/recon.md`
対象ADR: ADR-072

## 外部・過去事例の参照と我々への応用

該当なし: 本番DBのカラム型をマイグレーション定義に合わせる修正

## 目的

extraction_items.resolved_work_id カラムが UUID 型のままだが、master SSOT Phase 2 で work_id が INTEGER に変更されたため、抽出タスクがDB書き込み時にエラーとなる。カラム型を INTEGER に修正する。

## 受入条件と検証方法

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | resolved_work_id が INTEGER 型 | `\d tenant_004.extraction_items` で integer と表示 |
| 2 | 抽出タスクが正常完了する | pending extraction_job を1件実行して status=done |
| 3 | 既存テスト全通過 | CI green |

## 維持の仕組み

- 守り手: `migrations/20260919_190000_fix_extraction_work_id_type.sql` — 冪等設計で再実行可能
- 守り手: CI テナントスキーマ整合性チェック
