# recon: line_conditions の CHECK を毎回狭め直す不具合

- scripts/run_all_migrations.sh:80 は migration を先頭から毎回流す（適用記録なし）。
- migrations/20261017_120000_line_conditions_value_rank.sql:18 が line_conditions_value_group_check を作る最初の migration。
- migrations/20261019_100000_line_conditions_value_group_add_promo_single.sql:26 が DROP → ADD で box/case/pack/promo_pack/single に作り直す（booklet 抜き）。
- migrations/20261020_100000_line_conditions_value_group_add_booklet.sql:33 が booklet を足す同形の作り直し。
- 本番に booklet の行があるため、再実行時に 19 の ADD CONSTRAINT が失敗（deploy 39356908634・39359118758、run 39359118758 L5683-5684）。
- 前例: migrations/037_add_pending_dedup_review_to_contacts_check.sql:87 が pg_get_constraintdef で判定して skip する。
- ADR 検索: docs/adr/ADR-1031-single-and-promo-pack-conditions.md、docs/adr/ADR-1035-condition-unit-and-booklet-category.md（値を足した側）。
