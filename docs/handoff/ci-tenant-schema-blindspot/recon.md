# recon — CIがテナント004向けmigrationを検査していない

この文書は何か（専門用語なしの1行）: 本番だけにあるデータ置き場に向けた変更が、公開前の自動検査を一度も通らずに本番へ届いている、という現状の報告。

親（設計仕様書）へのリンク: ../../specs/process-hardening/README.md

- 仕事名: ci-tenant-schema-blindspot
- 日付: 2026-09-04
- 実測時の origin/main SHA: 1fd1fbbbc3f32dc2131639e6ede050466fb24a13
- 対象ADR: なし（既存テーマ process-hardening の子テーマ候補として記録）
- 担当: architect
- 区分（STANDARD-WORKFLOW 1.8）: 既存の延長・修正（索引に process-hardening が公開済みのため新規仕様書を作らない）

本reconで「部品」とは次の2種を指す。① CIの検査ワークフロー ② migration ファイル。

---

## 0. 既存ADR検索の結果

本recon は既存テーマ process-hardening の子テーマ候補として記録するものであり、新規ADRを起案しない。

実行コマンドと結果（SHA 1fd1fbbb で実測）。

- git grep -l "Migration SQL Test" → .github/workflows/migration-test.yml / CONTRIBUTING.md / docs/handoff/fedex-label-validation-wizard/design.md
- git grep -l "migration-test-run" → .github/workflows/migration-test.yml / docs/handoff/migration-full-dryrun/design.md
- git grep -l "Migration Guard" → .github/workflows/migration-guard.yml / CONTRIBUTING.md / docs/handoff/incident-paypal-invoicing-false-complete/recon.md

---

## 1. 全体像

migration を検査する関所は .github/workflows/migration-test.yml の1本である。ジョブは6つ。

- .github/workflows/migration-test.yml:32 detect-changes
- .github/workflows/migration-test.yml:53 migration-registration-exists
- .github/workflows/migration-test.yml:72 migration-registration-exists-regression
- .github/workflows/migration-test.yml:88 migration-test-run
- .github/workflows/migration-test.yml:689 migration-full-dryrun
- .github/workflows/migration-test.yml:1370 migration-test

検査ロジックは別スクリプトではなくワークフロー内に直接記述されている。実測: git grep -l "migration-test-run" の結果に scripts/ 配下のファイルが1件も含まれない。

---

## 2. 共用部品

CIのテストDBに用意されるテナントスキーマは2つだけである。

- .github/workflows/migration-test.yml:230 CREATE SCHEMA IF NOT EXISTS tenant_001
- .github/workflows/migration-test.yml:421 CREATE SCHEMA IF NOT EXISTS tenant_002
- .github/workflows/migration-test.yml:806 CREATE SCHEMA IF NOT EXISTS tenant_001（migration-full-dryrun 側）

全1394行に対する実測で、CREATE SCHEMA は tenant_001 と tenant_002 の2種のみ。

---

## 3. 非共用部品

tenant_004 向けの migration は12本ある。うちデータを書き込むもの（INSERT または UPDATE を含む）は7本。

書き込みを含む7本:
- migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql
- migrations/20260903_130000_tcg_note_master_t004.sql
- migrations/20260903_150000_tcg_status_master_t004.sql
- migrations/20260903_160000_tcg_normalization_rules_t004.sql
- migrations/20260903_180000_tcg_products_mark_en_t004.sql
- migrations/20260903_210000_tcg_distribution_settings_t004.sql
- migrations/20260904_160000_tcg_magazine_promo_products_t004.sql

---

## 4. ルールの所在

- docs/specs/process-hardening/ideal-state.md:35 ミスをAIエージェントの注意で防ぐのではなく、機械が自動で止める・自動で正す状態にする（PO自筆）
- docs/specs/process-hardening/kgi.md:56 ②-a 新しい手順ミスが実測されたら、対応ガードのPRが立つまで機械が「未対応」警告を出す
- docs/specs/process-hardening/kgi.md:66 柱1-a PR作成後に .pr-number が確実に生成される

---

## 5. 維持の仕組み

守り手の実物と、その効き方。

