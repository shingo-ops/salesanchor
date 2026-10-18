# design: 在庫表のタブを中分類（work_id）で絞り、products.tcg_type をやめる（ADR-1030）

- 現在地: docs/handoff/inventory-tab-by-work-id/recon.md／決定: [ADR-1030](../../adr/ADR-1030-drop-products-tcg-type.md)／前例: [drop-products-type-master-id/design.md](../drop-products-type-master-id/design.md)
- PO の言葉（2026-10-18）: 「中分類が正だと考えている」「在庫表のタブを中分類で絞る（y）」「SSOTしたいので不要なら列を消してくれ」「配線とDBのSSOTは遵守してデータを分散させることは禁止」「金型登録のないハードコードを禁止」「整備できたらGAS側も整備してくれ」
- 区分: 便1 = 通常 PR（migrations・deploy.yml・本番 scripts を含まない）。便2 = 危険 PR（migrations を含む・列削除）。

## 1. 目的（PO に見える変化）
- 在庫表の「ポケモンBOX」「ワンピース」などのタブに、中分類がその作品の商品がすべて出る。ハドウシーカー（466045）が「ポケモンBOX」タブに出る。今後新しく登録した商品も、登録した日からタブに出る。
- 商品一覧の「カテゴリー」列と絞り込みが、中分類の作品名で動く。
- 商品編集画面から「カテゴリ」欄が消える（作品は TCG 商品マスタの商品詳細「作品」で直す）。
- 便2 の後、DB から写しの欄 products.tcg_type が消え、作品は中分類1か所だけになる。

## 2. 対象と対象外
| 対象 | 対象外（触らない） |
|---|---|
| 便1: recon §a-1・§a-2・§a-3・§i の products.tcg_type を読む・書く・返す全箇所（backend の routers/services/schemas、frontend の InventoryPage・ProductsPage・ProductEditPage・型、テスト、openapi.json） | public.tcg_series_master.tcg_type とそれを使う super_admin_tcg.py・central_masters.py・seed_tcg_series*.py |
| 便2: 列・FK・索引の削除 migration 1つ、run_all_migrations.sh 登録1行、ADD 文と FK 追加文の扱い、テスト準備（conftest.py:812・rls_bootstrap.py・test_products_tcg_type_fk.py） | type_master 表・GET /products/tcg-types の URL と関数名（中身は type_master の一覧で products.tcg_type を読まない。名前替えは別件） |
| 便3: 在庫一覧 GAS（調査結果で変更要否を決める。§5） | InventoryPage のタブの見た目・部品（生 button の ui-allow #2624 は今回触らない。値の送り方だけ変える） |
| | products.category 列、category_class、work_id の値 |

## 3. 便1 の変更前後（コードの真実は recon の抜粋。行番号は origin/main 222f07098）

共通の書き方（作品の符号の取り方）: products を `p`（または `pp`）としたとき
```sql
LEFT JOIN public.type_master tm ON tm.id = p.work_id
-- 返す: tm.code AS work_code
-- 絞る: tm.code = :work_code
```
例外（実装中に判明・Opus 承認 2026-10-18）: 列名を修飾せずに書いている SELECT（products.py の一覧など）は、type_master と同名の列（id・name_en・created_at・updated_at）があって JOIN すると曖昧になるため、同じ意味の相関サブクエリにする。返す値は `(SELECT tm.code FROM type_master tm WHERE tm.id = products.work_id) AS work_code`、絞り込みは `work_id = (SELECT tm.id FROM type_master tm WHERE tm.code = :work_code)`。
SQLite のテスト経路は同じ形で `type_master`（スキーマ名なし）を使う。既存の `_products_ctx` / `is_postgresql` の分岐に従う。

