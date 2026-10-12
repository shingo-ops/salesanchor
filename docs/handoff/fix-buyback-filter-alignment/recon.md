# Recon: 買取相場フィルタ水平配置修正

## 調査対象
- frontend/src/components/FormField.css:22 — .comp-field { margin-bottom: var(--space-4) }
- frontend/src/components/TextField.tsx:42-50 — className は outer .comp-field div に適用
- frontend/src/components/ContentToolbar.css:2 — .content-toolbar__left { display: flex; flex-wrap: nowrap }
- frontend/src/pages/buyback-prices/BuybackByProductPage.tsx:214-221 — TextField に searchField クラス未適用

## 根本原因
TextField の .comp-field ラッパーに margin-bottom: var(--space-4) が常時付与され、ContentToolbar の flex コンテナ内でも縦余白が発生。SelectControl（bare appearance）にはラッパーがないため高さ差分が生じ、水平配置が崩れていた。
