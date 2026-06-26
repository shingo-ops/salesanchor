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
| `frontend/src/components/Select.tsx:73` | `<select className="comp-field__select">` — スタイル適用先 |
| `frontend/src/components/Select.tsx:15` | `SelectSize` 型（sm/md/lg）— サイズバリアント定義 |
| `docs/adr/ADR-073-design-system-kgi-rubric.md:1` | ADR-073 — デザインシステム KGI ルーブリック（本変更の根拠） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | sm/lg サイズで padding shorthand が padding-right を上書きするか | CSS ソース確認 → `padding: var(--space-1) var(--space-2)` は shorthand のため上書きする | ✅ 解消済み |
| 2 | SVG カラー (`%23888`) が check-css-hardcoded-colors に引っかかるか | スクリプト確認 → `%23` は URL エンコードのため検出対象外 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
