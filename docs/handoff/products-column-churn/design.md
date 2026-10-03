# Design: public.products 列 churn 停止（1600 列上限インシデント対応）

**対象**: インシデント 2026-10-03（本番デプロイ失敗、deploy run 37130920016）
**recon**: docs/handoff/products-column-churn/recon.md
**日付**: 2026-10-04
**担当**: Opus(設計) / Sonnet(実装)

---

## 外部・過去事例の参照と我々への応用

PostgreSQL 16 公式ドキュメントを fetch して確認済み（未確認のまま断定していた前回版を修正）。

- `ALTER TABLE` の Notes（https://www.postgresql.org/docs/16/sql-altertable.html）:
  > The `DROP COLUMN` form does not physically remove the column, but simply makes it invisible to SQL operations. ... dropping a column is quick but it will not immediately reduce the on-disk size of your table, as the space occupied by the dropped column is not reclaimed.
- `limits.html`（https://www.postgresql.org/docs/16/limits.html）:
  > columns per table | 1,600 | further limited by tuple size fitting on a single page
  > Columns that have been dropped from the table also contribute to the maximum column limit.

**我々への応用**: DROP COLUMN はカタログ上の attnum を解放しない。`ADD COLUMN`（毎回新しい attnum を発行）→`DROP COLUMN`（その attnum を永久に使用不能のまま残す）を毎デプロイ繰り返すと、1 テーブルにつき最大 1,600 の attnum 枠を独占的に消費し尽くす。これは今回のインシデントの直接原因そのものであり、外部ドキュメントの記述と本番の実測（dropped attributes 1541件）が一致する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `scripts/run_all_migrations.sh` の構文が壊れていない | `bash -n scripts/run_all_migrations.sh` → exit 0 |
| condition/unit/category_classification の再 ADD が無い | 5 ファイルの diff を目視（本書 recon.md §3） |
| 次回デプロイで「Run database migrations」ステップが成功する | 本番デプロイ後の GitHub Actions run 結果を確認（本PRのスコープ外・次回デプロイで確認） |
| 本番 `public.products` の dropped attribute 数が今後増え続けない | 次回デプロイ後に 1541+2（今回一回限りの condition/unit 最終 DROP）で固定、以降のデプロイで変化しない（要・次回以降デプロイ後の実測確認、本PRのスコープ外） |
| CI: changed-SQL ジョブ（1周目/2周目）が通る | `.github/workflows/migration-test.yml` の `migration-test-run` ジョブ（本 PR の変更ファイルは `steps.detect.outputs.changed_sql` に乗るため対象) |
| CI: 全件ドライラン（`migration-full-dryrun`）が通る | 同ファイルの `migration-full-dryrun` ジョブ — **注意: 本 PR が変更する 5 ファイルは全て `20260602_*` のため、このジョブの対象ファイル正規表現 `^migrations/0|^migrations/2026060[4-9]|^migrations/2026061|^migrations/2026062` に一致せず、全件ドライランの対象外**（下記「CI カバレッジの既知のギャップ」参照） |

---

## 設計方針（改訂版: Opus 指示）

本番事実（しんごさん確認, 2026-10-03）: `public.products` 1347行、`count(unit)=0`、`count(condition)=0`（失敗した run が `20260602_040000` まで実行済みの後でも）。つまり condition/unit の ADD→backfill→(inventoryへコピー)→DROP の一連は現在の本番データに対して**何も書き込んでいない**。backfill の本来目的は 2026-06-29 の `20260629_010000`（本番 UPDATE 62 件確認済み）で既に達成済み。よって「再 ADD を止める」ことは現在の挙動を変えない（無効化しても書き込まれるはずのデータは元から無い）。

変更内容（5ファイル、recon.md §3 に詳細）:

1. `migrations/20260602_000000_add_products_central_columns.sql` — `condition` を ADD リストから削除
2. `migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql` — `condition` を INSERT 列リスト・SELECT 列リストの両方から削除（コメントで理由明記）
3. `migrations/20260602_030000_add_products_unit.sql` — 無効化（`SELECT 1; -- no-op`、ファイルは登録維持）
4. `migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql` — 無効化（同上。この UPDATE は列存在ガード無しで `p.unit`/`p.condition` に直接アクセスしていたため、ADD を削除した後に残すと「column does not exist」で確実に失敗する）
5. `migrations/20260602_170000_add_products_master_label_columns.sql` — `category_classification` を ADD リストから削除

