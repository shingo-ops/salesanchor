# converted_deal_id を状態で判定する設計

リードがどの段階にあるかを、古い商談IDではなくリード自身の状態で判定する変更です。親設計: [deal-removal design](../../specs/db-ssot/deal-removal/design.md)。調査: docs/handoff/deal-removal-converted-dealid/recon.md。対象ADR: ADR-121。

## 外部・過去事例の参照と我々への応用

#3052 の analytics 読み替えの延長として、集計と操作可否を lead_status の単一事実へ寄せる。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 転換率が新定義で算出される | dashboard/goals/analytics のテスト |
| ボタンが lead 時のみ表示 | LeadsPage 型・ビルド確認 |
| 統合ガードが status ベース | leads テスト・コード確認 |
| converted_deal_id がレスポンスに無い | LeadResponse とE2E fixture確認 |
| 既存テストが緑 | backend/frontend 検証 |

## 維持の仕組み

守り手: process-artifacts gate
対象: converted_deal_id への再依存
