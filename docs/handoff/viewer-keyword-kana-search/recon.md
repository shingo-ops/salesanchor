# recon: 顧客向け在庫一覧GAS — 検索ワードを検索対象にし、ひらがな・カタカナを同一視する

- 作成: 2026-10-05（調査は Sonnet、記録と確認は Opus）
- 設計: [design.md](design.md)
- 基準: origin/main 828d19aa0（worktree `release/viewer-keyword-kana-search`）
- GAS の基準: 本番 GAS（scriptId `1hc-Wn3g…`）とテスト用 GAS（`1Tb-84Fj39…`）を 2026-10-05 に `clasp clone` した写し。保存先はセッションの scratchpad で、repo には入れていない。以下、`<gas-prod>` は本番の写しを指す。
- 社外秘: 仕入元名・投稿本文は書かない（集計値と file:line だけ）。

## 1. 発端（観測事実）
- 2026-10-05 のお客様の申告：「ラウンドワン」と入力してもヒットしない。
- 本番 DB の値：名称・英語名・Mark に「ラウンドワン」を含む active 商品は 0件。検索ワード表（public.product_search_keywords）で「ラウンドワン」を持つ商品は 1件。

## 2. 既存 ADR（git grep 済み）
- `docs/adr/` を distribution・配信・tcg-client-viewer・在庫一覧・search_keywords・検索ワード・normaliz・カナ で検索した。ヒットは 11本で、関係するのは次の4本。
  - `docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md:76,98,108,129`：product_search_keywords を public に統一。tcg_distribution_svc.py のスキーマ参照を変更。
  - `docs/adr/ADR-158-product-level-supersession.md:57,70`：配信クエリ（is_current の扱い）。
  - `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`：配信は needs_review=false の行に限る。
  - `docs/adr/ADR-093-inventory-table-product-master-redesign.md:33`：products.search_keywords 列。
- `docs/adr/FEATURE-INDEX.md:18` は在庫・商品マスタ（ADR-099/093/014）のみ。配信・在庫一覧・検索の行は無い。
- 配信の列数（12列）を定めた ADR は見つからなかった。「12列」の記述は `backend/app/services/tcg_distribution_svc.py:46` のコメントと、直前の設計 `docs/handoff/gas-viewer-series-tabs/design.md` だけ。

## 3. SA 側（配信）
- 列の定義：`backend/app/services/tcg_distribution_svc.py:46-60`（`DIST_HEADERS` 12列。末尾が Series・提供者）。
- 行の取得：`backend/app/services/tcg_distribution_svc.py:188-283`（`fetch_output_rows`）。SELECT は :224-237、WHERE は :254-261、返却の12列リストは :267-282。
- 書き込み：`backend/app/services/tcg_distribution_svc.py:508-511`。毎回 `worksheet.clear()` でタブを消し、`[DIST_HEADERS] + rows` を書く（全置換）。列数は `DIST_HEADERS` に連動する。行数の上限は `DIST_ROW_LIMIT = 5000`（:44、確認は :500-506）。
- 手動配信の経路：`backend/app/line_import_admin.py:117` も `fetch_output_rows` を呼ぶ。
- 列の形を固定しているテスト：
  - `backend/tests/test_tcg_result_order.py:104`（`len(r) == 12`）
  - `backend/tests/test_tcg_distribution.py:184`（`written[0] == DIST_HEADERS`）
  - ほかに配信を扱うテストは `backend/tests/` に6本（test_line_import_admin / test_tcg_completion_safety / test_tcg_condition_review / test_tcg_distribution_pg / test_tcg_is_active_filter / test_tcg_work_matching_integration）。
- 「在庫集計」タブを読む SA 内のコードは無い（git grep で0件）。

## 4. 検索ワードの正本
- 正本は `public.product_search_keywords`（1商品に複数行）。定義は `migrations/20260919_020000_master_ssot_public_tables.sql:301-307`。列は id・keyword・position・product_id・updated_at。
- 照合（判定）はこの表を読む。
  - `backend/app/services/tcg_analyzer_svc.py:190-199`
  - `backend/app/services/extraction_shadow_svc.py:93-98`
  - `backend/app/services/tcg_product_master_svc.py:140-153`
  - `backend/app/services/buyback_scraper/product_matcher.py:67`
