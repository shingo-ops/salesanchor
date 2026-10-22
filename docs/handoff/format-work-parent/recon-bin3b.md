# recon 便3b: 旧列 product_formats.type_master_id を DB から落とす

> 親の書類: [recon.md](recon.md)（全体の現在地。§10.1 が旧列の読み手・書き手）。この書類は便3b の現在地だけ。
> 基準: origin/main 14b1b6d39（PR #4633 取り込み後）。生出力は PR の報告に記載。本番の読み取りは ADR-1024 の reader 鍵の道（SELECT のみ）。

## 1. 旧列を名指しする場所（git grep -n "type_master_id" -- migrations scripts backend/tests backend/app、51 行）
(A) 旧列 product_formats.type_master_id を指す行:
- migrations/20260923_010000_product_formats_add_type_master_id.sql の Step 1（ADD。便3b で削除してコメント化）と Step 3 のコメント
- scripts/run_all_migrations.sh:919-920（その migration の登録。残す）
- backend/tests/test_product_format_game_links_pg.py:28（migration 名）、:295（旧列の SELECT）、:319（旧列への UPDATE）。便3b で :295・:319 を外す。
(B) links（product_format_game_links）由来・すでに落とした products.type_master_id・名前だけ同じ行: backend/app/routers/super_admin_product_formats.py:40,185,192-193、backend/app/services/tcg_product_master_svc.py:109,134-135、migrations/20260922_030000、20261017_210000、20261022_100000、backend/tests の links の INSERT・SELECT。触らない。
- backend/app 内の (A) は 0 件（旧列の読み手 0）。他の migration で product_formats.type_master_id を UPDATE・INSERT・VIEW で名指しするものは 0 件。

## 2. 本番の事実（2026-10-22、reader 鍵の道）
- product_formats は 28 行、type_master_id は 28 行とも非 NULL。recon の raw/q28_pf_tmid_values.txt（recon §10.1）と id・code・値の diff は 0 行。
- 旧列に依存するビューは 1 本だけ: ai_ro.public__product_formats（ai_ro 以外は 0 本）。
- 制約 product_formats_type_master_id_fkey（type_master(id) ON DELETE SET NULL）と索引 idx_product_formats_type_master_id がある。列と一緒に消える。
- 列数: 総数 11、削除済み 0（1600 上限に対して余裕あり）。
- K4 基準値: products 総数 1454、(work_id, product_format_id) の組 73 組、links に無い組（不一致）0 件。便2 の基準値と組ごとの件数表が完全一致（diff 0 行）。

## 3. ai_ro ビューの扱い
- scripts/run_all_migrations.sh:183-185 が一覧の先頭で migrations/20261017_125900_drop_ai_ro_views.sql（DROP SCHEMA IF EXISTS ai_ro CASCADE）を流す。
- :187-215 が、スクリプトの成否にかかわらず終了時に migrations/20261017_130100_create_ai_ro_views.sql を流す（trap :215）。
- 作成 SQL は列を名指ししない。pg_attribute の今の列から組み立てる（migrations/20261017_130100_create_ai_ro_views.sql:26-44、EXECUTE format :63-66）。列を落とした後は旧列なしで作られる。

## 4. 解析・監視の読み手
- v102 の解析、backend/app/tasks、scripts/accuracy、gas/ に type_master_id・typeMasterId を含む行は 0 件（便3a の recon-bin3a.md と同じ範囲）。
- product_formats を読む解析側は tcg_product_import_svc.py:267 と tcg_product_roundtrip_svc.py:240-241（使うのは code と id）。旧列の値は使わない。

## 5. 前例と検査
- 前例 03d770375（ADR-1026）: ADD 文を消した migration は「（削除済み）…ここに ADD を戻さないこと」、DROP の migration は DROP CONSTRAINT / DROP INDEX / DROP COLUMN の各 IF EXISTS。churn の許可表は足していない。
- チェック 10: scripts/check-migration-column-churn.js が scripts/run_all_migrations.sh の登録順で ADD→DROP を検出（.github/workflows/migration-guard.yml:518-550）。チェック 8: scripts/check-migration-value-writes.py --check 8（同 :411-425）。DDL は対象外。
- ADR: ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）、ADR-1026（docs/adr/ADR-1026-drop-products-type-master-id.md）、ADR-1024（docs/adr/ADR-1024-ai-readonly-db-path.md）。

## 6. CI での失敗（事実）
- run 39727376560 の「マイグレーションSQL 実行テスト（実DB）」は、product_formats が無い空の DB に新 migration だけを流し、`relation "public.product_formats" does not exist` で落ちた（/tmp/CC報告ファイル/format-work-parent/bin3b/mig_fail.txt:26）。ALTER TABLE を IF EXISTS 付きに直した。
