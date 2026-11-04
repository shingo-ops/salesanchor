# 便4 実装報告

## §0 着手前の点検（変更前の実物。すべて想定どおり）
```
219:def parse_loc(loc):
279:TAG_RE = re.compile(r"\s*\[(R-\d+)\]\s*$")
349:print("L2_UNTAGGED=" + L2_UNTAGGED)
```
```
142:    scope = [f for f in md if f.startswith("docs/specs/") or f.startswith("docs/ai-agents/")]
```
```
3:# 使い方: bash scripts/dev/doc-entry-weekly-check.sh（RESULT=OK なら rc=0、NG なら rc=1）
101:LV_BI="$(lib_val BOOKS_IMPORTED)"
191:  echo "RESULT=OK"; exit 0
193:  echo "RESULT=NG${NG}"; exit 1
```
```
153:check "出力の順" test "$ORDER" = "K1_DEF K1_DEF_FILES K1_DEF_MISSING L2_CHANNEL L2_DUP_LEDGER L2_DUP_ID L2_DUP_LINE L2 L2_UNTAGGED L3_INDEX L3_BOOKS L3_LEDGER L3_MATCH BOOKS_IMPORTED "
```
```
51:- 同じ役割の詳細参照（7つ）: `docs/agents/architect.md`・`docs/agents/evaluator.md`・`docs/agents/generator.md`・`docs/agents/governance.md`・`docs/agents/planner.md`・`docs/agents
```
```
104:## 話題の重なり表
108:| 話題 | 個人の本の所在 | リポジトリの所在 | 正 |
```
（`parse_loc` の中の `re.match(r"^(.*):(\d+)$", rest)` は変更前の 224 行にあった）

## 変えたファイル（`git diff --stat origin/main`）
```
 docs/handoff/doc-library-one-tree/card-impl-4.md   | 163 +++++++++++++++++++++
 scripts/ci/check_doc_index.py                      |   4 +-
 scripts/dev/doc-entry-weekly-check.sh              | 146 ++++++++++++++++++
 scripts/dev/doc-library-check.sh                   |  70 ++++++++-
 scripts/dev/test_doc_entry_weekly_check.sh         |  93 +++++++++++-
 scripts/dev/test_doc_library_check.sh              |  34 ++++-
 .../doc-index/unreached-new-runbook/case.json      |   7 +
 .../fixture-sub/zz-fixture-unreached.md.fixture    |   3 +
 8 files changed, 508 insertions(+), 12 deletions(-)
