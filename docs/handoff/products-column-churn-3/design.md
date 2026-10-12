# Design: tcg_uuid 未ガード参照の修正（第3便）

**対象**: デプロイ失敗 2026-10-04（run 37135632445、`migrations/20260913_200000_tcg_cardset_exclusion.sql` ステップ238/317、`column p.tcg_uuid does not exist`）
**recon**: docs/handoff/products-column-churn-3/recon.md
**関連PR**: #3958（第1便: condition/unit/category_classification）・#3959（第2便: tcg_uuid ADD churn のガード）
**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装)

---

## 外部・過去事例の参照と我々への応用

該当なし（理由: 本件は外部仕様・ライブラリの問題ではなく、自社migration群の中で「後から列が
DROPされる」という事実を考慮し忘れた参照箇所を機械的に洗い出す作業であり、参照すべき外部の
ベストプラクティス文書は無い。PostgreSQL の列数上限に関する外部事例は第1便 design.md で
既に引用済みであり、本件（存在しない列への参照エラー）はその応用ではなく別種の不具合のため
再掲しない）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `scripts/run_all_migrations.sh` の構文が壊れていない | `bash -n scripts/run_all_migrations.sh` → exit 0 |
| `tcg_uuid` への未ガード参照が無い（全件スキャンで確認） | recon.md §2 の生スキャン出力 + 判定表（8箇所、全て GUARDED） |
| `products.condition`/`.unit`/`.category_classification` への未ガード参照も無い | recon.md §4 の生スキャン出力 + 判定表（全57ヒット、products列参照は既存ガード済みのみ） |
| 次回デプロイで「Run database migrations」が成功する | 本番デプロイ後の GitHub Actions run 結果を確認（本PRのスコープ外・次回デプロイで確認） |
| フレッシュDB 1周目: 移行データが正しく入る（既存挙動を壊さない） | CI `migration-test-run` ジョブの「変更 SQL 1回目実行」 |
| フレッシュDB 2周目: 再実行してもエラーなし | 同ジョブの「変更 SQL 2回目実行（冪等性テスト）」 |

---

## 設計方針

recon.md §2 の全件スキャンにより、`scripts/run_all_migrations.sh:651`
（`migrations/20260913_200000_tcg_cardset_exclusion.sql:27`）と `:652`
（`migrations/20260913_210000_tcg_cardset_bundle_registration.sql:29`）の2箇所が
未ガードだと判明した。両ファイルとも同一パターン:

```sql
IF (tenant_004.product_search_keywords.product_id が INTEGER) THEN
    _pid_col := 'id';
ELSE
    _pid_col := 'tcg_uuid';   -- ← ここで決めた列名を、後続の EXECUTE format(...) で
                              --   public.products に対して無条件に使う
END IF;
...
EXECUTE format('SELECT p.%I AS pid FROM public.products p WHERE p.product_code = $1', _pid_col)
```

`tenant_004.product_search_keywords.product_id` が既に INTEGER に変換済み（本番は
`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql` で変換完了済み）なら
`_pid_col := 'id'` の分岐に入るはずだが、designer のエラー報告（`_pid_col := 'tcg_uuid'`
が選ばれた）が示す通り、本番ではこの判定ロジック自体は ELSE 分岐（`tcg_uuid`）を選んでいる
（`tenant_004.product_search_keywords.product_id` の型が本件とは独立の別の状態にあるため。
本 PR はこの型判定ロジック自体は変更しない）。ELSE に入った場合、`tcg_uuid` 列が既に
`migrations/20260916_120000_phase_c_drop_tcg_uuid.sql` で DROP されていると、その列名を
使った `EXECUTE format(...)` がエラーになる。

### 選んだ修正: `_pid_col := 'tcg_uuid'` の直後に列存在ガードを追加し、無ければ `RETURN`

```sql
ELSE
    _pid_col := 'tcg_uuid';

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
    ) THEN
        RAISE NOTICE '...tcg_uuid が存在しません（Phase C 完了済み）。tenant_004 keyword
                       テーブルは Phase 2c で別途 DROP される対象のため、ここでは何もしない — skip';
        RETURN;
    END IF;
END IF;
```

**理由**: `tcg_uuid` が無い状態まで到達したということは、`public.products` 側は既に
Phase C（`migrations/20260916_120000`）を完了している。一方 `tenant_004.product_search_keywords`
/`product_exclude_keywords` 側がまだ INTEGER に変換されていない（`_pid_col='tcg_uuid'` に
落ちた）状態だとしても、これらの keyword テーブル自体は ADR-1001 Phase 2c で後から
別migrationによって DROP される運命のテーブルであり、`PM0263` 等への1個のキーワード追加に
失敗したところで実害は無い（recon.md §1）。したがって「何もしない（RETURN）」が最も安全で、
既存の他の分岐（テーブルが無い・商品が見つからない等）と同じ「ADR-155: 商品データの存在を
前提としない」方針に合致する。

`EXECUTE format(...)` 自体を `IF tcg_uuid 存在` でラップして `id` 側にフォールバックする、
より複雑な代替案も検討したが、`_pid_col='id'` 分岐に落ちるべき時は既にそちらに分岐している
はずで、ここでフォールバックすると「本来 INTEGER 変換が終わっていないテナントに対して
誤って `id` 列（存在するが無関係な値）でマッチさせてしまう」リスクがあるため採用しなかった。
単純に「もう手の施しようがないので何もしない」が最も安全な選択。

---

## 修正後の再ウォーク

