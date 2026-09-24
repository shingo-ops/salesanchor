# release-fix-buyback-category-key

**状態**: PR作成済み
**ブランチ**: release/fix-buyback-category-key
**作業日**: 2026-09-25

## 概要

買取 by-product カテゴリタブ重複修正。
`UPPER(p.category)` を `bsp.card_game` に切り替え（4箇所）。

## 変更ファイル

- `backend/app/routers/buyback_prices.py` — SQLを4箇所修正
- `docs/handoff/fix-buyback-category-key/recon.md`
- `docs/handoff/fix-buyback-category-key/design.md`
