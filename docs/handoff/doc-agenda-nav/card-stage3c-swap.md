# 実装カード 段3c-2 — 入口の入れ替え（AGENTS.md を正本に、CLAUDE.md を取り込みだけに）

> この文書は何か：doc-agenda-nav 段3c-2 の作業指示書です。入口（AGENTS.md・CLAUDE.md）を審査済みの案文どおりに入れ替え、行数の上限・目次・入口を指す3つの文書と見張りの一覧を合わせて直し、ADR-1040 を Accepted にします。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §24: 隙間 G5・G6 と K11 の確かめ方（この便の根拠）
  - §23: 段3c の分け方と消える参照
  - §5-2・§6・§8: 入口2本の行き先、行数の上限、段3c の行
- K11 の意味の対応表: docs/handoff/doc-agenda-nav/k11-map.md
- 対象ADR: ADR-1040（この便で Accepted にする）。関連: ADR-076、ADR-025、ADR-027、ADR-144
- 状態: 設計は審査済み（PR #4649）。§23・§24 は Opus の設計判断（2026-10-24）。PO の承認は 2026-10-23 の「1」（段3c に進む＝入口を入れ替え、決まりも正式にする）。
- 危険便かどうか: `docs/STANDARD-WORKFLOW.md` は scripts/check-process-artifacts.js:115-128 の DANGEROUS_PATTERNS に当たります。また CLAUDE.md を触るので docs/ai-agents/executor-checklist.md §2 により GO の記録が要ります。PR 本文に `### GO記録` が要ります。GO は ADR-1003 の委譲により Opus が書きます（担当は GO 記録を書かず、マージもしない）。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 審査: Opus（reviewer を model "opus" で新しく起こす）
  - GO とマージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段3c-2 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れるもの: §3 のファイル。

入れないもの:
- 案文（docs/handoff/doc-agenda-nav/draft/）、design.md、k11-map.md の変更（Opus がコミット済み）。
- 入口の文面の書き換え・言い回しの改善（案文を写すだけ）。
- frontend/・backend/ の AGENTS.md・CLAUDE.md（段4）。
- .github/ の全ファイル（PR テンプレート・workflow を含む）、claude-md-staleness-check.yml（段5）。
- docs/INDEX.md の判定木の 2・3 番（frontend/CLAUDE.md・backend/CLAUDE.md への案内。段4）。

## 2. 前提の事実（Opus が 2026-10-24 に確かめた。起点は段3c-1（PR #4708）のマージ後の origin/main d298ab129）

| # | 事実 | 出典 |
|---|---|---|
| F1 | CLAUDE.md 88行・AGENTS.md 110行。案文 draft/AGENTS.entry.md 53行・draft/CLAUDE.entry.md 9行 | `wc -l` |
| F2 | 案文 draft/AGENTS.entry.md:21 は CLAUDE.md:79 と一字一句同じ（G5。このカードと同じコミットで Opus が直した） | `diff <(sed -n 21p 案文) <(sed -n 79p CLAUDE.md)` が出力なし |
| F3 | frontend/scripts/check-claude-size.js:23 は `  { path: 'CLAUDE.md', limit: 120 },`。:56-58 は次の3行 | `sed -n '23p;56,58p'` |
|    | `    console.error(\`   → 詳細ルールをサブディレクトリ CLAUDE.md に分割してください（ADR-076）\`);` | |
|    | `    console.error(\`   　 例: backend/db/CLAUDE.md、backend/tenant/CLAUDE.md\`);` | |
|    | `    console.error(\`   　 ファイル名は必ず CLAUDE.md にすること（それ以外は AI が自動ロードしない）\`);` | |
| F4 | docs/INDEX.md は42行。:10 がブランチ運用の行、:30 が「> この節は入口 CLAUDE.md から写した決まり（doc-agenda-nav 段3b）。節の中の「このファイル」は入口の CLAUDE.md を指す。」、:42 が「**ファイル全体が 120 行を超えたら `frontend/scripts/check-claude-size.js` がコミットをブロックする。**」 | `cat -n docs/INDEX.md` |
| F5 | docs/STANDARD-WORKFLOW.md:160 は `  - **ターミナル**：\`CLAUDE.md\`（自動ロード）に要約＋このファイルへのリンク。` | `sed -n 160p` |
| F6 | docs/onboarding/claude-code.md:145 は `` `<repo>/CLAUDE.md` の「プロジェクト前提」を必ず読むこと。特に以下は事故の原因になりやすい:`` | `sed -n 145p` |
| F7 | .claude/hooks/check-freshness.sh:25 は `RULES="CLAUDE.md docs/STANDARD-WORKFLOW.md backend/CLAUDE.md frontend/CLAUDE.md"` | `sed -n 25p` |
| F8 | docs/adr/ADR-1040-doc-agenda-nav-entry-index.md:5 は `| ステータス | Proposed（2026-10-22） |`。docs/adr/README.md:221 の ADR-1040 の行は Proposed | `sed -n 5p`・`grep -n 1040 docs/adr/README.md` |
| F9 | docs/PARALLEL_TERMINAL_GUIDE.md は存在する（1行目 `# 複数ターミナル並行開発ガイド`） | `head -1` |
| F10 | 入れ替え後の文面で目次の到達検査を回すと、SUMMARY は入れ替え前と同じ `unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10` | design.md §24 |

