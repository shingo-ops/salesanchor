# design: fix-migration-runner-0922

## 参照ADR

- ADR-082: run_all_migrations.sh を migrations の SSoT とする

## 問題

Migration Guard CIが `20260922_040000_fix_phase2c_fk_blocker.sql` 未登録でfailure。
`070000` が2重登録。

## 修正方針

`scripts/run_all_migrations.sh` の行661（070000の重複エントリ）を `040000` の登録に変更する。

### 選択理由

- `040000` は冪等（BEGIN/COMMIT + IF EXISTS / IF NOT EXISTS ガード付き）
- 実行順序は問題なし（`050000` が後続で同じ操作をDROP-onlyで行うため安全）
- ファイルを削除する選択肢は Migration Guard が「ファイルが存在するなら登録必須」という要件を持つため不可

## 変更内容

`scripts/run_all_migrations.sh:661` の変更:

変更前:
```
# Phase 2c 前処理: tcg_products 参照 FK をクリーンアップ（冪等・2回目）
run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql
```

変更後:
```
# Fix: Phase 2c blocker — initial FK fix draft (public.analysis_results stale FK DROP + re-add)
# NOTE: superseded by 050000 for the DROP step, but registered here to satisfy migration guard
run_sql migrations/20260922_040000_fix_phase2c_fk_blocker.sql
```

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| Migration Guard CIがpassになること | `gh pr checks <PR番号>` で全件pass確認 |
| `040000` が登録済みになること | `grep 040000 scripts/run_all_migrations.sh` で1件ヒット |
| `070000` が重複しないこと | `grep -c 070000 scripts/run_all_migrations.sh` が1になること |

## 影響範囲

- 触るファイル: `scripts/run_all_migrations.sh` のみ
- 本番への影響: `040000` は冪等のため重複実行しても安全

## 外部事例

Migration Guard は `migrations/` 配下の全 `.sql` ファイルを検出し、`run_all_migrations.sh` または `deploy.yml` への登録を要求する（`.github/workflows/deploy.yml` 内のスクリプト参照）。

## 守り手

このPRは `scripts/run_all_migrations.sh` のみを変更する。マイグレーションファイルの追加・削除はない。
