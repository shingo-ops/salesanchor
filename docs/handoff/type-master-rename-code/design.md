# design: ADR-156 Phase 2 — tcg_type_master → type_master コード統一

## 背景

Phase 1（PR #3620）で DB テーブルを `public.tcg_type_master` → `public.type_master` にリネームし、
後方互換ビュー `CREATE VIEW public.tcg_type_master AS SELECT * FROM public.type_master` を提供した。
Phase 2 では Python コード・テスト内の `tcg_type_master` 文字列参照を `type_master` に統一し、互換ビューへの依存を解消する。

## 受入基準

| 基準 | 検証方法 |
|-----|--------|
| Python 本体（backend/app/）に `tcg_type_master` が残っていない | `grep -rn "tcg_type_master" backend/app/ --include="*.py"` → 0件 |
| テスト内に `tcg_type_master` が残っていない（migration ファイル名文字列は除外） | `grep -rn "tcg_type_master" backend/tests/ --include="*.py" \| grep -v "085_create_tcg_type_master.sql"` → 0件 |
| フロントエンドに `tcg_type_master` が残っていない | `grep -rn "tcg_type_master" frontend/ --include="*.tsx"` → 0件 |
| migration-guard.yml に `tcg_type_master` が残っていない | `grep "tcg_type_master" .github/workflows/migration-guard.yml` → 0件 |
| CI テストが通過する（pytest） | GitHub Actions の test ジョブが green |
| conftest.py の SQLite テーブルが `type_master` を正しく作成する | SQLite テスト全般が pass |
| 旧 migration（085/086）が CI 並列テスト環境で互換ビュー共存時でもエラーにならない | test_tcg_distribution_pg / test_tcg_product_list_pg 等が pass |

## 影響範囲

- **Python コード**: 12ファイル（SQL 文字列・コメント）
- **Pydantic スキーマ**: 2ファイル（コメントのみ）
- **テスト**: 8ファイル（SQLite DDL・SQL 文字列・コメント）
- **フロントエンド**: 2ファイル（コメントのみ、ロジック変更なし）
- **CI/CD**: 1ファイル（PROTECTED_TABLES / PUBLIC_TABLES のテーブル名）
- **Migration**: 4ファイル（relkind チェック追加・本番テーブルの変更なし）

## 弊害・リスク

| リスク | 対処 |
|-------|------|
| 互換ビュー経由で実行中のクエリが残存する | Phase 2 完了後に互換ビューを DROP する Phase 3 で対処（今回は DROP しない） |
| 旧 migration が CI 並列テストで VIEW 化後に実行されエラー | relkind チェックを migration に追加して回避（本番はリネーム済みなので実質スキップ） |
| dict キー `"tcg_type_master"` の変更が下流コードに影響 | `tcg_work_comparison_svc.py` のみ。同ファイル内で参照・消費されており外部影響なし |

## 外部事例

PostgreSQL テーブルリネームの互換ビューパターン（互換ビューで旧名を残しつつコードを順次移行）は
Rails の rename_table → view migration などで一般的に採用される段階的移行手法。

## 守り手（rollback）

1. 本 PR を revert して main にマージ → コードが `tcg_type_master` 参照に戻る
2. Phase 1 の互換ビューは残っているため、revert 後も本番は動作する

## 計画

1. PR #3620（Phase 1: DB リネーム + 互換ビュー）— main マージ済み
2. 本 PR（Phase 2: コード統一）— 今回
3. Phase 3（互換ビュー DROP）— Phase 2 稼働確認後に別 PR