**触らない**: `20260623_020000_drop_products_category_classification.sql`（既存ガード済み・DROP 側）、`20260629_010000_backfill_inventory_unit_from_products.sql`（列存在ガード済みで安全）、`20260629_020000_drop_products_condition_unit.sql`（DROP 側）。

**残る制約（本 PR の範囲外）**: 本番 `public.products` の max attnum は既に 1600 に達している。このテーブルは**新しい列を今後一切追加できない**（この churn を止めても、過去に消費された 1541 件の dropped attnum は戻らない）。新規列が必要になった場合はテーブルの物理再構築（`CREATE TABLE ... AS SELECT` + リネーム、または `pg_repack`/`VACUUM FULL` 相当の全面的なリライト）が必要で、これは本番データに対する不可逆的な重い操作であり、PO（しんごさん）自身の判断・GO が必須。本 PR はこの再構築を一切含まない。

---

## attnum 消費のウォークスルー

### 修正前（現状、インシデントの原因）

デプロイ1回あたり:

| 列 | この回で発生すること | 新規 attnum 消費 |
|---|---|---|
| `category_classification` | line191 で前回分を DROP → line230 で再 ADD（新 attnum） | +1 |
| `condition` | line216 で ADD（新 attnum）→ line491 で DROP（今回発行分を即死化） | +1 |
| `unit` | line219 で ADD（新 attnum）→ line491 で DROP（今回発行分を即死化） | +1 |

→ **毎デプロイ +3 attnum**。本番の dropped attribute 1541 件はこれが繰り返された結果（他テーブルでは最大3件のみ＝この3列チャーンに相当する規模のデプロイ回数を reflect）。1600 件に到達した時点でデプロイが失敗する（今回の run 37130920016 がちょうどそれ）。

### 修正後・本番（次回デプロイ以降）

- **次回デプロイ（1回限りの後始末）**: `condition`/`unit` は失敗した run 37130920016 がすでに ADD 済みで本番に live（attnum 1599, 1600）。line216/219/220 はこの PR で no-op 化されているため何もしない。line491（`20260629_020000`、無変更）の `DROP COLUMN IF EXISTS` が初めて実行され、この2列を最終的に DROP する。これは**新規 attnum を消費しない**（既存の attnum 1599/1600 を dead にするだけ）。`category_classification` は失敗した run で ADD される前に abort したため既に無い状態（line191 の DROP IF EXISTS が no-op）。
- **2回目以降のデプロイ**: `condition`/`unit`/`category_classification` のいずれも存在しないため、line191・line491 の `DROP COLUMN IF EXISTS` は全て no-op。line216/219/220/230 はいずれも ADD 文自体が無い（または no-op）。

→ **修正後は毎デプロイ +0 attnum**。

### 修正後・CI フレッシュ DB

フレッシュ DB で `run_all_migrations.sh` を通しで実行する場合（本番と異なり condition/unit/category_classification は最初から存在しない）:

- line191: `category_classification` 存在しない → DROP IF EXISTS no-op
- line216/219/220: condition/unit の ADD が無い（この PR で削除・no-op化） → 何も起きない
- line230: category_classification の ADD が無い（この PR で削除） → 何も起きない
- line491: condition/unit 存在しない → DROP IF EXISTS no-op

→ **フレッシュ DB でも毎回 +0 attnum**。最終スキーマは condition/unit/category_classification いずれも**存在しない**。

**修正前のフレッシュ DB・単発フルランとの比較**: 修正前のコードをフレッシュ DB で1回通しで実行すると、condition/unit は line216/219 で ADD → line491 で DROP されるため、最終的に**存在しない**（修正後と同じ最終状態）。category_classification は line191（まだ存在しないので no-op）→ line230 で ADD → 以降 DROP されないため、1回の通し実行の最後には**存在する**（修正後は存在しない）。2回目の通し実行では line191 が今度は存在するものを DROP → line230 が再 ADD、で結局**存在する**に戻る。つまり修正前は category_classification の最終状態が「今から見て何回通しで実行したか」のパリティに依存して ADD→ADD→... と churn し続ける一方、修正後は常に「存在しない」で固定される。双方とも「存在しない」という最終状態に収束する condition/unit とは異なり、category_classification は修正によって最終スキーマが変わる（既存 DROP 済み本番とは整合する。フレッシュ DB 上の最終スキーマは「列が無い」点で変わらない——1回限りの通し実行後に限れば「ADD されて存在する」という一過性の違いはあるが、CI の 2周目冪等性チェックが通る時点のスキーマは安定しているので実運用上の差は無い）。

---

## CI カバレッジの既知のギャップ（新たに判明した事実、要認識）