## 3. 触るファイル（これ以外は触らない）

- 変更: `AGENTS.md`
- 変更: `CLAUDE.md`
- 変更: `frontend/scripts/check-claude-size.js`
- 変更: `docs/INDEX.md`
- 変更: `docs/STANDARD-WORKFLOW.md`
- 変更: `docs/onboarding/claude-code.md`
- 変更: `.claude/hooks/check-freshness.sh`
- 変更: `docs/adr/ADR-1040-doc-agenda-nav-entry-index.md`
- 変更: `docs/adr/README.md`（`node scripts/generate-adr-index.js` で作り直すだけ。手で書かない）
- 変更: `docs/handoff/doc-agenda-nav/card-stage3c-swap.md`（このカード。担当は §11 の報告欄に追記するだけ）
- design.md §24・draft/AGENTS.entry.md:21・k11-map.md は Opus がコミット済み。担当は触らない。

## 4. 作り方

行番号はすべて、作業場所の起点（`B=$(git merge-base origin/main HEAD)`）でのもの。zsh では必ず `"${B}:CLAUDE.md"` と書く。

### 4-1. 入口2本を案文で置き換える

- `AGENTS.md` の中身を `docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md` と1バイトも違わない内容にする（`cp docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md AGENTS.md` でよい）。
- `CLAUDE.md` の中身を `docs/handoff/doc-agenda-nav/draft/CLAUDE.entry.md` と1バイトも違わない内容にする（同じく cp でよい）。

### 4-2. frontend/scripts/check-claude-size.js（Edit）

- :23 の1行（F3）を、次の3行に置き換える:

```
  { path: 'AGENTS.md', limit: 80 },
  { path: 'CLAUDE.md', limit: 10 },
  { path: 'docs/INDEX.md', limit: 60 },
```

- :56-58 の3行（F3）を、次の3行に置き換える（:59 の「追加後は LIMITS 配列に登録して…」は残す）:

```
    console.error(`   → 入口（AGENTS.md・CLAUDE.md）には安全の決まりだけを置き、手順・詳細は目次 docs/INDEX.md からたどる文書へ移してください（ADR-1040）`);
    console.error(`   　 領域別の決まりは frontend/・backend/ などのサブディレクトリの AGENTS.md・CLAUDE.md へ分けてください（ADR-076）`);
    console.error(`   　 CLAUDE.md は「@AGENTS.md」と Claude Code だけの決まりに限ること（ADR-1040）`);
```

ほかの行は変えない。

### 4-3. docs/INDEX.md（Edit）

- :10（ブランチ運用の行）の直後に、次の1行を足す（G6）:

```
| A 開発の進め方 | [並行ターミナルの使い方](PARALLEL_TERMINAL_GUIDE.md) | 作業場所（worktree）を複数並べて作業するとき |
```

- 起点の :30（F4。足した後は :31）を、次の1行に置き換える:

```
> この節は入口から写した決まり（doc-agenda-nav 段3b）。節の中の「このファイル」は入口の AGENTS.md を指す（段3c で本文の正本を CLAUDE.md から AGENTS.md へ移した）。
```

- 起点の :42（F4。足した後は :43）を、次の1行に置き換える:

```
**入口の AGENTS.md が 80 行、CLAUDE.md が 10 行、この目次が 60 行を超えたら `frontend/scripts/check-claude-size.js` がコミットをブロックする。**
```

結果は43行。

