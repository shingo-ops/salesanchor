# Recon: 買取マッチャーが旧関数を使用している問題

## 問題
`backend/app/services/buyback_scraper/product_matcher.py` の `score_product` が検索キーワード照合に `match_one_kw`（連続文字列一致）を使用。
同リポジトリ内の `match_product_search_keyword`（トークンAND単語境界照合）が正しい関数だが未使用。

## エビデンス
- `backend/app/services/buyback_scraper/product_matcher.py:19`: `from ... import match_one_kw`
- `backend/app/services/buyback_scraper/product_matcher.py:48`: 検索チェックに `match_one_kw` 使用
- `backend/app/services/tcg_analyzer_svc.py:528`: `match_product_search_keyword` が正しいトークンAND照合を実装済み
- `backend/app/services/tcg_analyzer_svc.py:570`: `match_pid_with_work` が search=`match_product_search_keyword` / exclude=`match_one_kw` の正しいパターンで使用中
- 本番DB（2026-09-25）: 未紐付け140件中、キーワード登録済みだがマッチ失敗あり（FUTURISTIC BOX等）
- テスト `test_product_all_terms_boundaries`: `match_product_search_keyword` で "30th FUTURISTIC" → "30th CELEBRATION FUTURISTIC BOX" は既にPASS

## ADR
- ADR-157: 買取相場機能
