# Recon: buyback-chart-period

## 観測事実

- 現行: Drawer内グラフは `days=30` 固定（`frontend/src/pages/buyback-prices/BuybackPricesPage.tsx` handleRowClick内 history API呼び出し）
- バックエンドAPI: `days` パラメータ既存（1〜365、`backend/app/routers/buyback_prices.py:69`）
- フロント変更のみで期間切り替え可能
- Tabs金型: `variant="pill" size="sm"` がページ内で既に使用済み（カードゲームタブ、`BuybackPricesPage.tsx:341-347`）
- `historyDays` i18nキー: `ja.json:314` / `en.json:314` に固定文字列（"過去30日" / "Last 30 days"）が存在
- 既存ADR検索結果: ADR-027（i18n強制）、ADR-144（UIガバナンス）が関連
