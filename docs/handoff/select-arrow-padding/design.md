# Phase 3 設計 — select-arrow-padding

**対象ADR**: ADR-073
**recon**: docs/handoff/select-arrow-padding/recon.md
**日付**: 2026-06-26
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 事例: `appearance: none` + SVG `background-image` によるセレクトカスタムアイコンは、
  MDN・CSS-Tricks が推奨する標準パターン（クロスブラウザ実績あり）。
  同プロジェクト内では `frontend/src/styles/components.css:712-719` の `.page-header-select`
  で同一手法を採用済み。差分は `padding-right` のトークン値のみ。
- 我々への応用: 既存パターンを `FormField.css` に横展開し、全 `<Select>` 部品の見た目を統一する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `<Select>` に OS 標準 `▽` が表示されなくなる | ブラウザ目視（Playwright スクリーンショット） |
| 統一した SVG `▽` アイコンが右端に表示される | Playwright スクリーンショット比較 |
| sm/lg サイズでアイコンとテキストが重ならない | Playwright: 短・長オプション両方で確認 |
| `check-css-hardcoded-colors` がパスする | CI: Frontend lint & custom checks |
| stylelint がパスする（詳細度順序守る） | CI: Frontend lint & custom checks |

---

## 技術 How・KPI

- 手法: `appearance: none` + `background-image: url(SVG)` + `padding-right: var(--space-5)`
- KPI: CI 全グリーン・ブラウザ目視でアイコン重なりなし
- スコープ: `frontend/src/components/FormField.css` 1ファイル・19行追加のみ

---

## 弊害・トレードオフ

- `%23888`（= `#888`）はライトモード専用色。ダークモードでは薄すぎる可能性あるが、
  現状は既存 `.page-header-select` と同値であり一貫性を優先（改善は別PR）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `FormField.css` に `appearance:none` + SVG + `padding-right` 追加 | Generator |
| 2 | sm/lg サイズの `padding-right` override 追加 | Generator |
| 3 | Playwright スクリーンショットで before/after 確認 | Evaluator |

---

## 継続

- 完了後の監視: 本番デプロイ後 UI 目視確認（CSS のみのため影響範囲は視覚のみ）
- ダークモード対応は別タスクとして棚上げ
