# design: 便E DROP TABLE deals

## KGI
全テナントで deals テーブルが存在しないこと

## KPI（検算基準）

| 基準 | 検証方法 | 結果 |
|---|---|---|
| deals テーブル消滅（全テナント） | to_regclass → NULL | ✓ 全6テナント NULL |
| deals を参照するビュー 0件 | pg_views LIKE '%deals%' | ✓ 0件 |
| deals への FK 0件 | FK constraint check | ✓ 0件 |
| deals RLS ポリシー消滅 | pg_policies | ✓ 0件 |
| 主要テーブル無事（leads/companies等） | pg_tables 存在確認 | ✓ 9テーブル確認 |
| v_company_stats 正常動作 | ビュー SELECT 実行 | ✓ 返却値確認 |
| 本番 API 応答 | HTTP ステータス | ✓ 401（認証ゲート正常） |

## 変更ファイル
- migrations/20260729_043520_drop_deals.sql（新規）
- scripts/run_all_migrations.sh（登録）

## CASCADE 要否
不要。外部依存ゼロ（dry-run 実証済み）。

## 適用経路
- 既存テナント: 本番で直接実行済み（2026-07-29）
- 新規テナント: tenant.py 便D-1 で deals DDL 除去済み（作成されない）
