# 重複商品 3 組の統合（PM0226→DB-FB09、PM0224→YGO-LOCR、PM0223→YGO-LOCH）

状態: 本番に適用済み（2026-10-05 02:03:16Z）。実行記録は末尾。product code・商品名のみ記載（仕入元名・投稿本文は含まない）。

## PO の決定（チーム長経由で受領した引用）
- 統合する側: 残す行 = id 226（DB-FB09）、625（YGO-LOCR）、626（YGO-LOCH）。退役させる行 = id 440561（PM0226）、440572（PM0224）、440571（PM0223）。
- 統合用 SQL とその件数への承認: 「はい」（autoMode.allow「Duplicate product merge by direct SQL」が追加済み）。
- 実行は、PO が「psql write」の許可チケットを 2 回発行（各 1 回限り）した後に行った。詳細は末尾の実行記録。

## 公式の根拠（公式サイトのみ。引用は取得ツールが返した文面）
- FB09: https://www.bandai.co.jp/catalog/item.php?jan_cd=4582769937064000
  - 商品名 「ドラゴンボールスーパーカードゲーム フュージョンワールド DUAL EVOLUTION [FB09]」 / 「発売時期：2026年3月14日発売」。
- FB09（グローバル公式サイト）: https://www.dbs-cardgame.com/fw/en/products/02_230.html — "BOOSTER PACK -DUAL EVOLUTION- [FB09]" / "March 13, 2026"（日本の発売日は上のバンダイの 2026-03-14）。
- LOCR: https://www.yugioh-card.com/japan/products/locr/ — 「遊戯王OCGデュエルモンスターズ LIMIT OVER COLLECTION - THE RIVALS -」 / 「2026年3月20日(金･祝) 発売」。
- LOCR（公式カードデータベース）: https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=1&sess=1&pid=1000009564000&rp=99999&request_locale=ja — 「LIMIT OVER COLLECTION －THE RIVALS－」、「公開日 : 2026年03月20日」。
- LOCH: https://www.yugioh-card.com/japan/products/loch/ — 「遊戯王OCGデュエルモンスターズ LIMIT OVER COLLECTION - THE HEROES -」 / 「2026年2月28日(土) 発売」。
- LOCH（公式カードデータベース）: https://www.db.yugioh-card.com/yugiohdb/card_search.action?ope=1&pid=1000009563000&rp=99999&request_locale=ja — 「LIMIT OVER COLLECTION －THE HEROES－」、「公開日：2026年02月28日」。
- 略称 LOCR / LOCH は公式 URL のパスにのみ現れ、ページ本文中の文字としては 未確認。FB09 の日本語公式ページ（dbs-cardgame.com/fw/products/02_230.html）は 404 で 未確認。
- 本番の値との一致: 3 組とも、発売日・mark は 2 行とも公式と一致（FB09 は 2026-03-14、LOCR は 2026-03-20、LOCH は 2026-02-28）。各組は同一の商品。
- 元データ（ローカル）: /tmp/CC報告ファイル/system-accuracy-v9/product-check/item1_official_check.md

## 行の比較の要約（products の 57 列、本番の読み取り 2026-10-05）
- DB-FB09（226）と PM0226（440561）: 20 列が違う。code、name（「DUAL EVOLUTION」と「FB-09」）、name_en（ある／null）、created_at・updated_at、type_master_id（3 = ドラゴンボール／1 = ポケモンカード）、product_category_id・category_class・manufacturer_id・division_id（PM 側にだけ入っている）、価格・入数・set_type（226 側にだけ入っている）、旧形式のキーワード列。mark FB09、release_date 2026-03-14、work_id、image_url、分類（大・小・細）は同じ。
- YGO-LOCR（625）と PM0224（440572）、YGO-LOCH（626）と PM0223（440571）: 各 14 列が違う。code、name（ハイフンの有無のみ）、created_at・updated_at、product_category_id・category_class・manufacturer_id・division_id（PM 側にだけ入っている）、unit_price・set_type（YGO 側にだけ入っている）。mark、release_date、work_id、type_master_id、キーワードは同じ。
- 同じ work の他の商品（DB-FB08〜12、YGO-*）は product_category・category_class・manufacturer・division が空。値が入っているのは PM 側の行と YGO の 1 行のみ。