### 3-1. backend/app/routers/inventory_offers.py
| 行 | 変更前 | 変更後 |
|---|---|---|
| :73 _BASE_SELECT | `p.tcg_type AS tcg_type` | `tm.code AS work_code`（:77 の products JOIN の次に `LEFT JOIN public.type_master tm ON tm.id = p.work_id` を足す） |
| :296 / :298 | `SELECT x.*, pp.tcg_type AS tcg_type, pp.category AS category FROM rows_main x {join}` | `SELECT x.*, tm.code AS work_code, pp.category AS category FROM rows_main x {join}`（:293 の join 文字列に ` LEFT JOIN public.type_master tm ON tm.id = pp.work_id` を足す） |
| :188-197 | 引数 `tcg_type`、`d.tcg_type = :tcg_type` | 引数 `work_code`、`d.work_code = :work_code`、params キー `work_code` |
| :332 | `tcg_type: str \| None = Query(... description="TCG種別 (public.products.tcg_type)")` | `work_code: str \| None = Query(default=None, max_length=50, description="作品の符号（products.work_id → type_master.code）")` |
| :377 | `tcg_type=tcg_type` | `work_code=work_code` |
| :173 | `tcg_type=row.get("tcg_type")` | `work_code=row.get("work_code")` |

backend/app/schemas/inventory_offers.py:111 と :152 の `tcg_type: str | None = None` → `work_code: str | None = None`（コメントは「作品の符号（products.work_id → type_master.code）」）。

### 3-2. 在庫の集計 backend/app/services/inventory_aggregated_service.py・inventory_aggregation.py・backend/app/routers/inventory_aggregated.py・backend/app/schemas/inventory_aggregated.py
- `_load_products`（service :28-45）: `SELECT DISTINCT p.id, p.name, p.tcg_type` → `SELECT DISTINCT p.id, p.name, tm.code AS work_code`、FROM に `LEFT JOIN public.type_master tm ON tm.id = p.work_id`、絞り込み `AND p.tcg_type = :category` → `AND tm.code = :category`（引数名 category は既存の API 契約なので変えない）。
- service :76-78、:88-90、:96-102、:110 と inventory_aggregation.py:44,71,247,352、backend/app/schemas/inventory_aggregated.py:6,22,33、router :5,51,61,75 の `tcg_type` を `work_code` に揃える（タブは distinct work_code の昇順）。docstring の「tcg_type で絞る」は「work_id の作品の符号で絞る」に直す。

### 3-3. 在庫検索 backend/app/services/inventory_search.py・backend/app/routers/inventory_search.py・backend/app/schemas/inventory_search.py
- :346-347 `p.tcg_type,` → `tm.code AS work_code,`（同 SELECT の products JOIN の次に `LEFT JOIN public.type_master tm ON tm.id = p.work_id`）。:104-107 の項目と :445、router :125、schema :65 を `work_code` に。
- 実装者は変更の前に、検索結果の `tcg_type` を読む backend の処理（見積・請求の明細の取り込み）を `git grep -n "tcg_type" -- backend/app` で確かめる。§3-1〜3-5 の一覧に無い読み手があれば、手を付けずに止めて報告する（想定分岐 B1）。

### 3-4. 商品 API backend/app/routers/products.py・backend/app/schemas/product.py
- 一覧の SELECT（:152）: `tcg_type` → `tm.code AS work_code`（products の FROM に type_master の LEFT JOIN）。
- 一覧の引数（:186）と絞り込み（:246-248）: `tcg_type` → `work_code`、`tcg_type = :tcg_type` → `tm.code = :work_code`。
- 書く側: `_UPDATABLE_COLUMNS` の `"tcg_type"`（:71）、`_validate_tcg_type`（:112-133）、POST の検査（:402-403）と INSERT 列・値（:437,447）、PATCH の検査（:525-526）を消す。
- backend/app/schemas/product.py: ProductCreate（:63）・ProductUpdate（:111）から `tcg_type` を消す。ProductResponse（:181）は `tcg_type` → `work_code: str | None = None`。単票の GET /products/{id} の SELECT も同じく `tm.code AS work_code` を返す（ProductResponse を返す全 SELECT を揃える）。
- GET /products/tcg-types（:285-312）は変えない（type_master の一覧で、products.tcg_type を読まない）。

