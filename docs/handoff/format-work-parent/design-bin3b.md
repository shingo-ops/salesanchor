# design 便3b: 旧列 product_formats.type_master_id を落とす

> 設計の正本: [design.md](design.md) §4 便3b・§8・§11。この書類に新しい設計判断はない。
> 現在地: [recon-bin3b.md](recon-bin3b.md)（docs/handoff/format-work-parent/recon-bin3b.md）／対象 ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）

守り手: backend/tests/test_product_format_game_links_pg.py

## 変更前後の要約
- 変更前: DB に二重の置き場（旧列 product_formats.type_master_id と links）があった。
- 変更後: 旧列を FK・索引ごと落とす。親子の正本は product_format_game_links だけ。28 行の値は CSV（docs/handoff/format-work-parent/data/product_formats_type_master_id_20261022.csv）に控えた。控えはどのコードからも読まない。
- 変えないもの: links、products の複合 FK、API・画面（便3a で旧列を外し済み）。値は migration に書かない。
- 試験の直し: 旧列の値を読む・書く確認（旧 :295、:319）だけ外し、「type_master_id を付けて送っても保存でき、応答に出ない」は残す。旧列が無い DB では前提が成り立たないため。

## 受入条件と検証方法
|基準|検証方法|
|---|---|
|DROP COLUMN を含む PR は PO 本人の GO 後にだけマージ|PR は Draft。「### GO記録」を PO の「GO #番号」の後に埋める|
|新 migration が冪等|IF EXISTS だけで書く。CI の PG 試験の土台（test_product_format_game_links_pg.py の fixture が新 migration を流す）と migration-guard で判定。手元の使い捨て PG での 2 回流しは、フック psql-write-guard に止められたため未実行|
|旧列の読み手 0|git grep -n "type_master_id" の残りが links 由来の行だけ。git grep -n typeMasterId frontend/src が空。openapi.json の ProductFormat 系に type_master_id が無い|
|ADD を戻していない（チェック 10）|node scripts/check-migration-column-churn.js が通る。許可表は足さない|
|データ参照を書いていない（チェック 7・8）|python3 scripts/check-migration-value-writes.py diff origin/main HEAD が 0 件|
|K4: 商品の (work_id, product_format_id) が変わらない|GO 前と反映後に同じ組ごとの件数表を取って比べる。基準値は 1454 件・73 組・不一致 0|
|K5: 反映後、product_formats に type_master_id 列が無い|reader の道で information_schema.columns を見る|
|ai_ro が戻る|反映後に ai_ro.public__product_formats が読める（旧列なしで作り直される）|

## 外部・過去事例の参照と我々への応用
数値つきの外部事例はない（design.md §10 のとおり）。過去事例は ADR-1026（products.type_master_id の取り外し、commit 03d770375）。ADD 文を消し、DROP migration を IF EXISTS で足す順番を踏襲する。

## 維持の仕組み
- 守り手: backend/tests/test_product_format_game_links_pg.py（旧列を受け取っても無視し、返さない）と migration-guard のチェック 10。
- 旧 migration の Step 1 に「ここに ADD を戻さないこと（ADR-1038）」と書いた。親子の正本は links だけで、旧列の代わりの置き場は作らない。
- 戻し方（実行できる順）:
  1. この PR を revert してデプロイする。revert で戻るのは、scripts/run_all_migrations.sh の末尾の登録 2 行（コメントと run_sql）の削除、migrations/20261022_110000_product_formats_drop_type_master_id.sql の削除、migrations/20260923_010000_product_formats_add_type_master_id.sql の Step 1（ADD の DO ブロック）の復元。事実: git diff 14b1b6d39 HEAD -- migrations/20260923_010000_product_formats_add_type_master_id.sql で Step 1 が DO ブロックから ADR-1038 のコメントに置き換わっており、revert はこの逆になる。デプロイで列が空（全 NULL）の INTEGER、type_master(id) 参照、ON DELETE SET NULL として再作成される。
  2. 値は migration に書けない（ADR-1007）。PO 確認のうえ、docs/handoff/format-work-parent/data/product_formats_type_master_id_20261022.csv から手で戻す。本番への書き込みは、Opus が用意した台本を PO が `!` で流す。
  3. 確かめ方: reader の道（ADR-1024）で `SELECT id, code, type_master_id FROM public.product_formats ORDER BY id` を取り、CSV（28 行）との差分が 0 であること。

## 解析の正答率への影響（2026-10-22 調べ）
影響する経路は無い。
- 便3a の結果: v102 の解析、backend/app/tasks、scripts/accuracy、gas/ に type_master_id・typeMasterId を含む行は 0 件。
- 便3b の git grep -n "type_master_id" -- backend/app は、links 由来の行だけ（旧列の読み手は app に 0 件。recon-bin3b.md §1）。
- 解析側で product_formats を読む行は code と id だけを使う（recon-bin3b.md §4）。正答率の採点は TSV の突き合わせだけで DB に接続しない（docs/handoff/format-work-parent/design-bin2.md）。

## CI での失敗と直し
- PR #4642 の CI「マイグレーションSQL 実行テスト（実DB）」（run 39727376560）が、空の DB で変更した SQL だけを流して `relation "public.product_formats" does not exist` で落ちた。全体の流し（migration-full-dryrun）は success だった。
- 直し: 2 つの ALTER を `ALTER TABLE IF EXISTS public.product_formats` にした。表が無い DB では何もしない。
