# design: 全件ドライラン step の引数修正

recon: docs/handoff/ci-dryrun-psql-args/recon.md
対象ADR: ADR-1007（docs/adr/ADR-1007-migration-structure-only-run-once.md、決定5）

## KGI
- K1: 修正後の PR 上の CI で、当 step のログに「周目」行が出て、登録 run_sql の本数分（対象 287 ファイル、run_all_migrations.sh の登録に対応）を流したことが分かる
- K2: 当 step は従来どおり報告のみ（continue-on-error・job の合否は変えない）

## 変更
- .github/workflows/migration-test.yml の当 step: `--psql psql -h localhost -U jarvis` を `--psql psql` にし、step の env に PGHOST=localhost・PGUSER=jarvis を追加。
- 触らない: workflow-lint.yml、他の job、scripts/migration-dryrun-report.py（argparse は変えない）。

## 検証基準
|基準|検証方法|
|---|---|
|usage が出ない|PR の CI の当 step ログに「全件ドライラン（報告のみ）」行と「[1周目 1/287]」形式の行がある|
|job の合否が変わらない|continue-on-error: true が残っている（diff で確認）|
|手元確認|scripts/migration-dryrun-report.py に PGHOST/PGUSER env＋`--psql psql` を渡して usage にならない（verify 出力）|

## 影響範囲
呼び出し箇所は当 step 1つ（grep 済み）。

## 戻し方
当コミットを revert。

## 外部・過去事例の参照と我々への応用
argparse の nargs="+" は後続の `-x` 形式の引数を別オプションとして解釈する標準動作。接続先を libpq の環境変数（PGHOST・PGUSER）で渡すのが psql の標準的な方法。

## 維持の仕組み
- 守り手: 当 step のログに「周目」行が出ること。以後 PR の CI で目視できる。
