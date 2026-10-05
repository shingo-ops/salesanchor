# recon: 商品コードを PM-00001 形式にそろえ、品番の照合を mark だけにする（ADR-1006、2026-10-05、読み取りのみ）

基準: origin/main a3438193795d26059dca4c7051a7fcc204df9a10。本番の読み取りは `BEGIN READ ONLY` の中の SELECT。生の出力・集計は「社外秘のローカル作業メモ（リポジトリ外）」にあり、ここには集計値と file:line だけを書く。行番号は、先行する PR が入ると動く（編集前に再検索する）。

## 0. 着手前の ADR 検索（`git grep -il product_code docs/adr`、docs/adr/FEATURE-INDEX.md）
- docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md:14, :45, :149（PM0001〜PM0297、`public.products.product_code ← tcg_products.code`、`ON CONFLICT (product_code)`）
- docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md:15, :28, :33, :88-100, :158（採番は `'PM' || lpad(nextval(...), 4, '0')`、受入条件「SEQUENCE で自動採番」）。ADR-1006 はこの §4 を変更する（Amends）。
- docs/adr/ADR-155-product-master-ssot-csv-app.md:21, :26-31（mark = 型番。マイグレーションは構造変更のみ、値の操作は禁止）
- 商品 ID 形式の一般則を定めた ADR は他にない（`git grep -i "PM0\|接頭辞\|連番\|product_code" docs/adr docs/specs` の 121 行は別件）。

## 1. 本番の product_code（2026-10-05）
- 1347 行（有効 1333、無効 14）。最大 id 458213。product_code が NULL の行 12。形はそろっていない（SV7、DB-FB09、YGO-LOCR、PM0198、UA-PC02BT など）。
- public.product_code_seq: start 298、last_value NULL（一度も使っていない）。products.product_code は varchar(50)、DEFAULT なし、CHECK なし。
- 制約: products の主キー1つと外部キー10。product_code の一意は部分一意インデックス `uq_public_products_code`（`WHERE product_code IS NOT NULL`）のみ。mark にインデックスなし。
- トリガ: `trigger_set_updated_at_public_products`（BEFORE UPDATE）。全行を更新すると 1347 行の updated_at が変わる。
- products の列に旧コード用の列はない。product_code を参照するビュー・関数は 0。
- 有効な商品 1333 のうち: code = mark が 160、code <> mark が 1134、mark が空が 27（PM 16、その他 13 のうち 2 は code も NULL）、code が NULL が 12。

## 2. product_code を読む・使う場所（file:line）
### 2a. v6 の品番の関門: backend/app/services/tcg_analyzer_svc.py
- :1209-1215 `legacy_code_rows`（`SELECT product_code, id FROM public.products WHERE is_active = TRUE AND product_code IS NOT NULL`）と `product_code_to_id`。`product_code_to_id` の使用は :1213, :1215, :1224 だけ。
- :1219-1224 `mark_rows`（`SELECT mark, id FROM public.products WHERE is_active = TRUE AND mark IS NOT NULL AND mark <> ''`）を `rawcode_to_id` にし、`rawcode_to_id.update(product_code_to_id)` で product_code が mark に勝つ。**ORDER BY がない**ので、mark が重なると最後に返った行（ヒープ順）が勝つ。
- :1427-1434 `_rawcode = (ei_raw_product_code or "").strip()`、`rawcode_to_id.get(_rawcode)`（正規化なし、文字列そのまま）、`_rawcode_valid`。使う分岐: :1436（RAWCODE_OVERRIDE）、:1446（RAWCODE）、:1448-1471（除外語の検査、RAWCODE_EXCLUDED）。basis の文字列は analysis_results に保存され、ダッシュボードが読む。
- `product_code_to_uuid`（名前は紛らわしいが、キーは `str(products.id)`）: load_lookup_maps :85。:1206, :1503。PM の変更の影響を受けない。
- 保存済みジョブの再解析: :1262-1265 `Work reference changed; re-extraction required`（参照のダイジェストが変わると止まる。マスタを 1 件変えれば起きる）。