- .github/workflows/migration-test.yml:88 migration-test-run が変更SQLを実DBで実行する。
- ただし tenant_004 スキーマが存在しないため、tenant_004 向け migration は冒頭のスキーマ存在チェックで即座に終了する。SQL本体は1行も実行されない。それでもジョブは success と判定される。

守り手が無い箇所（名指し）。

- tenant_004 向け migration の中身を、本番より前に実行して確かめる仕組みが存在しない。
- 実測: .github/workflows/migration-test.yml 全1394行に文字列 tenant_004 は0件。

---

## 6. 設計図との対照（一致／不足／余剰）

親 docs/specs/process-hardening/README.md の「子テーマ候補」表との対照。

| 既存の候補 | 本reconの事象との関係 | 判定 |
|---|---|---|
| 関所の自動再採点 | 別事象 | 対象外 |
| 宣言漏れの自動照合 | 別事象 | 対象外 |
| 本番SQL実行の固定化 | SSH引用符の話であり、CIの検査範囲の話ではない | 対象外 |
| テスト用スキーマ定義の集約 | conftest.py のテスト側DDL複製の話であり、CIのテナントスキーマ不足とは別 | 対象外 |
| 検証ヘルパーのSHA紐づけ | 別事象 | 対象外 |
| 記載なし | CIのテストDBに tenant_004 が無く、12本が検査されない | 不足・候補として追記 |

親 kgi.md の合格条件との対照。

| 合格条件 | 2026-09-04 の実測 | 判定 |
|---|---|---|
| 柱1-a PR作成後に .pr-number が確実に生成される | PR #3268 と PR #3272 の2回で .pr-number が存在せず、gh-pr-merge-safe.sh がマージを中断した | 未達（再現） |
| ②-a 新しい手順ミスが実測されたら機械が未対応警告を出す | 本reconの事象に警告は出ていない | 未達 |

---

## 7. ノイズと境界

本reconで見ないと決めた範囲。

- tenant_004 以外のテナント（tenant_001・tenant_002・tenant_006）の検査状況。
- migration-full-dryrun ジョブの詳細な挙動。
- 打ち手の選定（CIにスキーマを用意する／素通りを検知する／静的に検査する等）。本recon では選定しない。

数え上げの単位。

- 「12本」は migrations/ 配下でファイル名に t004 を含むものの数。
- 「7本」はそのうち文字列 INSERT INTO または UPDATE を含むものの数。
- 「0件」は .github/workflows/migration-test.yml 全文に対する文字列 tenant_004 の出現回数。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 本事象を既存のどの柱に位置づけるか、新しい柱にするか | POの判断 | 未解消 |
| 2 | PO承認済みの実装順序に割り込ませるか | POの判断 | 未解消 |
| 3 | tenant_004 のテーブル定義をCIに用意する場合、定義をどこから持つか | design局面で検討 | 未解消 |
| 4 | 書き込みを含む7本の中に、本番でしか通っていない他の誤りが残っていないか | 未調査 | 未解消 |

未解決ゼロ確認: 未解決4件あり。いずれもPO判断または設計局面で解消する。

---

## 発端となった事故（2026-09-04）

PR #3268 のマージ後、デプロイが失敗した。

- 生ログ: >>> [204/204] psql < migrations/20260904_160000_tcg_magazine_promo_products_t004.sql
- 生ログ: ERROR: null value in column "position" of relation "product_exclude_keywords" violates not-null constraint

原因は migration の INSERT が position 列（NOT NULL）を省略していたこと。CIの Migration SQL Test は success だったが、tenant_004 スキーマが無いため SQL本体は実行されていなかった。PR #3272 で修正し、デプロイは復旧した。

run_all_migrations.sh は毎デプロイで全204本を実行するため、修正するまで全てのデプロイが同じ箇所で失敗し続ける状態だった。

---

## 実測の出所

- ファイル実測: git show および git ls-tree および git grep を SHA 1fd1fbbbc3f32dc2131639e6ede050466fb24a13 指定で実行。ローカル作業ツリーは読んでいない。
- 事故の記録: GitHub Actions の deploy.yml run 33869888394 の生ログ。
