# KGI（入力部品 寸法金型・○×で測る）

> 親: [README.md](./README.md) / recon: docs/handoff/field-size/recon.md

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| ① | 高さ金型が3段で在る | h-sm/h-md/h-lg のCSS定義数 | 3/3 |
| ② | 幅金型が3段で在る | w-sm/w-md/w-lg のCSS定義数 | 3/3 |
| ③ | 高さと幅が独立に選べる | 部品が高さprop・幅propを別々に受ける | 在る=1 |
| ④ | 操作台上で水平が揃う | リードで高さ揃い・1行表示（PO目視） | 揃う=1 |
| ⑤ | 生button/生selectの直書き寸法が0 | 対象画面の手書きwidth/height残存数 | 0 |
| ⑥ | 位置ズレ番人が在る | CI関所で寸法違反検出 | 在る=1 |

KPI: 達成KGI数 4/6（2026-07-29 実測・main=ff64def72a161c93b0d0748341942fe94eda2855）。⑤⑥は全画面移行後の最終判定。

## 判定の根拠（2026-07-29）

| # | 判定 | 根拠 |
|---|---|---|
| ① | ○ | frontend/src/tokens.css:162-164 に --field-h-sm(28px)/--field-h-md(36px)/--field-h-lg(44px) を定義 |
| ② | ○ | frontend/src/tokens.css:165-167 に --field-w-sm(160px)/--field-w-md(280px)/--field-w-lg-max(480px) を定義 |
| ③ | ○ | frontend/src/components/field-size.css で .field-h-* と .field-w-* を独立クラスとして定義。frontend/src/index.css:2 で読込 |
| ④ | ○ | 2026-07-29 14:48 JST に PO（Shingo）が本番 https://app.salesanchor.jp/crm/leads を目視し「揃っている」と判定。本番配布物 assets/index-CjU4lrK7.css に --field-h-md:36px・--field-w-sm:160px の配布を curl で実測（http_code=200）。なお設計パートナーは同スクリーンショットからプルダウンとボタンの高さ差の可能性を指摘したが、本項目は kgi.md が定める PO 目視判定であり PO の判定を採用した。金型は min-height 指定のため上限は縛らない（frontend/src/components/field-size.css）。 |
| ⑤ | 未 | 便D（生select 38ページ）完了後に判定 |
| ⑥ | 未 | 便E（番人）完了後に判定 |
