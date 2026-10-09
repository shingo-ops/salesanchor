# recon: 商品マスタの二重登録10組の統合（merge 2、2026-10-05、読み取りのみ）

本番の読み取りは、すべて `BEGIN READ ONLY ... ROLLBACK` の中の SELECT。生の出力は社外秘のローカル作業メモ（リポジトリ外）にある。ここには集計値だけを書く。

## 1. 対象の10組（PO 決定 2026-10-05）
| 残す（survivor） | 退役（retired） | 公式上の同一商品の根拠 |
|---|---|---|
| 398 UA-PC02BT | 440573 PM0225 | https://www.unionarena-tcg.com/jp/products/boosters/pc_nik.php 「UNION ARENA プレシャスブースターパック 勝利の女神：NIKKE【PC02BT】」2026年2月13日(金) |
| 440434 PM0232 | 1386 LOR-the-first-chapter | https://www.takaratomy.co.jp/products/disneylorcana/product/the-first-chapter/booster-pack/ 2025年1月25日(土) |
| 440435 PM0233 | 1385 LOR-rise-of-the-floodborn | .../rise-of-the-floodborn/booster-pack/ 2025年3月22日(土) |
| 440578 PM0234 | 1384 LOR-into-the-inklands | .../into-the-inklands/booster-pack/ 2025年5月17日(土) |
| 440579 PM0235 | 1383 LOR-ursulas-return | .../ursulas-return/booster-pack/ 2025年7月12日(土) |
| 440580 PM0236 | 1382 LOR-shimmering-skies | .../shimmering-skies/booster-pack/ 2025年9月6日(土) |
| 440581 PM0237 | 1381 LOR-azurite-sea | .../azurite-sea/booster-pack/ 2025年10月31日(金) |
| 440582 PM0238 | 1380 LOR-archazias-island | .../archazias-island/booster-pack/ 2025年12月27日(土) |
| 440583 PM0239 | 1379 LOR-reign-of-jafar | .../reign-of-jafar/booster-pack/ 2026年2月21日(土) |
| 440587 PM0243 | 1376 LOR-wilds-unknown | .../wilds-unknown/booster-pack/ 2026年5月8日(金) |

公式ページには JAN も商品コードも出ていない。同一とみなした根拠は「名称と発売日の一致」。詳細は社外秘のローカル作業メモ（リポジトリ外）。

## 2. products の列（57列）
2行の違いは14〜15列。同じ値の列は省略。
- PM 行にあって LOR/UA 行にない: release_date（PC02BT・ARCHAZIAS は両方同じ）、division_id、manufacturer_id、product_category_id=1。
- LOR/UA 行にあって PM 行にない: category、set_type=booster。UA 行は unit_price=495.0。
- 名称: PM 行は日本語のみ、LOR 行は「英語＋日本語」。
- 検索の語: LOR 行は「英語＋日本語」1件。PM 行は日本語1件。UA-PC02BT は2件、PM0225 は検索2件＋除外3件（WS／ヴァイス／ヴァイスシュヴァルツ）。

## 3. 参照（読み取り 2026-10-05T03:16Z、全スキーマの product 名の列を走査）
| 退役 id | analysis_results | extraction_items（id の文字列） | buyback | shadow results |
|---|---|---|---|---|
| 440573 | 10 | 0 | 0 | 0 |
| 1386 | 11 | 14 | 0 | 0 |
| 1385 | 7 | 4 | 0 | 0 |
| 1384 | 8 | 8 | 0 | 0 |
| 1383 | 4 | 4 | 0 | 0 |
| 1382 | 18 | 22 | 0 | 0 |
| 1381 | 12 | 16 | 0 | 0 |
| 1380 | 4 | 4 | 0 | 0 |
| 1379 | 1 | 1 | 0 | 0 |
| 1376 | 0 | 0 | 0 | 0 |
| 合計 | 75 | 73 | 0 | 0 |