- `products.search_keywords`（TEXT 列。`migrations/20260602_170000_add_products_master_label_columns.sql:33`）は、照合の読み取り元ではない。値のある 221件のうち、検索ワード表をカンマでつないだ値と一致するものは 0件（差の中身は未確認）。
- `tenant_004.product_search_keywords` は `to_regclass` が NULL で、存在しない。

## 5. 本番 DB の値（2026-10-05、読み取りのみ）
| 項目 | 値 |
|---|---|
| products（全件／active） | 1,347／1,323 |
| product_search_keywords の行数 | 2,914 |
| 行を持つ商品 | 1,347件（active の 1,323件すべて） |
| 1商品あたりの語数 | 最大 13、平均 2.16 |
| 1語の文字数 | 最長 57、平均 11.7 |
| active 商品の語 2,833語のうち、ひらがなを含む／カタカナを含む／英字を含む／全角英数を含む／半角カナを含む | 328／1,012／2,133／18／0 |
| 配信先 | 有効3件、last_distributed_count は各 813、last_result は各 ok |

## 6. GAS 側（本番の写し）
- 写しどうしの比較
  - 本番の写しと `~/tcg-inventory-viewer-prod-1hc`（手順書でいう作業フォルダ）は、3ファイルとも差が0行。
  - 本番とテスト用：Code.js（テスト用では「コード.js」）と appsscript.json は差が0行。index.html は本番が 1398行、テスト用が 1467行で、差は CSS のデザイントークン化だけ。`<script>` 部分の差は0行。
  - `~/tcg-client-viewer/src`（コードの正本のリポジトリ）は旧版。Code.js の許可リストは10列で、Series が無い。
- 列の引き方：`<gas-prod>/Code.js:10-23` の許可リスト（12列。末尾が Series）。`:67-70` でヘッダー名を `indexOf` で引く。ヘッダーが無い列は -1 になり、空文字で続ける（:78,83）。返す列の順は許可リストの順（:94）。許可リストに無い列は返さない。
- 画面の列番号：`<gas-prod>/index.html:848-861` の `COL`（0〜11 の直書き。許可リストの順と一致している前提）。
- 検索：`<gas-prod>/index.html:699`（検索窓。プレースホルダは「商品名で検索（日本語・英語）」）、`:1187`（query を trim して小文字にする）、`:1204-1210`（日本語名・英語名・Mark の3列を `indexOf` で部分一致）。かなや全角・半角の吸収は無い。
- 24時間の絞り込み：`:816`（`FRESH_WINDOW_HOURS = 24`）、`:1196-1202`。
- データの取得：`:1016`（`google.script.run.getInventoryData()`）、`:1032-1034`（Sold out を除く）。
- 認証：Code.js の冒頭コメントでは ANYONE_ANONYMOUS（URL を知っていれば誰でも見られる）。
- 反映手順：`docs/handoff/dist-deploy-guard/gas-deploy-runbook.md`。作業フォルダで直す → テスト用に反映（PO の permit-danger チケットが毎回必要）→ 版を作る → 既存のデプロイ ID で版を差し替える → 画面で確認 → 本番で同じ手順。戻すときは前の版に差し替える。現在は本番が版12、テスト用が版14。

## 7. かなの正規化（既存の実装）
- SA：`backend/app/services/extraction_judgement_svc.py:17-26`（NFKC・小文字化・カタカナからひらがなへ）、`:32-40`（空白・記号を除く版）。
- GAS・frontend：既存の実装は無い。

## 8. 未確認
- 「在庫集計」タブを、SA と在庫一覧 GAS 以外（ほかの GAS・人の手作業・外部）が読んでいるか。
- clone した本番の写しが版12そのものか、リモートの HEAD か（手順書 `gas-deploy-runbook.md:73` は 1377行と記載。写しは 1398行）。
- products.search_keywords（221件）と検索ワード表の差の中身。
- 本番シートのヘッダー行そのもの（DB の配信記録と Code.js から推定しているだけ）。
