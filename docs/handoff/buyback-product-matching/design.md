# Design: buyback-product-matching

## recon参照
- `docs/handoff/buyback-product-matching/recon.md`

## KGI / KPI
| 基準 | 検証方法 |
|------|---------|
| 買取460件のうち318件以上（69%）が自動紐付け | POST /rematch 後のDB集計 |
| 複数候補3件が pending_review として管理画面に表示 | GET /pending-reviews の件数 |
| 紐付き商品の一覧に product_code / product_name_ja が表示 | 画面目視 |

## マッチングロジック
```
買取商品名 → normalize_en() → match_keyword(search_kw, exclude_kw)
├─ 1件マッチ → auto（product_id書込み）
├─ 複数候補（最長KW一意）→ auto
├─ 複数候補（同長複数）→ pending_review（人間確認）
└─ 0件 → unmatched
```

## 守り手
- `backend/app/services/buyback_scraper/product_matcher.py` — マッチングロジック
- `backend/app/routers/buyback_prices.py` — API エンドポイント
- `frontend/src/pages/buyback-prices/BuybackPendingReviewModal.tsx` — 確認UI

## 外部・過去事例の参照と我々への応用
- 自社既存ロジック `tcg_analyzer_svc.match_keyword()` の横展開。同一アルゴリズムを LINE解析パイプラインで運用中（精度: parity02測定済み）。新規外部事例は不要。

## 維持の仕組み
- `product_matcher.py` は `tcg_analyzer_svc` に依存するため、KW辞書追加・正規化ロジック変更時は自動的に買取マッチングにも反映される
- `match_status` の値（auto/pending_review/unmatched）はDB制約で列挙管理
- 管理画面の pending_review モーダルにより人間によるフォールバックを確保
