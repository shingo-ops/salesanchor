# Design: tenant_004 UUID→INTEGER 変換の tcg_uuid 依存を除去（第4便）

**対象**: デプロイ失敗 2026-10-04（run 37136832562、`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql` ステップ245/317、`column p.tcg_uuid does not exist`）
**recon**: docs/handoff/products-column-churn-4/recon.md
**関連PR**: #3958（第1便）・#3959（第2便）・#3960（第3便）
**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装)

---

## 外部・過去事例の参照と我々への応用

該当なし（理由: 本件は自社migration群内で「他テナントは変換済み」という未検証の前提が
実際には成立していなかったことに起因する不具合であり、参照すべき外部のベストプラクティス
文書は無い。PostgreSQLの列数上限に関する外部事例は第1便 design.md で引用済みのため
再掲しない）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `scripts/run_all_migrations.sh` の構文が壊れていない | `bash -n scripts/run_all_migrations.sh` → exit 0 |
| tenant_004 の4テーブル（0行確認済み）で tcg_uuid 依存の UPDATE が無条件実行されない | recon.md §0 の生クエリ出力（4テーブル全て0行）+ design.md の diff |
| 0行テーブルは join 無しで構造変換が完了する（データロス無し、0行のまま） | design.md「修正後の再ウォーク」 |
| 1行以上のテーブルがあれば人間判断のため EXCEPTION で停止する（サイレント破損を防ぐ） | 追加した `RAISE EXCEPTION` 文言（design.md「変更内容」） |
| 671以降の全ステートメントが本番状態（tcg_uuid無し・condition/unit/category_classification無し・tenant_004の4テーブルがUUID・public.productsに新規列を割り当てられない）で失敗しない | design.md「ステップ4: 671以降の全件ウォーク」 |
| フレッシュDB 1周目: 既存の実データ移行ロジックが壊れない | design.md「フレッシュDB 1周目/2周目シミュレーション」 |
| フレッシュDB 2周目: 冪等 | 同上 |

---

## 設計方針

recon.md §1 のライフサイクル表が示す通り、`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`
の5つのテーブル変換ブロック（product_search_keywords・product_exclude_keywords・
products_logistics・analysis_results・analysis_run_snapshots）は全て同一パターンで
`UPDATE ... FROM public.products p WHERE p.tcg_uuid = ...` を使って UUID→INTEGER の
対応付けを行う。本番ではこの5つのうち4つ（products_logisticsを除く）が UUID のまま、
かつ全て0行であることを確認済み（recon.md §0、Sonnet 自身が read-only で再確認）。

### 選んだ修正: tcg_uuid 存在チェック→0行なら join無しで構造変換・1行以上なら EXCEPTION

coordinator 指定の「preferred」パターンをそのまま採用（複雑な代替案は不要と判断）:

```sql
-- ループの外（schema非依存）で一度だけ判定
SELECT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='products' AND column_name='tcg_uuid'
) INTO _tcg_uuid_exists;

...
-- 各テーブルのUPDATE部分のみ分岐（Step1/3以降の構造変換ステップは無変更）
IF _tcg_uuid_exists THEN
    EXECUTE format('UPDATE %I.<table> ... WHERE p.tcg_uuid = ...', _schema);  -- 既存ロジックそのまま
ELSE
    EXECUTE format('SELECT count(*) FROM %I.<table>', _schema) INTO _row_count;
    IF _row_count > 0 THEN
        RAISE EXCEPTION 'Phase B: tcg_uuid is absent but %.<table> has % row(s) — cannot map product_id without tcg_uuid; needs a human decision', _schema, _row_count;
    ELSE
        RAISE NOTICE '  tcg_uuid absent and %.<table> has 0 rows — skipping UUID join, nothing to map', _schema;
    END IF;
END IF;
```

0行の場合、Step2（UPDATE）をスキップしても `product_int_id` は全行（0行）で NULL のままで
問題ない。直後の Step3（孤立行チェック: `product_id IS NOT NULL AND product_int_id IS NULL`
の件数確認）は対象行が0件のため常に0を返し、安全に通過する。以降の DROP COLUMN / RENAME /
SET NOT NULL / ADD CONSTRAINT / CREATE INDEX は全て**行データに依存しない構造変更のみ**
であり、0行のテーブルに対して無条件に成功する。

この修正を **5つの変換ブロック全て**（product_search_keywords・product_exclude_keywords・
products_logistics・analysis_results・analysis_run_snapshots）に適用した。products_logistics
は本番では既に INTEGER（`IF _atttypid=_int_oid THEN skip` で素通りするためこの修正の対象
分岐には入らない）だが、将来他のテナントスキーマで同じ状況（UUIDのまま・tcg_uuid無し）が
発生した場合に備えて一貫して適用した。

### なぜ複雑な代替案を採らなかったか

