# 設計：試験が自分で seed を用意する（ADR-1007 段2）【雛形・設計担当（Opus）が記入】

この文書は何か（1行）: migration が値を書かなくなっても試験が壊れないように、試験が使うマスタのデータを試験側で持たせる変更の設計。

親: ADR-1007（PR #3985）。事実: docs/handoff/tests-own-seed-data/recon.md（実装の担当が記入済み）
状態: 実装済み（Draft PR）。この雛形のうち「（設計担当が記入）」の欄は設計担当が埋める。

## 1. 目的
（設計担当が記入）
参考の事実: 段3（値を書く migration の無効化）に入っても、試験が緑のままで、かつ「何も検証しなくなる」ことがない状態にする。

## 2. 現在地
docs/handoff/tests-own-seed-data/recon.md の §1・§2 を参照。

## 3. 変更（実装の担当が事実として記入）
- backend/tests/seed_data.py（新規）: 国・type_master・集計ルール・商品区分（PC_BOX・PC_SINGLE）の seed SQL の供給元。
- backend/tests/rls_bootstrap.py: seed_type_master、bootstrap_public_countries、bootstrap_inventory_aggregation_rules。
- 試験 8 ファイルの seed の呼び出し（recon.md §3）。migrations/ と本番は変更しない。

## 4. 代替案と選んだ理由
（設計担当が記入）

## 5. リスクと対処
（設計担当が記入）
参考の事実: 変更後の PG 試験は、ローカルの使い捨て PG16 で、基準と同じ 6 本が失敗し、新たな失敗は無い（recon.md §4-2）。CI での結果は未確認。

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 試験が countries 190 行を、migration でなく試験側の seed から得る | backend/tests/test_seed_data.py の test_country_seed_rows_match_frontend_constant、backend/tests/test_countries_master.py |
| test_lead_country_control が、test_countries_master に先に流されなくても通る | recon.md §4-3（基準で 1 failed → 変更後 5 passed） |
| 集計ルール 4 行の PG 試験が CI で動く | backend/tests/test_inventory_aggregation.py の skipif（RLS_ADMIN_DATABASE_URL に fallback）。CI の実測で確認（未確認） |
| type_master の行を 085・086 でなく試験側の seed から得る | 8 ファイルの seed 呼び出し、CI の PG 試験 |
| 試験に新しい CREATE TABLE が入らない | scripts/check_test_schema_dup.py（pass） |
| migrations/ と本番に変更がない | git diff origin/main...HEAD --name-only |

## 7. 外部・過去事例の参照と我々への応用
（設計担当が記入）

## 維持の仕組み
- 守り手: 設計担当（Opus）。段3 の PR で migration の値の書き込みを止めるとき、この変更の試験が緑のままであることを確かめる。
- 対象: 試験が migration のデータに頼る状態に戻ること。
