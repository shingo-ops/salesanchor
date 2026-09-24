<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — 買取相場レイアウト再構成

**仕事名**: buyback-layout-restructure  
**日付**: 2026-09-24  
**対象ADR**: ADR-144  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:288` | PageLayout headerAction prop の配置先 |
| `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:306` | ContentToolbar 1行目（ビュー切替）の構造 |
| `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:335` | ContentToolbar 2行目（検索＋フィルタ）の構造 |
| `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx:210` | BuybackByProductPage の ContentToolbar 構造 |

---

## 問題

- 買取店 SelectControl だけ size 未指定（デフォルト md）、他3つは sm → 高さ不一致
- ビュー切替・検索・フィルタ・タブ・アクションボタンが1行に混在
- アラート設定・今すぐ取得ボタンがフィルタ行にあり、ページアクションとして認識しづらい

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|

**未解決ゼロ確認**: 該当なし
