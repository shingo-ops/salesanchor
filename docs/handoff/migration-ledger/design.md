# 設計：実行済み記録（ledger）付きのランナー（ADR-1005 段階2、2026-10-07）

この文書は何か（1行）：デプロイで「まだ実行していない migration だけを1回実行する」ために、実行済みの記録の表と、ランナーの変更と、記録だけを入れる1回限りの手順を足す変更の設計。

親：ADR-1005（migration を「実行済みの記録＋未実行のものだけ1回」の方式へ。段階2）、ADR-1007。事実：docs/handoff/migration-ledger/recon.md。

状態：設計案作成済み／Opus 自己審査 APPROVE（条件付き。§5 の未確認を参照）／実装済み（Draft PR）。

**マージの条件**
- マージは PO 本人の GO（ADR-1005 の計画票）による。
- 段階1（テナントの正本）と、段3 のデプロイの後にマージする。

## 1. 目的
- デプロイのたびに、登録済みの 318本の migration を最初から流し直すのをやめる。まだ流していないものだけを、登録の順に1回流す（ADR-1005 の KPI1：毎デプロイで再実行される古い手順の数 317件 → 0件、＋毎回実行リストの件数）。
- 流し終えた migration の書き換えを、デプロイの前（CI）で止める。直したいときは、新しい migration を足す。
- これにより、2026-10-05 のような値の書き戻しや、列を足して消す組の衝突（2026-10-03 の 1600列の上限）が、仕組みとして起きなくなる。

## 2. 現在地
docs/handoff/migration-ledger/recon.md の §1 を参照。段3（ADR-1007）で、値を書く migration を無効にした後に入る。

## 3. 変更
- 3-1 ledger の表（専用スキーマ ops）
  - ops.migration_ledger の列：id、scope、kind、filename、checksum、status（applied／baseline）、applied_at、duration_ms、git_sha。UNIQUE (scope, filename)。
  - 作成は、構造だけの migration（migrations/20261007_100000_create_migration_ledger.sql）で行う。
  - **専用スキーマにする理由**：public に作った表には、salesanchor_app への SELECT・INSERT・UPDATE・DELETE が自動で付く（migrations/20260605_030000_create_salesanchor_app_role.sql:21-22）。ops には、その設定もスキーマの USAGE も無い。そのため、アプリのロールは記録を書き換えられない。migration でも、PUBLIC と salesanchor_app への権限を明示して取り消す。ops は tenant_NNN の走査にも入らない。
- 3-2 ランナー（scripts/run_all_migrations.sh と scripts/lib/migration_ledger.sh）
  - 通常：ledger に無い手順だけを、登録の順に実行する。成功したものだけを記録する。記録済みで中身が同じものは飛ばす。
  - 記録済みのファイルの中身（sha256、改行は LF にそろえる）が変わっていたら、**何も実行する前に**失敗する。
  - 全件やり直しのモード（戻し方）：`--full`（または MIGRATION_FULL_RERUN=1）。記録を無視して全件を実行し、記録を更新する。
  - 毎回実行のリスト：scripts/migration-ledger/every-run.list の1ファイル。今は 0件（実物を読んで「毎回の実行に意味がある」と確かめられたものが無かったため）。確かめていないものは載せていない（§5）。
  - deploy.yml は変えない（`bash scripts/run_all_migrations.sh` のまま）。
- 3-3 CI で、実行済みのファイルの書き換えを止める（デプロイの前）
  - scripts/check-migration-immutability.sh と .github/workflows/migration-ledger-check.yml を使う。
  - base に既にある登録済みのファイルが、head で変わったら失敗する（毎回実行のリストは除く）。
  - 段階2 が main に入った後は、段3 のような「既存のファイルの書き換え」の PR は、この検査に止められる。段3 の PR を先にマージするのは、このためである。
- 3-4 baseline（記録だけを入れる）の手順
  - scripts/migration-ledger/record-baseline.sh：登録された全ファイルを、status=baseline で記録だけ入れる。**実行はしない。この PR では実行しない。**
  - 前提（満たさないと --commit は拒否する）
    1. #3978・#4018・#4017 がマージされ、デプロイ済みである（scripts/migration-ledger/step3-neutralized.list の 26本に「NEUTRALIZED (ADR-」の印がある）。無効にする前に取ると、無効にする書き換えが、すべてチェックサムの不一致になる。
    2. 段階1 が済んでいる。
    3. 作業ツリーが、デプロイ済みの main のコミットと一致している（--expect-sha）。
  - 手順
    1. dry-run（既定。DB に触れず、件数を表示）
    2. PO の「psql write」のチケット
    3. --commit --expect-sha <SHA>（ledger の表が無ければ、作成の migration だけを実行する）
    4. 件数の確認
  - baseline を取らずに ledger を有効にしても、1回目のデプロイで全件が実行され、記録される（無効にした後の中身で1回流れるだけ）。

