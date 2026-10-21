# design: 全件試し実行（migration-full-dryrun）の失敗21本を0本にする

- 状態: 設計（Opus）。実験 A〜F を CI で実測済み。PO 設計承認「y」（2026-10-17 チャット「試し実行の失敗21本を直す設計を新しく始めるか」）。マージは PO の GO 待ち。
- 対象ADR: ADR-1007（段2「試験の準備の側にデータを移す」:97）、ADR-1005（:19,:27 対象外の理由を明らかにし戻せるものは戻す）
- recon: docs/handoff/migration-dryrun-baseline/recon.md

## 目的
空のDBに全 migration を流す試し実行（.github/workflows/migration-test.yml の migration-full-dryrun、報告のみ）で、2周目に21本が失敗している（基準 run 39009175807、ログ 6703行「2周目: 成功 268 / 失敗 21」）。新しい空の環境を migration から作り直せるかを、この試し実行で正しく見られるようにする。

## 原因（実測で確定）
1. 除外一覧 scripts/migration-guard/dryrun-exclusions.tsv の5行が「public.products 等が無いため落ちると見込まれる（未実行）」という見込みで除外されていた。実際は Sprint1 python（migration-test.yml:1630）が public.products を作るため、5本とも流すと成功した。除外されていたため、それらが作る表・列（analysis_results・extraction_*・tcg_*_master・tenant_discord_ticket_config・products.mark・products.work_id の型）が無く、後続19本と1周目の2本が落ちていた。
2. 試験用の手書きの土台（migration-test.yml:1150-1630）の tenant_001/002.leads に、本番にある company_name VARCHAR(255)・notes TEXT が無かった（作成元 migrations/003_add_phase1_tenant_tables.sql の leads 定義。本番 tenant_001.leads で varchar(255)・text を読み取り確認）。migrations/20260703_010000_txn_backbone_ben1a.sql:24,36 がこの2列へ INSERT して落ちていた。

## 変更前後
| 対象 | 変更前 | 変更後 |
|---|---|---|
| dryrun-exclusions.tsv | 下記5行あり | 5行削除: 20260602_000000_add_products_central_columns / 20260602_120000_add_discord_ticket_config / 20260919_010000_master_ssot_work_id_recast / 20260919_020000_master_ssot_public_tables / 20260921_110000_pipeline_tables_public |
| migration-test.yml 手書きの土台 tenant_001.leads・tenant_002.leads | company_name・notes なし | customer_name の次に `company_name VARCHAR(255),` `notes TEXT,` を追加（各2行、計4行） |

触らない: migrations/ 配下・scripts/run_all_migrations.sh・deploy.yml・本番DB。試し実行は「報告のみ」のまま（強制化は別便）。

## 影響範囲
- CI の試験だけ。本番のデプロイ・DB には影響しない（migration-test.yml は pull_request でのみ動く。tsv は試し実行の対象選びだけに使う）。
- 実験E/F の run で、同じワークフローの他ジョブ（migration-test-run 系・登録ファイル存在点検）に新しい失敗なし。

## 実測（Draft PR #4466 の CI）
| 実験 | 変更 | 1周目 失敗 | 2周目 失敗 | run |
|---|---|---|---|---|
| 基準 | なし | 24 | 21 | 39009175807 |
| A | 除外2行（20260919_020000・20260921_110000） | 5 | 3 | 39027579225 |
| B | A＋20260602_120000 | 4 | 2 | 39027751242 |
| D | B＋20260602_000000・leads.company_name | 2 | 1 | 39028310632 |
| E | D＋leads.notes | 1 | 0 | 39029145777 |
| F | E＋20260919_010000 | 0 | 0 | 39029580449 |

F のログ: 1周目 6442行「成功 297 / 失敗 0」、2周目 6740行「成功 297 / 失敗 0」、ERROR 行 0（/tmp/CC報告ファイル/dryrun_exp/F_log_clean.txt）。

## 受入条件
|基準|検証方法|
|---|---|
|K1 2周目の失敗が0本|マージ前の最終 HEAD の migration-full-dryrun ログで「2周目: 成功 N / 失敗 0」|
|K2 1周目の失敗が0本|同ログで「1周目: 成功 N / 失敗 0」|
|K3 同じワークフローの他ジョブに新しい失敗が無い|gh pr checks で process-artifacts gate（GO記録待ち）以外が pass|
|K4 本番に影響しない|git diff origin/main...HEAD --name-only に migrations/・deploy.yml・run_all_migrations.sh が無い|

## 戻し方
この PR を revert する（tsv の5行と leads の4行が元に戻る）。本番には何も入らないので本番側の戻しは不要。

## 残り（別便）
- 試し実行を「報告のみ」から「失敗したら止める」へ切り替える（0本になったので可能になった。1件ずつ変える原則に従い別便）。
- 除外一覧の残り（初期タイムスタンプの Python 依存など）も同じ方法で実測して戻せるか確かめる。
- 20260919_030000 の DO ブロックは、表がビューに変わった後は ALTER をスキップするため、2周目は成功しても外部キーは作られない（実験 D/E の2周目）。この挙動は別途確認する。

## 維持の仕組み
守り手: migration を追加・変更する PR の審査役（Opus）。migration-full-dryrun の集計行（1周目・2周目の失敗本数）を PR ごとに見る。除外一覧へ行を足すときは、見込みではなく実測の ERROR を理由欄に書く。

## 外部・過去事例の参照と我々への応用
- ADR-1005（docs/adr/ADR-1005-migration-run-once-ledger.md :19,:27）: 全件試し実行が多くを対象外にしていた事例と「理由を明らかにし、戻せるものは戻す」方針。今回は見込みだけの除外5行を実測で戻せることを確かめて戻した。
- 外部事例は使わない（理由: 当リポジトリ固有の除外一覧と手書きの土台の不整合で、CI の実測が直接の根拠になるため）。
