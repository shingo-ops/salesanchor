# Design: Buyback Chart Grade Switch

## KGI

チャートDrawerでグレードS/A/Bを切り替えると、両店舗（ホムラ・シンソク）の該当グレード価格推移が表示される。

## recon参照

- recon: `docs/handoff/buyback-chart-grade-switch/recon.md`
- ADR-157: 買取相場ログ
- ADR-144: UIガバナンス（SelectControl使用）
- ADR-027: i18n強制（既存キー流用）

## 変更設計

### MergedDataPoint 型変更

Before: `homura_s`/`shinsoku_s` 固定フィールド
After: `homura`/`shinsoku`（グレードサフィックスなし・動的参照）

### mergeHistory 動的化

`selectedGrade` パラメータを受け取り `price_s`/`price_a`/`price_b` を動的に参照。

### グレード切り替えUI

- SelectControl（ADR-144準拠・生select禁止）を期間Tabsと横並び配置
- gradeOptions: S/A/B（`buybackPrices.columnPriceS/A/B` キー流用）
- デフォルト: "s"

### エラー表示修正

サイレントcatch → error state に格納してUIに表示（`buybackPrices.loadError` キー）

## 検証テーブル

| 基準 | 検証方法 |
|------|---------|
| Sグレード選択時に price_s が表示される | Drawerを開き S 選択 → チャートの値が price_s と一致する |
| Aグレード選択時に price_a が表示される | A に切り替え → チャートの値が price_a に変わる |
| 期間切り替え（7/30/90日）が引き続き動作する | 各期間ボタンクリック → チャートデータ期間が変わる |
| エラー時にメッセージが表示される | API モックでエラーを発生 → 赤文字エラーが表示される |

## 影響範囲

- `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx` のみ（他コンポーネントは参照なし）
- Line の dataKey が `homura_s` → `homura` に変わるが外部参照なし

## 戻し方

```bash
git revert <commit>
```
フロントエンドUI変更のみ・DBなし・APIなし

## 外部・過去事例の参照と我々への応用

該当なし。SelectControl + recharts は既存基盤（ADR-144/ADR-157）を踏襲。グレード切り替えパターンは同ページの期間切り替え（Tabs + days state）と同一実装パターンを適用した。

## 維持の仕組み

- 守り手: TypeScript型チェック（`keyof PriceHistoryEntry` キャストで price_x フィールドのみ許可）+ 既存recharts基盤（新規依存なし）+ ADR-144 SelectControl（生select禁止・CIで強制）
