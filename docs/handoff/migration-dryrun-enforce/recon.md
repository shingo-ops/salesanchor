# recon: 全件試し実行（migration-full-dryrun）を「報告のみ」から「失敗したら止める」へ

- 基準: origin/main 0d8ee61e5（#4470 マージ後。#4466 1f24a465c を含む）
- 調査: Sonnet（生出力 /tmp/CC報告ファイル/dryrun_enforce/）＋ Opus の実物確認
- 既存 ADR 検索: `git grep -n -i "報告のみ\|強制しない\|dryrun\|ドライラン" -- docs/adr docs/handoff`（s5_grep_full.txt 371行）。ADR-1005・ADR-1007 が該当。「報告のみ→強制」と明記した ADR は無い。

## 「報告のみ」を作っている2か所（両方直さないと止まらない）
1. /Users/tanizawashingo/worktrees/salesanchor/release-migration-dryrun-enforce/.github/workflows/migration-test.yml:1813 step 名「全件ドライラン（報告のみ・強制しない）：登録された全ファイル − 除外一覧」、:1814-1817 のコメント、:1818 `continue-on-error: true`、:1824 `python3 scripts/migration-dryrun-report.py run --db jarvis_report --rounds 2 --psql psql`
2. /Users/tanizawashingo/worktrees/salesanchor/release-migration-dryrun-enforce/scripts/migration-dryrun-report.py:89 `return 0  # 報告のみ`。:2 と :8 の docstring に「強制はしない」「終了コードは常に 0（報告のみ）」。:68 と :69 の表示文言に「報告のみ」。
   - 実測（Opus、ローカル）: `--psql false`（全ファイル失敗）でも exit 0。「1周目: 成功 0 / 失敗 297」（/tmp/CC報告ファイル/dryrun_enforce/local_false.txt）。`--psql true` でも exit 0（local_true.txt）。

## 止める経路はすでにある
- 集約 job `migration-test`（表示名「マイグレーションSQL 実行テスト（実DB）」）: migration-test.yml:1829-1851。needs に migration-full-dryrun があり（:1831）、結果が success か skipped 以外なら exit 1（:1845）。
- main の Ruleset 15777895 の必須チェック15件に「マイグレーションSQL 実行テスト（実DB）」が入っている（s3_*.json）。classic の Branch Protection は 404。
- よって Ruleset と集約 job は変更不要。step が失敗するようにするだけで、マージが止まる。

## 走る条件
- pull_request（branches main, develop）のみ（:21-23）。paths-filter（:37-48）は migrations/**、scripts/migrate_*.py、scripts/check-migration-registration-exists.sh、scripts/run_all_migrations.sh、scripts/migration-guard/**、scripts/migration-dryrun-report.py、.github/workflows/migration-test.yml。
- 対象外の PR では job が skipped になり、集約は成功扱い。

## 直近の実測（s4_table.tsv、30 run）
- #4466 マージ（2026-10-17T12:03:37Z）より後に job が動いた2件は、どちらも 1周目 0・2周目 0（対象298）: 39031125623（inbox-badge-column）、39031405176（drop-products-type-master-id）。
- 所要時間は60〜78秒。

## 試験
- /Users/tanizawashingo/worktrees/salesanchor/release-migration-dryrun-enforce/scripts/tests/test_migration_value_writes.py:240-250 `test_run_reports_failures_but_exits_zero` が「失敗があっても終了コード 0」を確かめている。強制化するとこの試験の期待が逆になる。
- この試験ファイルを CI で動かしている workflow は無い。migration-guard.yml:403 はコメントで名前を挙げているだけ（`git grep` の結果）。
- 変更前のローカル実行: 24件中1件失敗（unittest_before.txt）。`test_protected_tables_include_the_four_added_masters`（:273）が 28 != 27。今回の変更とは関係なく、main の時点で既に失敗している。

## 危険パス
- scripts/check-process-artifacts.js:115-127 の危険パスに ^scripts/ が入っている。そのため report.py・tsv・試験の変更は PO の「GO #番号」が必要。.github/workflows/migration-test.yml は危険パスに入っていない。
- workflow-lint.yml（:86-90 has_aggregator_pattern）が migration-test.yml を検査する。step の continue-on-error を禁じる規則（:173-195）は migration-test.yml を対象にしていないため、外しても残しても検査結果は変わらない。

## 除外一覧
- scripts/migration-guard/dryrun-exclusions.tsv は33行で、データ行は27。:2-3 のコメントに「強制はしない。強制への切り替えは、報告を見てから別の PR で行う」とある。
