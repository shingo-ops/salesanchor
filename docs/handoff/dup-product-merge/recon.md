# recon: 重複商品 3 組の統合（PM0226→DB-FB09、PM0224→YGO-LOCR、PM0223→YGO-LOCH）

実測時の origin/main SHA: 225c0c0ad292a13173a7b1bef5de8f484215faae
事実のみ。評価・提案は書かない。商品コードと商品名のみ（仕入元名・投稿本文は含まない）。

## §1 既存 ADR の検索
実行: `git grep -il -e "ADR-155" -- docs/adr`、`git grep -il -e "product master" -- docs/adr`、`git grep -il -e "商品マスタ" -- docs/adr`、`git grep -n -i -e "ADR-155" -e "product master" -e "商品マスタ" -- docs/adr/FEATURE-INDEX.md`（先行の recon と同じ origin/main の結果）

- "ADR-155" を含む: docs/adr/ADR-155-product-master-ssot-csv-app.md、docs/adr/ADR-156-product-classification-tree-and-master-separation.md、docs/adr/README.md
- "product master" を含む: 該当なし（0 件）
- "商品マスタ" を含む: docs/adr/ADR-014-inventory-management.md、docs/adr/ADR-015.md、docs/adr/ADR-093-inventory-table-product-master-redesign.md、docs/adr/ADR-099-sa-inventory-model.md、docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md、docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md、docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md、docs/adr/ADR-110-sa-translation-subsystem.md、docs/adr/ADR-129-audit-log-coverage-medium.md、docs/adr/ADR-145-public-products-force-rls.md、docs/adr/ADR-155-product-master-ssot-csv-app.md、docs/adr/ADR-156-product-classification-tree-and-master-separation.md、docs/adr/ADR-157-buyback-price-logger.md、docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md、docs/adr/FEATURE-INDEX.md、docs/adr/README.md
- docs/adr/FEATURE-INDEX.md:18: 「在庫 / inventory / 商品マスタ / 仕入元 / オファー | ADR-099 ／ ADR-093 ／ ADR-014」（ADR-155 の行はない）
- docs/adr/ADR-155-product-master-ssot-csv-app.md:25-26: 正規の更新手段は CSV 取り込みとアプリ画面。マイグレーションでの値の操作（INSERT / UPDATE / DELETE）は禁止。
- docs/adr/ADR-145-public-products-force-rls.md:55: `ALTER TABLE public.products FORCE ROW LEVEL SECURITY;`
- docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md と docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md: tcg_products を public.products に統一した経緯（重複が生じた原因。docs/handoff/product-duplicate-cleanup/design.md 参照）。
- 先行する同種の変更: docs/handoff/deckbuild-master-fix/（PR #3966）、docs/handoff/mega-dream-mark-fix/（PR #3968）、重複 203 件の整理 scripts/one-time/cleanup-product-duplicates.sql（commit c0e63f40e、docs/handoff/product-duplicate-cleanup/design.md）。

## §2 FK・索引・トリガ（本番の pg_constraint / pg_indexes / pg_trigger、2026-10-05 の読み取り）
- public.products(id) を参照する FK は 36 本。ON DELETE: public.inventory_movements は RESTRICT、public.buyback_shop_products / extraction_shadow_results / product_search_keywords / product_exclude_keywords / product_quantity_units は NO ACTION、テナントの invoice_items・purchase_order_items・quote_items は RESTRICT、テナントのキーワード表と products_logistics は CASCADE。ON UPDATE はすべて NO ACTION。
- 付け替える列を含む一意索引はなし: analysis_results は pkey(id) と analysis_results_extraction_item_id_key のみ、extraction_items は pkey のみ、buyback_shop_products は pkey と (shop_code, external_product_id)、product_search_keywords は pkey のみ。products の一意索引は pkey、uq_public_products_code（product_code）、uq_public_products_jan（jan_code）。
- トリガ: public.products の `trigger_set_updated_at_public_products`（BEFORE UPDATE、updated_at を更新）のみ。migrations/062_create_inventory_movements_and_budget.sql:71-80。他の表にはなし。
- 行レベルセキュリティ: public.products は有効かつ FORCE（書き込みに app.is_operator が必要。backend/app/services/tcg_product_detail_svc.py:170）。analysis_results・extraction_items・buyback_shop_products・product_search_keywords はなし。

