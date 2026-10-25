# 実装カード 段5b — 古さの見張りの対象に AGENTS.md を足す

> この文書は何か：doc-agenda-nav 段5b の作業指示書です。.github/workflows/claude-md-staleness-check.yml（90日更新が無い決まりの文書を四半期ごとに Issue にする見張り）の探す対象に AGENTS.md を足し、node_modules の中を数えないようにします。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §26: 段5の設計判断（この便の根拠。§26-4 が作り方と受け入れ基準）
  - §8 段5の行
- 対象ADR: ADR-1040（Accepted）。関連: ADR-076
- 状態: 設計は Opus の設計判断（§26、2026-10-25）。PO の承認は 2026-10-25 の「1」（見張りを強める段へ進む：決まりの文書が古いまま放っておかれていないかも見張る）。5a は PR #4733 でマージ済み（origin/main 01e53da6b）。
- 危険便かどうか: 触るファイルは scripts/check-process-artifacts.js の DANGEROUS_PATTERNS に当たらない（§26-1）。workflow-lint.yml は触らない。GO は ADR-1003 の委譲により Opus が書きます（担当は GO 記録を書かず、マージもしない）。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 審査: Opus（reviewer を model "opus" で新しく起こす）
  - GO とマージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段5b の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

- やること: §4 の1ファイルの書き換えと、§5 の確かめ、PR の作成。
- やらないこと:
  - 日数（THRESHOLD_DAYS=90）・実行の時期（cron :12）・Issue の作り方（:84-86）・actions/checkout の版（:25）を変えない。
  - 手動実行（workflow_dispatch）をしない。`gh workflow run` を使わない（Issue #3904 が開いたままで、同じ内容の Issue がもう1本できる）。
  - Issue #3904 を閉じない・書き込まない。
  - ほかの .github/workflows/ のファイル、特に workflow-lint.yml を触らない。

## 2. 前提の事実（Opus が 2026-10-25 に確かめた。起点は origin/main 01e53da6b）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | :45-48 の find は `-name "CLAUDE.md"` だけを探し、除外は `./.git/*`・`./node_modules/*`・`./frontend/node_modules/*` | .github/workflows/claude-md-staleness-check.yml:45-48 |
| F2 | 「CLAUDE.md」と書いてある文は :1・:3・:18・:29・:57・:71・:85 の7か所 | 同ファイル |
| F3 | 起点で `\( -name CLAUDE.md -o -name AGENTS.md \)`・node_modules 除外の find が出すのは9本（AGENTS.md 3本・CLAUDE.md 6本） | 起点の作業場所での find |
| F4 | 90日を超えるのは backend/scripts/CLAUDE.md（146日）と backend/tenant/CLAUDE.md（144日）の2本だけ | 同上で `git log -1 --format=%ct` |
| F5 | この作業場所に frontend/node_modules は無い | `ls -d frontend/node_modules` |

一つでも実物と違えば、§6 の分岐に従う。

## 3. 触るファイル（これ以外は触らない）

| ファイル | 変えるところ |
|---|---|
| .github/workflows/claude-md-staleness-check.yml | :1・:3・:18・:29・:45-48・:57・:71・:85 |

## 4. 作り方（Edit。変更前の文を1つずつ置き換える）

| 行 | 変更前 | 変更後 |
|---|---|---|
| :1 | `name: CLAUDE.md 定期見直しチェック（90日）` | `name: CLAUDE.md・AGENTS.md 定期見直しチェック（90日）` |
| :3 | `# 四半期ごとに CLAUDE.md ファイルの最終更新日を確認し、` | `# 四半期ごとに CLAUDE.md・AGENTS.md ファイルの最終更新日を確認し、` |
| :7 | `# 参照: docs/adr/ADR-076-claude-md-hierarchy.md` | `# 参照: docs/adr/ADR-076-claude-md-hierarchy.md・ADR-1040（本文は AGENTS.md へ移った）` |
| :18 | `    name: CLAUDE.md 陳腐化チェック` | `    name: CLAUDE.md・AGENTS.md 陳腐化チェック` |
| :29 | `      - name: Check CLAUDE.md staleness (90 days)` | `      - name: Check CLAUDE.md and AGENTS.md staleness (90 days)` |
| :57 | `            echo "全 CLAUDE.md ファイルは ${THRESHOLD_DAYS}日以内に更新されています"` | `            echo "全 CLAUDE.md・AGENTS.md ファイルは ${THRESHOLD_DAYS}日以内に更新されています"` |
| :71 | `            echo "以下の CLAUDE.md ファイルが90日以上更新されていません。内容が実態と合っているか確認してください。"` | `            echo "以下の CLAUDE.md・AGENTS.md ファイルが90日以上更新されていません。内容が実態と合っているか確認してください。"` |
| :85 | `            --title "CLAUDE.md 定期見直し ${YEAR_Q}（90日以上未更新あり）" \` | `            --title "CLAUDE.md・AGENTS.md 定期見直し ${YEAR_Q}（90日以上未更新あり）" \` |

- :7 は F2 の7か所に含まれないが、根拠の ADR を足すために変える（行数は変わらない）。

:45-48 の変更前:

```
          done < <(find . -name "CLAUDE.md" \
            -not -path "./.git/*" \
            -not -path "./node_modules/*" \
            -not -path "./frontend/node_modules/*")