- 付け替えない履歴: analysis_run_snapshots、`_backup_20260924_*`、tcg_product_import_rows、extraction_items の旧 product_code 文字列（アナライザは数値以外を無視: backend/app/services/tcg_analyzer_svc.py:1273-1279）、extraction_attempts.parsed_items（13 id に言及あり、件数のみ確認）、extraction_jobs.work_reference_snapshot（1146 ジョブが20 id すべてを含む）。
- テナント表・inventory・FK を持つ他の表には、20 id の参照が 0 件。
- ids を含む文字列/JSON: pid_basis（1380・1382・1384 に各1）、shadow review_items（1376・1386・440434・440587 に各2）。付け替えない。

## 4. 制約・インデックス・トリガ（読み取り）
- analysis_results: 一意は extraction_item_id と id のみ。product_id の付け替えで衝突しない。
- extraction_shadow_results: 一意は (run_id, block_index) と id。product_id は無関係。
- product_search_keywords / product_exclude_keywords: 主キー id のみ（identity BY DEFAULT、sequence は最大 id と一致: 14176 / 1306）。(product_id, keyword) の一意制約はない。
- buyback_shop_products: 一意 (shop_code, external_product_id)。product_id の付け替えで衝突しない。
- products: トリガは updated_at の1つのみ。uq_public_products_code / uq_public_products_jan は不変（コード・JAN は変えない）。

## 5. is_current（アプリの規則: tcg_analyzer_svc.py:1759-1791）
残す側の id で再計算。flips to false の合計 9、flips to true は 0。
| survivor ← retired | 影響する区切り | false への変更 |
|---|---|---|
| 398 ← 440573 | 5 | 0 |
| 440434 ← 1386 | 1 | 1 |
| 440435 ← 1385 | 3 | 1 |
| 440578 ← 1384 | 4 | 2 |
| 440579 ← 1383 | 1 | 1 |
| 440580 ← 1382 | 3 | 2 |
| 440581 ← 1381 | 1 | 1 |
| 440582 ← 1380 | 2 | 1 |
| 440583 ← 1379 | 1 | 0 |
| 440587 ← 1376 | 0 | 0 |
- 同時刻の引き分け: 440435 ← 1385 の1区切りに、received_at・computed_at が完全に同じ退役側2行（現在 true が1、false が1）がある。アプリの規則は順序を決めていないため、SQL は `is_current DESC, id` で決める（今 true の行を残すので、この区切りは変更なし）。
- 規則の外にある行: 1385 の analysis_results 1行は pid_resolved=false。付け替えるが is_current は触らない。

## 6. キーワードの引き継ぎ（normalize_for_match で比較済み）
挿入する行（survivor の次の position）: PC02BT 用 検索1＋除外3、Lorcana 9組 各 検索1（退役側の「英語＋日本語」の語）。計 13行（検索10・除外3）。

## 7. v9 T2 のシミュレーション（手元・3066ブロック、基準は統合1回目の後）
- 実際の方向（UA-PC02BT を残す／PM 行を残す）＋キーワード引き継ぎ: 変化 0、悪化 0。
- 参考: PM 側を退役してキーワードを引き継がない案は、2ブロックが matched→unmatched になる（残す側に日本語のみの検索語がないため）。

## 8. シードの再実行との関係（migrations/20260604_010000_seed_product_marks.sql）
このマイグレーションは毎回のデプロイで再実行され、products.mark を名称の完全一致で UPDATE する。is_active・キーワード・analysis_results は触らない。20 id の名称・コード・mark のいずれも、このシード（154行）には現れない（部分一致も確認、「未知なる冒険」FB05 は別商品）。この統合は mark も名称も変えないので、再実行で元に戻らない。

## 9. 未確認
- 本番で、実行直前に件数が変わっていないか: precheck.sql の完全一致のガードで確認する。
- 公式の JAN: ページに記載なし。
