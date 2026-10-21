# design 便2: products に複合 FK を足す

> 設計の正本: [design.md](design.md) §4 便2。この書類に新しい設計判断はない。
> 現在地: [recon-bin2.md](recon-bin2.md)（docs/handoff/format-work-parent/recon-bin2.md）／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

## 変更前後の要約
- 変更前: 細分類が中分類の子であることは、アプリの照合だけで守っている。DB は不一致の組を受け入れる。
- 変更後: products(product_format_id, work_id) → product_format_game_links(format_id, type_master_id) の複合 FK（fk_products_format_in_work）を DB が持つ。不一致の組は書けない。
- 流れ: 事前点検（不一致が 1 件でもあれば止める）→ NOT VALID で追加 → VALIDATE。索引は足さない。値は書かない。
- 変えないもの: API の形、エラー符号、links 削除の 409。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|links に無い組を products に直接書くと DB が拒否する|test_db_rejects_pair_not_in_links|
|片方が NULL なら通る|test_db_allows_pair_with_null_side|
|使われている links の行を直接消すと DB が拒否する。API は今と同じ 409|test_db_rejects_removing_link_in_use と、既存の test_replace_games_blocks_removal_in_use|
|使われている細分類の物理削除の結果が一貫している。通るか落ちるかを CI のログに残す|test_physical_delete_of_format_in_use_outcome（警告 BIN2_T4_PHYSICAL_DELETE_OUTCOME）|
|migration が値を書かない|python3 scripts/check-migration-value-writes.py diff origin/main HEAD が 0 件|
|本番で不一致が 0 件|recon-bin2.md の本番の基準値が 0|

## 外部・過去事例の参照と我々への応用
この便は design.md §10 の判断のとおり。前例は migrations/20260919_030000_master_ssot_fk_work_id.sql（EXECUTE format で制約を足す冪等 DO ブロック）。数値つきの外部事例はない。

## 維持の仕組み
- 守り手: backend/tests/test_product_format_game_links_pg.py（FK の試験。CI の pytest が毎回走らせる）
- 親子の保証は DB の FK が持つ。FK を外すと、上の試験が落ちる。