## 4. 代替案と選んだ理由
- ledger を public に置く：アプリのロールに書き込みの権限が自動で付き、記録を書き換えられてしまう。そのため、専用スキーマにした。
- 外部の道具（Flyway・Alembic）を入れる：既存の 318本と、run_sql・run_py の2種類の手順と、テナントのループの書き方に合わせる手間が大きい。考え方（記録の表・baseline・検証）だけを取り入れ、今のスクリプトの上に作った。
- 毎回実行のリストに、#3965 の「C の 22件」をそのまま載せる：分類表が手元に無く、1件ずつ確かめられない。確かめられないものは載せずに、0件から始めた。必要になったら、確かめてから1行ずつ足す。
- 段3 の前に入れる：段3 の書き換えが止められ、値を書く migration を無効にできなくなる。そのため、順番を固定した。

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| 毎回の実行が本当に必要な migration を、リストから漏らしている（run_py の 26本、テナントごとのビュー 3本、#3965 の C の 22件は未確認） | マージの前に、この3つを1件ずつ読んで確かめ、要るものだけをリストに足す（未確認の間は、PO の GO の前提を満たさない） |
| 段階1 の前に有効にすると、新しいテナントに、テナント向けの変更が届かない（recon.md §4） | 段階1 の後にマージする（冒頭に明記） |
| baseline の取り方を間違える | record-baseline.sh が前提を検査して拒否する。既定は dry-run |
| 本番のデプロイの実行スクリプトと DB の構造を変える | ADR-136 の危険な PR。PO 本人の GO。戻し方は `--full`（今と同じ全件の流し直し） |
| run_all_migrations.sh の末尾で、ほかの PR と食い違う（#3986・#4012・#3998 も同じファイルを触る） | merge で解消する。登録の順は、main にある行の位置を変えずに、後ろに足す |

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 未記録の手順だけが実行され、成功したものだけ記録される | scripts/tests/test-migration-ledger.sh の T1・T2・T5（CI の migration-ledger-check.yml） |
| 記録済みのファイルの中身が変わると、何も実行せずに失敗する | 同 T3 |
| 全件やり直しのモードで、全件が実行され、記録が更新される | 同 T4、T12（本物の run_all_migrations.sh を、偽の docker で通す） |
| baseline は実行せずに記録だけを入れ、段3 の無効化の印が無いと拒否する | 同 T8・T9・T10 |
| 実行済み（登録済み）のファイルの書き換えが CI で止まる | 同 T11 と scripts/check-migration-immutability.sh（migration-ledger-check.yml） |
| アプリのロールが記録に触れない | デプロイの後に、本番で salesanchor_app から ops.migration_ledger を SELECT して、権限のエラーになることを確かめる |
| デプロイの手順の実行時間が短くなる | 段階2 のデプロイの後、5回分のデプロイのログで実測する |

## 7. 外部・過去事例の参照と我々への応用
- 外部事例
  - Flyway の flyway_schema_history（実行済みの記録）と baseline・validate（チェックサムで書き換えを検出）。
  - Alembic の stamp（実行せずに記録だけを入れる）。
  - この3つの考え方を、今のスクリプトの上に作った。数値の主張には使っていない。
- 過去事例
  - 2026-10-03 の 1600列の上限の事故（毎回の流し直しで、列を足して消す組が衝突した）と、2026-10-05 の値の書き戻しが、この仕組みを入れる理由である（ADR-1005・ADR-1007）。

## 維持の仕組み
- 守り手: scripts/tests/test-migration-ledger.sh（ledger の論理）と scripts/check-migration-immutability.sh（実行済みの書き換えの検出）。設計担当（Opus）が、段階2 のデプロイの前後で確かめる。
- 守り手: .github/workflows/migration-ledger-check.yml（上の2つを CI で実行する）。
- 対象：実行済みの migration が書き換えられること。記録と実態がずれること。
