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
```typescript
// Before
interface MergedDataPoint {
  date: string;
  homura_s: number | null;
  shinsoku_s: number | null;
}

// After
interface MergedDataPoint {
  date: string;
  homura: number | null;
  shinsoku: number | null;
}
```

### mergeHistory 動的化
```typescript
// Before: price_s 固定
dateMap[date].homura_s = entry.price_s;

// After: 選択グレードに応じた price_s/a/b
const priceKey = `price_${selectedGrade}` as keyof PriceHistoryEntry;
dateMap[date].homura = (entry[priceKey] as number) ?? null;
```

### グレード切り替えUI
- SelectControl（ADR-144準拠）を期間Tabsと横並び配置
- gradeOptions: S/A/B（columnPriceS/A/B キー流用）
- デフォルト: "s"

### エラー表示修正
```typescript
// Before: サイレント
.catch(() => { /* サイレント */ })

// After: error state に格納
.catch((err: unknown) => {
  const msg = err instanceof Error ? err.message : null;
  setError(msg ?? t("buybackPrices.loadError"));
})
```

## 検証テーブル

| 基準 | 検証方法 |
|------|---------|
| Sグレード選択時に price_s が表示される | Drawerを開き S 選択 → チャートの値が price_s と一致する |
| Aグレード選択時に price_a が表示される | A に切り替え → チャートの値が price_a に変わる |
| 期間切り替え（7/30/90日）が引き続き動作する | 各期間ボタンクリック → チャートデータ期間が変わる |
| エラー時にメッセージが表示される | API モックでエラーを発生 → 赤文字エラーが表示される |

## 影響範囲

- `BuybackProductHistoryDrawer.tsx` のみ（他コンポーネントは参照なし）
- Line の dataKey が `homura_s` → `homura` に変わるが外部参照なし

## 戻し方

```bash
git revert <commit>
```
フロントエンドUI変更のみ・DBなし・APIなし

## 守り手

- TypeScript型チェック（`price_${selectedGrade}` は `keyof PriceHistoryEntry` にキャスト済み）
- 既存recharts基盤（新規依存なし）
- ADR-144 SelectControl（生select禁止）準拠
