# 会社画面から商談集計を外し、リード統合が商談テーブルを触らないようにする

親設計: [deal-removal design](../../specs/db-ssot/deal-removal/design.md)

調査: [recon.md](./recon.md)

対象ADR: ADR-121

## 方針

lead が親であり、会社ごとの商談数は正本の状態を表さない。会社詳細の `total_deal_amount` と `deal_count` をAPI契約・型・画面から外す。リード統合でも `deals.lead_id` を付け替えない。`v_company_stats` 本体のdeals依存はDB変更となるため便Dで削除する。

## 外部・過去事例の参照と我々への応用

#3106 と便Aで、商談を正本にした参照をlead statusベースへ置き換えた。本便はその延長として、会社画面とリード統合からdealsへの実行時依存を外す。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 会社APIが商談金額・商談数を返さない | `CompanyResponse` とcompanies routerのSELECTを確認 |
| 会社詳細が商談金額・商談数を表示しない | TypeScript buildとCompanyBasicTabの確認 |
| リード統合がdealsを更新しない | leads routerの差分と`rg` |
| リード統合のstatus guardが維持される | leads routerのguardを確認 |
| 既存テストが緑 | SQLiteテストとCI |

## 維持の仕組み

守り手: process-artifacts gate とCI

対象: 会社詳細API・画面、及びリード統合へのdeals再参照。