## 参照している表と件数（本番の読み取り 2026-10-05。保証は apply.sql 内の件数ガード）
| 表.列 | 440561 → 226 | 440572 → 625 | 440571 → 626 | 扱い |
|---|---|---|---|---|
| public.analysis_results.product_id | 82 | 53 | 32 | 付け替え |
| public.analysis_results.is_current の再計算で false になる行 | 8 | 6 | 4 | 付け替え後に再計算 |
| public.extraction_items.resolved_product_code（id の文字列） | 1 | 6 | 10 | 付け替え |
| public.buyback_shop_products.product_id | 0 | 1 | 0 | 付け替え |
| public.products.is_active | 1 行 | 1 行 | 1 行 | false にする（キーワード行は残す） |
| public.analysis_run_snapshots / _backup_* / extraction_attempts / pid_basis / review_items | 33 / 31 / 16 ほか | | | 履歴のため変更しない |
| extraction_items の旧 code 文字列（PM0226 / PM0224 / PM0223） | 3 | 10 | 4 | 変更しない（アナライザは数字以外を拒否: tcg_analyzer_svc.py:1277-1279） |
| テナント表、inventory 系、extraction_shadow_results.product_id | 0 | 0 | 0 | なし |

- 一意制約・索引の衝突: 付け替える列を含む一意索引はなし（analysis_results は extraction_item_id のみ、buyback_shop_products は (shop_code, external_product_id)）。
- トリガ: public.products の updated_at トリガ 1 本のみ（migrations/062_create_inventory_movements_and_budget.sql:71-80）。他の表にはなし。

## is_current の規則（backend/app/services/tcg_analyzer_svc.py:1759-1791）
- (仕入元チャネル, 商品, 状態) の区画ごとに、`sm.received_at DESC, ar.computed_at DESC` の先頭 1 行だけを is_current = TRUE にする（同順位の決め方は他になし）。
- 対象は `pid_resolved = TRUE` かつ `product_id IS NOT NULL` の行。状態の一致は `=` なので、状態が NULL の行は触らない。
- 付け替えで退役側と残す側がどちらも current の区画が生じる（本番で 21 区画）。この規則どおりに再計算すると、false にする行は 18 行（226: 8、625: 6、626: 4）、true にする行は 0、同順位は 0。残り 3 区画は規則の対象外の行（pid_resolved が false など）を含み、そのまま。

## シミュレーション（ローカル、v9 T2 3,066 ブロック、実際の match_product）
- 退役する 3 行を無効にした本番相当のマスタで: ambiguous → matched が 23（DB-FB09 に 16、YGO-LOCR に 6、YGO-LOCH に 1）。退行 0（退役行に確定していたブロックはなく、matched → 非 matched / 別商品の変化なし）。
- matched 2,408 → 2,431、自動確定 343 → 344。

## 戻し方
- apply.sql は、商品ごとの audit_log 行の new_values（JSON、`merge` キー、merge_id = dup-merge-20261005）に、付け替えた全行の id と、is_current を変えた行の id・元の値・元の updated_at を残す。
- rollback.sql はその行だけを元に戻す（product_id、is_current と updated_at、resolved_product_code、buyback の product_id、is_active）。件数が違えば RAISE して全体が戻る。すでに戻した audit 行は対象外。
- ローカルの使い捨て DB（乱数のデータ）で、precheck → dryrun（変化なし）→ apply → postcheck → rollback を通し、audit_log 以外の表が元と完全に一致することを確認した。apply と rollback の 2 往復も確認した。
- 実行には新たな PO の判断が必要。

