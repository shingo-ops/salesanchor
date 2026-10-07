# recon：実行済み記録（ledger）付きのランナー（ADR-1005 段階2）

この文書は何か（1行）: デプロイで「まだ実行していない migration だけを 1 回実行する」仕組み（ledger）を足す変更について、現状と実装と試験結果を、行番号つきの事実だけで記録したもの。

親: ADR-1005（docs/adr/ADR-1005-migration-run-once-ledger.md。Accepted（方向性）2026-10-06）、ADR-1007（PR #3985）。設計: docs/handoff/migration-ledger/design.md
実測時の origin/main: 768c69d71（2026-10-07）。以下の「変更前」の行番号はこの SHA のもの。
既存 ADR の検索: 機能キーワード（migration、ledger、run-once、チェックサム）で docs/adr/ と docs/adr/FEATURE-INDEX.md を引いた結果、直接の ADR は ADR-1005（段階2の定義）と ADR-1007（段3の後に入る順序）、関連は ADR-045、ADR-082、ADR-1002（全件やり直しを選んだ理由と、記録が無いという既出の記録）。

## 1. 変更前の事実（origin/main 768c69d71）

- scripts/run_all_migrations.sh:20 `set -e`。:44 `STEP=0`、:47 `TOTAL=…`、:49-59 `run_py()`（docker exec で Python を実行）、:61-66 `run_sql()`（docker exec で psql にファイルを渡す）。どちらも実行済みかを見ずに毎回実行する。:68-76 登録先ファイルの存在確認。
- .github/workflows/deploy.yml:500-514 `Run database migrations`（`bash scripts/run_all_migrations.sh`）。:371-376 の blue-green 切替が先、migration が後。
- 登録は run_sql 292 行・run_py 26 行＝318 行（重複 1 件: :530 と :536）。ledger の作成 migration を足して 319 行。
- 実行済みの記録は無い（docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md:23）。
- public に作った表には salesanchor_app への SELECT/INSERT/UPDATE/DELETE が自動で付く: migrations/20260605_030000_create_salesanchor_app_role.sql:21-22（ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public GRANT … TO salesanchor_app）。
- 毎回実行の候補を実物で確認した結果:
  - migrations/014_create_current_tenant_id_function.sql: public の関数 1 つの定義（CREATE OR REPLACE FUNCTION）。1 回で足りる。
  - migrations/20260604_130000_create_supplier_parse_stats_view.sql: public のビュー 1 つの定義。1 回で足りる。
  - migrations/20260605_030000_create_salesanchor_app_role.sql:21-24: ALTER DEFAULT PRIVILEGES が、あとから作る表にも付ける。
  - migrations/20260605_040000_grant_salesanchor_app_tenant_schemas.sql:22-25 と backend/app/services/tenant.py:1676-1687: 新しいテナントの作成が同じ権限付与（GRANT USAGE、ALL TABLES、ALL SEQUENCES、ALTER DEFAULT PRIVILEGES）を持つ。
  - migrations/20260604_100000_create_company_stats_view.sql、20260611_130000_fix_v_company_stats_deleted_at.sql、20260612_120000_fix_company_stats_ssot.sql: テナントごとのビュー（tenant のループ）。backend/app/services/tenant.py に v_company_stats は 0 件（grep）。新テナントには、ひな形に取り込むまで届かない（段階1）。
  - run_py の Python 26 本: 実物は未確認（値を書く 4 本は静的な文字列の数で UPDATE／INSERT を含む）。
  - ADR-1005 の recon の「毎回実行に意味がある 22 件」の一覧: 手元に無く、未確認。
- 実行順の前提: 段3 の PR（#3978、#4018、#4017）の無効化が本番に出る前に baseline を取ると、無効化の書き換えがすべてチェックサム不一致になる（段5カード step5_card.md §3-5）。

## 2. 実施した変更（ブランチ release/migration-ledger、base は origin/main）

