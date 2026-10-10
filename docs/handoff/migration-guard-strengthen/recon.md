# recon: migration-guard を強くする（値の書き込みを、変更されたファイルと全件でも止める。2026-10-07）

基準: origin/main 768c69d71。値（件数・表名・行番号）だけを記載する。元の調査は「社外秘のローカル作業メモ（リポジトリ外）」にある。

## 0. 既存 ADR の検索（STANDARD-WORKFLOW）
- 検索語: migration-guard / ADR-155 / ADR-1007 / neutralize。対象 ADR: ADR-155（docs/adr/ADR-155-product-master-ssot-csv-app.md:26「マイグレーションは構造変更のみ。値の操作は禁止」）。ADR-1007（段階の計画）は別ブランチで起案中で、この PR の時点では main に無い。

## 1. 事実：今のチェック 7・8 の穴
1. 対象ファイルの取り方: .github/workflows/migration-guard.yml:81 `git diff "$BASE" "$HEAD" --name-only --diff-filter=A` — 追加（A）されたファイルだけ。変更（M）されたファイルは、チェック 7（:408 の gate は new_sql）にもチェック 8（:496）にも入らない。つまり、既存の migration に値の書き込みを足す変更は止まらない。
2. チェック 7 は、ファイルごとに「追加された行だけ」を見る（:421-426）ので、変更ファイルを渡せばそのまま使える。チェック 8 は、ファイル全体を見る（:509-511）ので、変更ファイルにそのまま使うと、既存の行まで違反にする。
3. 正規表現の穴: チェック 7 の INSERT / UPDATE / DELETE の正規表現（:432-440）は、スキーマの前置きを `(public\.|tenant_[0-9]+\.)?` に限る。テナントのループが動的に書く `EXECUTE format('INSERT INTO %I.tcg_products ...')` は見逃す。登録された全ファイルに当てた結果（手元の走査）: 今の正規表現で 23 ファイル、`%I.` を許すと 34 ファイル（差の 11 本は tenant_004 向けの鎖など）。
4. 保護対象の表の一覧が、コメントと実際で食い違う: コメントと出力は「14」（:400、:473、:574）。コードは 23 表（:416、:503）。履歴（git log -S）: e364dd233（2026-09-18）で 4 → 14、57dd67c55（2026-09-19）で 21、48731a698（2026-09-21）で 23。実際に効くのはコードの 23。ADR-155 の本文は 4 表（:27-31）のまま。product_lines / product_formats / product_kinds / supplier_aliases は一覧に無い（ADR-1007 決定1 は全マスタ表が対象）。
5. 全件を見る仕組みが無い: 登録された migration（scripts/run_all_migrations.sh の run_sql。2026-10-07 時点で 292 行、291 本）に、保護対象の表への値の書き込みが残っているかを、一覧で確かめる検査が無い。

## 2. 事実：全件ドライランの範囲
- .github/workflows/migration-test.yml の 1周目・2周目の step は、同じ絞り込み `grep -E '^migrations/0|^migrations/2026060[4-9]|^migrations/2026061|^migrations/2026062'` で流す（既存コメントの理由は、初期のタイムスタンプ 20260601-20260603 が Python migration に依存するため）。日付の範囲は 2026-06-12 以降、広げられていない。登録 292 行のうち、絞り込みで流れるのは 128、流れないのは 164（163 本）。
- 空の DB で落ちると見込まれる 19 本（静的な参照の解析による見込み。未実行）は、public.products / public.suppliers / public.knowledge_rules を、作成元（056・058・062）が登録されていないために参照できない。
- job の条件: migration-test.yml:1031-1034（migration-full-dryrun。migration を変える PR でだけ動く）。

## 3. 事実：workflow を変える制約
- CLAUDE.md:38 の PO 確認が要る操作には、.github/workflows/workflow-lint.yml の変更と、gh api による Branch Protection・Ruleset・Required Status Check の変更が入っている。migration-guard.yml と migration-test.yml は入っていない。この PR は workflow-lint.yml に触れない。
- workflow-lint.yml が、この 2 本に課す規則: migration-guard.yml は pull_request に paths: を付けない（.github/workflows/workflow-lint.yml:53）。migration-test.yml は detect-changes と、if: always() の集約 job を持つ（:88）。どちらも保つ。job の名前は変えない（必須チェックの名前と一致させる）。

## 4. 変更（この PR）
- scripts/migration-guard/protected-tables.txt: 保護対象の唯一の正本（27 表: 今の 23 + 上の 4）。チェック 7・8 と全件走査がこの一覧だけを読む。「14」の文言はコードから外し、数は一覧から出す。
- scripts/check-migration-value-writes.py: diff モード（チェック 7・8。新規は全体、変更ファイルは追加された行だけ。neutralize の編集は通る。字下げだけの変更は数えない）と repo モード（全件走査）。正規表現は、チェック 7 と同じ形に `%I.` と語境界を足した（products が products_category_classification_backup に当たらない。role_permissions が permissions に当たらない）。
- scripts/migration-guard/value-write-allowlist.tsv: 全件走査の許可一覧。初期は 33 行（2026-10-07 時点の走査結果）。理由を読んで確かめられなかったものは「未確認（段3 以降で精査）」と書いた。33 は、チェック 7 の今の正規表現で見つけた 34 から、products_category_classification_backup への INSERT（保護対象の表ではない）を語境界で外した数。
- scripts/migration-guard/dryrun-exclusions.tsv と scripts/migration-dryrun-report.py: 全件ドライランの対象 = 登録された全ファイル − 除外（32 行 = 空の DB で落ちると見込まれる 19 本 + 初期タイムスタンプの 13 本）。この PR は報告のみ（強制しない）。migration-test.yml の既存の 1周目・2周目は変えない。
- .github/workflows/migration-guard.yml: チェック 7・8 の本体を検査スクリプトの呼び出しに置き換え、全件走査の step を足す。
- .github/workflows/migration-test.yml: 報告用の DB（jarvis_report。1周目の直前の状態のコピー）を作る step と、報告のみの step（continue-on-error）を足す。変更の検出の範囲に scripts/migration-guard/** と報告の script を足す。

## 5. 事実：試験
- scripts/tests/test_migration_value_writes.py（22 本、標準ライブラリだけ。一時の git リポジトリで、BASE / HEAD の差分に流す）。実行: python3 -m unittest scripts/tests/test_migration_value_writes.py -v。
- 実物の PR への当て方（手元）: neutralize の PR #4017（8 ファイル）、#3978（1 ファイル）、#3986（1 ファイル）の差分に diff モードを流し、チェック 7・8 とも通ることを確認した。

## 6. 未確認・実施していないこと
- 全件ドライラン（報告のみ）を CI で流した結果: この PR の CI の報告が最初の実行。除外した 19 本以外のファイルが 1周目・2周目で通るかは未確認。
- 手元で SQL を流しての確認はしていない（書き込みを防ぐフックが手元の DB 実行も止める）。
- 動的なテーブル名（文字列の連結）や、2 行にまたがる文は、行単位の正規表現では見つけられない。何本あるかは未確認。
- 許可一覧の各行の理由のうち「未確認」としたものは、段3 以降で一つずつ読む。
- 段3 の PR（#4017・#3978・PR-3a）が先に main に入ると、この PR の許可一覧に、もう値の書き込みを持たないファイルの行が残る（全件走査が古い行として失敗する）。後から入る側が、自分のファイルの行を消す。