### 4-4. docs/STANDARD-WORKFLOW.md:160 を1行だけ置き換える（Edit）

```
  - **ターミナル**：`AGENTS.md`（本文の正本。`CLAUDE.md` が「@AGENTS.md」で取り込み、自動ロードされる）に要約＋このファイルへのリンク。
```

### 4-5. docs/onboarding/claude-code.md:145 を1行だけ置き換える（Edit）

```
`<repo>/AGENTS.md`（`<repo>/CLAUDE.md` が取り込む入口の本文）の「プロジェクト前提」を必ず読むこと。特に以下は事故の原因になりやすい:
```

### 4-6. .claude/hooks/check-freshness.sh:25 を1行だけ置き換える（Edit）

```
RULES="AGENTS.md CLAUDE.md docs/INDEX.md docs/STANDARD-WORKFLOW.md backend/CLAUDE.md frontend/CLAUDE.md"
```

### 4-7. ADR-1040 を Accepted にする

- docs/adr/ADR-1040-doc-agenda-nav-entry-index.md:5 を、次の1行に置き換える（Edit）:

```
| ステータス | Accepted（2026-10-24。採用の根拠: PO 承認「1」2026-10-23＝段3c に進み決まりも正式にする。入口の入れ替えはこの PR） |
```

- `node scripts/generate-adr-index.js` を実行する。docs/adr/README.md を手で直さない。

## 5. 確かめ方

担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage3c/impl2/ に保存する。

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3c-swap && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-0. 起点が §2 と合うかを確かめる。
- `git show "${B}:CLAUDE.md" | wc -l` が 88、`git show "${B}:AGENTS.md" | wc -l` が 110、`git show "${B}:docs/INDEX.md" | wc -l` が 42。
- F3〜F8 の行を次のコマンドで取り出して保存し、§2 と照らす: `git show "${B}:frontend/scripts/check-claude-size.js" | sed -n '23p;56,58p'`、`git show "${B}:docs/INDEX.md" | sed -n '10p;30p;42p'`、`git show "${B}:docs/STANDARD-WORKFLOW.md" | sed -n 160p`、`git show "${B}:docs/onboarding/claude-code.md" | sed -n 145p`、`git show "${B}:.claude/hooks/check-freshness.sh" | sed -n 25p`、`git show "${B}:docs/adr/ADR-1040-doc-agenda-nav-entry-index.md" | sed -n 5p`。
- F2 の diff が出力なし。
- 違えば何も変えずに NEEDS_DECISION:。

5-1. 入口が案文と同じかを確かめる。2本の diff がどちらも出力なし:

```
diff AGENTS.md docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md
diff CLAUDE.md docs/handoff/doc-agenda-nav/draft/CLAUDE.entry.md
```

5-2. K11（起点の入口2本の空行以外 128 行が、入れ替え後のどこかに在るか）。grep には必ず `-a` を付ける（付けないと macOS の grep が全文ファイルを binary と判定し、一致を見落とす。design.md §24）:

```
P=/tmp/CC報告ファイル/an-stage3c/impl2
git ls-files docs ':!docs/handoff' | tr '\n' '\0' | xargs -0 cat > $P/docs-all.txt
for f in CLAUDE.md AGENTS.md; do git show "${B}:$f" | awk -v f="$f" '{print f":"NR"\t"$0}'; done > $P/old-lines.tsv
while IFS=$'\t' read -r k l; do [ -z "$l" ] && continue; if grep -aFxq -- "$l" AGENTS.md CLAUDE.md; then echo "OK-ENTRY $k"; elif grep -aFxq -- "$l" $P/docs-all.txt; then echo "OK-DOCS $k"; else echo "MISSING $k"; fi; done < $P/old-lines.tsv > $P/k11.txt
grep -c '^OK-ENTRY' $P/k11.txt; grep -c '^OK-DOCS' $P/k11.txt; grep -c '^MISSING' $P/k11.txt
grep '^MISSING' $P/k11.txt | awk '{print $2}' | sort > $P/missing-keys.txt
grep -oE '^\| (CLAUDE|AGENTS)\.md:[0-9]+' docs/handoff/doc-agenda-nav/k11-map.md | sed 's/^| //' | sort > $P/map-keys.txt
comm -23 $P/missing-keys.txt $P/map-keys.txt
```