### 3-5. フロントエンド
| ファイル:行 | 変更前 | 変更後 |
|---|---|---|
| InventoryPage.tsx:189 | `params.set("tcg_type", activeTab)` | `params.set("work_code", activeTab)` |
| InventoryPage.tsx:149 のコメント | 「種別マスタ（tcg_type コード → 日本語名）」 | 「中分類マスタ（type_master.code → 日本語名）」 |
| ProductsPage.tsx:139 | `params.set("tcg_type", tcgType)` | `params.set("work_code", tcgType)` |
| ProductsPage.tsx:366 | `p.tcg_type ? (tcgTypeName.get(p.tcg_type) ?? p.tcg_type) : (p.category \|\| "-")` | `p.work_code ? (tcgTypeName.get(p.work_code) ?? p.work_code) : (p.category \|\| "-")` |
| ProductEditPage.tsx:65,131,241-251 | 「カテゴリ」欄（SelectControl・data-testid product-edit-tcg-type）と form の tcg_type | 欄と form 項目を消す。tcgTypes を取るのがこの欄のためだけなら、その取得も消す |
| products.types.ts:34 | `tcg_type: string \| null;` | `work_code: string \| null;` |
| products.types.ts:59,94 | フォームの `tcg_type` | 消す |
| inventoryColumns.tsx:34、InventorySearchBar.tsx:56 | `tcg_type` の型宣言 | `work_code` |
- 新しい UI 部品・文言・色は足さない（消すだけ・値の名前を替えるだけ）。i18n キー `products.field.category` が ProductEditPage 以外で使われていなければ ja.json・en.json から同時に消す（両方同じキー集合を保つ）。使われていれば残す。
- タブの固定3つ（pokemon_booster_box / one_piece / dragon_ball）とその他プルダウンは type_master.code のまま変えない（GET /products/tcg-types が出どころ。recon §a-3）。

