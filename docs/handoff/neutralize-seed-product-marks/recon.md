# recon: seed_product_marks migration が mark の修正を戻していた件（2026-10-05）

基準: origin/main a34381937。商品名・商品コード・件数のみ記載する。仕入元名・投稿本文は含まない。
元になった調査は「社外秘のローカル作業メモ（リポジトリ外）」にある。ここには事実と出所だけを写す。

## 0. 既存 ADR の検索（STANDARD-WORKFLOW）
- git grep -i と docs/adr/FEATURE-INDEX.md で検索した対象: ADR-155（マイグレーションで値を操作しない）、ADR-1006（起案中。実施順序の PR-0 にあたる）、ADR-136（危険 PR の GO）。
- 結果: docs/adr/ADR-155-product-master-ssot-csv-app.md:26「マイグレーションは商品マスタ関連テーブルの構造変更にのみ使用する。値の操作（INSERT / UPDATE / DELETE）は禁止する。」

## 1. 事実：何が mark を戻したか
1. migrations/20260604_010000_seed_product_marks.sql:23-25
   `UPDATE public.products p SET mark = v.mark, updated_at = NOW() FROM (VALUES ...) AS v(name, mark) WHERE p.tenant_id IS NULL AND p.name = v.name;`
2. 同ファイル :36 に `('MEGAドリームex', 'M3')`。名前が完全に一致する商品（id 440559）の mark を M3 にする。全部で 125 組（:25-:151 の VALUES）。
3. scripts/run_all_migrations.sh:264 に登録されている。scripts/run_all_migrations.sh:12-15 は「全マイグレーションは冪等設計」と書き、.github/workflows/deploy.yml:514 が毎デプロイで scripts/run_all_migrations.sh を実行する。つまりこの UPDATE は毎デプロイ流れる。
4. 本番の観測（読み取りのみ、2026-10-05）:
   - 商品 440559（PM0198）の mark は M3、updated_at は 2026-10-05 02:38:41.12765。2026-10-05 00:33:42Z に M2a へ直した記録が audit_log（id 27、new_values の mark は M2a）にある（PR #3968）。
   - 同じ 02:38:41 に 110 商品の updated_at が揃って書き換わっている（1秒の中に 110 行）。
   - audit_log に 02:38:41 の行は無い（アプリを通らない書き込み）。
5. 同時刻に動いていたデプロイ（gh run list）: Deploy to VPS run 37256103838（main、headSha 0e3f2f954、02:37:03〜02:39:42）と run 37256155526（main、headSha 3210edeea、02:37:52〜02:40:58）。どちらも 02:38:41 を含む。どちらが書いたかは 未確認。
6. 125 組と本番の比較（読み取り 1 本）:
   - 名前が完全に一致する商品: 110（1 商品 1 行。すべて tenant_id が NULL。1 件は is_active が偽、id 29）。
   - 一致する商品が無い名前: 15。
   - 110 件すべて updated_at が 2026-10-05 02:38:41。
   - 今の本番の mark と seed の mark が違う組: 0。ただしそれは 440559 が M3 に戻ったため。戻る前は ('MEGAドリームex', 'M3') だけが違っていた（手元の 2026-10-05 のスナップショット 109 行との照合でも、違うのは 440559 の 1 組だけ）。
7. デッキビルド修正（PR #3966）の対象 58・60・74・75・103・105 は、mark・名前・キーワードとも目標どおり。58・74・103 は updated_at だけが 02:38:41 に変わった（seed が同じ mark を書き直したため）。60・75・105 の名前は seed の名前と一致せず、触られていない。
8. 重複統合（PR #3969）の退役 3 行（440561・440571・440572）は is_active が偽のまま。残す 3 行（226・625・626）は有効のまま。この seed は is_active を書かない。

## 2. 同種の migration の前例（無効化の形）
- 無効化の PR: #3544「fix: neutralize product data in migrations (ADR-155 Stage C)」、commit fd7423f99（2026-09-18）。13 本の migration の本体を no-op にした。
- 形（migrations/20260603_030000_seed_dragonball_products.sql:14-19）:
  `-- NEUTRALIZED (ADR-155, 2026-09-18):` / `-- 商品マスタデータはアプリ画面/CSVで管理する。migrationは構造変更のみ。` / `-- 元の内容は git history で参照可能。` / `DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: ...'; END $$;`
- 同じ形: migrations/20260604_040000_seed_tcg_products_8series.sql:35、migrations/20260615_235900_seed_pokemon_mega_products.sql、migrations/20260913_010000_seed_dragonball_products_v2.sql、migrations/20260913_020000_seed_onepiece_products.sql、migrations/20260913_030000_seed_unregistered_products.sql。
- 20260604_010000_seed_product_marks.sql はその 13 本に入っていなかった。
- この seed を参照するテストは無い（git grep: 自分自身のファイルと scripts/run_all_migrations.sh:264 だけ）。

## 3. 他に public.products を書き戻す migration の確認
- public.products を UPDATE する登録済み migration（git grep -n の結果）: 20260602_020000（tcg_type）、20260603_000000（product_kind）、20260604_020000（出荷の既定値）、20260605_000000（display_order）、20260616_000000（tcg_type）、20260916_130000（work_id）。mark と name を書くものはこの 20260604_010000 だけ。
- migrations/20260902_110100_tcg_products_classification_ids.sql と migrations/20260903_180000_tcg_products_mark_en_t004.sql は PM0198 の行を持つが、書く先は tenant_004.tcg_products（20260903_180000 の UPDATE は :61）。どちらも tcg_products が無ければ飛ばす（20260902_110100:19-22、20260903_180000:28-31）。scripts/run_all_migrations.sh:548 と :563 に登録されている。public.products には触らない。tenant_004.tcg_products が本番に今あるかは 未確認（migrations/20260909_000000_public_products_phase2b_columns.sql の冒頭に、2026-10-04 時点で存在するとの記述）。

## 4. migration-guard との関係
- .github/workflows/migration-guard.yml:394-493（チェック 7）は PR で追加した行だけを見る。.github/workflows/migration-guard.yml:485-593（チェック 8）は新規ファイルだけを見る。どちらも、この seed が入った時点より後にできた検査なので、すでに入っていたこの UPDATE は止められなかった。
- 変更後の追加行は NOTICE の 1 行だけで、保護対象の表名を含まない（差分から抽出して手元で確認）。

## 5. 未確認・実施していないこと
- 手元で SQL を流しての確認: していない（書き込みを防ぐフックが、手元の使い捨て DB への実行も止めた）。変更後の本文は RAISE NOTICE だけ。CI の Migration SQL Test で確かめる。
- 02:38:41 を書いたデプロイがどちらか: 未確認。
- 本番の 110 件と手元スナップショットの 109 件の差（1 件）は、無効の商品 id 29 によるもの。
