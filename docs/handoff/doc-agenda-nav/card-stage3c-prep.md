# 実装カード 段3c-1 — 入口の入れ替えの準備（移り先の隙間を埋め、消える参照の指す先を直す）

> この文書は何か：doc-agenda-nav 段3c-1 の作業指示書です。入口（AGENTS.md・CLAUDE.md）を短い案文に入れ替える前に、移り先がまだ無い決まりの置き場を用意し、入れ替えで指す先が消える参照2件を直します。入口そのもの（AGENTS.md・CLAUDE.md）はこの便では触りません。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §23: 段3c の分け方と隙間 G1〜G4 の判断（この便の根拠）
  - §5-2: 入口2本の全行の行き先
  - §8: 段3c の行
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076、ADR-027、ADR-144
- 状態: 設計は審査済み（PR #4649）。§23 は Opus の設計判断（2026-10-24）。PO の承認は 2026-10-23 の「1」（段3c に進む＝入口を入れ替え、決まりも正式にする）。
- 危険便かどうか: `scripts/check-process-artifacts.js` は scripts/check-process-artifacts.js:115-128 の DANGEROUS_PATTERNS の `^scripts/` に当たります。PR 本文に `### GO記録` が要ります。GO は ADR-1003 の委譲により Opus が書きます（担当は GO 記録を書かず、マージもしない）。ほかのファイル（docs/handoff/・docs/INDEX.md・docs/runbooks/）はどの正規表現にも当たりません。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 審査: Opus（reviewer を model "opus" で新しく起こす）
  - GO とマージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段3c-1 の実行結果である」と書くこと。

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
- AGENTS.md・CLAUDE.md・frontend/ の文書（入れ替えは段3c-2、frontend は段4）。
- 写す文の書き換えや言い回しの改善。
- frontend/scripts/check-claude-size.js、CI の設定、docs/STANDARD-WORKFLOW.md、docs/onboarding/、.claude/hooks/（段3c-2）。
- 指す先が入れ替え前から切れている参照（scripts/setup_tenant.py:31・:474）。

## 2. 前提の事実（Opus が 2026-10-24 に確かめた。起点は段3b-4（PR #4706）のマージ後の origin/main 50d7f52da）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 案文 docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md は45行。:39 `## 作業の型`、:41-45 がその箇条で、:45 `- 画面は \`frontend/AGENTS.md\`、サーバー側は \`backend/AGENTS.md\` の決まりにも従う` が最後の行 | `git show origin/main:docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md \| cat -n` |
| F2 | CLAUDE.md は88行。:71 `## i18n 強制（ADR-027）`、:73 i18n の本文、:86 `## UIガバナンス遵守（ADR-144）`、:87 UI ガバナンスの本文 | `git show origin/main:CLAUDE.md \| sed -n 69,73p;84,88p` |
| F3 | docs/INDEX.md は40行。:15 が章A の最後の行（開発コマンド）、:16 が章B の唯一の行（設計仕様書の索引） | `git show origin/main:docs/INDEX.md \| cat -n` |
| F4 | docs/ai-agents/kpi.md は存在する（1行目 `# AI Agent KPI Canonical Definition`） | `git cat-file -e origin/main:docs/ai-agents/kpi.md` |
| F5 | scripts/check-process-artifacts.js:356 は `      '   → 詳細: CLAUDE.md §ブランチ運用ルール',`。この文を確かめる試験は無い | `git grep -n '詳細: CLAUDE.md' origin/main -- scripts .github`（1件） |
| F6 | GO 手順（ADR-136）の本文は docs/specs/branch-operations/README.md の `## 8. 日々の運用ルール（入口から写した決まり）` にある | 同 README :82・:94 |
| F7 | docs/runbooks/adr-019-english-ui-temporary-deploy.md:186 は `通常の develop → main リリース PR と同じ手順（[CLAUDE.md ブランチ運用ルール](../../CLAUDE.md) §「develop → main も PR 経由」）。` | `git show origin/main:docs/runbooks/adr-019-english-ui-temporary-deploy.md \| sed -n 186p` |
| F8 | design.md §23 はこのカードと同じコミットで Opus が追記済み | この作業場所の `git log` |

## 3. 触るファイル（これ以外は触らない）

- 変更: `docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md`
- 変更: `docs/INDEX.md`
- 変更: `scripts/check-process-artifacts.js`
- 変更: `docs/runbooks/adr-019-english-ui-temporary-deploy.md`
- 変更: `docs/handoff/doc-agenda-nav/card-stage3c-prep.md`（このカード。担当は §11 の報告欄に追記するだけ）
- design.md §23 は Opus がコミット済み。担当は触らない。

## 4. 作り方

行番号はすべて、作業場所の起点（`B=$(git merge-base origin/main HEAD)`）でのもの。写す行は `git show "${B}:CLAUDE.md" | sed -n 73p` のように起点から取り出し、1文字も変えない。zsh では必ず `"${B}:CLAUDE.md"` と書く。

### 4-1. 案文 AGENTS.entry.md の :45 の後ろに8行足す（Edit）