### フレッシュDB・CI 1周目
line628（`migrations/20260909_000000` の `tcg_uuid` ADD、第2便のガード）の判定: `work_id`
列はまだ存在しない → ガードTRUE → `tcg_uuid` が ADD される。line651・652 に到達する時点
（`scripts/run_all_migrations.sh:651 > 628` を確認済み、下記）では `tcg_uuid` が既に存在する
ため、新ガードの `IF NOT EXISTS` は FALSE（存在する）→ 元のロジックがそのまま実行される
（regression なし）。

### フレッシュDB・CI 2周目 / 本番・次回デプロイ
`tcg_uuid` は既に DROP 済み（1周目末・既存の恒久状態）。`work_id` は既に INTEGER（1周目末・
本番は設計担当 Opus 確認済み）。line651/652 の ELSE 分岐に入った場合でも、新ガードの
`IF NOT EXISTS (tcg_uuid)` が TRUE → `RAISE NOTICE` + `RETURN`。エラー無く安全にスキップ。

### 628 < 651 < 652 の順序再確認（file:line）
```
$ grep -n "run_sql migrations/20260909_000000_public_products_phase2b_columns.sql\|run_sql migrations/20260913_200000_tcg_cardset_exclusion.sql\|run_sql migrations/20260913_210000_tcg_cardset_bundle_registration.sql" scripts/run_all_migrations.sh
628:run_sql migrations/20260909_000000_public_products_phase2b_columns.sql
651:run_sql migrations/20260913_200000_tcg_cardset_exclusion.sql
652:run_sql migrations/20260913_210000_tcg_cardset_bundle_registration.sql
```
628 < 651 < 652 を確認済み。

### 524（`migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql`）の再ガード確認
既存ガード（`:20-28`）を再読し、`tcg_uuid` 列が存在しない場合に `RAISE NOTICE` の上で
`RETURN` することを確認済み（recon.md §2 判定表）。本 PR では無変更。

---

## 変更内容

1. `migrations/20260913_200000_tcg_cardset_exclusion.sql:27` 直後にガード追加（`RETURN`）。
2. `migrations/20260913_210000_tcg_cardset_bundle_registration.sql:29` 直後に同じガード追加。

**触らない**: `migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql`（524、既存ガード
済み）、`migrations/20260909_000000_...`・`migrations/20260914_140000_...`（628・661、第2便で
修正済み・無変更）、`migrations/20260922_040000_fix_phase2c_fk_blocker.sql`（665、既存ガード
済み）、`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql`（671、既存ガード済み）、
`migrations/20260916_120000_phase_c_drop_tcg_uuid.sql`（674、既存ガード済み）。

---

## CI カバレッジ

第1便・第2便と同じ既知のギャップ。本PRが変更する2ファイル
（`20260913_200000`・`20260913_210000`、いずれも9月付け）は `migration-full-dryrun`
ジョブの対象ファイル正規表現（`^migrations/0|^migrations/2026060[4-9]|^migrations/2026061|
^migrations/2026062`）に一致しない（6月4日〜29日限定のため）。`migration-test-run`
ジョブ（`:937` の正規表現 `^migrations/[0-9][0-9][0-9].*\.sql$`）には一致し、変更SQLとして
1回目・2回目実行される。

---

## 変更範囲

| 層 | 変更 |
|---|---|
| migrations（ガード追加） | `20260913_200000`・`20260913_210000` の `_pid_col := 'tcg_uuid'` 分岐に列存在ガード |
| migrations（無変更） | `20260909_000000`・`20260914_140000`・`20260915_120000`・`20260916_120000`・`20260922_040000`・`20260922_070000` — いずれも既存または第2便のガードで対応済み |
| docs | `docs/handoff/products-column-churn-3/recon.md`（新規）・`docs/handoff/products-column-churn-3/design.md`（新規） |
| 台帳 | .claude-pipeline/active-work.d/release-stop-products-column-churn-3.md（main checkout に新規作成、このブランチには含めない） |

## 触るファイル

1. migrations/20260913_200000_tcg_cardset_exclusion.sql
2. migrations/20260913_210000_tcg_cardset_bundle_registration.sql
3. docs/handoff/products-column-churn-3/recon.md（新規）
4. docs/handoff/products-column-churn-3/design.md（新規・本ファイル）

削除するファイル: 無し（行削除も無し。既存ロジックの直後にガードを追加したのみ）。

---

## 維持の仕組み

守り手: 以下はアイデア提案のみで未実装（本PRのスコープ外）
- 第1便・第2便から継続: ある migration が `ALTER TABLE public.<table> ADD COLUMN <col>` を
  含み、別の登録済み migration が同じ `<table>.<col>` を無条件に `DROP COLUMN` する組み合わせを
  CIで検知する案。今回の不具合（`_pid_col := 'tcg_uuid'` という**動的な列名代入**からの
  `EXECUTE format(...)` 経由の参照）はこの静的解析だけでは検知できない種類の参照であり、
  「後で DROP される列の名前を動的に組み立てて参照している箇所」まで検知する場合は、
  単純な `ADD`/`DROP` 対応表だけでなく `EXECUTE format(... %I ...)` のような動的SQLの
  列名引数追跡が必要になる。これは静的解析としては難度が高いため、提案のみに留める。
- 実務的な代替案（提案）: 「DROP される運命の列を動的参照する」パターン自体を作らないよう、
  今後 Phase 2c 的な「後で丸ごと消えるテナント専用テーブル／列」を参照するロジックは、
  `to_regclass`/`information_schema` で**対象列自体の存在**を確認してから使う、という
  コーディング規約を `docs/specs/branch-operations/README.md` 等に追記する案（未実装・提案）。
- `migration-full-dryrun` の対象ファイル正規表現を全日付範囲に拡張する案（第1便・第2便から継続）。
