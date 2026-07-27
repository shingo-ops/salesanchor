# サービス層から商談テーブルへの依存をなくし、リード状態で同じ業務判断をする

親設計: [deal-removal design](../../specs/db-ssot/deal-removal/design.md)  
調査: [recon.md](./recon.md)（docs/handoff/deal-removal-serviceA/recon.md）

対象ADR: ADR-121

## 方針

deals を正本として数えていたサービス層を、leads の状態へ置き換える。物理テーブルの削除はこの便の対象外である。

| 対象 | 設計 |
|---|---|
| goals deal_count | `negotiating`、`existing_customer`、`lost` の lead 件数 |
| goals close_rate | `existing_customer / (existing_customer + lost)`。分母0は0.0 |
| goals conversion_rate | dashboardと同じ定義を維持 |
| priority scoring | 失注サンプルを `leads.status='lost'` で抽出 |
| reports | `deals` report key の互換性を保ち、商談段階の leads をCSV出力 |
| conversation logs | company を `companies.lead_id` で補完し、deals経由を廃止 |

## 外部・過去事例の参照と我々への応用

#3106 で `converted_deal_id` への依存を lead_status に置き換えた。この便は同じ正本をサービス層へ広げ、物理列・テーブルを後続便で安全に削除できる状態にする。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| deal_countが商談段階3状態を数える | goals SQLの単体・CI PostgreSQLテスト |
| close_rateが決着済みリードで算出される | goals SQLの単体・CI PostgreSQLテスト |
| conversion_rateがdashboard定義を維持する | goals/dashboard SQL比較とCI |
| priority scoringがdealsをJOINしない | `rg` とテスト |
| reportsとconversation logsがdealsを読まない | `rg` と対象テスト |

## 維持の仕組み

守り手: scripts/check-process-artifacts.js とCI
対象: サービス層への `deals` 再参照。対象4ファイルへの実行時SQLの再混入をレビュー・テストで検出する。