## 手順（この順。各ステップを実行し、結果を確認してから次へ）
1. precheck: `precheck.sql`（読み取り専用）。6 商品と件数が想定どおりでなければ RAISE して止まる。
2. dryrun: `dryrun.sql`（apply と同一処理 → 最終状態を SELECT → ROLLBACK）。
3. apply: `apply.sql`（1 トランザクション、末尾 COMMIT）。
4. postcheck: `postcheck.sql`（読み取り専用）。退役 3 行が無効、参照が 0、保存した id が残す側にあること、is_current の変更が反映されていることを確認。
- 件数は本番で動く値。分析が走って件数が変わると apply.sql のガードが RAISE する。その場合は gen_sql.py の仕様表を直して再生成する。
- 作業参照のダイジェストが変わるため、保存済み v5 以降ジョブの再解析は `Work reference changed; re-extraction required` になる（商品マスタを 1 件でも変えれば起きる既存の挙動）。

## ファイル
README.md / recon.md / design.md / gen_sql.py / precheck.sql / dryrun.sql / apply.sql / rollback.sql / postcheck.sql / logs/（dryrun.log, apply.log, postcheck.log）

## 実行記録（2026-10-05、PO 承認済みの本番データ変更）
許可: PO が「psql write」チケットを 2 回発行（各 1 回限り）。1 回目 2026-10-05T01:53:17Z（dryrun 用）、2 回目 2026-10-05T02:02:55Z（apply 用）。

| 順 | 内容 | 実行時刻 (UTC) | ファイル sha256 | 結果 |
|---|---|---|---|---|
| 1 | dryrun（最後は ROLLBACK） | 2026-10-05 01:53:35 | 1ee1e7bbb580d2f528e9c1d4c1a0a8ef312788add7585eb4d146358210862553 | 成功。何も保持されない。ログ: logs/dryrun.log |
| 2 | apply（COMMIT） | 2026-10-05 02:03:16 | e88746e72108d1727c4ba9216a938db5ebd6b9003da4b6bccb1ea48823aeea15 | 成功。COMMIT。ログ: logs/apply.log |
| 3 | 実行後の確認（読み取り専用の SELECT 3 本） | 2026-10-05 02:04 頃 | （ファイルは使わず、クエリ文をログ先頭に記載） | 想定どおり。ログ: logs/postcheck.log |

- 差分: dryrun.sql と apply.sql の違いは、先頭 2 行のコメントと最終行（ROLLBACK → COMMIT）のみ（diff で確認）。
- 件数（apply）:
  - analysis_results.product_id の付け替え: 82 / 53 / 32（440561 → 226 / 440572 → 625 / 440571 → 626）
  - is_current を false にした行: 8 / 6 / 4（true にした行は 0）
  - extraction_items.resolved_product_code の付け替え: 1 / 6 / 10
  - buyback_shop_products.product_id の付け替え: 0 / 1 / 0
  - products.is_active を false にした行: 各 1（440561、440572、440571）。キーワード行は残した。
  - audit_log: 3 行（id 31〜33、changed_by = 'claude-opus (PO承認 2026-10-05)'、changed_at = 2026-10-05 02:03:16.717601+00、new_values に merge_id = dup-merge-20261005 と付け替えた全行の id を保存）
- 実行後の確認:
  - 退役 3 行（440561、440571、440572）は is_active = f で、analysis_results・extraction_items・buyback_shop_products の参照はすべて 0。キーワード行は 3 / 2 / 2 のまま。
  - 残す 3 行（226、625、626）は is_active = t。analysis_results は 128 / 114 / 58、extraction_items は 90 / 67 / 33、buyback_shop_products は 0 / 1 / 0。
  - 残す 3 行の pid_resolved の行について、(チャネル, 状態) の区画は 26 / 15 / 12。すべての区画で is_current = true の行がちょうど 1 行。2 行以上の区画は 0。
- precheck.sql と postcheck.sql はファイルとしては実行していない（dryrun の中のガードで現在値と件数の一致を確認し、実行後は上記の SELECT で確認した）。
- rollback.sql は実行していない。実行するには新たな PO の判断が必要。
- 変更していないもの: analysis_run_snapshots、_backup_* の表、extraction_attempts、pid_basis の文字列、review_items、extraction_items の旧 code 文字列。
- 未確認: Gemini の選択が変わるか。保存済みジョブの再解析は、作業参照のダイジェスト変更により再抽出が必要（上記の手順の節のとおり）。
