# Pipeline Tables Public Migration — Design

## 目的
tenant_004スキーマに残っているパイプラインテーブル17本をpublicスキーマに移設し、TCG_SCHEMA依存を解消する。

## 対象テーブル（17本）
| # | テーブル | カテゴリ | FK依存 |
|---|---------|---------|--------|
| 1 | supplier_channels | C: チャネル | → public.suppliers |
| 2 | source_messages | C: メッセージ | → supplier_channels |
| 3 | import_jobs | B: インポート | なし |
| 4 | import_job_messages | B: インポート | → import_jobs, source_messages |
| 5 | extraction_jobs | A: 抽出 | → source_messages |
| 6 | extraction_items | A: 抽出 | → extraction_jobs |
| 7 | extraction_attempts | A: 抽出 | → extraction_jobs |
| 8 | analysis_runs | D: 解析 | → extraction_jobs |
| 9 | analysis_results | D: 解析 | → extraction_items, conditions, units, products |
| 10 | analysis_run_snapshots | D: 解析 | → analysis_runs |
| 11 | item_corrections | E: 補正 | なし（設計方針） |
| 12 | tcg_normalization_rules | E: 正規化 | なし |
| 13 | tcg_distribution_settings | F: 配信 | なし |
| 14 | tcg_distribution_targets | F: 配信 | なし |
| 15 | tcg_product_import_jobs | F: 商品取込 | なし |
| 16 | tcg_product_import_rows | F: 商品取込 | → tcg_product_import_jobs |
| 17 | audit_log | F: 監査 | なし |

## 5ステップ計画
1. **DDL作成**（本PR）: publicにCREATE TABLE IF NOT EXISTS — データ操作なし
2. **列チェック**: マイグレーションで列の有無のみ確認
3. **データ移植**: SSH経由でtenant_004 → publicへINSERT SELECT
4. **配線切替**: バックエンド17ファイルのTCG_SCHEMA参照をpublicに変更
5. **旧テーブル削除**: tenant_004の元テーブルをDROP

## 設計判断
- UUID PKを維持（パイプラインテーブルはマスタではないため整数変換不要）
- analysis_run_snapshots.unit_id/condition_idはUUID維持（レガシースナップショット形式）
- item_correctionsはFK制約なし（設計方針: 別スキーマ参照のため）
- CREATE TABLE IF NOT EXISTS で冪等性を確保

## 受入条件
| 基準 | 検証方法 |
|------|---------|
| 17テーブルがpublicに存在 | psql \dt public.* で確認 |
| migration-guard CI緑 | PR checks |
| 既存テーブルに影響なし | IF NOT EXISTS で保護 |
| データ操作なし | migration-guardがINSERT/UPDATE/DELETEをブロック |

## 外部事例
該当なし（内部スキーマ移行のため外部事例は不要）