| 足した後の行 | 中身 |
|---|---|
| 46 | 空行 |
| 47 | CLAUDE.md:71（`## i18n 強制（ADR-027）`） |
| 48 | 空行 |
| 49 | CLAUDE.md:73（i18n の本文） |
| 50 | 空行 |
| 51 | CLAUDE.md:86（`## UIガバナンス遵守（ADR-144）`） |
| 52 | 空行 |
| 53 | CLAUDE.md:87（UI ガバナンスの本文） |

結果は53行。ファイルの最後は改行1つで終える。

### 4-2. docs/INDEX.md に2行足す（Edit）

- :15（開発コマンドの行）の直後に、次の1行を足す（全文。前後に何も足さない）:

```
| A 開発の進め方 | [KPI の正本](ai-agents/kpi.md) | KPI を決める・測るとき |
```

- 起点の :16（設計仕様書の索引の行。足した後は :17）の直後に、次の1行を足す:

```
| B 設計仕様書 | 業務の仕様書 `salesanchor_system_overview.docx` 他 3 冊（リポジトリ外・PO から入手） | 業務の仕様（画面・データの意味）を確かめるとき |
```

結果は42行。ほかの行は変えない。

### 4-3. scripts/check-process-artifacts.js:356 を1行だけ置き換える（Edit）

変更前（F5）:

```
      '   → 詳細: CLAUDE.md §ブランチ運用ルール',
```

変更後:

```
      '   → 詳細: docs/specs/branch-operations/README.md §8',
```

行の数・字下げ・後ろのカンマは変えない。

### 4-4. docs/runbooks/adr-019-english-ui-temporary-deploy.md:186 を1行だけ置き換える（Edit）

変更後の全文:

```
通常の develop → main リリース PR と同じ手順（[ブランチ運用](../specs/branch-operations/README.md) §8）。
```

## 5. 確かめ方

担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage3c/impl1/ に保存する。

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3c-prep && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-0. 起点が §2 と合うかを確かめる。
- `git show "${B}:docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md" | wc -l` が 45、`git show "${B}:CLAUDE.md" | wc -l` が 88、`git show "${B}:docs/INDEX.md" | wc -l` が 40。
- `git show "${B}:CLAUDE.md" | sed -n '71p;73p;86p;87p'`、`git show "${B}:docs/INDEX.md" | sed -n 15,16p`、`git show "${B}:scripts/check-process-artifacts.js" | sed -n 356p`、`git show "${B}:docs/runbooks/adr-019-english-ui-temporary-deploy.md" | sed -n 186p` を保存し、F2・F3・F5・F7 と照らす。
- 違えば何も変えずに NEEDS_DECISION:。

5-1. 写しが一字一句同じかを確かめる。4本の diff がすべて出力なしであること:

```
D=docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md
diff <(git show "${B}:$D") <(sed -n 1,45p "$D")
diff <(git show "${B}:CLAUDE.md" | sed -n '71p;73p;86p;87p') <(sed -n '47p;49p;51p;53p' "$D")
diff <(printf '\n\n\n\n') <(sed -n '46p;48p;50p;52p' "$D")
diff <(git show "${B}:docs/INDEX.md") <(sed -n '1,15p;17p;19,42p' docs/INDEX.md)
```

あわせて `sed -n '16p;18p' docs/INDEX.md` を保存して報告に貼る（§4-2 の2行の全文と同じであること）。

5-2. K11（入れ替えで消える CLAUDE.md の i18n・UI ガバナンスの4行が、案文にあるか）:

```
k11() { git show "${B}:$1" | sed -n "$2p" | while IFS= read -r l; do [ -z "$l" ] && continue; if grep -Fxq -- "$l" "$3"; then echo "OK"; else echo "MISSING $1:$2 :: $l"; fi; done; }
{ k11 CLAUDE.md 71 "$D"; k11 CLAUDE.md 73 "$D"; k11 CLAUDE.md 86 "$D"; k11 CLAUDE.md 87 "$D"; } > /tmp/CC報告ファイル/an-stage3c/impl1/k11.txt
grep -c '^OK' /tmp/CC報告ファイル/an-stage3c/impl1/k11.txt; grep -c '^MISSING' /tmp/CC報告ファイル/an-stage3c/impl1/k11.txt
```

期待は OK 4・MISSING 0。

5-3. 置き換えた2行: `git diff "$B" -- scripts/check-process-artifacts.js docs/runbooks/adr-019-english-ui-temporary-deploy.md` の全文を保存する。期待は、それぞれ `-` 1行・`+` 1行で、`+` の行が §4-3・§4-4 の全文と同じこと。`node --check scripts/check-process-artifacts.js` が exit 0 であること。

5-4. 試験: `node scripts/tests/test-process-artifacts.js` の全文を保存し、exit 0 であること。失敗したら、失敗した試験名と出力を貼って NEEDS_DECISION:。

5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待は、どの数も増えないこと。

5-6. 案文の行数: `wc -l "$D" docs/handoff/doc-agenda-nav/draft/CLAUDE.entry.md` が 53・9 であること（合計 62。設計 §8 の段3c の上限 90 以下）。