```
（この報告ファイルは次の commit で加わる）

## §5 の出力（tail の生出力）
### t1 `test_doc_library_check.sh`（終了コード 0。最後が `PASS 40/40`、FAIL 行なし）
```
PASS T1 字下げ @ を数える
PASS T1 rc=0
PASS T2 行の途中の @ を数える
PASS T3 バッククォートの中は数えない
PASS T3 囲みの中は数えない
PASS T4 4段目まで数える
PASS T4 5段目は数えない
PASS T5 AGENTS.md は1回
PASS T5 K1_DEF=4
PASS T6 2回 @ しても1回
PASS T6 K1_DEF=5
PASS T7 K1_DEF_MISSING=none
PASS T8 L2_CHANNEL=1
PASS T8 取り込み先が別ファイル → 0
PASS T9 L2_CHANNEL=unreadable
PASS T10 L2_DUP_LEDGER=1
PASS T10 '; ' 区切りでも1（所在1つの番号は数えない）
PASS T11 L2_UNTAGGED=1
PASS T12 L2=unreadable
PASS T12 L2_UNTAGGED=unreadable
PASS T12 L3_LEDGER=unreadable
PASS T13 L2_DUP_ID=1
PASS T14 L2_DUP_LINE=1
PASS T14 '- 本:' の行だけ同じ → 0
PASS T15 食い違い → L3_MATCH=no R-01,R-02
PASS T15 合う → L3_MATCH=yes
PASS T15 L3_INDEX=1 L3_BOOKS=1 L3_LEDGER=1
PASS T16 囲みの外 → 1
PASS T16 囲みの中 → 0
PASS T-L1 行が合う → 0
PASS T-L2 行がずれる → 1
PASS T-L3 見出しの文字が違う → 1
PASS T-L4 本の札つき見出し → 0
PASS T-L5 1段目の見出し → 0
PASS T-L6 言い直しは節の中なら合格 → 0
PASS T-L7 言い直しでも節の外 → 1
PASS T-L8 行番号なし → 1
PASS T-L9 台帳なし → unreadable
PASS T-L10 囲みの中 → 1
PASS 出力の順
PASS 40/40
```
### t2 `test_doc_entry_weekly_check.sh`（終了コード 0）
```
PASS T1 rc=0
PASS T2 K1=214
PASS T2 RESULT=NG K1>200
PASS T2 rc=1
PASS T3 K2_COPY=DIFF
PASS T3 RESULT=NG
PASS T4 K12_DUE=yes
PASS T4 RESULT=OK
PASS T5 K12_LAST=2026-11-01
PASS T5 K12_DUE=yes
PASS T6 K12_DUE=no
PASS T7 DOC_INDEX_CI=failure
PASS T7 RESULT=NG
PASS T8 DOC_INDEX_CI=pending
PASS T8 RESULT=OK
PASS T9 PEER_LAST=2027-01-24
PASS T9 RESULT=NG
PASS T10 RESULT=OK
PASS T11 PEER_LAST=2027-01-24
PASS T11 RESULT=NG
PASS T12 K12_OPEN_PR=URL
PASS T12 RESULT=OK
PASS T13 K12_OPEN_PR=none
PASS T14 K1_MISSING
PASS T14 RESULT=NG
PASS T15 DOC_INDEX_CI=unreadable
PASS T15 K12_OPEN_PR=unreadable
PASS T15 RESULT=NG
PASS T16 BOOKS_IN_CONTEXT=skipped
PASS T16 skipped だけでは NG にならない
PASS T16 L2=0
PASS T16 L3_MATCH=yes
PASS T17 L2=unreadable
PASS T17 RESULT=NG に L2= が入る
PASS T17 rc=1
PASS T18 K1=31
PASS T18 K1_FILES に ~/kb/x.md
PASS T19 K1=30
PASS T20 K1=31
PASS T20 z.md が無い
PASS T20 w.md が無い
PASS T20 K1_MISSING=none
PASS T21 K1=30
PASS T21 K1_FILES に ~/kb/n1.md
PASS T22 K1=28
PASS T22 repo/AGENTS.md が1回
PASS T23 K1=28
PASS T23 ~/kb/AGENTS.md が1回
PASS T24 K1=28
PASS T24 K1_MISSING=none
PASS T24 RESULT=OK
PASS T-G1 G1_OUTSIDE=0
PASS T-G1 G3_INTENT=yes
PASS T-G1 G6_NO_OWNER=0
PASS T-G1 K4_WIDE_UNREACHED=0
PASS T-G1 L2_LINE_NG=0
PASS T-G1 RESULT=OK
PASS T-G2 G1_OUTSIDE=1
PASS T-G2 G1_TABLE に E7:1
PASS T-G2 RESULT=NG
PASS T-G3 G1_OUTSIDE=0
PASS T-G4 Why の行は数えない
PASS T-G4 How to apply の行は数える
PASS T-G5 G1_OUTSIDE=0
PASS T-G5 report_style は 0
PASS T-G6 G1_TABLE に missing
PASS T-G6 G1_OUTSIDE=0
PASS T-G7 G1_OUTSIDE=unreadable
PASS T-G7 RESULT=NG
PASS T-G8 見出しなし → G3_INTENT=no
PASS T-G8 RESULT=NG
PASS T-G8 取り込みなし → G3_INTENT=no
PASS T-G9 G6_NO_OWNER=1
PASS T-G9 RESULT=NG
PASS T-G9 節なし → unreadable
PASS T-G10 K4_WIDE_UNREACHED=2
PASS T-G10 RESULT=NG
PASS T-G11 L2_LINE_NG=1
PASS T-G11 RESULT=NG
PASS 89 / FAIL 0
```
### t3 `check_doc_index.py --strict`（終了コード 0）
```
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
```
### t3b 見本 `run_rule_fixtures.py --only doc-index`（終了コード 0）
```
OK doc-index/reached-new-doc [doc index reachability] 期待=pass 終了コード=0
OK doc-index/unreached-new-runbook [doc index reachability] 期待=fail 終了コード=1
OK doc-index/unreached-new-spec [doc index reachability] 期待=fail 終了コード=1

