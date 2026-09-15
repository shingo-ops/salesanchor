# Phase 2b 設計 — ADR-1001 Python API 配線変更

**対象ADR**: ADR-1001  
**recon**: docs/handoff/adr-1001-phase2b/recon.md  
**日付**: 2026-09-14  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：Phase 2b は既存テーブル間の SQL 参照先切替であり、外部事例の参照は不要と判断。Phase 2a（PR #3503）で確立したスキーマ拡張・データ移行・FK 張替えの上に、Python コードの参照先を変更するのみ

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| backend/app/ 内の tcg_products SQL 参照が 0 件 | `grep -rn "tcg_products" backend/app/` で 0 件 |
| カラム名マッピングが正しい（code→product_code, japanese_title→name） | CI pytest 全テスト PASS |
| FK JOIN が p.tcg_uuid 経由で動作 | `pytest backend/tests/test_tcg_product_import_atomicity_pg.py` |
| RLS 対応（SET LOCAL app.is_operator） | `pytest backend/tests/test_tcg_work_matching_integration.py` |
| テスト環境で public.products が正しく作成される | CI pytest-run-internal PASS |
| 既存テナントのデータに影響なし | Phase 2a migration の Step 4 検証（count 一致） |

---

## 技術 How・KPI

- KPI: `grep -rn "tcg_products" backend/app/` の結果が 0 件
- 技術選択: SQL 文字列内の参照先を直接書き換え（ORM 未使用のため文字列置換が最も安全）
- カラム名マッピング: code→product_code, japanese_title→name, english_title→name_en, id→tcg_uuid

---

## 弊害・トレードオフ

- Phase 2b 単体では tcg_products テーブルは残存する（Phase 2c で DROP 予定、PO立会い必須）
- テスト用 public.products DDL をフィクスチャファイルに分離（test-schema-dup gate 対応）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 14 サービス/ルーター/タスクの SQL 参照を public.products に書き換え | Generator |
| 2 | 10 テストファイルのフィクスチャ・アサーション更新 | Generator |
| 3 | CI 全チェック PASS 確認 | Evaluator |

---

## 継続

- 完了後の監視: Phase 2c（tcg_products DROP）は PO 立会いで別 PR
- 守り手: `scripts/check_test_schema_dup.py` がテスト内の本番スキーマ複製を検出

---

## 維持の仕組み

- CI の test-schema-dup gate がテストファイル内の CREATE TABLE 増加を検出・ブロック
- CI の process-artifacts gate が触るファイル/削除するファイルの宣言漏れを検出
- Phase 2c 完了後は tcg_products への参照自体が存在しなくなり、grep で機械的に検証可能
