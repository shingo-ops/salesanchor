# Phase 3 設計 — ファネル型目標対比ダッシュボード フロントエンド（PR4+5）

**対象ADR**: ADR-139  
**recon**: docs/handoff/dashboard-funnel-kgi/recon.md  
**日付**: 2026-06-12  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 事例1: Salesforce Einstein Analytics — KPIカードにボトルネック自動ハイライト → 我々への応用: 最低達成率カードに自動 `.fn-bottleneck-badge` を付与、マネージャーが即座に課題を特定できる
- 事例2: HubSpot Deal Pipeline — 各ステージの数値とペースバッジを1画面に集約 → 我々への応用: ファネル4カード + 売上カードを1スクロールで確認できる第1層レイアウト
- 事例3: Pipedrive Follow-up Tracking — 顧客ごとの経過日数と区分をセグメントフィルタで絞り込み → 我々への応用: `/dashboard/follow-ups` のセグメントチップ（発注停止/初回後未フォロー/成約後未発注）

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `VITE_FUNNEL_DASHBOARD` 未設定時にファネルセクションが非表示 | `funnel-dashboard.spec.ts`（MOCK_MODE検証）|
| 第1層8カードが正しいモックデータで表示される | `funnel-dashboard.spec.ts:92`（Playwright E2E）|
| ボトルネックバッジが最低達成率カードに自動付与される | `funnel-dashboard.spec.ts:107`（Playwright E2E）|
| 売上ペースバッジ `on_track` が表示される | `funnel-dashboard.spec.ts:123`（Playwright E2E）|
| 要フォロー顧客カードのセグメント件数が正しく表示される | `funnel-dashboard.spec.ts:132`（Playwright E2E）|
| マネジメント/プレイヤービュー切替ができる | `funnel-dashboard.spec.ts:145`（Playwright E2E）|
| `/dashboard/follow-ups` にテーブルとフィルタが表示される | `funnel-dashboard-subpages.spec.ts:64`（Playwright E2E）|
| セグメントフィルタで絞り込みができる | `funnel-dashboard-subpages.spec.ts:77`（Playwright E2E）|
| `/dashboard/leads` チャネルテーブルが表示される | `funnel-dashboard-subpages.spec.ts:135`（Playwright E2E）|
| `/dashboard/revenue` 売上金額と目標が表示される | `funnel-dashboard-subpages.spec.ts:176`（Playwright E2E）|
| `/dashboard/reasons` 成約/失注タブ切替ができる | `funnel-dashboard-subpages.spec.ts:230`（Playwright E2E）|
| 全UIテキストが `t()` 経由（生キーが見えない） | CI ESLint `local/no-japanese-literal` |
| CSSが全てデザイントークン（px/rgba直書きなし） | CI `check:css-colors` + `check:css-values` |
| 視覚回帰ベースライン5枚が `toHaveScreenshot()` でパス | Playwright E2E（chromium-darwin スナップショット）|

---

## 技術 How・KPI

- KPI: Playwright E2E 全22テストパス、視覚回帰ベースライン差分なし
- 技術選択: `VITE_FUNNEL_DASHBOARD` 3状態フラグ（本番デフォルトOFF）— バックエンド未結線でも壊れない
- モックデータ: `frontend/src/api/funnel.ts` の `FUNNEL_MODE === "mock"` 時に Promise.resolve() でフィクスチャを返す

---

## 弊害・トレードオフ

- `Promise.resolve()` による同期的モックデータはReactの非同期レンダリングと競合するため、E2EテストでのDOM確認は `waitFor({ state: "visible" })` が必須
- 視覚回帰ベースライン（PNG）はOS/ブラウザ依存のためCI（Linux）と手元（macOS）で差分が生じる可能性あり → `maxDiffPixelRatio: 0.005` で吸収

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | PR4: 第1層ファネルセクション + `VITE_FUNNEL_DASHBOARD` フラグ | Generator |
| 2 | PR5: 下層4ルート実装 | Generator |
| 3 | 本番安全対策（フラグデフォルトOFF）+ Playwright視覚回帰 | Generator |
| 4 | ADR-067 CSS違反修正（pxトークン化） | Generator |

---

## 継続

- 完了後: バックエンドPR2/3がdevelopにマージされた時点で `VITE_FUNNEL_DASHBOARD=live` に切替える小PR
- 次フェーズ: 実API結線後に視覚回帰ベースラインを `live` データで再撮影