```

変更後:

```
          done < <(find . \( -name "CLAUDE.md" -o -name "AGENTS.md" \) \
            -not -path "./.git/*" \
            -not -path "*/node_modules/*")
```

- 行は1つ減る（:48 以降が1行ずつ上がる）。上の表の :57・:71・:85 は変更前の行番号。
- YAML の `run: |` の中なので、括弧は `\(`・`\)` のまま書く（エスケープを二重にしない）。

## 5. 確かめ方

生出力はすべて `/tmp/CC報告ファイル/an-s5b/impl/` に保存する（無ければ作る）。各コマンドは作業場所への cd から始める。

### 5-0. 変更前の値（§4 より先に実行する）

1. 作業場所で、§4 の変更前の run（:32-58）と同じ処理を手元の bash で回す。GitHub 専用の `$GITHUB_OUTPUT` は `/tmp/CC報告ファイル/an-s5b/impl/gh-output-before.txt` に置き換える。手順: Write で `/tmp/CC報告ファイル/an-s5b/impl/run-before.sh` を作り、中身は :32-58 の行を字下げを外して写したもの（先頭に `GITHUB_OUTPUT=/tmp/CC報告ファイル/an-s5b/impl/gh-output-before.txt` の1行を足す）。`bash /tmp/CC報告ファイル/an-s5b/impl/run-before.sh > /tmp/CC報告ファイル/an-s5b/impl/t1-before.txt 2>&1; echo rc=$? >> /tmp/CC報告ファイル/an-s5b/impl/t1-before.txt`。stale_files.txt は作業場所にできるので、終わったら `rm stale_files.txt`。
2. 期待: 対象ファイルの一覧に backend/scripts/CLAUDE.md・backend/tenant/CLAUDE.md の2本、gh-output-before.txt が `stale=true`。

### 5-1. T1（90日で今と同じ2本が出る）

§4 の後、5-0 と同じやり方で変更後の run（:32-57）を `run-after.sh` に写し、出力先を t1-after.txt・gh-output-after.txt にする。期待: 5-0 と同じ2本・`stale=true`。終わったら `rm stale_files.txt`。

### 5-2. T2（AGENTS.md も対象になる）

run-after.sh の `THRESHOLD_DAYS=90` を `THRESHOLD_DAYS=-1` にした写し `run-after-all.sh` を作り、出力先を t2.txt にする。期待: 9本（AGENTS.md・frontend/AGENTS.md・backend/AGENTS.md を含む。node_modules の中は0本）。終わったら `rm stale_files.txt`。リポジトリのファイルは変えない（写しだけを変える）。

### 5-3. T3（node_modules の中は数えない）

`mkdir -p frontend/node_modules/s5probe` と Write で frontend/node_modules/s5probe/AGENTS.md（`probe` の1行）を作り、run-after-all.sh を回して t3.txt に保存。期待: s5probe は出ない（git の履歴が無いので :39 で飛ばされるため、find の出力そのものも見る: run-after-all.sh とは別に、§4 の変更後の find だけを `find . \( -name "CLAUDE.md" -o -name "AGENTS.md" \) -not -path "./.git/*" -not -path "*/node_modules/*" > /tmp/CC報告ファイル/an-s5b/impl/t3-find.txt` で保存し、s5probe が無いことを確かめる）。その後 `rm frontend/node_modules/s5probe/AGENTS.md`、`rmdir frontend/node_modules/s5probe`、`rmdir frontend/node_modules`（F5 で無かったので消す）。`rm stale_files.txt`。

### 5-4. T4（文法）

`actionlint .github/workflows/claude-md-staleness-check.yml > /tmp/CC報告ファイル/an-s5b/impl/t4.txt 2>&1; echo rc=$? >> /tmp/CC報告ファイル/an-s5b/impl/t4.txt`。期待: rc=0・指摘0件。

### 5-5. 差分

`git diff $(git merge-base origin/main HEAD) --stat > /tmp/CC報告ファイル/an-s5b/impl/diff-stat.txt` と同じ起点の `git diff` 全文を diff.txt に保存。期待: 製品側の変更は §3 の1ファイルだけ（docs/handoff/doc-agenda-nav/ の design.md・card-stage5b.md は Opus のコミット）。`git status --short` で stale_files.txt・frontend/node_modules が残っていないこと。

## 6. 分岐ごとの対処

| 起きたこと | 対処 |
|---|---|
| §2 の F1〜F5 のどれかが実物と違う | 書き換えずに NEEDS_DECISION: 違った事実と実物の出力 |
| §4 の変更前の文が見つからない・2か所ある | 書き換えずに BLOCKED: 見つかった行番号 |
| 5-0 で2本以外が出る | 書き換えずに NEEDS_DECISION: t1-before の全文のパス |
| 5-1 が 5-0 と違う | §4 の find を見直す。直らなければ BLOCKED: |
| actionlint が無い・指摘が出る | 直さずに BLOCKED: 出力の全文のパス（shellcheck の指摘が変更前から在る行のものなら、変更前のファイルにも同じ actionlint をかけて比べ、その結果を書いて NEEDS_DECISION:） |
| commit がフックで止まる | 言い換えて再試行しない。止めた文の原文で BLOCKED: |
| `gh workflow run` を使いたくなった | 使わない（§1） |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 90日では今と同じ2本が出る | t1-before と t1-after の一覧が同じ（backend/scripts・backend/tenant の CLAUDE.md） |
| AGENTS.md も対象になる | t2 が9本で、AGENTS.md 3本を含む |
| node_modules の中は数えない | t3-find.txt に s5probe が無い |
| 文法 | t4 rc=0 |
| 触ったのは1ファイルだけ | diff-stat.txt |
| 試しのファイルが残っていない | `git status --short` |
| 本番での確認 | 次の定期実行 2027-01-01 09:00（日本時間）。それまでは「まだ確かめていない」と記録する |

## 8. 戻し方

PR を revert する（1ファイル）。

## 9. PR

- 作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage5b。Opus が作成済み（origin/main 01e53da6b が起点）で、このカードと design.md の追記のコミットも入っている。担当は作り直さない。
- commit は1つ（1ファイルとカードの §11）。メッセージは `fix: 古さの見張りの対象に AGENTS.md を足す（doc-agenda-nav 段5b）`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- push は `git push -u origin release/doc-agenda-nav-stage5b`。
  - commit の後に `git log -1 --oneline` で確かめる。
  - push の後に `git log origin/release/doc-agenda-nav-stage5b -1 --oneline` で確かめる。
- PR は担当が作らない（Opus が作る）。本文の下書きを Write ツールで `/tmp/CC報告ファイル/an-s5b/pr-body.md` に作るところまでを行う。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` には次を書く。
  - `recon: docs/handoff/doc-agenda-nav/recon.md`
  - `設計: docs/handoff/doc-agenda-nav/design.md`
  - `対象ADR: ADR-1040（関連: ADR-076）`
  - `設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`
  - `触るファイル: .github/workflows/claude-md-staleness-check.yml, docs/handoff/doc-agenda-nav/design.md, docs/handoff/doc-agenda-nav/card-stage5b.md`
  - `削除するファイル: .github/workflows/claude-md-staleness-check.yml, docs/handoff/doc-agenda-nav/design.md`
  - `区分: A（ADR-1015。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`
  - `PO承認: 「1」（2026-10-25）`
  - `Opus 審査記録: コード審査はこれから`
- 本文には §7 の各基準の結果（t1-before・t1-after の一覧、t2 の本数、t4 の rc）を貼る。末尾は `🤖 Generated with [Claude Code](https://claude.com/claude-code)`。
- validate-pr-body.sh は担当が実行しない（比べ元が古いローカルの main になり数分かかるため。Opus が実行する）。

## 10. 報告

- 完了の報告に書くこと:
  - 冒頭の受領文
  - §5-0〜5-5 の結果（rc と該当行。全文はファイルのパス）
  - 新しい HEAD の sha
  - 判断が必要だった点（事実のみ）
- 停止したときに書くこと:
  - 止まった手順の番号
  - 最後に実行したコマンド
  - 止まった理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれかにする。
- 委任のときの決まり:
  - sleep しない。
  - ファイルの作成と編集は Write/Edit ツールで行う（§5 の試しのファイルの rm・rmdir、stale_files.txt の rm を除く）。
  - フックや自動判定に止められたら、言い換えて再試行しない。

## 11. 報告欄（担当が追記）

（未記入）

END OF CARD
