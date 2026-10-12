# 設計：run_py が毎デプロイ届ける値の書き込みの無効化 PR-3c（ADR-1007 段3）

この文書は何か（1行）: scripts/run_all_migrations.sh の run_py が毎デプロイ流す SQL と Python のうち、値を書く 14 件を、構造だけ残して止める変更の設計（is_super_admin の再付与の停止を含む）。

親: ADR-1007（PR #3985）、ADR-155（migration で値を操作しない）。事実: docs/handoff/neutralize-value-migrations-3c/recon.md（実装の担当が記入済み）。super admin の手順: docs/handoff/neutralize-value-migrations-3c/super-admin-bootstrap.md
状態: 設計案作成済み／Opus 自己審査 APPROVE（§5 の未確認は CI で確かめる）／PO 承認済み（ADR-1007 の進め方「進めて良い」2026-10-05、PR-3c の着手「y」2026-10-07、064 の扱い A・試験の扱い A）／実装済み（Draft PR #4023）。migrations/ と scripts/ を触るので、マージには PO の「GO #4023」が要る（ADR-136）。

## 1. 目的（PO に見える変化）
- 画面の見た目は変わらない。本番の今の値も変わらない（recon.md §2：14 件すべて、今の本番では 1 行も変えない）。
- デプロイのたびに、run_py の経路で値が書き戻されることが無くなる。人やアプリが直した値が、次のデプロイで元に戻らない（2026-10-05 の MEGAドリームex の書き戻しと同じ型を、この経路でも止める）。
- super admin（アプリ全体の管理者の権限）が、デプロイのたびに特定の人へ付け直されることが無くなる。PO の決まり「PO と担当エンジニアだけに付与し、一般のテナントには付与しない」（2026-10-07）を、付与も取り消しも人の手順だけで行う形にする。
- 段階2（#4020、実行済みの記録）の baseline を、無効化した後の中身で取れるようにする（段3 の残りを終える）。

## 2. 現在地
docs/handoff/neutralize-value-migrations-3c/recon.md の §1・§2・§3 を参照。要点：
- 段3a（#4018、SQL 18 本）・段3b（#4017、7 本）は、run_sql の経路だけを扱った。run_py の経路の 14 件（SQL 12 本、Python 5 本。064 を含む）が残っていた。
- is_super_admin を TRUE にする経路は 064 の UPDATE だけで、アプリ・スクリプト・管理 API には無い（recon.md §3）。

## 3. 変更
- SQL 12 本：値を書く文だけを外し、印のコメントと NOTICE に置き換えた。構造（表・列・索引・トリガー・COMMENT）は残した（recon.md §1）。
- Python 5 本：run_py が呼ぶ入口 main() を何もしない形にした。`backfill_schema`（adr119、country）は、試験が import するので、関数として残した。run_py の登録は変えない。
- 064：UPDATE とメールを含むコメントを外した。ファイルの中のメールは 0 件。列・索引・COMMENT は残した。
- 試験：backend/tests/test_value_migrations_neutralized_3c.py（新規）。TEST_PG_URL だけで動く試験 3 ファイルは、自分でキー・既定行を入れる形に直した（backend/tests/seed_inventory_data.py、新規）。
- super admin：docs/handoff/neutralize-value-migrations-3c/super-admin-bootstrap.md（PO の合意のもとの手動の SQL。users.id で指定し、メールは書かない）。
- 触らない：本番のデータ、deploy.yml、run_all_migrations.sh の登録、#4020 の一覧（申し送りは recon.md §5）。