### 3-6. テスト・API 契約
- backend テスト（recon §e）の `tcg_type` を使う期待を `work_code` に直す。追加するテスト（必須）: 「tcg_type が NULL で work_id=1 の商品の在庫行が、GET /inventory?work_code=pokemon_booster_box に出る」「work_id=2 の商品は出ない」。PG の既存テスト（test_inventory_distribution_rows_pg.py）に足すのを優先し、無理なら SQLite の test_inventory_distribution_rows.py に足す。商品一覧の `work_code` 絞り込みのテストも1つ足す。
- 便1 では列は残るので、conftest.py:812・rls_bootstrap.py・test_products_tcg_type_fk.py は触らない（便2 で扱う）。
- 実装中の変更（2026-10-18、Opus 判断）: backend/tests/test_products_tcg_type_fk.py の API 経由の部分（POST/PATCH で tcg_type を送って 400 を期待する検査）は、便1 で API から tcg_type の入力と検査を外したため成り立たない（CI 実行 39083662764 で失敗）。便1 でこの API 部分だけを消す。列への直接 INSERT で外部キーを確かめる部分は、列が残る便1 の間は有効なので残し、便2 でファイルごと消す。
- frontend のテストと fixture の `tcg_type` を `work_code` に。CommerceNavigationButtonMigration.test.tsx の URL 期待は `work_code=` に。tests-e2e/product-edit-tcg-type.spec.ts は欄が消えるので削除し、PR 本文の削除欄に書く。tests-e2e/inventory-table-layout.spec.ts:41 は `work_code` に。
- openapi.json は `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で作り直す（手で直さない）。

### 3-7. 便1 の完了点検（実装者が実行）
```
git grep -n -E "tcg_type" -- backend/app frontend/src frontend/tests-e2e frontend/api-contract
```
残ってよいのは: tcg_series_master 系（super_admin_tcg.py・central_masters.py）と、関数名・URL `list_product_tcg_types` / `/products/tcg-types` と、frontend の変数名 `tcgType`/`tcgTypes`（type_master の一覧を持つ変数。products.tcg_type ではない）だけ。それ以外が残れば直すか止めて報告。

## 4. 便2 の変更前後（便1 の本番確認 K1〜K5 合格の後に着手）
前例 ADR-1026 と同じ型（drop-products-type-master-id/design.md §3）。
### 4-1. migrations/20260602_020000_add_products_tcg_type.sql
:7 の `ADD COLUMN IF NOT EXISTS tcg_type VARCHAR(50)` と :14 の `CREATE INDEX IF NOT EXISTS idx_public_products_tcg_type` を消し、次のコメントを残す:
```sql
-- （削除済み）products.tcg_type は ADR-1030 で取り除いた。作品の正本は products.work_id。
-- products は列番号が上限 1600 に達しているため、ここで列を足し直すと毎デプロイ失敗する。ADD を戻さないこと。
```
実装者はファイル全文を読み、他の文（値の書き込みなど）が残るなら内容を報告して止める（想定分岐 B3）。
### 4-2. migrations/20260623_060000_add_products_tcg_type_fk.sql
列が無いときに飛ばす分岐がある（recon §h）。実装者は全文を読み、列が無い状態で流してもエラーにならないことを migration-test の「全件試し実行」で確かめる。エラーになるなら本文を「何もしない」コメントだけに替える。
### 4-3. 新規 migrations/20261018_HHMMSS_drop_products_tcg_type.sql（HHMMSS は既存の最新 20261018_100000 より後）
```sql
-- ADR-1030: products.tcg_type を取り除く（作品の正本は products.work_id）
-- 便1 でアプリは列を読まない（docs/handoff/inventory-tab-by-work-id/design.md §3）
-- 依存は FK・索引・ai_ro ビューのみ（recon §h）。ai_ro ビューは run_all_migrations.sh の先頭で外れ最後に作り直される
-- 冪等: IF EXISTS。値は書かない（ADR-1007）
ALTER TABLE public.products DROP CONSTRAINT IF EXISTS fk_products_tcg_type;
DROP INDEX IF EXISTS public.idx_public_products_tcg_type;
ALTER TABLE public.products DROP COLUMN IF EXISTS tcg_type;
```
### 4-4. scripts/run_all_migrations.sh
末尾に `run_sql migrations/20261018_HHMMSS_drop_products_tcg_type.sql` とコメント1行（ADR-1030）。:248・:487・:471 の既存の登録行はファイルが残るので消さない。
### 4-5. テスト準備
conftest.py:812 の SQLite products 表から `tcg_type` 列を消す。rls_bootstrap.py:19-32,266,307 は列が無い前提で動くよう直す（ADD を消した migration を流しても問題ないことを確かめる）。test_products_tcg_type_fk.py は対象の列が無くなるため削除し、PR 本文の削除欄に書く。test_value_migrations_neutralized.py は期待を確かめ、必要なら直す。
### 4-6. 退避（マージ前）
本番 public.products 全行の `id, tcg_type, work_id` を ADR-1024 の読み取りの道で CSV に保存（~/CC報告ファイル-keep/inventory-tab-work-id/products_tcg_type_backup.csv）。行数が本番 count(*)（1426＋その時点の増分）と一致しなければ止める。

## 5. 便3: 在庫一覧 GAS
結論: **GAS の変更は不要**（調査 2026-10-18、生出力 ~/CC報告ファイル-keep/inventory-tab-work-id/gas/q1.out・q2.out）。
- シート「在庫集計」を書くのは backend の backend/app/services/tcg_distribution_svc.py（run_distribution :952、_write_to_target_sync :686）。Series 列（DIST_HEADERS :59）の式は :331 `COALESCE(ser.name_ja, '') AS series`、ser は :364-365 `LEFT JOIN public.type_master ser ON ser.id = p.work_id`。すでに中分類 work_id → type_master.name_ja で、products.tcg_type を読まない。
- 本番の概算: product がある行で Series が空は 0。tcg_type が NULL の商品も Series は work_id から入っている（q2.out）。
- GAS（1hc-release・1tb-head の index.html:981 COL.series、buildSeriesTabs :1196）は Series の文字列をそのままタブ名にするだけで、tcg_type・work_id を参照しない。
- したがって GAS 在庫一覧はすでに中分類でタブを作っており、今回の便1・便2 でアプリの在庫表が GAS と同じ基準にそろう。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 便1 の CI がすべて緑（api-contract-check・test.yml・frontend-check・e2e を含む） | `gh pr checks <PR>` で fail 0・pending 0 |
| K2 便1 の完了点検 grep（§3-7）で許可されたもの以外 0 行 | 実装者の生出力と、Opus がマージ前に origin のブランチで同じ grep を再実行 |
| K3 tcg_type が NULL で work_id=1 の商品が work_code=pokemon_booster_box の在庫に出るテストが CI で実行され合格 | CI ログでそのテスト名が PASSED（skip でない） |
| K4 便1 デプロイ成功、/health 200、未ログインの GET /inventory?work_code=pokemon_booster_box が 401（500 でない）、backend ログに tcg_type / work_code のエラー 0（デプロイ後 10 分） | `gh run view`、curl、ログ（読み取り） |
| K5 本番で配信行の判定を DB で再現: 466045 の現行行（is_current・pid_resolved 等の条件を満たす行）が work_id=1 で、type_master id=1 の code が pokemon_booster_box | 読み取りの道の SELECT（recon §d と同じ経路） |
| K6 PO が在庫表の「ポケモンBOX」タブで「24時間以内」を外し、ハドウシーカーの行を見る | PO 目視（再読み込みしてから） |
| K7 便2: 退避 CSV の行数＝本番 products の総行数 | `wc -l` と count(*) |
| K8 便2: リポジトリで products に tcg_type を足す文 0 件 | `git grep -n -i "ADD COLUMN IF NOT EXISTS tcg_type" origin/main -- migrations` が 0 行 |
| K9 便2 デプロイ後、列・FK・索引 0、ai_ro.public__products に tcg_type 無し、tcg_series_master.tcg_type は残る | 本番カタログを読み取りの道で |
| K10 便2 デプロイ成功・/health 200・API 401・ログにエラー 0、次のデプロイも成功 | K4 と同じ＋次回 deploy の結果 |

## 6-1. 受入結果（2026-10-19 記録）
| 基準 | 結果 | 事実 |
|---|---|---|
| K4 | ○ | 便1 #4508 マージ 035b0145e、Deploy 39086222367 success。未ログイン GET は 401、アプリエラー 0 |
| K5 | ○ | 466045 は work_id 1 = pokemon_booster_box |
| K6 | ○ | PO 目視で「ポケモンBOX」タブに 466045 が表示（2026-10-18「出た」） |
| K7〜K9 | ○ | 便2 #4512 マージ 57da62446（PO「GO #4512」）、Deploy 39125114956 success。本番 products の tcg_type 列・FK・索引 0 件、ai_ro.public__products に tcg_type 無し |
| K10 | ○ | 次回デプロイも成功。Deploy 39127734950（#4516、2026-10-18T12:32:53Z）success。ログで 20261018_110000 は「does not exist, skipping」の NOTICE のみ・ERROR なし、20260602_020000 は neutralized、ai_ro views created 510 / failed 0、Migrations done。続く 39127839895（#4517）も success。2026-10-18T20:42Z の本番読み取りで tcg_type 列 0 件・制約 0 件 |

K1〜K3 は便1 のマージ前に確認済み（#4508）。K7 の退避 CSV を含む証拠の保存先: ~/CC報告ファイル-keep/inventory-tab-work-id/（中身は社外秘のためここに載せない）。

付随: GAS 在庫一覧の既定「新しい順」を発売日→英語名に変更（SA アプリと同じ）。テスト版23・本番版17（戻し先16）、PO 目視○。GAS ソースは salesanchor リポジトリ外。

## 7. 影響範囲・リスクと対処
| リスク | 対処 |
|---|---|
| 一覧にない読み手が残り、便2 で 500 | §3-7 の grep を便1 で 0 にしてから便2。便2 の直前にもう一度 grep |
| API の名前替えで外部の呼び出しが壊れる | `tcg_type=` を送るのは InventoryPage と ProductsPage だけ（recon §b）。リポジトリ外の呼び出しは未確認。名前の違う引数は無視されるだけで 500 にはならない（絞られない） |
| 便2 の ADD 残りで毎デプロイ失敗 | 4-1 と 4-3 を同じ PR。K8 |
| 値を失う | 4-6 の CSV と自動 pg_dump。便1 の時点でアプリは列を使わない |
| 商品編集画面で作品を直せなくなる | 元々この欄は写しを書くだけで中分類は変わらなかった（recon §a-2）。作品は TCG 商品マスタの商品詳細で直す（既存） |

戻し方: 便1 は revert PR。便2 は列を足し直せないため、値が要るときは CSV と pg_dump から読む。

## 8. 維持の仕組み
- 守り手: backend/tests/test_inventory_distribution_rows_pg.py（work_id だけで work_code の絞り込みに出ることを毎回の CI で確かめる）
- 作品の判定は type_master の JOIN 1か所の書き方に揃え、写しの列が無いので写し忘れが起きない。
- 4-1 の「ADD を戻さない」コメントと CI migration-guard Check 10（同じ列の ADD→DROP を止める）。
- 追加するテスト（K3）が、work_id だけで在庫表のタブに出ることを毎回の CI で守る。

## 9. 外部・過去事例
外部事例は不要（社内の二重持ち列の整理。判断は自社 DB と参照箇所の実測）。過去事例: ADR-1026（type_master_id 削除、#4471）を便2 の型として使う。

## 10. 実装カード（Sonnet）
### 便1
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-inventory-tab-by-work-id（ブランチ release/inventory-tab-by-work-id）。最初に `./scripts/dev/executor-preflight.sh || exit 1`、docs/ai-agents/executor-checklist.md に従う。
- 触るファイル: §3-1〜3-6 に書いたものだけ。migrations・scripts・.github・deploy は触らない。
- 点検: backend `pytest -q`（該当テストと全体）、frontend の型検査・lint・単体テスト（frontend/package.json の既存コマンド）、openapi 再生成、§3-7 の grep。生出力は /Users/tanizawashingo/CC報告ファイル-keep/inventory-tab-work-id/impl1/ へ。
- 想定分岐: B1 §3 の一覧に無い tcg_type の読み手が見つかった → 止めて報告。B2 SQLite 経路で type_master が無いテストがある → 既存の分岐（to_regclass / sqlite_master）の型に合わせ、合わなければ止めて報告。B4 i18n 検査がキーの削除で失敗 → キーを残して報告。
- commit は意味ごとに分けてよい。push まで。PR は作らない（Opus が作る）。
- 報告: DONE/BLOCKED:/NEEDS_DECISION: で始め、HEAD、変更ファイル一覧、点検の生出力のパス。
### 便2
便1 の K1〜K5 合格後に Opus が発行する（§4 の内容。同じ型で別ブランチ release/drop-products-tcg-type）。

## 11. 設計審査（同一 AI の自己審査。独立した第二者レビューではない）
- 判定: **APPROVE（便1 着手可）**。便2 は便1 の K1〜K5 合格後に §4 を再点検してからカード発行。
- 根拠: 変更箇所は recon の file:line と一致（§3 の各表）。作品の正本 work_id（ADR-1026）に寄せ、新しい写しを作らない。受入条件はすべてコマンド出力か PO 目視で○×が決まる（§6）。GAS は変更不要を実物で確認（§5）。
- 実装中に止める点: B1（一覧外の読み手）、B2（SQLite 経路の type_master）、B4（i18n キー）。いずれも推測で進めず報告。
- 未解決: リポジトリ外から API に `tcg_type=` を送る呼び出しの有無は未確認（§7。届いても 500 にはならず絞られないだけ）。