`.github/workflows/migration-test.yml` には2つの関連ジョブがある:

1. **`migration-test-run`**（既存データ付きスキーマ + Sprint1 python script → PR で変更された SQL/python を検出して1回目・2回目実行）。本 PR の5ファイルは全て変更対象なので `steps.detect.outputs.changed_sql`（`.github/workflows/migration-test.yml:937` の正規表現 `^migrations/[0-9][0-9][0-9].*\.sql$`）に一致し、このジョブの対象になる。ただしこのジョブは**変更された5ファイルのみ**を実行するため、`20260629_020000`（condition/unit の DROP、無変更）や `20260623_020000`（category_classification の DROP、無変更）との組み合わせ検証は行われない。
2. **`migration-full-dryrun`**（`run_all_migrations.sh` の全 `run_sql` 行を記載順に1周目・2周目実行、組み合わせ問題を検知する目的のジョブ）。ただしこのジョブの対象ファイル正規表現は `^migrations/0|^migrations/2026060[4-9]|^migrations/2026061|^migrations/2026062`（`.github/workflows/migration-test.yml:1660,1665,1695,1699`）であり、コメント（`:1651`）に明記の通り「初期タイムスタンプ（20260601-20260603）は Python migration 依存のため引き続き除外」。実際に確認:
   ```
   migrations/20260602_000000_add_products_central_columns.sql -> EXCLUDED
   migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql -> EXCLUDED
   migrations/20260602_030000_add_products_unit.sql -> EXCLUDED
   migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql -> EXCLUDED
   migrations/20260602_170000_add_products_master_label_columns.sql -> EXCLUDED
   migrations/20260623_020000_drop_products_category_classification.sql -> INCLUDED
   migrations/20260629_010000_backfill_inventory_unit_from_products.sql -> INCLUDED
   migrations/20260629_020000_drop_products_condition_unit.sql -> INCLUDED
   ```
   **本 PR が変更する5ファイルは全て `migration-full-dryrun` の対象外**。つまり「全件ドライラン2周が通る」ことは、本 PR の変更と後続の DROP migration（20260623_020000 / 20260629_020000）との組み合わせを CI 上で機械的には検証しない。

**リスク**: この既知のギャップにより、CI 緑 = 本番で condition/unit/category_classification の churn が本当に止まる、を完全には保証しない。手動 recon（本書 recon.md §4）で全参照箇所を file:line で確認済みという事実が、このギャップを補っている唯一の根拠。

---

## 変更範囲

| 層 | 変更 |
|---|---|
| migrations (ADD側) | `20260602_000000` から `condition` 削除、`20260602_170000` から `category_classification` 削除 |
| migrations (INSERT列リスト) | `20260602_010000` の tenant_006 移行 INSERT から `condition` 列を削除 |
| migrations (無効化) | `20260602_030000`・`20260602_040000` を `SELECT 1; -- no-op` 化 |
| migrations (無変更) | `20260623_020000`・`20260629_010000`・`20260629_020000` — 触らない |

## 触るファイル

1. `migrations/20260602_000000_add_products_central_columns.sql`
2. `migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql`
3. `migrations/20260602_030000_add_products_unit.sql`
4. `migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql`
5. `migrations/20260602_170000_add_products_master_label_columns.sql`
6. `docs/handoff/products-column-churn/recon.md`（新規）
7. `docs/handoff/products-column-churn/design.md`（新規・本ファイル）
8. `.claude-pipeline/active-work.d/release-stop-products-column-churn.md`（新規・台帳）

削除するファイル: 無し。

---

## 維持の仕組み

守り手（提案のみ・未実装）:
- `bash -n scripts/run_all_migrations.sh` は構文のみで churn を検知しない。CI の `migration-full-dryrun` ジョブの対象ファイル正規表現（`.github/workflows/migration-test.yml:1659` 他）に `2026060[1-3]` も含めるよう拡張すれば、今回のような「ADD→DROP の繰り返しで attnum が尽きる」パターンを将来も機械的に検知できる可能性がある。ただし、このジョブが元々 20260601-20260603 を除外している理由（Python migration 依存）を壊さずに対応できるかは別途検証が必要なため、ここでは提案のみに留め、実装はしない。
- 本番 `public.products` の dropped attribute 数を定期監視するクエリ（`SELECT COUNT(*) FROM pg_attribute WHERE attrelid='public.products'::regclass AND attisdropped`）を監視ダッシュボードに追加するアイデも将来検討に値する（未実装・提案のみ）。