## 4. 代替案と選んだ理由
- 064 を残す（毎デプロイで付け直す）：PO の決まりに反する。外した人が次のデプロイで戻るため、取り消しができない。採らない。
- 064 を「super admin が 0 人のときだけ付与」にする（C）：特定のメールがコードに残り、新しい環境でその人に自動で付く。付与の判断が人の手を離れる。PO の決定（A）で採らない。
- アプリに初期化の入口を作る（B）：新しい管理 API は、攻撃される入口を増やす。新しい環境を作る頻度に比べて重い。PO の決定（A）で採らない。
- Python のファイルを登録から外す：run_all_migrations.sh の登録を触ると、#3986・#4012・#4020 と同じファイルで食い違う。入口 main() だけを止め、登録は変えない形にした。段3a・3b の「ファイルは残して中身を止める」とも同じ形になる。
- 試験の seed を #4015 の seed_data.py に入れる：本 PR は #4015 に積んでいない（base は main）。そのため新しいファイルに置いた。#4015 のマージ後に、必要なら1か所へ寄せる（データを2か所に散らさないため、寄せる作業を残件として持つ）。

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| migrations/ と scripts/ を触る危険な PR | ADR-136。マージは PO の「GO #4023」の後。Draft のまま待つ |
| 新しい環境（作り直した DB）で、super admin が自動では付かない | super-admin-bootstrap.md の手動の SQL を、PO の合意のもとで流す。今の本番には影響しない（3 人の値は変えない） |
| 新しい環境で、permissions のキーやテナントの既定行が migration からは入らない | 段3a・3b と同じ扱い。本 PR では、super admin 以外の初期化の手順は足さない。今の本番には 19/19 キーが既にある（recon.md §2） |
| adr109 の「想定外の status でデプロイを止める」検査（:136、:262）も止まる | 本番の status は全件が正しいコード（recon.md §2）。値の検査はデプロイの止め役から外れる。アプリの側で status を検査しているかは未確認。これを、ADR-155 に沿った値の検査の代わりの場所として、残件に記録する |
| setup_tenant.py・sync_tenant_schema.py が 042・044・051 を catch-up に使う（recon.md §3） | 044 のトリガーは残る。042 の付与の代わりは tenant.py:1504-1541（オーナー・管理者への付与）にある。schema-check の CI で確かめる |
| TEST_PG_URL だけの試験 3 ファイルは、CI で動かない（test.yml:222-231） | py_compile と静的な試験だけを確認済み。PG での結果は未確認と記録する（§6）。CI で動かす変更は、#4015 の範囲 |
| 044 のトリガーが、無効化後も新しい行を同期するか | 構造は変えていない。実行は未確認。CI の Migration SQL Test の結果で確かめる |
| 試験 seed のファイルが2か所になる（#4015 の seed_data.py と、本 PR の seed_inventory_data.py） | #4015 のマージ後に寄せる。残件として記録する |

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 無効化した SQL 12 本に、値を書く文が残らず、構造が残る | backend/tests/test_value_migrations_neutralized_3c.py の静的な試験 |
| Python 5 本の main() が、DB に触れずに終わる | 同ファイルの試験 |
| 064 が is_super_admin を書き換えない。列と索引は残る。メールは 0 件 | 同ファイルの試験（test_064_keeps_the_column_but_never_regrants_super_admin） |
| backfill_schema を使う既存の試験が変わらない | test_adr119_backfill_source_guard.py、test_lead_country_control.py（CI） |
| 変更した migration が CI で通る | CI の Migration SQL Test・全件ドライラン・schema-check（結果は未確認） |
| デプロイ後に、is_super_admin の値が変わらない | デプロイ前後で、本番の users で is_super_admin が TRUE の人数が 3 のままであること（読み取り。未実施） |
| デプロイ後に、14 件の対象の値が変わらない | デプロイ後に recon.md §2 と同じ読み取りを流し、同じ件数であること（未実施） |

## 7. 外部・過去事例の参照と我々への応用
- 外部事例：Flyway・Alembic などの一般的な migration の道具では、migration は「構造を1回だけ変える」ものとして扱い、繰り返し流さない。初期の値（特に管理者の権限）は、migration ではなく、人の手順や別の初期化の仕組みで入れる。本 PR は、この考え方に合わせて、値の書き込みと管理者の付与を migration から外した。特定の数値には依存しないため、数値の事例は挙げない。
- 過去事例
  - SQL の無効化の前例は PR #3544、段3a（#4018）、段3b（#4017）。同じ印と NOTICE の形にそろえた。
  - Python の無効化の前例は無い。入口 main() だけを止め、試験が使う関数は残す形を、本 PR で初めて決めた。
  - 2026-10-05、seed の migration が MEGAドリームex の mark を書き戻した。毎回の流し直しで値が戻る事故の直接の理由である。

## 維持の仕組み
- 守り手: backend/tests/test_value_migrations_neutralized_3c.py（無効化した 17 本に値を書く文が戻らないことを検出）と .github/workflows/migration-guard.yml（新しい migration による値の書き込みの検出。既存ファイルの書き換えの検出は段4 の #4019）。設計担当（Opus）が、段4 の例外の一覧を作り直すときに、この 17 本が一覧に無いことを確かめる。
- 守り手: docs/handoff/neutralize-value-migrations-3c/super-admin-bootstrap.md（super admin の付与と取り消しの唯一の手順。PO の合意が要る）。
- 対象: 無効化した migration・スクリプトに、値を書く文が戻ること。is_super_admin が、デプロイで書き換えられること。
