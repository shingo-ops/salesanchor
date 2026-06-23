# Phase 3 設計 — fedex-etd-ux-improvements

**対象ADR**: ADR-027, ADR-067, ADR-129  
**recon**: docs/handoff/fedex-etd-ux-improvements/recon.md  
**日付**: 2026-06-23  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は既存コンポーネント内の CSS/TSX のみ変更（新機能追加なし）。ステッパー UI は MDN CSS pseudo-element ドキュメントを参照し、`::before`/`::after` による connector line を実装。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| スクショが `width: 100%` で全幅表示される | Playwright: ETD ガイド Step1 スクショ要素の CSS 確認 |
| ステップ1説明文に Developer Portal へのインラインリンクが存在する | Playwright: `etd-guide__inline-link` の `href` 確認 |
| 旧「Developer Portal を開く」ボタンが消えている | Playwright: `etd-guide__actions--left` が不在 |
| ステップ式インジケーターが表示され、現在ステップがハイライトされる | Playwright: `.etd-stepper__item--current` の存在確認 |
| `npm run lint` で 0 errors | CI: Frontend lint & custom checks |
| `npm run build` で TypeScript エラーなし | CI: Storybook build check |

---

## 技術 How・KPI

- KPI: lint 0 errors / build 成功 / FE-only（migration/deploy.yml 変更なし）
- スクショ: `max-height` 削除 → `width: 100%` に戻す。未使用トークン `--size-screenshot-thumb-h` を削除。
- インラインリンク: `<Trans>` コンポーネント + `portalLink` named slot。`ja.json`/`en.json` 両方更新。
- ステッパー: `StepIndicator` コンポーネントを TSX 内で定義。CSS `::before`/`::after` で connector line。ADR-067 準拠（`z-index: var(--z-base)`、色は `--accent`/`--border` 使用）。

---

## 弊害・トレードオフ

- スクショ全幅表示によりページが長くなる → PO 判断でスクロール許容・明瞭さ優先
- ステッパーの connector line は `::before`/`::after` pseudo-element を使用するため、ブラウザ対応は現代的なもの（全主要ブラウザで対応済み）