- 新規 migrations/20261007_100000_create_migration_ledger.sql: 専用スキーマ ops と表 ops.migration_ledger（id、scope、kind、filename、checksum、status（applied／baseline）、applied_at、duration_ms、git_sha、UNIQUE (scope, filename)）。PUBLIC と salesanchor_app への権限を明示で取り消す。構造だけ（値は入れない）。
- 新規 scripts/lib/migration_ledger.sh: run_sql／run_py（記録を見て、無ければ実行し、成功したら記録）、チェックサム（sha256、改行は LF に正規化）、実行前の不一致検査（何も実行せず失敗）、全件やり直しモード、毎回実行リストの読み取り、ledger の表が無いとき作成の migration を先に実行。
- scripts/run_all_migrations.sh: `--full`（または MIGRATION_FULL_RERUN=1）の解釈、ライブラリの source、run_sql／run_py の定義の削除（ライブラリへ移動）、ledger_init の呼び出し、ledger の作成 migration の登録（末尾）。
- 新規 scripts/migration-ledger/every-run.list: 毎回実行リスト（1 ファイル）。現在は 0 件（§1 の確認で、毎回実行に意味があると確かめられたものが 0 件だったため）。確認したものと未確認のものを、コメントに残した。
- 新規 scripts/migration-ledger/record-baseline.sh: 登録された全ファイルを status=baseline で記録だけ入れる 1 回限りのスクリプト（既定は dry-run。--commit には --expect-sha が必要。段3 の無効化の印が無いと拒否）。実行は一切しない。
- 新規 scripts/migration-ledger/step3-neutralized.list: baseline の前提（段3 で無効化した 26 本。#3978 の 1 本、#4018 の 18 本、#4017 の 7 本）。
- 新規 scripts/check-migration-immutability.sh: base に既にある登録済みファイルが head で変わっていたら失敗（毎回実行リストは除く）。
- 新規 .github/workflows/migration-ledger-check.yml: 試験と書き換え検査（必須チェックではない）。
- 新規 scripts/tests/test-migration-ledger.sh: 試験 T1〜T12。
- deploy.yml は変更していない（`bash scripts/run_all_migrations.sh` の呼び出しはそのまま）。本番には何も実行していない。

## 3. 試験（TDD）

- 先に試験を書き、実装前に実行した（RED）: 「結果: 0 件 PASS / 6 件 FAIL」（ライブラリ・スクリプト・リスト・ledger の作成 migration のどれも存在しない）。
- 実装後（bash 3.2、macOS）: 「結果: 58 件 PASS / 0 件 FAIL」。内訳:
  - T1 未記録は実行して記録／T2 記録済みは飛ばす／T3 チェックサム不一致は何も実行せず失敗／T4 全件やり直しは全件実行して記録を更新／T5 途中の失敗は記録せず以降を実行しない／T6 毎回実行リストは毎回実行／T7 表が無ければ作成の migration を先に実行
  - T8 baseline は dry-run が既定で何も記録・実行しない／T9 無効化の印が無いと baseline を拒否／T10 baseline --commit は全件を status=baseline で記録し、実行しない（その後の通常実行は 0 件）
  - T11 書き換えの検出（登録済みの書き換えは失敗、毎回実行リストは許可、新規追加は成功）
  - T12 本物の scripts/run_all_migrations.sh を偽の docker で通しで実行: 1 回目は登録行数＋ledger 作成 1 件を実行し、登録ファイル数（重複を除く）と同じ件数を記録／2 回目は 0 件実行（skip）／--full は登録行数の全件を実行
- 実リポジトリでの確認: `BASE_SHA=origin/main HEAD_SHA=HEAD bash scripts/check-migration-immutability.sh` → 「OK: 登録済みで base に既にある 317 件のファイルは、書き換えられていません。」（exit 0）。`bash scripts/migration-ledger/record-baseline.sh --dry-run` → 「DRY-RUN: 記録する件数 318（run_sql 292、run_py 26）。」。段3 の印が無いファイルとして、#3978・#4018・#4017 の 26 本が出た（これらが main に入っていないため）。
- bash -n（scripts/run_all_migrations.sh、scripts/lib/migration_ledger.sh）: 構文エラーなし。ローカルの PG と docker は使っていない。

## 4. 未確認
- CI での結果（migration-ledger-check.yml、Migration SQL Test による ledger の作成 migration の実行、全件ドライラン）。
- 本番での動作（ops スキーマの作成、権限、1 回目のデプロイの挙動）。デプロイの前に、baseline の手順（design.md）を使うか、1 回目の実行で記録するかの判断が要る。
- Ubuntu の bash 5 での実行（ローカルは bash 3.2。CI で確認）。
- 1 手順 1 トランザクションで包めるか（自分で BEGIN・COMMIT を書く既存の手順が 13 件ある。ADR-1005 の design）。この変更は包んでいない（実行と記録は別の文）。
- 毎回実行リストの 0 件が正しいか（ADR-1005 の C 22 件の一覧が手元に無い。run_py の 26 本は未確認）。
- 段階1（テナントの正本を 1 つに）が未実施のため、ledger を有効にすると、新テナントにテナント向けの変更が届かない（段階1の前に有効にしてはいけない）。
