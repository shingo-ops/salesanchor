# recon 便2: products に複合 FK を足す

> 親の書類: [recon.md](recon.md)（全体の現在地）。この書類は便2 の現在地だけ。
> 基準: origin/main 0a22b62a8（PR #4627 取り込み後）

## 現在地（変更前）
- migrations/20260919_030000_master_ssot_fk_work_id.sql:13-37: 表名を `'pro' || 'ducts'` のように連結した変数に入れ、`EXECUTE format(... %I ...)` で制約を足す冪等 DO ブロック。この書き方を手本にする。
- scripts/run_all_migrations.sh（末尾）: `# コメント` の行のあとに `run_sql migrations/<ファイル名>` を 1 行足す形。直近は migrations/20261020_120000_create_viewer_message_templates.sql。
- scripts/run_all_migrations.sh:76-84: run_sql が `PGOPTIONS="-c lock_timeout=${SQL_LOCK_TIMEOUT}"` を付けて流す。docs/adr/ADR-1037-migration-lock-timeout.md:16-17 のとおり、1 秒の lock_timeout と流し直し（全体 40 回）は台本の側で掛かる。migration ファイルの中には書かない。
- backend/tests/test_product_format_game_links_pg.py:26-28: 試験の土台が links と型の列の migration を名前で流している。
- backend/tests/test_tcg_work_matching_integration.py:374: 同じく links の migration を名前で流している（ほかの試験が使う `pg` の土台）。
- backend/tests/test_tcg_product_list_pg.py:89-90: links の migration を読むが、この試験は products に細分類と作品の組を書かないため、FK を足さなくても今と同じに動く（足さない）。
- backend/tests/test_product_format_game_links_pg.py:142（変更前）: `test_detail_update_keeps_unchanged_old_pair`。links に無い組（作品A・細分類 unlinked）を前提に作るため、FK のもとでは成り立たない。
- backend/app/routers/super_admin_product_formats.py:170-180: links の削除の前に、使用中の商品があれば 409（PRODUCT_FORMAT_GAME_IN_USE）。この動きは変えない。
- migrations/20260920_130000_create_product_classification.sql:96-98: products.product_format_id は product_formats(id) への FK で ON DELETE SET NULL。
- migrations/20260922_030000_product_format_game_links.sql:12-17: links の主キーは (format_id, type_master_id)。format_id 側は ON DELETE CASCADE。

## 本番の基準値（読み取り専用の道・ADR-1024）
- 組ごとの件数表: 73 組・合計 1454 行（2026-10-22 取得。保存場所は PR の報告に記載）
- 不一致の件数: 0 件（同上）

## ADR を探した結果
- ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）: この便の根拠。
- ADR-1037（docs/adr/ADR-1037-migration-lock-timeout.md）: ロック待ちの上限は台本側。
- ADR-1026（docs/adr/ADR-1026-drop-products-type-master-id.md）: 作品の持ち方（work_id）。変えない。
- CI の実測: 使用中の細分類を物理削除すると、links の CASCADE 削除が fk_products_format_in_work に止められ ForeignKeyViolation（試験(4)）。
