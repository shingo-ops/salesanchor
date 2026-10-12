# recon: fix-buyback-chart-stocklike

## 既存ADR確認
- ADR-157: 買取相場ログ — 本修正の根拠ADR

## 現状把握

### Fix 1: diff-only INSERT ガード
- `backend/app/services/buyback_scraper/base.py:99-127` — 前回ログ取得→差分比較→条件付きINSERT
- 問題: 価格が変化しない日はログが記録されず、チャートに時系列データが蓄積しない

### Fix 2: ORDER BY
- `backend/app/routers/buyback_prices.py:261` — `ORDER BY fetched_at DESC`
- 問題: 降順返却でフロントチャートが右→左に描画される

### Fix 3: AM・C グレード欠落
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:34-44` — `BuybackProduct` に `price_am`/`price_c` がない
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:291-297` — `chartData` に AM/C が含まれていない
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:412-438` — `<Line>` が S/A/B の3本のみ
- `frontend/src/locales/ja.json:305-307` — `columnPriceAM`/`columnPriceC` キーなし

## 触らない範囲
- DB スキーマ変更なし（`buyback_price_logs` テーブル構造は変更しない）
- 認証・テナント分離ロジックは変更しない