5-7. `git status --short` と `git diff "$B" --stat` を実行する。期待は §3 のファイル（と Opus がコミットした design.md）だけ。

5-8. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けて1回だけ実行し、結果を貼る（待たない）。

## 6. 分岐ごとの対処

- 5-0 で起点が合わない → 何も変えずに NEEDS_DECISION:（行番号は Opus が出し直す）。
- 5-1・5-3 で差が出る → 写し方か置き換え方の誤り。直して 5-1 からやり直す。2回直しても合わなければ BLOCKED:。
- 5-2 で MISSING が出る → 一覧を貼って BLOCKED:。
- 5-4 が失敗 → 失敗した試験名と出力を貼って NEEDS_DECISION:（担当は試験を直さない）。
- 5-5 で数が増える → 一覧を貼って NEEDS_DECISION:（担当は直さない）。
- `scripts/dev/validate-pr-body.sh` に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行する。3回で通らなければ BLOCKED:。ただし `### GO記録` が無いことによる停止は想定どおり（Opus が後で書く）なので、その理由の原文だけを報告して PR 作成は続けてよいかを NEEDS_DECISION: で聞く。
- 見張りや自動判定に止められた → 言い換えずに、止まった手順、最後のコマンド、理由の原文を報告して停止する。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| i18n・UI ガバナンスの4行が、案文に一字一句ある（入れ替え後も入口に残る） | §5-1 の2本目の diff が出力なし・§5-2 で OK 4・MISSING 0 |
| 案文の既存45行・目次の既存40行は変わらない | §5-1 の1本目・4本目の diff が出力なし |
| 目次に KPI の正本と仕様書の行がある | §5-1 で 16行目・18行目が §4-2 の全文と同じ |
| GO 手順の案内とランブックのリンクが、入れ替え後も残る文書を指す | §5-3 |
| 試験が通る | §5-4 が exit 0 |
| 目次から届かない文書、行き先の無いリンクが増えない | §5-5 |
| 触ったのは §3 のファイルだけ | §5-7 |

## 8. 戻し方

この PR の revert を main にマージする（案文の8行・目次の2行が消え、2行の参照が元に戻る）。入口はこの便で変わらないので、AI の読む決まりは変わらない。

## 9. PR

- 作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3c-prep。Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage3c-prep` で作成済み（段3b-4 マージ後の origin/main 50d7f52da が起点）で、このカードと design.md §23 のコミットも入っている。担当は作り直さない。
- push は `git push -u origin release/doc-agenda-nav-stage3c-prep`。
  - commit の後に `git log -1 --oneline` で確かめる。
  - push の後に `git log origin/release/doc-agenda-nav-stage3c-prep -1 --oneline` で確かめる。
- PR の作り方:
  - `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage3c/pr-body-1.md` を作り、`--body-file` で渡す。
  - 作る前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
  - ready で作る。base は main。担当はマージせず、GO 記録も書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` には次を書く。
  - `recon: docs/handoff/doc-agenda-nav/recon.md`
  - `設計: docs/handoff/doc-agenda-nav/design.md`
  - `対象ADR: ADR-1040（関連: ADR-076・ADR-027・ADR-144）`
  - `設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`
  - `触るファイル: docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md, docs/INDEX.md, scripts/check-process-artifacts.js, docs/runbooks/adr-019-english-ui-temporary-deploy.md, docs/handoff/doc-agenda-nav/design.md, docs/handoff/doc-agenda-nav/card-stage3c-prep.md`
  - `削除するファイル: scripts/check-process-artifacts.js, docs/runbooks/adr-019-english-ui-temporary-deploy.md`（置き換えで消える1行も削除と数える。初版の「なし」は Opus の書き誤りで、pr-body-guard.sh に止められた）
  - `区分: A（ADR-1015。本番 scripts/ を触るため B 区分に当たらない。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`
  - `PO承認: 「1」（2026-10-23）`
  - `Opus 審査記録: コード審査はこれから`
- 本文には、§5-2 の OK と MISSING の数と、§5-5 の SUMMARY 行も貼る。
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
  - ファイルの作成と編集は Write/Edit ツールで行う。
  - PR を作る前に validate-pr-body.sh で exit 0 を確かめる。
  - フックや自動判定に止められたら、言い換えて再試行しない。

## 11. 報告欄（担当が追記）

本報告はカード doc-agenda-nav 段3c-1 の実行結果である。

- 5-0: 起点 50d7f52da。45/88/40 行、引用行は F2・F3・F5・F7 と一致（/tmp/CC報告ファイル/an-stage3c/impl1/s50.txt）。
- 5-1: diff 4本とも出力なし。INDEX.md の16・18行目は §4-2 の全文と同じ。
- 5-2: OK 4・MISSING 0。
- 5-3: 各 -1/+1 行、node --check exit 0。
- 5-4: 132 PASS / 0 FAIL、exit 0。
- 5-5: SUMMARY unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10（起点と同じ）。
- 5-6: 53 行・9 行（合計 62）。
- 5-7: 変更は §3 のファイルのみ。

END OF CARD
