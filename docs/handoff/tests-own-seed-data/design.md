# 設計：試験が自分で seed を用意する（ADR-1007 段2、2026-10-07）

状態：設計案作成済み／Opus 自己審査 APPROVE（§6）／PO 承認済み（ADR-1007 の進め方「進めて良い」2026-10-05）／実装済み（Draft PR）。この PR は試験と試験の準備だけを変え、migrations/ と本番には触らない。

親：ADR-1007（PR #3985、未マージ）。事実：docs/handoff/tests-own-seed-data/recon.md。

## 1. 目的
- 試験が使うマスタのデータ（国・type_master・在庫の集計の決まり・商品区分）を、migration ではなく試験の側の1か所（backend/tests/seed_data.py）から用意する。
- これにより、段3 で値を書く migration を止めても、試験が壊れない。また、試験が「何も確かめなくなる」状態にならない。
- 試験の順番への依存（test_lead_country_control が test_countries_master の後でしか通らない）をなくす。

## 2. 現在地（recon.md の要約）
- 試験が migration のファイルを流して、そのデータを使っている。
  - countries 190行：20260621_010000
  - 集計の決まり 4行：20260620_010000
  - type_master：085・086
  - ほかの試験も同じ形
- test_lead_country_control.py:151-154 は、test_countries_master.py が先に流した状態に頼っていた。xdist の --dist=loadfile では、ファイルの間の順番は保証されない。
- test_inventory_aggregation.py の PG の試験は TEST_PG_URL だけを見ていて、CI（test.yml:222,224）では一度も動いていなかった。

## 3. 既存の ADR との関係
- ADR-155：マスタの値を migration で扱わない。この PR は、試験の側がそれに頼らないようにする準備である。
- ADR-1007 の決定2（頼っている試験を先に直してから無効化する）と、実施順序の段2 にあたる。

## 4. 変更
- recon.md §3 のとおり。
  - backend/tests/seed_data.py を新しく作る。試験の seed の唯一の元にする。
  - backend/tests/rls_bootstrap.py に seed の関数を足す。
  - 8 ファイルの seed の呼び出しを、ここに寄せる。
  - test_inventory_aggregation.py の skip の条件を、CI の環境に合わせる。
- 触らない：migrations/、本番、アプリのコード。

## 5. 代替案と選んだ理由
- 試験ごとにデータを書く案：同じデータが試験の数だけ散らばる（SSOT に反する）。そのため、seed_data.py の1か所にまとめた。
- migration のファイルを試験で流し続ける案：段3 で値の部分を止めると、試験の前提が消える。
- countries は、画面の側の一覧（frontend/src/constants/countries.ts）と同じであることを試験で確かめる。そうしないと、試験のデータと画面の一覧が食い違う。

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| 試験の seed と本番の値が食い違う | countries は画面の一覧と比べる試験を置く。集計の決まりと type_master は、migration の値と同じ値を seed に写した（recon.md §3）。段3 の後は、この seed が試験の正本になる |
| CI の PG の試験の結果が、ローカルと違う | ローカルの使い捨て PG16 では、基準と同じ 6本が失敗し、新しい失敗は無かった（recon.md §4-2）。CI の結果を PR で確かめる |
| 試験に、本番の表の定義が写される | scripts/check_test_schema_dup.py で検出する（pass） |

## 7. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 試験が countries 190行を、migration でなく試験側の seed から得る | backend/tests/test_seed_data.py の test_country_seed_rows_match_frontend_constant、backend/tests/test_countries_master.py |
| test_lead_country_control が、test_countries_master に先に流されなくても通る | recon.md §4-3（基準で 1 failed → 変更後 5 passed） |
| 集計の決まり 4行の PG の試験が CI で動く | backend/tests/test_inventory_aggregation.py の skipif（RLS_ADMIN_DATABASE_URL に fallback）。CI の実測で確認する |
| type_master の行を、085・086 でなく試験側の seed から得る | 8 ファイルの seed の呼び出しと、CI の PG の試験 |
| 試験に新しい CREATE TABLE が入らない | scripts/check_test_schema_dup.py（pass） |
| migrations/ と本番に変更がない | git diff origin/main...HEAD --name-only |

## 8. 外部・過去事例の参照と我々への応用
- 外部事例：試験のデータは、試験の準備（fixture）で用意し、本番の migration に頼らない。これは試験の設計で一般的な形である。特定の数値には依存しないため、外部の事例は挙げない。
- 過去事例：#3544（2026-09-18）で seed を無効にしたとき、試験のデータを fixture の seed_products() に移した（backend/tests/test_tcg_work_matching_integration.py:349-363）。同じやり方を、ほかのマスタにも広げた。

## 維持の仕組み
- 守り手: scripts/check_test_schema_dup.py（試験への本番の表の定義の写しを検出）と backend/tests/test_seed_data.py（seed と画面の一覧の一致）。設計担当（Opus）が、段3 の PR で、この試験が緑のままであることを確かめる。
- 対象：試験が migration のデータに頼る状態に戻ること。
