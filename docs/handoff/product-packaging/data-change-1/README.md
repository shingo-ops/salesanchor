# ADR-1028 便2: 商品の荷姿の表へ値を写す（1 回だけのデータ変更）

## 目的
`products` の古い 4 列（boxes_per_case・case_weight_kg・packs_per_box・box_weight_kg）の値を、新しい表 `public.product_packagings` へ写す。あわせて `quantity_units` に CARD を 1 行足す。SQL は [design.md](../design.md) §4-1・4-2 のまま。足したのはトランザクション・件数ガードだけ（ADR-1007: migration に値を書かず、記録した SQL を 1 回だけ流す）。

## PO 承認
PO 2026-10-18 チャット「y」（便2 の実施）

## 順序
1. 事前確認 `00_precheck_read.sql`（読み取りの道・1 文）。
2. DRY-RUN `01_dryrun.sql`（BEGIN…ROLLBACK。件数ガード付き。`DRYRUN_OK`）。
3. 本実行 `01_apply.sql`（`psql -v ON_ERROR_STOP=1`。件数ガードが違えば COMMIT に進まない。`COMMIT_DONE`）。書く権限は本番データ変更の道（`SET LOCAL app.is_operator = 'true'` を同じトランザクションで張る）。
4. 事後確認 `02_verify_read.sql`（読み取りの道・1 文。K3・K4・K5）。

読み取りの道は SELECT/WITH を 1 文しか受けないため、`00_` と `02_` は UNION ALL で 1 文にしてある。

## 想定件数
| 項目 | 想定 |
|---|---|
| CARD | 1 行（display_order 40。既存 3 行は 10・20・30） |
| CASE の行 | 146 |
| BOX の行 | 176 |
| 表の合計 | 322（実施前は 0） |
| `<= 0` の値 | 4 列とも 0 |
| 照合の不一致（K4） | 0 / 0 / 0 / 0 |

違えば止めて Opus に報告する。

## 戻し方
updated_by が 'ADR-1028 data-change-1' の行を消し、CARD の行を消す。古い列は残っているので値は失われない。（戻しの SQL ファイルは作らない）

## 実行結果（実施後に記入）
| 項目 | 内容 |
|---|---|
| 事前確認 | |
| DRY-RUN | |
| 実施日時・COMMIT | |
| 事後確認（K3・K4・K5） | |
