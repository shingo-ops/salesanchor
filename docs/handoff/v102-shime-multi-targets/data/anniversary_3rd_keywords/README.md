# 3rd anniversary set の検索ワード1語・除外ワード4語の登録

## 目的
仕入元がカタカナで書く「3rd アニバーサリーセット」（日本語版）を、v102 の商品照合で 3rd anniversary set（440574・PM0227・ワンピース）に結びつける。英語版・中国版の投稿は同じ商品に入れない。
読む側: `backend/app/services/extraction_shadow_svc.py:86-106`（load_product_entries）→ `backend/app/services/gemini_raw_copy_v102_product_first.py`（照合。除外ワードに当たった商品は候補から外す）。

## PO 決定
2026-10-11「検索ワードと除外ワードを追加、"イングリッシュ"、"チャイナ"、"中国"、"英語"」（設計者経由）。
背景：商品マスタは日本語版の1件のみ。仕入元1社が 2026-09-25 に英語版（@65,000）・中国版（@40,000）を出していた。

## 登録内容
| 表 | product_id | position | keyword |
|---|---|---|---|
| product_search_keywords | 440574 | 2 | 3rd アニバーサリー |
| product_exclude_keywords | 440574 | 13 | イングリッシュ |
| product_exclude_keywords | 440574 | 14 | チャイナ |
| product_exclude_keywords | 440574 | 15 | 中国 |
| product_exclude_keywords | 440574 | 16 | 英語 |

## 登録前の比較（本番の全投稿 100,982 行、足す前と後。読み取りのみ・別コンテナ）
新しく商品が決まる行 12（すべて「3rd アニバーサリーセット」で次の行が「日本語版」）・別の商品に変わる行 0・決まらなくなる行 0。英語版・中国版の 4 行は「商品不明」のまま。行ごとの記録は社外秘のため repo に置かない。

## 手順（本番書き込みは commit.sql のみ）
1. `precheck.sql` — 検索 2 行・除外 12 行（1〜12）、足す語はどこにも無い、全件 2956 / 979、440574 は is_active
2. `dryrun.sql` — INSERT 0 1・INSERT 0 4、検索 3 行・除外 16 行が見えて ROLLBACK
3. `commit.sql` — 登録
4. `verify.sql` — 検索 3 語・除外 16 語、全件 2957 / 983

実行記録: 2026-10-11T00:44Z（UTC）に Opus が precheck（期待どおり）→ dryrun（INSERT 0 1・INSERT 0 4 → ROLLBACK）→ commit（INSERT 0 1・INSERT 0 4 → COMMIT、00:44:50Z）→ verify（検索 {3rd anniversary set, 3rd anniversary, 3rd アニバーサリー}、除外 16 語の末尾 4 語がイングリッシュ・チャイナ・中国・英語、全件 2957 / 983）。書き込みは PO 発行の permit-danger チケット（psql write）で実行。

## 戻し方
`rollback.sql` — 440574 の該当 5 行だけを DELETE（DELETE 1・DELETE 4 を確認して COMMIT）。

## 測り方
`verify.sql` の全件 = 2957 / 983。戻した後は 2956 / 979。
