# 設計：商品マスタ上書き migration 第2便（値書き部分の無効化 3d、2026-10-09）

状態：PO 承認済み（第2便の削除について「y」、2026-10-09）。設計者 Opus が範囲を C・E・L の 3 本に絞った。下書き PR まで。マージは PO の「GO #番号」が要る（ADR-136）。
事実：docs/handoff/neutralize-product-overwrite-3d/recon.md

## 1. 目的
デプロイのたびに流し直される migration のうち、商品マスタの値を上書きする書き込みが残っている 3 本から、値を書く部分を取り除く。DDL（表・列・制約の作成）は残す。#4018（ADR-1007 段3a）と同じ NEUTRALIZED 方式。画面の見た目と本番の今の値は変わらない。

## 2. 対象表
| 記号 | ファイル | 取り除く範囲（origin/main の行番号） | 残すもの |
|---|---|---|---|
| C | migrations/20260909_000000_public_products_phase2b_columns.sql | :60-144（Step2 の bootstrap コピー、INSERT ... ON CONFLICT DO UPDATE とループ） | DDL :43、:46-47、:53-58 |
| E | migrations/20260902_110100_tcg_products_classification_ids.sql | :79-365 の UPDATE、:367-385 の検証（RAISE EXCEPTION）。末尾 NOTICE は件数を書かない文言にする | FK 4 本 :27-77、冒頭ガード :13-22 |
| L | migrations/20260905_020000_tcg_fix_product_names_t004.sql | :15-89 の DO ブロック全体 | なし（NEUTRALIZED コメントと NOTICE のみ） |

印は「NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-09)」。#4018 の印（2026-10-07）と日付が違うため、試験は別リスト・別パラメータ化で足し、判定は既存の _strip_sql_comments と _VALUE_WRITE_PATTERNS を呼ぶ。

## 3. 触らないもの
scripts/run_all_migrations.sh の登録行、B・D・K・M、#4017/#4019/#4023 のブランチ、その他すべての migration。

## 4. 除外理由
- B（20260920_010000_phase3_fk_rewire_unit_condition.sql）：列の型変換の途中で使う一時列への書き込みで、同じファイルの後続 DDL が依存し、テストもファイル名で読むため、段5（記録して1回だけ流す仕組み #4020）で扱う。
- D（20260914_140000_unify_tcg_products_to_public.sql）：表の作りを変える変換 migration で、Step3 の FK 追加（:380-386 ほか）が Step2 のコピー（:179-280）に依存する。Step2 だけを外すと、変換の経路を通る環境で FK 追加が失敗する原因を作り込む。本番ではガード（tcg_uuid が UUID 型で存在しなければ Step2 を RETURN、:120-123）により値書きに届かない。段5 で B と一緒に扱う。
- K：空欄だけ埋める補充型で、上書きではない。
- M：無い行だけ足す補充型で、上書きではない。

## 5. 受入条件
|基準|検証方法|
|---|---|
| C, E, L に値書き文が残っていない | Read で 3 本の全文を確認。残る文がすべて DDL・ガード・NOTICE・コメント。試験 backend/tests/test_value_migrations_neutralized.py の静的試験 |
| DDL は変わっていない | git diff origin/main...HEAD -- migrations/ の削除行に DDL が無い |
| 変更ファイルは C, E, L、試験 1 本、docs、台帳だけ | git diff origin/main...HEAD --name-only |
| 検査がすべて通る | node scripts/check-migration-column-churn.js、scripts/check-migration-registration-exists.sh、scripts/check-migration-duplicate-registration.sh、bash -n scripts/run_all_migrations.sh、pytest |
| 変更した migration が CI で 2 回流れて通る | CI の Migration SQL Test |

## 6. 外部・過去事例の参照と我々への応用
該当なし：自社 migration の値書き除去で、出典と数値のそろった外部事例は確認していないため。
過去事例: #4018（ADR-1007 段3a）の NEUTRALIZED 方式に揃えた

## 7. 関連 ADR
ADR-155（migration で値を操作しない）、ADR-1005、ADR-1007（既存の値を書く migration は無効にする）。

## 維持の仕組み
- 守り手: backend/tests/test_value_migrations_neutralized.py（C・E・L に値を書く文が戻ることを検出）と .github/workflows/migration-guard.yml。
- 対象：値を書く文が、無効化した migration に戻ること。
