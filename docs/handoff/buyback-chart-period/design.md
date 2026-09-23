# Design: buyback-chart-period

recon: docs/handoff/buyback-chart-period/recon.md

## 方針

Drawer内チャート上部にTabs（pill/sm）で期間選択（7日/30日/90日）を追加。
バックエンド変更なし（既存 `days` パラメータを活用）。

## 変更前後

| 項目 | 変更前 | 変更後 |
|---|---|---|
| 期間 | 30日固定 | 7/30/90日 選択可能 |
| UI | なし | Tabs pill/sm |
| subtitle | "過去30日"（固定） | "過去{{days}}日"（動的） |

| 基準 | 検証方法 |
|---|---|
| 期間切り替えで API に正しい days が送られる | ブラウザ Network タブで `days=7` / `days=90` を確認 |
| グラフが更新される | 目視確認（データ点数・日付範囲の変化） |
| 新規商品クリック時に30日にリセット | 別商品クリック後のアクティブタブを確認 |

**対象ADR**: ADR-027（i18n強制）、ADR-144（UIガバナンス・Tabs金型使用）

守り手: frontend/src/pages/buyback-prices/BuybackPricesPage.tsx

## 触るファイル
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx`（期間セレクター追加・historyDays state・useEffect追加）
- `frontend/src/locales/ja.json`（3キー追加・historyDays動的化）
- `frontend/src/locales/en.json`（3キー追加・historyDays動的化）

## 触らないファイル
- backend/（変更なし・既存 days パラメータ活用）
- migrations/（変更なし）

## 外部・過去事例の参照と我々への応用
既存ページ内のTabs（pill/sm）パターンを踏襲（BuybackPricesPage.tsx:341-347）。

## 維持の仕組み
Tabs金型を使用しているため、デザインシステム更新時に自動追従。