### 2b. v7: backend/app/services/extraction_judgement_svc.py
- :108-115 `ProductEntry(id, product_code, mark, work_id, search_keywords, exclude_keywords)`。
- :141-149 `_code_candidate_basis`: `for raw in (product.product_code, product.mark): if raw and _value_hits(raw, nb, folded): return "RAWCODE"`。境界の条件（`_needs_boundary`）は 2 文字以下または数字だけの値にだけ働く。3 文字以上の値は語の途中でも一致する。
- 読み込み（同じ SELECT が 2 か所）: backend/app/services/extraction_shadow_svc.py:86-114（:94 SELECT、:107 `product_code=r[1]`）、backend/app/services/tcg_shadow_review_svc.py:201-224（:204, :217）と :250-262（:251, :258、検索語のプレビュー）。
- テストが `ProductEntry(product_code=...)` を作る: backend/tests/test_extraction_judgement_svc.py:105-120, backend/tests/test_extraction_shadow_svc.py:19-21, backend/tests/test_tcg_shadow_review_svc.py:135。
- backend/tests/test_extraction_judgement_svc.py:168-178 `test_matches_by_product_code`（OP-01 → RAWCODE。mark のみにするなら書き換えが必要）と :562-615 の境界のテスト（`product_code="151"` / `"ONP01"`）。v6 の関門を端から端まで通すテストは grep で見つからない（backend/tests/test_tcg_shadow_accuracy_pg.py:58-61 は信号の部品のみ）。

### 2c. コードの採番と、products への INSERT
- backend/app/services/tcg_product_master_svc.py:28 `_PM_CODE_RE = ^PM(\d{4})$`、:290-321 `_next_pm_code`（`nextval('public.product_code_seq')` → `f"PM{num:04d}"`、例外では `db.rollback()` して `^PM[0-9]{4}$` の最大 + 1。9999 超で PRODUCT_MASTER_V2_PM_CODE_EXHAUSTED）。呼び出しは :371 の `create_product` だけ。INSERT は :391-400（:403 `code`）。テストの差し替え: backend/tests/test_tcg_product_import.py:359。
- **2つ目の採番**（ADR の草案にはなかった）: backend/app/routers/products.py:379 の INSERT のあと :407-410 で `f"PD-{new_id:05d}"` を UPDATE する（POST /products）。CHECK `^PM-[0-9]{5}$` を入れるとこの API が失敗する。backend/tests/test_products.py:40 は `startswith("PD-")`。SQLite のテスト用表 backend/tests/conftest.py:798 には DEFAULT がなく nextval も使えない。
- スクリプト: scripts/seed_products_from_master.py:5, :13, :134, :179-202（mark を product_code に入れ、`ON CONFLICT (product_code)`）、scripts/seed_inventory_from_output.py:181-185（`{product_code: id}` の表を作る。振り直すと黙って壊れる）、scripts/qa/seed-tenant.sql:191（tenant_006、別の表）、scripts/one-time/cleanup-product-duplicates.sql（一度きり）。
- マイグレーション（デプロイのたびに scripts/run_all_migrations.sh が全部を再実行する。同:12-15）: migrations/20260602_010000 の :86、20260909_000000 の :104、20260914_140000 の :180/:216/:251（`ON CONFLICT (product_code)`、tcg_uuid が UUID でなければ読み飛ばす :96-121）。20260915_120000 の :424-443 は product_code_seq を存在しないときだけ作る。seed 系（20260603/20260604_040000/20260615/20260913_01〜03）は `RAISE NOTICE 'ADR-155 neutralized...'` で無効化済み。[未確認] 振り直し後に 20260909/20260914 の再実行が何も変えないか（tcg_uuid の有無を本番で見る必要がある）。

### 2d. 表示・並べ替えだけで読む場所（値が PM-xxxxx になるだけ）
backend/app/routers/buyback_prices.py:10,73,264,362,481,552,591（:552 は ORDER BY）、backend/app/routers/inventory_offers.py:54,380、backend/app/services/inventory_search.py:89,333,428、backend/app/routers/products.py:131,193、backend/app/tasks/reports.py:127、backend/app/services/buyback_scraper/product_matcher.py:59-81,129（ORDER BY p.product_code）、backend/app/services/tcg_product_detail_svc.py:74-75、backend/app/services/tcg_product_roundtrip_svc.py:97,145,368-377。CSV の往復の `revision()`（同:100-107）は snapshot["product"]（product_code を含む）のハッシュなので、振り直す前に書き出した CSV はすべて ROUNDTRIP_STALE になる。
フロント: frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:16,224、frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:162-168、BuybackPendingReviewModal.tsx:152、frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:152。ja.json・en.json（:384, :1741）に形式を埋め込んだ文字列はない。

### 2e. 別物（変更の対象外）
Gemini の出力列（`resolved_product_code` / `raw_product_code`: backend/app/services/gemini_extraction_svc.py:672-673,856-857、backend/app/tasks/tcg_extraction.py:135,479-508、backend/app/services/tcg_work_reference.py:15-74）。`str(id) AS product_code` の別名: backend/app/services/tcg_analysis_review_svc.py:214,270、backend/app/services/tcg_unit_recovery_svc.py:279,302,356,695。テナントの表: backend/app/services/tenant.py:719,748。