## §3 アプリの商品更新・削除の経路
- backend/app/routers/tcg_product_import.py:294-307 `PUT /tcg/products/detail/{product_id}`: ProductDetailUpdate に is_active はない（ドロワーから無効化はできない）。
- backend/app/routers/tcg_product_import.py:401-455 `DELETE /tcg/products/detail/{product_id}`: analysis_results.product_id を NULL にしてから商品を削除。FK 違反なら 409 PRODUCT_IN_USE。docstring はキーワードの CASCADE と書くが、本番の public のキーワード表 FK は NO ACTION。
- backend/app/services/tcg_product_detail_svc.py:193-199 の audit_log 挿入（record_id は新規 uuid、old/new は TEXT の JSON）。
- 本番に is_active = false の商品が 11 件（id 22, 29, 64, 125073, 125074, 420423, 420425, 420433, 420434, 420491, 440536）。is_archived / archived_at は 0 件。設定した方法は 未確認。
- 先行する整理: scripts/one-time/cleanup-product-duplicates.sql（FK の付け替え → 削除、一回限りのスクリプトを ssh の標準入力で実行）。

## §4 is_current の規則（backend/app/services/tcg_analyzer_svc.py）
- :1711-1736 `_merge_supplier_products` の説明と、ジョブのチャネル取得。
- :1738-1749 ジョブの (product_id, condition_id) の組。
- :1759-1791 区画 = (チャネル, product_id, condition_id)、順序 `sm.received_at DESC, ar.computed_at DESC`、`pid_resolved = TRUE` かつ `product_id IS NOT NULL`、`touched_triples` との一致は `=`（NULL の condition_id は対象外）。
- :1565-1590 analysis_results の UPSERT（extraction_item_id が一意）。
- backend/app/services/item_corrections_svc.py:57-72 手動の商品修正が analysis_results.product_id を更新する（pid_basis = 'MANUAL'）。

## §5 参照している箇所（backend/app）
- analysis_results.product_id を読む: backend/app/services/tcg_analysis_review_svc.py:41,216,232,270、backend/app/services/tcg_distribution_svc.py:250、backend/app/services/tcg_unit_recovery_svc.py:276-285,792-800、backend/app/services/tcg_condition_review_svc.py:111,246、backend/app/services/tcg_sold_out_results_svc.py:51、backend/app/services/tcg_import_progress.py:128、backend/app/services/tcg_work_comparison_svc.py:220-256、backend/app/services/tcg_analyzer_svc.py:1738-1790。
- extraction_items.resolved_product_code: 書き込み backend/app/tasks/tcg_extraction.py:479-507、検証 backend/app/services/gemini_extraction_svc.py:856、読み取り backend/app/services/tcg_analyzer_svc.py:1261-1284（数字以外は :1277-1279 で拒否）と :1394、集計 backend/app/services/tcg_analysis_dashboard_svc.py:636-645。
- buyback_shop_products.product_id: backend/app/services/buyback_scraper/product_matcher.py:108-170 がキーワード照合で設定・解除する。表示は backend/app/routers/buyback_prices.py:269-339,486,596。
- 買取・価格ロガーのモジュールは analysis_results.product_id を読まない。
- product_code の文字列をリテラルで使うアプリのコードは 0 件（backend/app、frontend/src、scripts）。テストの backend/tests/test_tcg_keyword_matching.py:2790-2829 と、適用済みの migrations/20260902_110100_tcg_products_classification_ids.sql:313-316、migrations/20260903_180000_tcg_products_mark_en_t004.sql:288-291 に出る。

