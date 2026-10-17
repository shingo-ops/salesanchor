# recon: 全件ドライラン step が -h を help と読んで1本も流れていない

基準: origin/main（15114e878）

## 事実
1. .github/workflows/migration-test.yml:1816（修正前）`python3 scripts/migration-dryrun-report.py run --db jarvis_report --rounds 2 --psql psql -h localhost -U jarvis`。step は :1809、continue-on-error は :1814、job は :1097 migration-full-dryrun。
2. scripts/migration-dryrun-report.py:99 `run.add_argument("--psql", nargs="+", ...)`、:96 サブコマンド run。run 側に既定の -h/--help があり、`-h` が help として解釈され usage を出して終了コード 0。
3. scripts/migration-dryrun-report.py:57 は `[*psql, "-d", db, ...]` で呼ぶため、`--psql psql` のみでも接続先は psql の環境変数（PGHOST・PGUSER）で解決される。PGPASSWORD は job の env（migration-test.yml:1121）にある。
4. 実 CI ログ: run 38967704526・38913019161 の当 step 出力は usage のみ、「周目」行 0 件（詳細: 同 side4 の recon.md、リポジトリ外）。
5. 手元実測（修正前の引数）: usage を表示して rc=0。修正後の引数（PGHOST/PGUSER を env、`--psql psql`）: 「全件ドライラン（報告のみ）: 登録 319 ファイル − 除外 32 = 対象 287 ファイル」と「[1周目 1/287]」行が出る（接続先はわざと不達にしたため各行は失敗表示）。
6. 既存 job env に PGHOST/PGUSER は無い（migration-test.yml の PGPASSWORD は :112 と :1121 のみ）。重複なし。

## 未確認
- PR 上の CI で「周目」行が実際に出ること（K1）。PR の CI で確認する。