「0行なら安全」という判定自体を疑う余地（例: 本当に0行か、同時実行中の書き込みが
無いか）はあるが、`scripts/run_all_migrations.sh` の全体がデプロイ時の単一シーケンシャル
実行であり、同時書き込みを想定していない（migration-guard の前提と同じ）。1行以上の
テーブルで EXCEPTION にする設計は、サイレントに一部の行の `product_id` を NULL にして
しまう（データ不整合を見逃す）リスクを避けるための安全策であり、coordinator の指示通り
これを最優先にした。

---

## ステップ3: 671以降の全ステートメントが安全に動くことの確認（file:line）

`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql` の Table1/2/4/5（修正対象）
について、修正後の結果（product_id が INTEGER・0行）を前提に、その後にこれらの列を読む
全ステートメントを確認した。

- `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:359-445`（同ファイル後半の
  product_code SEQUENCE 作成）: `product_search_keywords`等を参照しない。無関係。
- `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:23-222`（登録:707）:
  `analysis_results.unit_id`/`.condition_id` の変換で、`product_id`/`tcg_uuid` を一切参照
  しない（別列の独立した変換）。無関係・無変更。
- `migrations/20260919_020000_master_ssot_public_tables.sql:297-326`（登録:698）:
  `public.product_search_keywords`/`public.product_exclude_keywords` を**新規に空で CREATE**
  する DDL のみ。tenant_004側のデータへの参照（INSERT等）は無い（grep確認: `INSERT INTO
  public.product_search_keywords`/`public.product_exclude_keywords` は全migrationsに0件）。
  コメントに残る「708 rows」等の記述は過去の実データ件数の記録であり、実行文自体は
  件数に依存しないため無関係。
- `migrations/20260921_110000_pipeline_tables_public.sql:183-314`（登録:744）:
  `public.analysis_results`/`public.analysis_run_snapshots` を新規に空で CREATE する DDL
  のみ。同様にINSERT等の実データ参照は無い。無関係。
- `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql:17-18`（登録:747）:
  `DROP TABLE IF EXISTS tenant_004.analysis_run_snapshots`/`.analysis_results`。
  テーブルが INTEGER・0行になっていても、列の型やデータに関わらず `DROP TABLE` は無条件に
  成功する。問題なし。
- `migrations/20260921_130000_drop_tenant004_master_copies.sql:27-28`（登録:759）:
  `DROP TABLE IF EXISTS tenant_004.product_search_keywords`/`.product_exclude_keywords
  CASCADE`。同様に無条件成功。問題なし。
- その他、登録順で671より後の全ファイルを `analysis_results`/`analysis_run_snapshots`/
  `product_search_keywords`/`product_exclude_keywords` で再grepし、ヒットした全ファイルを
  上記で網羅したことを確認済み（recon.md §1 のライフサイクル表に対応するファイルが全て
  上記のいずれかに含まれる）。

**結論**: 修正後の結果（INTEGER・0行）に対して、671以降のどのステートメントも安全に動作する。

---

## ステップ4: 671以降の全件ウォーク（本番状態での失敗可能性の総点検）

coordinator 指定の4条件（(a) tcg_uuid absent, (b) condition/unit/category_classification
absent, (c) tenant_004の4テーブルの状態, (d) public.productsに新規列を割り当てられない）を
前提に、`scripts/run_all_migrations.sh` の line672（671の直後）から末尾（line880）までの
**全** run_sql/run_py を点検した。

- **(a) tcg_uuid**: 第3便recon.md §2 の全件スキャンで確定済みの通り、671より後に tcg_uuid
  を参照するのは line674（`migrations/20260916_120000_phase_c_drop_tcg_uuid.sql`、
  `DROP ... IF EXISTS` のみ、ガード済み）だけ。他には1件も無い（第3便の全件スキャンは
  スクリプト全体が対象だったため、671より後の範囲も包含済み。本便で新規 migration は
  追加していないため再スキャン結果は不変）。
- **(b) condition/unit/category_classification**: 同様に第3便recon.md §4 の全件スキャンで
  public.products への未ガード参照は0件と確定済み。671より後の範囲にも新規のヒットは無い。
- **(c) tenant_004の4テーブル**: 本書ステップ3で確認済みの通り、671より後にこれらのテーブルを
  参照するのは DDLのみ（CREATE/DROP、データ非依存）。
- **(d) public.productsへの新規列割り当て**: 第2便recon.md §2 の全件ウォーク（`scripts/
  run_all_migrations.sh` 全体を対象に、`public.products` に列を追加できる全ステートメントを
  洗い出した表）が既に確定済みで、671より後に該当するのは
  `migrations/20260920_130000_create_product_classification.sql`（:731、product_line_id/
  product_format_id追加）・`migrations/20260921_120000_add_products_product_kind_id.sql`
  （:750）・`migrations/20260921_140000_product_classification_masters.sql`（:762、
  quantity_unit_id/weight_class_id）・`migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql`
  （:768、type_master_id）の4件のみで、いずれも「その列名が既に存在するため ADD COLUMN
  IF NOT EXISTS がスキップされる」状態（本番で既に live、第2便recon.md確認済み）。
  新規 attnum は消費されない。