期待: 3つの数の合計が 128。最後の `comm` が出力なし（一致しない行はすべて対応表に載っている）。Opus の試算は OK-ENTRY 27・OK-DOCS 51・MISSING 50。数が試算と違っても `comm` が出力なしなら合格とし、数を報告に書く。

5-3. 置き換えた行の確かめ: `git diff "$B" -- frontend/scripts/check-claude-size.js docs/INDEX.md docs/STANDARD-WORKFLOW.md docs/onboarding/claude-code.md .claude/hooks/check-freshness.sh docs/adr/ADR-1040-doc-agenda-nav-entry-index.md docs/adr/README.md` の全文を保存する。期待:
- check-claude-size.js: `-` 4行・`+` 6行で、`+` の行が §4-2 の全文と同じ。`node --check frontend/scripts/check-claude-size.js` が exit 0。
- docs/INDEX.md: `-` 2行・`+` 3行で、`+` の行が §4-3 の全文と同じ。`wc -l docs/INDEX.md` が 43。
- STANDARD-WORKFLOW.md・onboarding・check-freshness.sh・ADR-1040: それぞれ `-` 1行・`+` 1行で、`+` の行が §4-4〜§4-7 の全文と同じ。`bash -n .claude/hooks/check-freshness.sh` が exit 0。
- docs/adr/README.md: ADR-1040 の行だけが Proposed → Accepted に変わる（ほかの行の変化が出たら NEEDS_DECISION:）。

5-4. 行数の検査:
- `node frontend/scripts/check-claude-size.js` の全文を保存し、exit 0 と `✅ CLAUDE.md サイズチェック PASSED` を確かめる。
- 逆の確かめ（上限を超えたら止まるか）: `cp AGENTS.md $P/AGENTS.keep` → `seq 1 30 >> AGENTS.md` → `node frontend/scripts/check-claude-size.js` の全文を保存し exit 1 と `❌ AGENTS.md: 83行（上限80行）` が出ることを確かめる → `cp $P/AGENTS.keep AGENTS.md` → `diff AGENTS.md docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md` が出力なし。

5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（F10）と並べて書く。期待は、どの数も増えないこと。

5-6. 試験: `node scripts/tests/test-process-artifacts.js` の全文を保存し、exit 0 であること。

5-7. `git status --short` と `git diff "$B" --stat` を実行する。期待は §3 のファイル（と Opus がコミットした design.md・draft/AGENTS.entry.md・k11-map.md・このカード）だけ。

5-8. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けて1回だけ実行し、結果を貼る（待たない）。

## 6. 分岐ごとの対処

- 5-0 で起点が合わない → 何も変えずに NEEDS_DECISION:（行番号は Opus が出し直す）。
- 5-1・5-3 で差が出る → 写し方か置き換え方の誤り。直して 5-1 からやり直す。2回直しても合わなければ BLOCKED:。
- 5-2 で `comm` に出力がある → その行の一覧と中身を貼って BLOCKED:（担当は対応表を直さない）。
- 5-4 の逆の確かめで exit 1 にならない → 出力を貼って BLOCKED:。AGENTS.md を案文に戻したことは必ず確かめる。
- 5-5 で数が増える → 一覧を貼って NEEDS_DECISION:（担当は直さない）。
- 5-6 が失敗 → 失敗した試験名と出力を貼って NEEDS_DECISION:（担当は試験を直さない）。
- commit のときに pre-commit（frontend/.husky/pre-commit）に止められた → 止まった検査と出力の原文を貼って BLOCKED:（`--no-verify` は使わない）。
- `scripts/dev/validate-pr-body.sh` に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行する。3回で通らなければ BLOCKED:。ただし `### GO記録` が無いことによる停止は想定どおり（Opus が後で書く）なので、その理由の原文だけを報告して PR 作成は続けてよいかを NEEDS_DECISION: で聞く。
- 見張りや自動判定に止められた → 言い換えずに、止まった手順、最後のコマンド、理由の原文を報告して停止する。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 入口2本が審査済みの案文と1バイトも違わない | §5-1 の diff 2本が出力なし |
| 入口から外した決まりが、移した先に 100% ある（K11） | §5-2 の `comm` が出力なし・合計 128 |
| 入口の行数が上限内で、上限を超えたら止まる | §5-4 の PASSED と、逆の確かめの exit 1 |
| 入口を指す文書・見張り・目次の注記が新しい入口を指す | §5-3 |
| ADR-1040 が Accepted で、一覧も Accepted | §5-3 |
| 目次から届かない文書、行き先の無いリンクが増えない | §5-5 |
| 試験が通る | §5-6 が exit 0 |
| 触ったのは §3 のファイルだけ | §5-7 |

