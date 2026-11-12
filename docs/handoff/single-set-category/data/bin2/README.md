# 区分「シングルセット系」便2 記録 SQL（本番未適用）

区分「シングルセット系」1 行をデータで入れる（設計 `docs/handoff/single-set-category/design.md` §5「### 便2」・受入 K4（§8）。ADR-1007 により migration には書かない）。前例: ADR-1035 便2（`docs/handoff/condition-unit-booklet/data/bin2/`）の PC_BOOKLET。

前提:
- 便1（PR #5417）のコードが本番に出ていること。2026-11-12 05:36Z の配備で済み（deploy run 43161834085 で HEAD 2ab2a99dc、43162066897 で 63709b0eb。backend は入れ替え、celery-worker は作り直し）。
- 便1 の反映の時点でシングルセット系の商品は 0 件（K3。2026-11-12 05:49Z reader で数えた。区分ごとの商品数: 箱系 350・シングル系 55・バルク系 24・セット系 20・プロモパック系 11・ブックレット系 5・区分なし 1009）。
- 本番の区分の行は 6 行（id 1 PC_BOX・2 PC_SINGLE・4 PC_SET・9 PC_BULK・11 PC_PROMO_PACK・13 PC_BOOKLET。すべて有効・tenant_id NULL。2026-11-12 06:51Z reader）。表には主キー（id）と code の一意索引 uq_tcg_product_categories_code がある（2026-11-12 reader の pg_indexes。作ったのは migrations/20260919_020000_master_ssot_public_tables.sql:293）。利用者が作った仕掛け（trigger）は無い。重なりは 01 と 02 の NOT EXISTS で先に止め、code の重なりは一意索引でも止まる。
- 画面とコードは区分を DB から読む。区分の code・表示名を直書きしている所は frontend・backend/app に無い（origin/main で `git grep` PC_BOOKLET・PC_PROMO_PACK、試験と説明を除いて 0 件。区分名の定数は解析の判定用で、便1 で足し済み）。

| 順 | 作業 | 期待 |
|---|---|---|
| 1 | `01_precheck.sql` | PRECHECK_OK が 3 行（category_absent・single_set_products 0・pc_set_active）。ROW 行 6 行・COUNT 行は情報 |
| 2 | `02_apply.sql` を `-v end=ROLLBACK` で DRY-RUN | INSERTED category 1・CHECK_OK 3 行（category・categories_total 7・single_set_products 0）。最後に ROLLBACK |
| 3 | `02_apply.sql` を `-v end=COMMIT` | 手順 2 と同じ件数、COMMIT |
| 4 | `03_verify.sql` | VERIFY_OK が 3 行（K4。categories_total 7 を含む）。ROW 行の既存 6 行と COUNT 行を 01 と突き合わせ、変わっていないことを確かめる |

戻し: `04_rollback.sql`（設計 §9。商品が付いていない間だけ is_active=false。商品が付いていれば止まる）。

- 実行: 本番への書き込みは見張り（psql-write-guard）が止めるので、PO の `bash scripts/permit-danger.sh "psql write"`（1 回限り・30 分）の後に Opus が流す。PO の合意は同意票で取る。
- ロック待ちは 1 秒で切る（ADR-1037）。
- この時点ではどの商品もこの区分に入っていないので、解析の結果は変わらない。商品の付け替えは便3。
