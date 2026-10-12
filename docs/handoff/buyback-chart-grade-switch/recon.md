# Recon: Buyback Chart Grade Switch

## 対象ファイル

- `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx:1-216` — メインコンポーネント（全変更対象）
- `frontend/src/locales/ja.json:309-313` — columnPriceS/A/B キー（既存・流用）
- `frontend/src/locales/en.json:309-313` — 同上
- `frontend/src/components/Select.tsx:23-65` — SelectControl コンポーネント（インポート追加）
- `frontend/src/pages/buyback-prices/buybackTypes.ts` — PriceHistoryEntry 型（price_s/price_a/price_b フィールド確認）

## 現行コードの問題点

### 1. グレード固定（BuybackProductHistoryDrawer.tsx:41-68）
- `mergeHistory()` が `price_s` のみを参照（:55, :64）
- `MergedDataPoint` が `homura_s`/`shinsoku_s` と固定名（:31-33）
- グレード切り替えUIなし

### 2. サイレントcatch（:92, :107）
```typescript
.catch(() => { /* サイレント */ })
```
- エラー状態がなく、取得失敗時もUIに何も表示されない

## 既存ADR検索結果

- `docs/adr/ADR-157` — 買取相場ログ（本機能のベースADR）
- `docs/adr/ADR-144` — UIガバナンス（SelectControl使用必須）
- `docs/adr/ADR-027` — i18n強制（新規キー不要・既存columnPriceS/A/B流用）

## 外部事例
該当なし（既存recharts基盤・既存SelectControl使用）
