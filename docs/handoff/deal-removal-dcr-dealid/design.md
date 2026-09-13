# 失注理由から deal_id を外す設計

この変更は、失注理由を商談ではなくリードに結び付けるため、古いdeal_id欄をコード定義とテストから取り除く作業です。

親仕様: [docs/specs/db-ssot/deal-removal/design.md](../../specs/db-ssot/deal-removal/design.md)

実測: [recon.md](recon.md)

相互参照（process-artifacts gate）: `docs/handoff/deal-removal-dcr-dealid/recon.md`

## 対象ADR

ADR-121

## 目的と範囲

失注理由の新規テナントDDLとテストfixtureから `deal_id`、対応FK、`UNIQUE (deal_id, reason_id)`、deal_id専用indexを除去する。重複防止は `UNIQUE (lead_id, reason_id)`へ置換する。既存本番DBの列・FK・index削除は次便で扱う。

## UNIQUE制約の判断

失注理由登録処理は `lead_id` で既存行を削除し、`lead_id`・`reason_id`の組で登録している。従来のdeal_idとreason_idの重複防止という意図を、現行の関連先であるlead_idとreason_idへ引き継ぐため、`UNIQUE (lead_id, reason_id)`を採用する。

## 外部・過去事例の参照と我々への応用

orders.deal_id除去の#3073、quotes.deal_id除去の#3084と同種の段階的作業の延長である。今回もコード側の参照・DDL・テストを先に整理し、本番DBの列・FK削除は別便で実施する。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 新規テナントDDLにdeal_idがない | `backend/app/services/tenant.py`のDDLを確認する |
| テストfixtureにdeal_idがない | `backend/tests/conftest.py`のDDLを確認する |
| deal_id機能そのものの検査がない | `backend/tests/test_close_reasons.py`の該当SELECT/assertを確認する |
| lead_id・reason_idの重複防止が維持される | DDLとfixtureの`UNIQUE (lead_id, reason_id)`を確認する |
| 失注理由登録処理が変わらない | `backend/app/routers/leads.py`の既存テストと全体テストを実行する |
| analyticsのAPI互換deal_idを壊さない | analytics関連テストを実行する |
| 本番DBをこの便で変更しない | 本便でDB migrationを実行しないことを確認する |

## 維持の仕組み

守り手: `.github/workflows/` の process-artifacts gate

対象: 失注理由への `deal_id` 再混入

handoff文書と実装差分をprocess-artifacts gateで継続検査し、DDL・fixture・失注理由関連コードへdeal_idが再導入されることを検知する。

## 次便

既存5テナントの `deal_close_reasons.deal_id` 列、`deal_close_reasons_deal_id_fkey`、deal_id専用index、および依存する旧UNIQUE indexを本番migrationで削除する。
