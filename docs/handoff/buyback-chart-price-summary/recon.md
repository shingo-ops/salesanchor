# recon: buyback-chart-price-summary

## 対象ファイル（file:line）

- `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx` — 変更対象。価格推移チャートDrawer（1-254行）
- `frontend/src/pages/buyback-prices/buybackTypes.ts` — `ByProductItem` 型定義（homura_price_s/a/b, shinsoku_price_s/a/b, yesterday_diff フィールド確認 96-118行）+ `formatPrice` 関数（148-151行）
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx` — `yesterday_diff` の既存レンダリングパターン（var(--success)/var(--danger)、154-172行）
- `frontend/src/locales/ja.json:382-400` — `buybackPrices.byProduct.columnYesterdayDiff: "前日比"`, `buybackPrices.shopHomura: "ホムラ"`, `buybackPrices.shopShinsoku: "シンソク"` すべて既存
- `frontend/src/locales/en.json:382-400` — 対応英語キー確認済み（i18n追加不要）
- `frontend/src/tokens.css:531` — `--color-success`, `--color-danger` 確認。コードベース内では `var(--success)` / `var(--danger)` 形式で使用（BuybackByProductPage.tsx:162-165 実例）

## ADR検索結果

- `docs/adr/ADR-157-buyback-price-logger.md` — 買取相場ログ（buyback-prices 機能の根拠ADR）
- `docs/adr/ADR-144-ui-component-governance.md` — UIガバナンス（SelectControl/Tabs等の金型部品使用確認済み）
- `docs/adr/ADR-027-ui-internationalization.md` — i18n強制（全テキストt()経由 確認済み）

## 既存パターン（参考）

`frontend/src/pages/buyback-prices/BuybackByProductPage.tsx` 157-171行:
```
const color = row.yesterday_diff > 0 ? "var(--success)" : row.yesterday_diff < 0 ? "var(--danger)" : "var(--text-muted)";
```
→ 同一パターンを `renderDiffRow` ヘルパーで実装

## i18n追加

不要。使用するキーはすべて既存:
- `buybackPrices.shopHomura`
- `buybackPrices.shopShinsoku`
- `buybackPrices.byProduct.columnYesterdayDiff`