### 2f. product_code の値を text として保存している列（本番の件数）
extraction_items.resolved_product_code 20703（うち現在のコードと等しいもの 5493、残りは数値の id。アナライザは数値以外を無視: backend/app/services/tcg_analyzer_svc.py:1273-1279）、raw_product_code 5759（4335）、_backup_20260924_extraction_items 1507（327）、tcg_product_import_rows.product_code 297（83）、analysis_results.pid_basis 30095（全体一致 0。旧コードを文字列の中に持つもの 787、`ID:<n>` 形式 1200）、tcg_series_master.series_code 56（49）、product_lines.code 10（1）。履歴の列は変えない。

## 3. mark と code: 照合に使われている実態（読み取り・手元のシミュレーション）
- 本番の raw_product_code（5759 行、260 種類）: product_code と mark の両方に等しい 4267 行、mark だけに等しい 1420 行、**product_code だけに等しい 0 行**、どちらにも等しくない 72 行。
- v9 の T2（100 件の投稿、3066 ブロック）で、投稿に出る code の語を持つ商品は 101、すべて code = mark の商品。code <> mark の 1134 商品では 0。
- 有効な商品の間で、2 つ以上が同じ mark を持つ文字列は 34 組（99 商品）。そのうち product_code がその文字列と等しい商品がある mark は 5（PCJ、SVI、SV2a、PROMO、ARCHRD。PROMO と ARCHRD の持ち主は同じ mark の商品ではない）。残る 29 組は、今も返る商品が Postgres の行の順で決まる（決定的でない）。
- v7 の mark のみのシミュレーション（T2、全 product_code を重複しない PM-%05d に置換）: 変化 5 ブロック、すべて ambiguous → matched、悪化 0。5 ブロックはどれも「■PRB02 ONE PIECE CARD THE BEST vol.2」の行で、今は候補が 39（PRB-02）と 199（code ARD、mark が空）になる。ARD が正規化後の「card」の中に境界の検査なしで一致するため。
- v6 の再解析の差（本番の集計。v6 のジョブ 10716 件のうち raw_product_code ありが 5973）: 共有された mark の行 272（GEMINI 146、RAWCODE_OVERRIDE 103、RAWCODE 7、GEMINI_EXCLUDED 5、analysis_results なし 11）。新しい規則での変化は、RAWCODE_OVERRIDE の 103 行（Gemini 自身の id に戻る。内訳は ST01 36、M3 23、SP 23、PROMO 10、azurite-sea 3、shimmering-skies 3、the-first-chapter 2、SV-P 2、SVD 1）と、Gemini が空で検索語に回る 7 行（ST01 6、SV2a 1）。**SV2a の 76 行は Gemini の id が関門と同じなので変化しない**（ADR の当初の想定とは違う）。Gemini と今の関門のどちらが正しいかは投稿の本文を見ないと決められない（未確認）。
- 検索語に回る 7 行の結果と、GEMINI_EXCLUDED の 5 行の基準の後ろの部分: 未確認（本文のエクスポートが拒否されたため再現していない）。

## 4. 店頭の GAS（~/crm-app-current、読み取り）
- PM 形式のリテラル: src/99_InvBookRecon.js（129 か所、例 :1544 `TARGET_IDS = ['PM0093', 'PM0175', 'PM0165', ...]`、:1712 `res.pmId === 'PM0165'`）。.claspignore:18 に載っており反映されない。src/99_DevImportrangeSurvey.js:494, :575（`['PM0232', 'PM0233', 'PM0234']`、調査用の関数。DEV のデプロイ対象）。
- 実際に動く結合は product_id の文字列そのもの: src/28_CoreInventoryOptionApi.js:27-50（共用在庫の product_id と数量 > 0 を、商品マスタ同期の product_id と結合して日本語名を取る）、src/28_SharedInventoryReadApi.js:18,81,177、src/00_CoreSchemaRegistry.js:123（商品マスタ同期、書き込み不可）, :162-178（共用在庫、product_id は主キーではない）、src/28_CoreQuoteApi.js:664。PM 形式の検査はコードにない。
- 商品マスタ同期・共用在庫・集計同期・SCM出力同期は IMPORTRANGE のシート（src/99_DevImportrangeSurvey.js:1-12）。店頭の商品台帳の product_id は PM 形式の値で、シート側で人が入れる（src/99_InvBookRecon.js:2424, :2563-2636）。DB の product_code を店頭シートの product_id へ写す仕組みは見つからない（未確認）。
- backend/app/tasks/tcg_mirror.py:109-124, :139, :149 が書く別のスプレッドシートの product_id は `p.id::text`（整数の id）で、product_code ではない。商品マスタ同期にも書かない。
- ローカルのコピーは origin より 4 コミット遅れている（未確認）。

