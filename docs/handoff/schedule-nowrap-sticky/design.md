# 設計 — schedule-nowrap-sticky

**対象ADR**: ADR-067
**recon**: docs/handoff/schedule-nowrap-sticky/recon.md
**日付**: 2026-06-21
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：スクロール固定 / flex nowrap は CSS レイアウト標準技術であり、外部事例参照は不要と判断。ADR-067 デザイントークン規約に準拠した z-index CSS 変数化で十分。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 週/日ビューで下スクロール時に曜日ヘッダーが上部固定 | 目視確認（ブラウザ /schedule 週ビュー） |
| 週/日ビューで下スクロール時に終日行が曜日ヘッダー直下に固定 | 目視確認（ブラウザ /schedule 週ビュー） |
| 1024px 幅で 7 列が折り返さず 1 行に収まる | 目視確認（DevTools 幅調整） |
| ページヘッダー（タイトル+アクション）が全ページでスクロール時も固定 | 目視確認（/leads 等でコンテンツスクロール） |
| 列境界（時間ガター+7曜日列）が日付行・終日行・時間グリッドで一直線 | 目視確認（縦1px境界の揃い） |
| z-index はすべて CSS 変数（ADR-067 準拠） | `grep 'z-index' schedule.css` でハードコードなし |

---

## 技術 How・KPI

- **nowrap**: `display: grid; repeat(auto-fit, minmax(10rem, 1fr))` → `display: flex; flex-wrap: nowrap` + 各セル `flex: 1; min-width: 0`
- **sticky**: `.schedule-grid__viewport { overflow-y: auto }` を scroll container に、`position: sticky; top: 0 / top: var(--schedule-day-head-h)` で固定
- **高さ伝播**: `schedule-page { height: 100% }` → `schedule-shell__content { flex: 1; grid-template-rows: 1fr; align-items: stretch }` → `schedule-main__surface { flex: 1 }` → `schedule-grid__viewport { flex: 1; overflow-y: auto }`
- **KPI**: 1024px 幅テストで 7 列折り返しゼロ / スクロール時ヘッダー常時可視

---

## 弊害・トレードオフ

- `align-items: stretch` に変更するが `.schedule-sidebar { align-self: start }` で上書きされるため影響なし
- `--schedule-day-head-h: 82px` は計算値（tokens.css から導出）。実装後の目視確認が必要

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `pages-layout.css`: `.page-layout-header` を sticky 化 | Generator |
| 2 | `schedule.css`: 高さ伝播チェーン整備 + `schedule-grid__viewport` overflow-y: auto | Generator |
| 3 | `schedule.css`: `schedule-grid__header` / `schedule-grid__allday-row` sticky 化 | Generator |
| 4 | `schedule.css`: `schedule-grid__days` を flex nowrap に変更 | Generator |

---
