# recon: buyback-score-matching

## 対象ADR
- ADR-157: 買取商品マッチング自動化

## 既存実装の調査

### product_matcher.py（変更対象）
`backend/app/services/buyback_scraper/product_matcher.py:1-181`

変更前ロジック:
- `match_keyword()` を使用（最初の1ヒットで即確定）
- `backend/app/services/buyback_scraper/product_matcher.py:103`: `hit, matched_kw = match_keyword(product_name, kws, ex_kws)`
- 複数候補の場合は最長キーワード長でソートし一意なら auto

### tcg_analyzer_svc.py（依存関数）
`backend/app/services/tcg_analyzer_svc.py`

- `match_one_kw()`: 1つのキーワードと商品名をマッチング（bool返却）
- `normalize_en()`: 商品名の正規化

### buyback_shop_products テーブル
- `match_status`: unmatched / auto / pending_review
- `product_id`: 自動紐付けされたproducts.id
- `match_candidates`: JSONB（候補一覧）

## 変更方針
- `match_keyword()` → `score_product()` に置き換え
- 全キーワードを評価してスコア（文字数合計）を計算
- 除外ワードヒット = 即NG（score=-1で候補から除外）
- 最高スコア一意 → auto、同点複数 → pending_review
