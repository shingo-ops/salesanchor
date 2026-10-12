# design: fix-migration-runner-0922

## 参照ADR

- ADR-082: run_all_migrations.sh を migrations の SSoT とする

## 問題

Migration Guard CIが 20260922_040000_fix_phase2c_fk_blocker.sql が未登録でfailure。
070000 が2重登録。

## 修正方針

scripts/run_all_migrations.sh の行661（070000の重複エントリ）を 040000 の登録に変更する。

### 選択理由

- 040000 は冪等（BEGIN/COMMIT + IF EXISTS / IF NOT EXISTS ガード付き）
- 実行順序は問題なし（050000 が後続で同じ操作をDROP-onlyで行うため安全）
- ファイルを削除する選択肢は Migration Guard が「ファイルが存在するなら登録必須」という要件を持つため不可

## 変更内容

scripts/run_all_migrations.sh:661 の変更。

070000 の重複エントリを 040000 の登録に変更した（2行の差分のみ）。

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| Migration Guard CIがpassになること | gh pr checks でMigration Guard が pass になること |
| 040000 が登録済みになること | grep 040000 scripts/run_all_migrations.sh で1件ヒット |
| 070000 が重複しないこと | grep -c 070000 scripts/run_all_migrations.sh の結果が1であること |

## 影響範囲

- 触るファイル: scripts/run_all_migrations.sh のみ
- 本番への影響: 040000 は冪等のため重複実行しても安全

## 外部・過去事例の参照と我々への応用

Migration Guard（.github/workflows/ 内）は migrations/ 配下の全 .sql ファイルを列挙し、scripts/run_all_migrations.sh または .github/workflows/deploy.yml への登録を要求する。登録漏れがあると CI が即座に fail する。

本件と同様の「ファイルが存在するが登録されていない」パターンはこれまでも複数回発生しており（#3669 相当）、対策は一貫して「登録追加」で対応している。

## 維持の仕組み

- Migration Guard が main へのマージ後に自動チェックするため、次回以降の漏れも CI で即検出できる
- ADR-082 の SSoT ルール（run_all_migrations.sh に追記する）を継続する

## 守り手

このPRは `scripts/run_all_migrations.sh` のみを変更する。マイグレーションファイルの追加・削除はない。
