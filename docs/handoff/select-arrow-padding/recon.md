# recon — select-arrow-padding

**仕事名**: select-arrow-padding
**日付**: 2026-06-26
**対象ADR**: ADR-073
**担当**: Hikky-dev

---

## 背景

棚の `<Select>` コンポーネント（`comp-field__select` クラス）は OS 標準の `▽` を表示するが、
ブラウザ・OS 間で見た目が異なる。統一した SVG アイコンを使いたい。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/components/FormField.css:73` | `.comp-field__select` ベースルール（変更対象） |
| `frontend/src/components/FormField.css:77` | `padding-right: var(--space-5)` — SVG アイコン幅確保 |
| `frontend/src/components/FormField.css:78` | `background-image` — SVG ▽ アイコン埋め込み |
| `frontend/src/components/FormField.css:129` | sm サイズ override（padding shorthand 上書き対策） |
| `frontend/src/components/FormField.css:152` | lg サイズ override（padding shorthand 上書き対策） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | sm/lg サイズで padding shorthand が padding-right を上書きするか | CSS ソース確認 → `padding: var(--space-1) var(--space-2)` は shorthand のため上書きする | ✅ 解消済み |
| 2 | SVG カラー (`%23888`) が check-css-hardcoded-colors に引っかかるか | スクリプト確認 → `%23` は URL エンコードのため検出対象外 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