## 8. 戻し方

この PR の revert を main にマージする（入口2本・上限・目次・3つの文書・見張り・ADR の状態がすべて元に戻る）。入れ替え後に AI の動きがおかしいと分かったときも同じ。

## 9. PR

- 作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3c-swap。Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage3c-swap` で作成済み（段3c-1 マージ後の origin/main d298ab129 が起点）で、このカードと design.md §24・案文 :21・k11-map.md のコミットも入っている。担当は作り直さない。
- push は `git push -u origin release/doc-agenda-nav-stage3c-swap`。
  - commit の後に `git log -1 --oneline` で確かめる。
  - push の後に `git log origin/release/doc-agenda-nav-stage3c-swap -1 --oneline` で確かめる。
- PR の作り方:
  - `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage3c/pr-body-2.md` を作り、別のコマンドで `--body-file` に渡す（同じコマンドで作ると pr-body-guard に止められる）。
  - 作る前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
  - ready で作る。base は main。担当はマージせず、GO 記録も書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` には次を書く。
  - `recon: docs/handoff/doc-agenda-nav/recon.md`
  - `設計: docs/handoff/doc-agenda-nav/design.md`
  - `対象ADR: ADR-1040（関連: ADR-076・ADR-025・ADR-027・ADR-144）`
  - `設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`
  - `触るファイル: AGENTS.md, CLAUDE.md, frontend/scripts/check-claude-size.js, docs/INDEX.md, docs/STANDARD-WORKFLOW.md, docs/onboarding/claude-code.md, .claude/hooks/check-freshness.sh, docs/adr/ADR-1040-doc-agenda-nav-entry-index.md, docs/adr/README.md, docs/handoff/doc-agenda-nav/design.md, docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md, docs/handoff/doc-agenda-nav/k11-map.md, docs/handoff/doc-agenda-nav/card-stage3c-swap.md`
  - `削除するファイル: AGENTS.md, CLAUDE.md, frontend/scripts/check-claude-size.js, docs/INDEX.md, docs/STANDARD-WORKFLOW.md, docs/onboarding/claude-code.md, .claude/hooks/check-freshness.sh, docs/adr/ADR-1040-doc-agenda-nav-entry-index.md, docs/adr/README.md, docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md`（置き換えで消える行も削除と数える）
  - `区分: A（ADR-1015。入口と STANDARD-WORKFLOW を触るため B 区分に当たらない。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`
  - `PO承認: 「1」（2026-10-23）`
  - `Opus 審査記録: コード審査はこれから`
- 本文には、§5-2 の3つの数と `comm` の結果、§5-4 の2つの結果、§5-5 の SUMMARY 行も貼る。
- 作る前に、`scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了の報告に書くこと:
  - 冒頭の受領文
  - §5-0〜5-8 の出力（長いものはファイルのパス）
  - PR の URL
  - 新しい HEAD の sha
  - 判断が必要だった点（事実のみ）
- 停止したときに書くこと:
  - 止まった手順の番号
  - 最後に実行したコマンド
  - 止まった理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれかにする。
- 委任のときの決まり:
  - sleep しない。
  - ファイルの作成と編集は Write/Edit ツールで行う（§4-1 の cp と §5-4 の一時的な書き足し・戻しを除く）。
  - PR を作る前に validate-pr-body.sh で exit 0 を確かめる。
  - フックや自動判定に止められたら、言い換えて再試行しない。

## 11. 報告欄（担当が追記）

- 本報告はカード doc-agenda-nav 段3c-2 の実行結果である。
- 5-0 起点一致／5-1 diff 2本 出力なし／5-2 OK-ENTRY 27・OK-DOCS 51・MISSING 50（合計128）・comm 出力なし／5-4 PASSED と逆の確かめ exit 1（83行）・AGENTS.md 復元済み／5-5 SUMMARY unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10（起点と同じ）／5-6 132 PASS 0 FAIL。
- 判断点: generate-adr-index.js は docs/adr/README.md の「最終更新」日付行も 2026-10-23 から 2026-10-24 に変えた（生成物の自動変更）。
- 生出力: /tmp/CC報告ファイル/an-stage3c/impl2/

END OF CARD
