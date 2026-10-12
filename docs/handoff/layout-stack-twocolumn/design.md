<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ -->
# Phase 3 設計 — layout-stack-twocolumn

**対象ADR**: ADR-144
**recon**: docs/handoff/layout-stack-twocolumn/recon.md
**日付**: 2026-10-10
**担当**: Planner(Opus) / Generator(Sonnet)

---

## 外部・過去事例の参照と我々への応用

- 事例1: Chakra UI の Stack / SimpleGrid（props で間隔をトークン段階として受ける）→ 応用: gap を `--space-N` の N の列挙で受け、任意の px を渡せない形にした
- 事例2: 本リポジトリの `frontend/src/components/Callout.tsx`（variant をクラス名に変換し CSS は var() のみ）→ 応用: 同じ書き方・命名（comp-*）で作った

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| Stack が縦積み・既定 gap=3 で描画される | `frontend/src/components/Stack.test.tsx`（vitest） |
| TwoColumn が既定 1:2・gap=3・align=start で描画される | `frontend/src/components/Stack.test.tsx`（vitest） |
| CSS に色・px 直値がない | `npm run check:css-values` / `npm run check:css-colors` |
| stories が存在する | `npm run check:stories` |
| 既存検査が通る | `cd frontend && npm run check:all` |
| UI ガバナンス検査が通る | `node scripts/tests/test-ui-governance.js` |

---

## 技術 How・KPI

- KPI: 新設部品2つ（Stack / TwoColumn）。#4094 の直書き style 4箇所が0になる。
- 技術選択: gap/ratio/align は列挙 prop → クラス名（理由: 任意値を許さずトークン段階に固定するため）

---

## 弊害・トレードオフ

- 列挙外の間隔・比率が必要になる場合 → 値を足すときは CSS に1行と型に1語を足す（PO判断不要の範囲）
- 画面の見た目が変わるリスク → 置き換え前後で CSS の計算結果が同一（flex column / grid 1fr 2fr / gap / align-items）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 金型2つ + stories + テスト + 本書類 | Generator |
| 2 | #4094 側の置き換え差分を保存 | Generator |
| 3 | 本PRのマージ後に #4094 へ適用 | 設計者 |

---

## 維持の仕組み

- 守り手: `frontend/scripts/check-stories-count.js`（stories 欠落を CI で検出）、`frontend/scripts/check-css-hardcoded-values.js`（px 直値を検出）、`frontend/src/components/Stack.test.tsx`（クラス契約）
- 人手で守る: 新しい並べ方が必要になったら直書きせず本金型に値を足す（`docs/CC_UI_GOVERNANCE.md` の手順）

## 継続

- 完了後の監視: なし（部品追加のみ）
- 次フェーズへの引き継ぎ: #4094 の置き換え適用
