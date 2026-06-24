# recon — ETD ガイド 左ナビ項目ラベル中央揃え

**仕事名**: ETD ガイド 左ナビ項目ラベル中央揃え
**日付**: 2026-06-24
**対象ADR**: ADR-129, ADR-067
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:95` | `.etd-guide__substep-nav-item` クラスを付与しているボタン要素 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.css:291` | `.etd-guide__substep-nav-item` CSS 定義ブロック開始 |

---

## 現状（file:line）

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:95` で各サブ手順ボタンに `.etd-guide__substep-nav-item` クラスを付与。
そのスタイルは `frontend/src/pages/integrations/FedexLabelValidationTab.css:291` に定義されており、`text-align: left` が設定されているため 1-1〜1-6 のボタンラベルが枠内左寄せになっている。

## 触らない範囲

- ナビ列の位置（左端固定）
- アクティブ時 border・color・background
- 他コンポーネント一切

## 不明点リスト

| # | 不明点 | 状態 |
|---|-------|------|
| - | 該当なし | — |

**未解決ゼロ確認**: 全て解消済み
