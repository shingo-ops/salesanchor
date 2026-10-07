# 設計：実行済み記録（ledger）付きのランナー（ADR-1005 段階2）【雛形・設計担当（Opus）が記入】

この文書は何か（1行）: デプロイで「まだ実行していない migration だけを 1 回実行する」ために、実行済みの記録の表と、ランナーの変更と、記録だけを入れる 1 回限りの手順を足す変更の設計。

親: ADR-1005（マイグレーションを「実行済み記録＋未実行のみ1回」方式へ。段階2）、ADR-1007。事実: docs/handoff/migration-ledger/recon.md（実装の担当が記入済み）
状態: 実装済み（Draft PR）。この雛形のうち「（設計担当が記入）」の欄は設計担当が埋める。**マージは PO 本人の GO（ADR-1005 の計画票）。段階1と、段3 のデプロイの後。**

## 1. 目的
（設計担当が記入）
参考の事実: ADR-1005 の KPI1「毎デプロイで再実行される古い手順の数 317 件 → 0 件（＋毎回実行リストの件数）」。ADR-155（migration で値を操作しない）に寄せた段3 の後で、値の書き込みが残らない状態から、1 回だけ流す方式に入る。

## 2. 現在地
docs/handoff/migration-ledger/recon.md の §1 を参照。

## 3. 変更（実装の担当が事実として記入）

### 3-1 ledger の表（専用スキーマ ops）
- ops.migration_ledger（id、scope、kind、filename、checksum、status（applied／baseline）、applied_at、duration_ms、git_sha、UNIQUE (scope, filename)）。作成は構造だけの migration（migrations/20261007_100000_create_migration_ledger.sql）。
- **専用スキーマにする理由**: public に作った表には salesanchor_app への SELECT/INSERT/UPDATE/DELETE が自動で付く（migrations/20260605_030000_create_salesanchor_app_role.sql:21-22）。ops にはその設定もスキーマの USAGE も無いので、アプリのロールは記録を書き換えられない。migration でも PUBLIC と salesanchor_app への権限を明示で取り消す。ops は tenant_NNN の走査にも入らない。

### 3-2 ランナー（scripts/run_all_migrations.sh と scripts/lib/migration_ledger.sh）
- 通常: ledger に無い手順だけを登録順に実行し、成功したものだけ記録する。記録済みで内容が同じものは飛ばす。
- 記録済みファイルの内容（sha256、改行は LF に正規化）が変わっていたら、**何も実行する前に**失敗する。
- 全件やり直しモード（戻し方）: `--full`（または MIGRATION_FULL_RERUN=1）。記録を無視して全件を実行し、記録を更新する。
- 毎回実行リスト: scripts/migration-ledger/every-run.list の 1 ファイル。現在は 0 件（実物を読んで「毎回の実行に意味がある」と確かめられたものが無かったため）。未確認のもの（ADR-1005 の C 22 件の一覧、run_py の 26 本、テナントごとのビュー）は載せていない。
- deploy.yml は変更しない（`bash scripts/run_all_migrations.sh` のまま）。

### 3-3 CI で、実行済みの書き換えを止める（デプロイの前）
- scripts/check-migration-immutability.sh と .github/workflows/migration-ledger-check.yml: base に既にある登録済みファイルが head で変わったら失敗する（毎回実行リストは除く）。直したいときは新しい手順を足す。段階2が main に入った後は、段3 のような「既存ファイルの書き換え」の PR は、この検査に止められる（段3 の PR を先にマージする理由）。

### 3-4 baseline（記録だけ入れる）の手順
- scripts/migration-ledger/record-baseline.sh: 登録された全ファイルを status=baseline で記録だけ入れる。**実行はしない。この PR では実行しない。**
- 前提（満たさないと --commit は拒否する）: (1) #3978・#4018・#4017 がマージされ、デプロイ済み（scripts/migration-ledger/step3-neutralized.list の 26 本に「NEUTRALIZED (ADR-」の印がある）。無効化の前に取ると、無効化の書き換えがすべてチェックサム不一致になる。(2) 段階1が済んでいる。(3) 作業ツリーがデプロイ済みの main のコミットと一致（--expect-sha）。
- 手順: dry-run（既定。DB に触れず、件数を表示）→ PO の「psql write」チケット → --commit --expect-sha <SHA>（ledger の表が無ければ、作成の migration だけを実行する）→ 件数の確認。baseline を取らずに ledger を有効にしても、1 回目のデプロイで全件が実行され、記録される（無効化後の内容で 1 回走るだけ）。

## 4. 代替案と選んだ理由
（設計担当が記入）

## 5. リスクと対処
（設計担当が記入）
参考の事実: 本番のデプロイの実行スクリプトと DB の構造を変える変更（ADR-136。マージには PO 本人の GO）。1 回目のデプロイで ops スキーマが作られる。段階1（テナントの正本）の前に有効にすると、新テナントにテナント向けの変更が届かない（recon.md §4）。

## 6. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 未記録の手順だけが実行され、成功したものだけ記録される | scripts/tests/test-migration-ledger.sh の T1・T2・T5（CI の migration-ledger-check.yml） |
| 記録済みファイルの内容が変わると、何も実行せずに失敗する | 同 T3 |
| 全件やり直しモードで、全件が実行され、記録が更新される | 同 T4、T12（本物の run_all_migrations.sh を偽の docker で通す） |
| baseline は実行せずに記録だけ入れ、段3 の無効化の印が無いと拒否する | 同 T8・T9・T10 |
| 実行済み（登録済み）ファイルの書き換えが CI で止まる | 同 T11 と scripts/check-migration-immutability.sh（migration-ledger-check.yml） |
| アプリのロールが記録に触れない | 本番での読み取り確認（デプロイ後。salesanchor_app で ops.migration_ledger を SELECT して権限エラーになること。未実施） |
| デプロイの手順実行時間が短くなる（目標は数秒。見込み） | デプロイのログ（段階2のデプロイ後 5 回の実測。未実施） |

## 7. 外部・過去事例の参照と我々への応用
（設計担当が記入）
参考の事実: ADR-1005 の外部事例（Flyway の flyway_schema_history と baseline／validate、Alembic の stamp）。

## 維持の仕組み
- 守り手: scripts/tests/test-migration-ledger.sh（ledger の論理）と scripts/check-migration-immutability.sh（実行済みの書き換えの検出）。設計担当（Opus）が、段階2のデプロイの前後で確かめる。
- 守り手: .github/workflows/migration-ledger-check.yml（上の 2 つを CI で実行する）。
- 対象: 実行済みの migration が書き換えられること、記録と実態がずれること。
