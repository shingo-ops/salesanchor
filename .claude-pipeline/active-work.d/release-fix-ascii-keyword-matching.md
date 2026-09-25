# release/fix-ascii-keyword-matching

## 概要
買取マッチャーの検索キーワード照合を `match_one_kw`（連続一致）から `match_product_search_keyword`（トークンAND照合）に差し替え。

## ステータス
PR作成済み・CI確認中

## 変更ファイル
- backend/app/services/buyback_scraper/product_matcher.py
- docs/handoff/fix-ascii-keyword-matching/recon.md
- docs/handoff/fix-ascii-keyword-matching/design.md
