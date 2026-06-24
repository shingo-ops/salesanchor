# recon: ETD ガイド タブ切替スクロール固定（スクロール親修正）

## 対象 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 現状把握

### スクロール親の特定

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:94-98` — 現状の onClick:
```tsx
onClick={() => {
  const scrollY = window.scrollY;
  setActiveIndex(i);
  requestAnimationFrame(() => window.scrollTo(0, scrollY));
}}
```
`window.scrollY` / `window.scrollTo` を使用しているが、実スクロール要素は `window` ではない。

### スクロール親が window でない理由

`frontend/src/pages/integrations/FedexLabelValidationTab.css:1-5` — `.setup-guide-page { height: 100dvh }` により、ページ全体が viewport 高さに固定される。
`frontend/src/pages/integrations/FedexLabelValidationTab.css` — `.page-layout-content { overflow-y: auto }` が実スクロール親（#2530 で導入）。

よって `window.scrollY` は常に 0 であり、復元処理は無効。実際のスクロール位置は `.page-layout-content` の `scrollTop` に格納されている。

### ジャンプの原因

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:105-124` — タブ切替でコンテンツ（descriptions + screenshots）が入れ替わり、詳細パネルの高さが変わる。スクロール親 `.page-layout-content` の `scrollTop` が自動調整されることで位置がずれる。

### 変更スコープ

FE のみ（tsx 1・docs 2）。新規トークンなし。migration/CI 含まない。