## §6 本番の値（2026-10-05、読み取り）
| id | code | mark | name | name_en | release_date | 中分類 | 商品区分 / category_class / メーカー | search_keywords（位置順） | created_at | updated_at |
|---|---|---|---|---|---|---|---|---|---|---|
| 226 | DB-FB09 | FB09 | DUAL EVOLUTION | Booster Pack -DUAL EVOLUTION- | 2026-03-14 | ドラゴンボール（id 3） | なし | DUAL EVOLUTION / FB09 / FB-09 | 2026-06-03T14:13:56Z | 2026-09-22T22:45:32Z |
| 440561 | PM0226 | FB09 | FB-09 | （空） | 2026-03-14 | ポケモンカード（id 1） | Box / Box / Bandai | FB-09 / FB09 / FB-09 | 2026-09-14T20:35:02Z | 2026-09-22T22:40:21Z |
| 625 | YGO-LOCR | LOCR | LIMIT OVER COLLECTION - THE RIVALS - | （空） | 2026-03-20 | 遊戯王 | なし | LIMIT OVER COLLECTION - THE RIVALS - / LOCR | 2026-06-03T23:37:24Z | 2026-09-22T22:40:21Z |
| 440572 | PM0224 | LOCR | LIMIT OVER COLLECTION THE RIVALS | （空） | 2026-03-20 | 遊戯王 | Box / Box / Konami | LIMIT OVER COLLECTION THE RIVALS / LOCR | 2026-09-14T20:35:02Z | 2026-10-02T11:34:44Z |
| 626 | YGO-LOCH | LOCH | LIMIT OVER COLLECTION - THE HEROES - | （空） | 2026-02-28 | 遊戯王 | なし | LIMIT OVER COLLECTION - THE HEROES - / LOCH | 2026-06-03T23:37:24Z | 2026-09-22T22:40:21Z |
| 440571 | PM0223 | LOCH | LIMIT OVER COLLECTION THE HEROES | （空） | 2026-02-28 | 遊戯王 | Box / Box / Konami | LIMIT OVER COLLECTION THE HEROES / LOCH | 2026-09-14T20:35:02Z | 2026-10-02T11:34:44Z |

6 行とも is_active = t。除外キーワードの行はなし。

参照している行数（本番の読み取り）:
- analysis_results.product_id: 226 = 46、440561 = 82、625 = 61、440572 = 53、626 = 26、440571 = 32
- extraction_items.resolved_product_code（id の文字列）: 226 = 89、440561 = 1、625 = 61、440572 = 6、626 = 23、440571 = 10。旧 code の文字列: DB-FB09 = 18、PM0226 = 3、YGO-LOCR = 18、PM0224 = 10、YGO-LOCH = 12、PM0223 = 4
- buyback_shop_products.product_id: 440572 = 1（他は 0）
- analysis_run_snapshots.product_id: 226 = 8、440561 = 33、625 = 3、440572 = 31、626 = 1、440571 = 16
- is_current: 退役側 28 / 10 / 7 行が current、残す側 18 / 16 / 14 行が current、両方 current の区画 9 / 7 / 5（規則で false にする行は 8 / 6 / 4）

## §7 T2 の証拠（v9 T2、3,066 ブロック、ローカルで実際の match_product）
- 現在の本番マスタ: matched 2,408 / ambiguous 357 / unmatched 301。曖昧のうち退役側と残す側の組が候補になるもの 23 ブロック（FB09 の組 16、LOCR 6、LOCH 1）。
- 退役 3 行を無効にしたマスタ: ambiguous → matched 23、退行 0、matched 2,431、自動確定 343 → 344。退役行に確定していたブロックはなし。

## §8 公式の根拠
- https://www.bandai.co.jp/catalog/item.php?jan_cd=4582769937064000: 「ドラゴンボールスーパーカードゲーム フュージョンワールド DUAL EVOLUTION [FB09]」 / 「発売時期：2026年3月14日発売」
- https://www.yugioh-card.com/japan/products/locr/: 「2026年3月20日(金･祝) 発売」
- https://www.yugioh-card.com/japan/products/loch/: 「2026年2月28日(土) 発売」
