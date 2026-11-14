# card: 便V 追補1（CI の赤2件を直す。invoice-create-portfolio）

- 発行: Claude Opus（2026-11-15）。元の指示書は card-V.md（PR #5512 で main 入り）。実装は PR #5515（ブランチ release/invoice-create-portfolio-bin-v-impl）
- 承認: 2026-11-14 の PO の選択「1,」（設計第9版）と 2026-11-13 の指示「…確立したなら進める。…PRマージ、デプロイまで完走させてくれ。」の範囲。設計（design.md §3-8）の決まりは変えない。直すのは card-V.md が決めた書き方2か所だけ

## Opus の決めごと（根拠つき）

- F1 移行で振込先の表が無いスキーマを見つけたら、止めずに飛ばす。
  - 根拠: CI「マイグレーションSQL 実行（内部）」が `psql:migrations/20261115_100000_add_payment_method_versioning.sql:149: ERROR:  tenant_invoice_payment_methods is missing in tenant_001` で失敗した。CI の試験用 DB の tenant_001 は最小の表しか持たない（.github/workflows/migration-test.yml:253-）。
  - 一つ前の便A の移行 migrations/20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql:101 は、表が無ければ飛ばす形（`IF to_regclass(...) IS NOT NULL THEN`）で通っている。design.md §3-8 は止める形を求めていない（止める形は card-V.md で足したもの）。
  - 本番では scripts/run_all_migrations.sh:1267 で表を作る移行 20261112_160000 が先に流れるので、全テナントに表がある。飛ばされた会社が無いことは、反映後に読み取り用の鍵で全テナントの見張り6つ・列2つ・関数3つを数えて確かめる（Opus が行う）。
  - 案 (b) の migration-test.yml に前提の移行の段を足す形は取らない。.github/workflows は card-V.md で「触らない」とした範囲で、範囲を広げるほどの利点が無い。
- F2 新しい試験の文字 `"CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_methods ("` を2つの文字のつなぎに分ける。
  - 根拠: CI「test-schema-dup gate」が `テストに本番テーブル定義の新規コピーが増えています: backend/tests/test_tenant_payment_versioning_pg.py (0 -> 1)` で失敗した。scripts/check_test_schema_dup.py:28 の `CREATE\s+TABLE` は文字の1つずつ（ast.Constant）に当てるので、分けると当たらない。既存の試験 backend/tests/test_tenant_issuer_tables_pg.py:51 も同じ分け方で通っている。
- F3 ほかは変えない。tenant.py・関数の中身（D7 の一字一句同じの試験）・見張り6つ・ほかの試験は触らない。

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

card-V.md §0-2 の表の全行をそのまま守る（読み直してから始める）。

## 受領確認（最初の報告の 1 行目に書く）

`受領確認: card-V-fix1.md（F1・F2 の2か所・2ファイル）を END OF CARD まで読んだ`

## 0-3. 実装前点検（外れたら直さず BLOCKED: で停止）

- P1 `git log --oneline -1` の先頭が、この追補を入れた commit であること（Opus が push した HEAD）
- P2 `grep -n -F -e "RAISE EXCEPTION 'tenant_invoice_payment_methods is missing in %', r.nspname;" migrations/20261115_100000_add_payment_method_versioning.sql` が 113 行目の1件だけ
- P3 `grep -n -F -e 'marker = "CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_methods ("' backend/tests/test_tenant_payment_versioning_pg.py` が 74 行目の1件だけ

## 1. 触るファイル

- migrations/20261115_100000_add_payment_method_versioning.sql（1か所）
- backend/tests/test_tenant_payment_versioning_pg.py（1か所）

これ以外のファイルは触らない。

## 2. 変更

### 2-1. migrations/20261115_100000_add_payment_method_versioning.sql（:112-114）

変更前:
```
        IF to_regclass(format('%I.tenant_invoice_payment_methods', r.nspname)) IS NULL THEN
            RAISE EXCEPTION 'tenant_invoice_payment_methods is missing in %', r.nspname;
        END IF;
```

変更後:
```
        -- 振込先の表が無いスキーマは飛ばす（便A と同じ形。本番は 20261112_160000 が先に流れて全テナントにある）
        IF to_regclass(format('%I.tenant_invoice_payment_methods', r.nspname)) IS NULL THEN
            CONTINUE;
        END IF;
```

### 2-2. backend/tests/test_tenant_payment_versioning_pg.py（:74）

変更前:
```
    marker = "CREATE TABLE IF NOT EXISTS {schema}.tenant_invoice_payment_methods ("
```

変更後:
```
    marker = "CREATE TABLE IF NOT EXISTS " + "{schema}.tenant_invoice_payment_methods ("
```

## 3. 手順

1. 作業場所で `git fetch origin release/invoice-create-portfolio-bin-v-impl` のあと、そのブランチを取り出して P1〜P3 を流す。外れたら停止
2. §2-1・§2-2 を Edit ツールで直す（変更前の文字をそのまま探して置き換える）
3. `git diff --stat` が上の2ファイル・足す行と消す行が 2-1 で +2/-1、2-2 で +1/-1 であることを確かめる
4. `cd backend && ruff check tests/test_tenant_payment_versioning_pg.py` が通ること
5. `python3 scripts/check_test_schema_dup.py` が使える形なら流し、新しい試験のファイルが数に出ないことを確かめる（使い方は台本の冒頭の説明に従う。流せないときはその旨と生の出力を書く）
6. `cd backend && python -m pytest tests/test_tenant_payment_versioning_pg.py tests/test_tenant_loop_migration_guard.py -q` が failed 0 であること（実 DB の試験は skipped でよい）
7. commit（`fix(tenant): skip schemas without payment tables and split test marker (invoice-create-portfolio bin V fix1)`。最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）
8. `git -C "$(pwd)" push origin release/invoice-create-portfolio-bin-v-impl` を作業場所の中で単独の命令で流す（`$(pwd)` は作業場所の絶対パスに書き換えてよい）

## 4. 想定される分かれ道

- P1 の HEAD が違う: 停止して BLOCKED: で HEAD を書く
- P2・P3 の行番号がずれている・件数が1でない: 停止
- 手順5の台本が引数や git の比べ元を要求して流せない: 流さずに理由を書いて先へ進む（CI が確かめる）
- push が見張りで止められた: 言い換えずに停止して生の出力を書く

## 5. 報告の形

1行目に受領確認。続けて P1〜P3 の生の出力・`git diff` の全文・手順4〜6の結果の要点・commit の番号・push の出力の最後の行。最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか。

END OF CARD