違反の見本 2 件中 2 件で止まった・正しい見本 1 件中 1 件で通った・見本が一部を止めている決まり 1 件（10.2 秒）
```
### t4 `DOC_ENTRY_HOME=/nonexistent doc-library-check.sh`（終了コード 0。値はクラウドに実の HOME が無いため数えない）
```
K1_DEF=55
K1_DEF_FILES=/root/worktrees/salesanchor/release-doc-library-one-tree-checks/CLAUDE.md,/root/worktrees/salesanchor/release-doc-library-one-tree-checks/AGENTS.md
K1_DEF_MISSING=~/.claude/CLAUDE.md
L2_CHANNEL=unreadable
L2_DUP_LEDGER=0
L2_DUP_ID=0
L2_DUP_LINE=0
L2=unreadable
L2_UNTAGGED=0
L2_LINE_NG=82
L3_INDEX=0
L3_BOOKS=0
L3_LEDGER=5
L3_MATCH=no R-21,R-22,R-31,R-32,R-33
BOOKS_IMPORTED=0
```
### t5 `check-before-submit.sh`（終了コード 0）
```
  ○ check_rule_registry                                 0.2 秒
  ○ lint_tenant_schema (strict)                         0.5 秒
  ○ check-claude-size                                   0.1 秒
  ○ generate-adr-index --check                          0.2 秒
  ○ test-ui-governance                                  0.0 秒
  ○ check-ui-governance                                 0.0 秒
  ○ check-dangling-routes                               1.0 秒
  ○ test-dangling-routes                                0.2 秒
  ○ check-lessons-section                               0.0 秒
  ○ check-migration-registration-exists                 0.0 秒
  ○ test-migration-registration-exists                  0.1 秒
  ○ migration-value-writes diff --check 7               0.1 秒
  ○ migration-value-writes diff --check 8               0.0 秒
  ○ migration-value-writes repo                         0.1 秒
  ○ test_migration_value_writes                         5.8 秒
  - check-migration-column-churn                     関連パスの変更なし（CI と同じ条件で対象外）
  - check-migration-duplicate-registration           関連パスの変更なし（CI と同じ条件で対象外）
  ○ check-doc-heading-duplicates                        0.0 秒
  ○ test_check_rule_registry                            1.0 秒

-- 違反の見本（変更に関係するものだけ）--
  ○ 見本の選別（case.json）                      0.0 秒
  ○ run_rule_fixtures --only doc-index                 12.9 秒

-- 重い組（--full のときだけ）--
  - test-guard-evaluations (node --test)             CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    CI で確かめる（約 375 秒。--full で流せます）

== 必須チェック（docs/specs/rule-enforcement/required-checks.txt）==
  - pytest (SQLite + PostgreSQL RLS) — CI で確かめる（DB・redis が要る）
  - テナントスキーマ整合性チェック — CI で確かめる（DB が要る）
  △ マイグレーションSQL 実行テスト（実DB） — 一部だけ手元で流した。残りは CI で確かめる（登録ファイルの存在確認だけ。実DBでの実行は CI）
  △ models.py に新 Column → deploy.yml にマイグレーション追記必須 — 一部だけ手元で流した。残りは CI で確かめる（独立した台本の step だけ。ワークフロー内に直接書かれた step は CI）
  ○ ADR-072 tenant schema lint (strict mode) — 手元で流した
  - Lint & Dark Mode Check (ADR-067) — CI で確かめる（npm ci が要り時間がかかる）
  - gitleaks（シークレット漏洩検出） — CI で確かめる（履歴の走査は手元の見張りで止まるため、この段では流さない）
  ○ CLAUDE.md line count check — 手元で流した
  ○ ADR index is up to date — 手元で流した
  ○ UI governance gate — 手元で流した
  ○ dangling-route gate — 手元で流した
  ○ warn-direct-lesson-edit — 手元で流した
  - guard-authoring/evaluation — CI で確かめる（評価本体は GitHub のイベントと権限が要る（台本の試験は --full で流せる））
  - process-artifacts gate — CI で確かめる（PR 本文が要る。PR 作成時に validate-pr-body.sh が確かめる）
  - API contract is up to date — CI で確かめる（uv と npm ci が要る）
  ○ doc index reachability — 手元で流した

