# Phase 3 設計 — fix-unify-step3-type-guard

**対象ADR**: ADR-1002  
**recon**: docs/handoff/fix-unify-step3-type-guard/recon.md  
**日付**: 2026-09-22  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 事例1: PR #3672（release/fix-unify-type-mismatch-v2）にて Step 2 の work_id に pg_attribute 経由の型チェックガードを適用済み → 同パターンを Step 3 の4テーブルに横展開する
- 事例2: PostgreSQL `pg_attribute.atttypid` を `pg_type.oid` と比較して型を確認する手法は公式ドキュメントに記載のある標準パターン

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| products_logistics.product_id が INTEGER の場合、FK作成をスキップしエラーを出さない | CIマイグレーションが通過すること（deploy.yml の migrate step が成功） |
| analysis_results.product_id が INTEGER の場合、FK作成をスキップしエラーを出さない | 同上 |
| product_search_keywords.product_id が UUID の場合、FK作成を実行する | CI マイグレーション NOTICE ログで created FK を確認 |
| product_exclude_keywords.product_id が UUID の場合、FK作成を実行する | 同上 |

---

## 技術 How・KPI

- KPI: CI マイグレーション step がエラーなく通過（exit 0）
- 技術選択: `pg_attribute.atttypid` を `pg_type` の `uuid` oid と比較（PR #3672 と同一手法）

---

## 弊害・トレードオフ

- 型ガードでスキップした場合、FK は作成されない（INTEGER 型テーブルには tcg_uuid への FK は不要なため問題なし）
- DDL変更・データ変更なし。ガードを追加するだけのため副作用なし

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | DECLARE に _pid_type OID を追加 | Generator |
| 2 | 各テーブル（3-1〜3-4）の新FK作成ブロック直前に型チェックを挿入 | Generator |
| 3 | コミット・push・PR作成 | Generator |

---

## 継続

- 完了後: Phase 2a マイグレーション全体の CI が通過することを確認
- 次フェーズ: ADR-1002 Phase 2c（tcg_uuid DROP）への引き継ぎ

## 維持の仕組み

守り手: migrations/20260914_140000_unify_tcg_products_to_public.sql

- 型ガードは冪等。同じマイグレーションを再実行しても安全（すでに UUID 型ならFK作成、INTEGER型ならスキップ）
- 将来 product_id が UUID に戻された場合、ガードは自動的に FK 作成を実行する
