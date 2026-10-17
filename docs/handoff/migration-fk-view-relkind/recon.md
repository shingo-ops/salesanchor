# recon: 20260919_030000 で、表がビューのとき外部キーが作られない件（件4）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:22-25（#4481 件4）
> 基準: origin/main a89341670。生出力: ~/CC報告ファイル-keep/kenn4-fk-view-20261018/（recon/01〜10、fresh/）

## 既存 ADR
- `git grep -il "type_master\|relkind" docs/adr/` → ADR-083、ADR-090、ADR-1007、ADR-1026、ADR-156（recon/07_adr.txt）。
- ADR-1007（migration は構造だけ・1回だけ流す）。既存ファイルの書き換えを止める仕組み（チェックサム）は未導入。
- backend/CLAUDE.md の additive-only 規則は、制約の追加を許している。

## 事実
1. 引継ぎ書の前提「存在確認が relkind を見ていない」は、すでに直っている。commit 0e3dd5b5d（#4446 P5）で migrations/20260919_030000_master_ssot_fk_work_id.sql:25 に `AND c.relkind IN ('r', 'p')` が入った（`git log -- <file>`、本文 :21-26、`grep -n relkind` で :25）。
2. 実行の順番（scripts/run_all_migrations.sh の行番号）は次のとおり。
   - :222 で 085_create_tcg_type_master.sql が表を作る。
   - :718 で 20260919_010000 が products.work_id INTEGER を足す（ファイルの :107）。
   - :727 で 20260919_030000 が外部キーを張る。
   - :764 で 20260921_070000 が名前を type_master に変え、互換ビュー tcg_type_master を作る。
   - したがって 030000 が流れる時点では、tcg_type_master はまだ表である（fresh/linenos.txt）。
3. 名前を変えても表の oid は変わらないので、外部キーは改名後の type_master を指したまま残る。
4. 本番の外部キー fk_products_work_id は products → type_master を指し、convalidated=t（docs/handoff/migration-guard-precision/recon.md:12）。
5. 空の DB からの実測：CI の .github/workflows/migration-test.yml の job `migration-full-dryrun`（:1112〜。土台 :1165〜1753、全件実行 :1828）を、postgres:16 の一時コンテナで再現した。
   - 結果は 328本で、1周目が成功328・失敗0、2周目が成功328・失敗0（fresh/out_step13.txt）。
   - 全件のあとの pg_constraint は次のとおり（fresh/select_result.txt）。
     - `fk_products_work_id | products | type_master | t`
   - relkind は products=r、type_master=r、tcg_type_master=v。
6. 030000 は除外表に入っていない（scripts/migration-guard/dryrun-exclusions.tsv のデータ行は0本）。
7. 2周目で 030000 が ALTER を飛ばすのは、外部キーがすでにあるうえ、tcg_type_master がビューになっているからである。2周目のあとも外部キーは残っている（事実5）。docs/handoff/migration-dryrun-baseline/design.md:52 の「外部キーは作られない」は、2周目の ALTER が飛ぶことだけを見た記述で、1周目で作られた外部キーは見ていない。
8. 後続の migration と backend は、この制約名に依存していない（recon/06_dep.txt、06_fkname.txt）。

## 結論（事実から）
- 空から作る環境（CI と同じ手順）でも、本番でも、外部キーはある。引継ぎ書の「新しい環境を空から作るときに効いてくる」は、今の main には当てはまらない。
- 外部キーが張られないのは、「外部キーが無いまま、すでに 070000 まで流れた環境」だけ。run_all_migrations.sh は登録順に流すので、030000 が失敗したまま 070000 へ進んだ場合に限られる。そうした環境は確認できた範囲（本番・CI 手順の再現）に存在しない。

## 未確認
- 1周目の直後の pg_constraint は取っていない（取ったのは2周目のあとだけ）。2周目で外部キーを作る経路は無い（事実7）ので、結論は変わらない。
- 開発者の手元の DB は調べていない（共有の正本ではないため対象外）。
