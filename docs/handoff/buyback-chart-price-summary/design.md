# design: buyback-chart-price-summary

## 概要

`BuybackProductHistoryDrawer` の価格推移チャート下に、各店舗の現在価格と前日比を表示するサマリーセクションを追加する。

## 参照

- recon: `docs/handoff/buyback-chart-price-summary/recon.md`
- ADR-157: 買取相場ログ機能
- ADR-144: UIガバナンス（デザイントークン・金型部品）
- ADR-027: i18n強制

## 変更内容

### 追加ヘルパー関数（モジュールスコープ）

`frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx` に3関数を追加:

1. `getShopPrice(item, shop, grade): number | null`
   - `item[${shop}_price_${grade}]` を動的アクセスで取得
   - `homura_price_s` / `shinsoku_price_a` 等に対応

2. `renderShopRow(label, price): JSX`
   - 店舗名（左）+ 価格（右、`formatPrice`で整形）

3. `renderDiffRow(label, diff): JSX`
   - ラベル（左）+ 前日比（右）
   - diff > 0: `var(--success)` + `+¥X,XXX`
   - diff < 0: `var(--danger)` + `-¥X,XXX`
   - diff == 0: `var(--text-muted)` + `±0`
   - diff == null: `var(--text-muted)` + `—`

### サマリーセクション表示条件

`{item && hasData && ( ... )}` — チャートデータが存在する場合のみ表示

### 表示レイアウト

```
ホムラ      ¥70,000
シンソク    ¥62,000
前日比      +¥2,000  (緑)
```

- `yesterday_diff` は `ByProductItem.yesterday_diff`（最高買取価格の前日比・shop横断）
- 表示は1行に統合（店舗個別の前日比はAPIが提供しないため）

### デザイントークン

- 背景: `var(--bg-surface)`
- ラベル色: `var(--text-secondary)`
- 上昇: `var(--success)`
- 下降: `var(--danger)`
- 変化なし/null: `var(--text-muted)`
- 間隔: `var(--space-2)`, `var(--space-3)`
- 角丸: `var(--radius-sm)`
- フォント: `var(--font-sm)`

## KGI / 検証テーブル

| 基準 | 検証方法 |
|------|----------|
| チャート下にホムラ・シンソク価格行が表示される | Drawerを開いてチャートが出た状態で目視確認 |
| グレード切り替え（S/A/B）で価格が連動して変わる | セレクタを切り替えて各行の数値が変化することを確認 |
| 前日比が上昇=緑・下降=赤・0/null=グレーで表示 | テストデータで各ケースを目視確認 |
| チャートデータ0件時にサマリーが表示されない | noHistory表示時にサマリーが非表示であることを確認 |
| t()経由でテキスト表示（ハードコード日本語なし） | grep `\"ホムラ\"\|\"シンソク\"\|\"前日比\"` が追加コードに0件 |

## 外部・過去事例の参照と我々への応用

該当なし。本実装は `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx` の既存 `yesterday_diff` レンダリングパターン（`var(--success)`/`var(--danger)` 色分け）を Drawer 内サマリーに応用したもの。外部ライブラリ・外部事例への依存なし。

## 影響範囲

- 変更: `frontend/src/pages/buyback-prices/BuybackProductHistoryDrawer.tsx` のみ
- i18n追加: なし（既存キーを再利用）
- 削除: なし

## 維持の仕組み

守り手: TypeScript型チェック（`ByProductItem` 動的キーアクセスは `as keyof ByProductItem` キャスト） + デザイントークン強制（CSS変数のみ使用・hardcoded色・px値なし）