**結論**: 671より後、末尾までのどのステートメントも、本番の現状態（(a)〜(d)全て）で
失敗しない。

---

## フレッシュDB 1周目/2周目シミュレーション（`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`）

### 1周目
`_tcg_uuid_exists` 判定時点（ループ開始前）: `public.products.tcg_uuid` は line628
（`migrations/20260909_000000`）で既に ADD 済み（フレッシュDBの1周目では
`work_id` 列がまだ存在しないため第2便のガードが「まだ必要」と判定して ADD する）→
`_tcg_uuid_exists = TRUE`。よって Table1/2/3/4/5 の全てで元の `IF _tcg_uuid_exists THEN`
分岐（既存ロジックそのまま）が実行される。実データが入っている場合も `tcg_uuid` 経由で
正しく対応付けられる（regressionなし）。

### 2周目（1周目適用済みDBへの再実行）
1周目の末尾で `tcg_uuid` は line674（phase_c drop）で DROP 済み。2周目のループ開始前の
`_tcg_uuid_exists` 判定は FALSE。しかし Table1〜5 は1周目で既に INTEGER に変換済みのため、
各テーブルの外側の `IF _atttypid = _int_oid THEN skip` （または Table5 の
`a.atttypid != _int_oid` 条件）で ELSE 分岐（変換ロジック本体）には入らない。つまり
2周目では新ガードの `IF _tcg_uuid_exists ELSE ...` 自体に到達しないため、この修正は
2周目の挙動に影響しない（元から安全だった部分）。

---

## 変更内容

1. `migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`:
   - DECLARE に `_tcg_uuid_exists BOOLEAN`・`_row_count BIGINT` を追加
   - ループ開始前に `_tcg_uuid_exists` を一度だけ計算
   - Table1（product_search_keywords）・Table2（product_exclude_keywords）・
     Table3（products_logistics）・Table4（analysis_results）・Table5
     （analysis_run_snapshots）の各 Step2（`UPDATE ... WHERE p.tcg_uuid = ...`）を
     `IF _tcg_uuid_exists THEN (元のUPDATE) ELSE (0行なら NOTICE・1行以上なら EXCEPTION) END IF`
     で保護

**触らない**: Step1（ADD COLUMN）・Step3（孤立行チェック）・Step4以降（FK/RENAME/インデックス）
は全ブロックで無変更。`migrations/20260916_120000_phase_c_drop_tcg_uuid.sql`・
`migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql`・
`migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`・
`migrations/20260921_130000_drop_tenant004_master_copies.sql` は無変更（ステップ3で安全性
確認済み）。

---

## CI カバレッジ

第1便〜第3便と同じ既知のギャップ。本PRが変更する1ファイル（`20260915_120000`、9月付け）は
`migration-full-dryrun` ジョブの対象ファイル正規表現（6月4日〜29日限定）に一致せず対象外。
`migration-test-run` ジョブ（変更SQLを2回実行）には対象として乗る。

---

## 変更範囲

| 層 | 変更 |
|---|---|
| migrations（ガード追加） | `20260915_120000` の5テーブル分の Step2 を tcg_uuid 存在チェック + 行数チェックでガード |
| migrations（無変更） | `20260916_120000`・`20260920_010000`・`20260921_050000`・`20260921_130000`・`20260919_020000`・`20260921_110000` — ステップ3で安全性確認済み |
| docs | docs/handoff/products-column-churn-4/recon.md（新規）・docs/handoff/products-column-churn-4/design.md（新規） |
| 台帳 | .claude-pipeline/active-work.d/release-stop-products-column-churn-4.md（main checkout に新規作成、このブランチには含めない） |

## 触るファイル

1. migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql
2. docs/handoff/products-column-churn-4/recon.md（新規）
3. docs/handoff/products-column-churn-4/design.md（新規・本ファイル）

削除するファイル: 無し（行削除も無し。既存ステートメントを `IF`/`ELSE` で包んだのみ）。

---

## 維持の仕組み

守り手: 以下はアイデア提案のみで未実装（本PRのスコープ外）
- 第1便〜第3便から継続: ADD/DROP対応表のCI検知案・動的列参照（EXECUTE format経由）の
  追跡案・`migration-full-dryrun` の対象範囲拡張案。
- 今回新たに判明した教訓: 「全テナントで既に変換済み」という前提は、少なくとも1テナントを
  本番 read-only で確認するまで事実として扱わない（本書§0でSonnet自身が再確認した方法を
  レビュー手順として明文化する案）。具体的には、複数テナントスキーマを横断する migration
  を変更する際は、該当する **全テナントスキーマ名**を列挙し、各スキーマで実際にどの状態
  （変換済み/未変換、行数）にあるかを本番 read-only で確認してからガード設計をする、という
  チェックリスト項目を `docs/specs/branch-operations/README.md` 等に追記する案（未実装・提案）。
