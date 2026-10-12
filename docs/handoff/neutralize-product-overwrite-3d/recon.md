# recon：商品マスタ上書き migration 第2便（3d）

この文書は何か（1行）: デプロイのたびに流し直される migration のうち、値を書く部分を取り除く 3 本（C・E・L）について、行番号つきの事実だけを記録したもの。

実測時の origin/main: 039bfd2330eab389b263c4f49a7e6b2c87fe18ab（2026-10-09）。行番号は同 SHA の migrations/ のもの。
根拠ファイル: /tmp/CC報告ファイル/second-batch-recon/classification_by_Read.txt、/tmp/CC報告ファイル/second-batch-recon/overlap.txt、/tmp/CC報告ファイル/second-batch-recon/per_file.txt
既存 ADR の検索: docs/adr/ で migration 値書き・ADR-155・ADR-1005・ADR-1007 を引いた。直接の ADR は ADR-155（migration で値を操作しない）、ADR-1007（既存の値を書く migration は無効にする）。前例は PR #4018（3a、同じ NEUTRALIZED 方式）。

## 1. 対象 3 本（classification_by_Read.txt の行より）
| 記号 | ファイル | 取り除いた値書き | 残したもの |
|---|---|---|---|
| C | migrations/20260909_000000_public_products_phase2b_columns.sql | :60-144（Step2 の DO ブロック。:103-135 の INSERT ... ON CONFLICT DO UPDATE と、それを回すループ） | :33-58 の DDL（ADD COLUMN と CREATE UNIQUE INDEX） |
| E | migrations/20260902_110100_tcg_products_classification_ids.sql | :79-365 の UPDATE（268 行の VALUES）と :367-385 の検証（RAISE EXCEPTION） | :13-22 のガード、:27-77 の FK 4 本 |
| L | migrations/20260905_020000_tcg_fix_product_names_t004.sql | :15-89 の DO ブロック全体（:43-47、:51-53 の UPDATE と :55-86 の検証） | なし（コメントと NOTICE のみ） |

## 2. 依存の確認（git grep -n の結果）
- C: migrations/20260909_000000_public_products_phase2b_columns.sql を名前で読むのは scripts/run_all_migrations.sh:624、scripts/migration-column-churn-allowlist.json:11（tcg_uuid の ADD の記述）、migrations/20260914_140000_unify_tcg_products_to_public.sql:36-44（コメントのみ）。backend/・.github/ からの参照は 0 件。値を前提とする RAISE EXCEPTION・FK は、C を名前で辿れる範囲に無い。
- C の同じコピーは migrations/20260914_140000_unify_tcg_products_to_public.sql:179-280（Step2）にも残る（本便では触らない）。
- E: scripts/run_all_migrations.sh:544 のみ。backend/・.github/ からの参照は 0 件。取り除く検証 :373-384 は、取り除く UPDATE の結果だけを確かめている。
- L: scripts/run_all_migrations.sh:577 のみ。backend/・.github/ からの参照は 0 件。:55-86 は読み取りの検証で、:65-70 以外は NOTICE のみ。

## 3. 本便に含めないもの（classification_by_Read.txt、overlap.txt より）
- B: migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql（一時列への書き込み。後続 DDL が依存。テストがファイル名で読む）
- D: migrations/20260914_140000_unify_tcg_products_to_public.sql。Step3 の FK 追加（:380-386、:437-443、:494-500 ほか）が Step2 のコピー（:179-280）で埋めた tcg_uuid を参照する。
- K: migrations/20260903_180000_tcg_products_mark_en_t004.sql（空欄だけ埋める補充型）
- M: migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql（無い行だけ足す補充型）
- overlap.txt に挙がる #4018 の対象（fix_tcg_type_dedup ほか 6 本）は本便と重ならない。

## 4. 未確認
- ローカルに PostgreSQL が無く、backend/tests/test_tcg_product_list_pg.py は 7 skipped。SQL として流した確認は CI に任せる。
- 本番への影響（デプロイ後に products の updated_at 等が動かないことの読み取り確認）はデプロイ前のため未実施。