## 5. マイグレーションの制約（実装の前提）
- scripts/run_all_migrations.sh は `set -e` で全マイグレーションを毎回再実行する（:12-15, :61-66）。末尾の最新は `run_sql migrations/20261003_100000_create_app_fx_rate_history.sql`。
- .github/workflows/migration-guard.yml: ファイル名 `^[0-9]{8}_[0-9]{6}_.*\.sql$`（:95-117）、登録（:119-169）、`{schema}` 禁止（:171）、タイムスタンプの重複禁止（:287）、DROP には PR 本文に ADR 番号（:343-393）、**Check 7（:394-493）が products などへの INSERT/UPDATE/DELETE を禁止**、**Check 8（:485-593）が products を含む行を、構造変更（CREATE/ALTER/DROP TABLE、CREATE INDEX、ADD/DROP/ALTER COLUMN、COMMENT ON、information_schema など）以外では禁止**。したがって、振り直しの UPDATE はマイグレーションにできない。列の追加・DEFAULT・CHECK・一意インデックスは構造変更として書ける。
- docs/adr/ADR-155-product-master-ssot-csv-app.md:26「マイグレーションは商品マスタ関連テーブルの構造変更にのみ使用する。値の操作（INSERT / UPDATE / DELETE）は禁止する」。backend/CLAUDE.md:46-56（追加のみ・冪等・タイムスタンプ命名・登録・既存と新規テナントの適用経路を PR 本文に書く）。
- ADR を追加・変更したときの手順: docs/ai-agents/lessons.d/20260902-data-durability.md:41-44（`node scripts/generate-adr-index.js`、docs/adr/README.md をコミット、PR 本文の触るファイルに docs/adr/README.md を書く）。CI「ADR index is up to date」。

## 6. 2026-10-05 02:38:41Z に mark が元に戻った件（440559、M2a → M3）
- 本番の 440559 は mark M3（目標は M2a。audit_log id 27 で M2a に適用済みだった）。デッキビルドの 6 行と統合 3 行は目標どおり。
- 02:38:41 の 1 秒間に products が 110 行更新された（updated_at が同一）。audit_log に対応する行はない（アプリを通らない直接 SQL、つまりマイグレーション）。同じ時刻帯に main への Deploy to VPS が 2 本（run 37256103838、run 37256155526）あり、どちらも 02:38:41 を含む。どちらが書いたかは未確認。
- 原因（ファイルから）: migrations/20260604_010000_seed_product_marks.sql（scripts/run_all_migrations.sh:264 に登録。毎回のデプロイで再実行）が、:23-25 で `UPDATE public.products p SET mark = v.mark, updated_at = NOW() FROM (VALUES ...) AS v(name, mark) WHERE p.tenant_id IS NULL AND p.name = v.name`、:36 で `('MEGAドリームex', 'M3')`。125 組の (名称, mark)。`updated_at = NOW()` が 110 行の同時刻を説明する。migration-guard の Check 7 は新しい PR のマイグレーションだけを見るので、この古い UPDATE は止まらない。
- 手元のコピー（M2a 修正後、有効 1333）で、シードの名称に一致する行は 109。mark が異なるのは 440559 の 1 行だけ。ほかの行は同じ値を書き直す。本番の 110 と手元の 109 の差 1 行は未確認。
- 同じ仕組みでほかの修正が戻るか: デッキビルドの 58/74/103 は同じ mark（SV9/SV7/SV3）を書く。60/75/105 の名称はシードの名称と一致しない。統合の退役行の is_active、キーワードの表はシードが触らない。次のデプロイでも 440559 は M3 に戻る（この PR は直さない。ADR-1006 の範囲外）。
- [未確認] migrations/20260902_110100 と migrations/20260903_180000 にある ('PM0198','M3',...) が今も public.products に対して動くか。

## 7. 未確認の一覧
- 検索語に回る 7 行と GEMINI_EXCLUDED の 5 行の結果（投稿の本文が要る）。
- 振り直し後の migrations/20260909_000000・20260914_140000 の再実行が何も変えないか（tcg_uuid の有無）。
- デプロイで、マイグレーションがバックエンドのコンテナの入れ替えの前か後か（.github/workflows/deploy.yml:514 の前後関係）。
- 店頭シートの product_id が DB の product_code とどう対応づけられているか（コードでは見つからない）。
- CSV 往復の revision が updated_at を含むか。
