# 設計：run_py が毎デプロイ届ける値の書き込みの無効化 PR-3c（ADR-1007 段3）【雛形・設計担当（Opus）が記入】

この文書は何か（1行）: scripts/run_all_migrations.sh の run_py が毎デプロイ流す SQL と Python のうち、値を書く 14 件を、構造だけ残して止める変更の設計（is_super_admin の再付与の停止を含む）。

親: ADR-1007（PR #3985）、ADR-155（migration で値を操作しない）。事実: docs/handoff/neutralize-value-migrations-3c/recon.md（実装の担当が記入済み）。super admin の手順: docs/handoff/neutralize-value-migrations-3c/super-admin-bootstrap.md
状態: 実装済み（Draft PR）。この雛形のうち「（設計担当が記入）」の欄は設計担当が埋める。

## 1. 目的
（設計担当が記入）
参考の事実: 毎デプロイ届く値の書き込みのうち、段3a（SQL の 18 本）・段3b（7 本）の対象外だった、run_py 経由の 14 件。064 は、デプロイのたびに users.is_super_admin を TRUE に戻していた（人が外しても戻る）。

## 2. 現在地
docs/handoff/neutralize-value-migrations-3c/recon.md の §1・§2・§3 を参照。

## 3. 変更（実装の担当が事実として記入）
- SQL 12 本: 値を書く文だけを外し、構造と存在確認は残した（recon.md §1）。
- Python 5 本: run_py が呼ぶ入口 main() を何もしない形にした。`backfill_schema`（adr119、country）は、試験が import するので、関数として残した。
- 試験: backend/tests/test_value_migrations_neutralized_3c.py（新規）。TEST_PG_URL だけの試験 3 ファイルは、自分で seed を入れる形に直した（backend/tests/seed_inventory_data.py、新規）。
- super admin: docs/handoff/neutralize-value-migrations-3c/super-admin-bootstrap.md（PO の合意のもとの手動の SQL）。
- 本番のデータには何も実行しない。baseline（#4020）は、本 PR のデプロイ後に取る。

## 4. 代替案と選んだ理由
（設計担当が記入）
参考の事実: 064 は、PO の決定（A）で、再付与を外し、新しい環境の初期化は手動の SQL にした。B（アプリに初期化の入口）、C（0 人のときだけ付与）は採らない。

## 5. リスクと対処
（設計担当が記入）
参考の事実: migrations/ と scripts/ を触る危険な PR（ADR-136。マージには PO の「GO #番号」）。本番との比較（読み取り）は、14 件すべて変更 0（recon.md §2）。新しい環境では、super admin が自動では付かない（手動の SQL。PO の合意が要る）。

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 無効化した SQL 12 本に、値を書く文が残らず、構造が残る | backend/tests/test_value_migrations_neutralized_3c.py の静的な試験 |
| Python 5 本の main() が、DB に触れずに終わる | 同ファイルの試験 |
| 064 が is_super_admin を書き換えない。列と索引は残る | 同ファイルの試験（test_064_keeps_the_column_but_never_regrants_super_admin） |
| backfill_schema を使う既存の試験が変わらない | test_adr119_backfill_source_guard.py、test_lead_country_control.py（CI） |
| 変更した migration が CI で通る | CI の Migration SQL Test・全件ドライラン（結果は未確認） |
| デプロイ後に、is_super_admin の値が変わらない | デプロイ後に、本番の users で is_super_admin が TRUE の人数が同じであること（読み取り。未実施） |

## 7. 外部・過去事例の参照と我々への応用
（設計担当が記入）
参考の事実: SQL の前例は PR #3544、段3a（#4018）、段3b（#4017）。Python の無効化の前例は無い。

## 維持の仕組み
- 守り手: backend/tests/test_value_migrations_neutralized_3c.py（無効化した 17 本に値を書く文が戻らないことを検出）と .github/workflows/migration-guard.yml（新しい migration による値の書き込みの検出。既存ファイルの書き換えの検出は段4）。設計担当（Opus）が、段4で確かめる。
- 対象: 無効化した migration・スクリプトに、値を書く文が戻ること。is_super_admin が、デプロイで書き換えられること。