== 流した検査 ==
  ○ check_doc_index --strict                            0.8 秒
  ○ check_rule_registry                                 0.2 秒
  ○ lint_tenant_schema (strict)                         0.5 秒
  ○ check-claude-size                                   0.1 秒
  ○ generate-adr-index --check                          0.2 秒
  ○ test-ui-governance                                  0.0 秒
  ○ check-ui-governance                                 0.0 秒
  ○ check-dangling-routes                               1.0 秒
  ○ test-dangling-routes                                0.2 秒
  ○ check-lessons-section                               0.0 秒
  ○ check-migration-registration-exists                 0.0 秒
  ○ test-migration-registration-exists                  0.1 秒
  ○ migration-value-writes diff --check 7               0.1 秒
  ○ migration-value-writes diff --check 8               0.0 秒
  ○ migration-value-writes repo                         0.1 秒
  ○ test_migration_value_writes                         5.8 秒
  - check-migration-column-churn                     流していない: 関連パスの変更なし（CI と同じ条件で対象外）
  - check-migration-duplicate-registration           流していない: 関連パスの変更なし（CI と同じ条件で対象外）
  ○ check-doc-heading-duplicates                        0.0 秒
  ○ test_check_rule_registry                            1.0 秒
  ○ 見本の選別（case.json）                      0.0 秒
  ○ run_rule_fixtures --only doc-index                 12.9 秒
  - test-guard-evaluations (node --test)             流していない: CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    流していない: CI で確かめる（約 375 秒。--full で流せます）

== 版の違い（手元と CI）==
  手元: Python 3.11.18 / node v22.23.4
  CI  : Python 3.12 / node 22（guard-authoring だけ 24）
  版が違うので、最後の判定は CI です（この入口は提出前の補助）

合計 23.4 秒 / 必須 16 件を表示 / 流した検査 19 件 / 落ちた検査 0 件 / ログ /tmp/check-before-submit.D2Udbr（消さずに残します）
結果: ○ 流した検査は全部通りました（終了コード 0）
流した印を書きました: /home/user/salesanchor/.git/worktrees/release-doc-library-one-tree-checks/check-before-submit.ok
```

## K1 の期待値を直した試験（`test_doc_entry_weekly_check.sh`）
setup が `$H/.claude/CLAUDE.md` の末尾に 2 行（`## 報告の型`・`  @~/kb/00-rules/chat-layout.md`）を足し、その取り込みで `chat-layout.md`（1 行）が数えられるため、K1 が一律 +3。
- T1: 24 → 27
- T18: 28 → 31 / T19: 27 → 30 / T20: 28 → 31 / T21: 27 → 30 / T22: 25 → 28 / T23: 25 → 28 / T24: 25 → 28
- T2（K1=214）は CLAUDE.md を丸ごと置き換えるので変えない。

## 補足（カードに書いていない判断）
- setup の台帳に、足した 2 つの見出し（`報告の型`・`答える前に`）の行を 2 行足した。足さないと `L2_UNTAGGED=2` で T1 が `RESULT=NG` になるため（カードの「T1 で RESULT=OK のまま」を守る）。
- 見本 `unreached-new-runbook` は `docs/runbooks/fixture-sub/` に置いた。INDEX が `runbooks/` のフォルダを指しており、直下の .md は届いてしまうため。見本の実行は commit 済みの HEAD の写しで走るので、台本の変更を commit した後に流した。
- 実の HOME での `L2_LINE_NG=0`・`G1_OUTSIDE=0` は担当は流していない（カード §5 のとおり Opus が手元で）。

## 最後の HEAD の sha
実装の commit: 220971d99（この報告を足す commit が続く。最終の sha は push 後の `git rev-parse HEAD`）

DONE
