# Recon: 買取相場レイアウト再構成

## 調査対象
- frontend/src/pages/buyback-prices/BuybackPricesPage.tsx — ContentToolbar に全要素が1行詰め込み
- frontend/src/components/PageLayout.tsx — headerAction prop（ReactNode、タイトル右端に配置）
- frontend/src/components/Select.tsx — size prop（"sm"|"md"|"lg"、デフォルト "md"）

## 問題
- 買取店 SelectControl だけ size 未指定（デフォルト md）、他3つは sm → 高さ不一致
- ビュー切替・検索・フィルタ・タブ・アクションボタンが1行に混在
- アラート設定・今すぐ取得ボタンがフィルタ行にあり、ページアクションとして認識しづらい

## ADR
- ADR-144: UIガバナンス（金型コンポーネントのみ使用）
