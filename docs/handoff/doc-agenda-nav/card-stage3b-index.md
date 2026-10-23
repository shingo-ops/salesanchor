# 実装カード 段3b-4 — 「このファイルにルールを追加する前に」を CLAUDE.md から目次 docs/INDEX.md の末尾へ移す（文は変えない）

> この文書は何か：doc-agenda-nav 段3b-4 の作業指示書です。CLAUDE.md の「## このファイルにルールを追加する前に」の節（判定の8問と行数上限の文、13行）を、docs/INDEX.md の末尾へ一字も変えずに写します。写した見出しのすぐ下に、「このファイル」が何を指すかの注記を1行だけ足します。そのうえで、CLAUDE.md からこの節を消します。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §5-2: CLAUDE.md :105-117 の行。「ルール追加の判定木・行数上限の文 → docs/INDEX.md の末尾章（:117 の上限の文はここ1か所）」
  - §8: 段3b の行。「1PR に移動先1つ」
  - §7: 移動のときに文が欠けるリスク
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076
- 状態: 設計は審査済み（PR #4649）。PO の実装承認は 2026-10-23 の「1」。Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事です。
- 危険便かどうか: CI の分類（scripts/check-process-artifacts.js:115-127 の DANGEROUS_PATTERNS）には当たりません。CLAUDE.md も docs/INDEX.md も、どの正規表現にも一致しないことを Opus が確かめました（段3b-3 では docs/STANDARD-WORKFLOW.md が :121 に当たっていたのに、カードに書き忘れました。その反省で、今回は行番号まで示しています）。ただし docs/ai-agents/executor-checklist.md §2 により、CLAUDE.md に触る便は「危険ファイル変更 PR」として扱います。GO は ADR-1003 の委譲により Opus が PR コメントで出します（担当は GO を書かず、マージもしない）。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 審査: Opus（reviewer を model "opus" で新しく起こす）
  - GO とマージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段3b-4 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れるもの: §3 の3ファイル。

入れないもの:
- 写す文の書き換えや言い回しの改善。docs/INDEX.md の既存の行（:1-24）の変更。
- 行数上限の数値の変更。今の「120 行」は frontend/scripts/check-claude-size.js の上限と一致しているので、そのまま写す。上限を 10 行へ変えるのは段3c で、LIMITS と同じ PR で行う（設計 §13）。
- CLAUDE.md のほかの節。i18n と UI ガバナンスを frontend/AGENTS.md へ移すのは段4の後にする。
- frontend/scripts/check-claude-size.js、CI の設定。

Opus の設計判断（このカードで決めたこと）:
- 段3b では、移す先へ一字一句写し、入口から消すのは「入口の案文に要点が残らない行」だけにする。この節の13行は、案文 AGENTS.entry.md にも CLAUDE.entry.md にも1行も残らない（`grep -n -E 'ルール|追加|判定' docs/handoff/doc-agenda-nav/draft/*.md` の7件はどれも別の話。§2 F4）。そのため、節ごと消す。
- 写した節の「このファイル」（見出しと4問目）は、もとは CLAUDE.md を指していた。目次の中に置くと、目次自身を指すように読める。そこで、見出しの直後に注記を1行だけ足して、指す先を示す。写した文そのものは変えない。注記の文は §4-1 に全文を書く（担当は文を考えない）。
- 段3b-1・3b-2 と同じく、注記の行は K11 の対象外とする（移した決まりではなく、置き場の説明のため）。

## 2. 前提の事実（Opus が 2026-10-23 に確かめた。起点は段3b-3（PR #4705）のマージ後の origin/main）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 段3b-3 の後の CLAUDE.md は101行。中身は次のとおり。<br>:83 `## ADRと実装の優先順位（最上位原則）`<br>:84 ADR 優先の文<br>:85 空行<br>:86 `## このファイルにルールを追加する前に`<br>:87 空行<br>:88 `以下に順番に答える:`<br>:89 空行<br>:90-97 判定の1〜8問<br>:98 `**ファイル全体が 120 行を超えたら …**`<br>:99 `## UIガバナンス遵守（ADR-144）`<br>:100 UI ガバナンスの文<br>:101 executor-checklist の文 | PR #4705 の HEAD 035bf62f5 の `cat -n CLAUDE.md`（/tmp/CC報告ファイル/an-stage3b/recon/08-claude-tail.txt）。マージ後の origin/main 71a5687ae の `git show origin/main:CLAUDE.md \| sed -n 83,101p` と一致（diff 出力なし、`wc -l` 101） |
| F2 | docs/INDEX.md は24行。:6-24 が目次の表で、:24 `\| F 運用・本番 \| [手順書のフォルダ](runbooks/) \| …` が最後の行。表の後ろには行が無い | /tmp/CC報告ファイル/an-stage3b/recon/09-index.txt |
| F3 | 「このファイルにルールを追加」「ルールを追加する前に」を名前で指すのは、CLAUDE.md:86 自身だけ（docs/handoff を除く） | `git grep -n -E 'このファイルにルールを追加\|ルールを追加する前に' -- . ':!docs/handoff/'`（/tmp/CC報告ファイル/an-stage3b/recon/13-refs.txt） |
| F4 | 案文2本にこの節の要点は無い | /tmp/CC報告ファイル/an-stage3b/recon/12-draft-grep.txt（7件。どれも前提・ADR-025・main/develop・preflight・目次への案内） |
| F5 | 目次の検査 docs/handoff/doc-agenda-nav/check_doc_index.py は、表の行（`\|` で始まる行）だけで「いつ読むか」の欄を数える（:161）。表の外の文は欄の数に入らない | check_doc_index.py:156-165 |

## 3. 触るファイル（これ以外は触らない）

- 変更: `docs/INDEX.md`
- 変更: `CLAUDE.md`
- 変更: `docs/handoff/doc-agenda-nav/card-stage3b-index.md`（このカード。担当は §11 の報告欄に追記するだけ）

## 4. 作り方

行番号はすべて、作業場所の起点（`B=$(git merge-base origin/main HEAD)`）でのもの。中身は `git show "${B}:CLAUDE.md" | sed -n 86p` のように起点から取り出して写し、1文字も変えない。zsh では必ず `"${B}:CLAUDE.md"` と書く。

### 4-1. docs/INDEX.md の :24 の後ろに足す（Edit）

足した後の行と中身は次のとおり。

| 足した後の行 | 中身 |
|---|---|
| 25 | 空行 |
| 26 | CLAUDE.md:86（`## このファイルにルールを追加する前に`） |
| 27 | 空行 |
| 28 | 注記（下の全文をそのまま書く） |
| 29 | 空行 |
| 30 | CLAUDE.md:88（`以下に順番に答える:`） |
| 31 | 空行（CLAUDE.md:89） |
| 32-39 | CLAUDE.md:90-97（判定の1〜8問） |
| 40 | CLAUDE.md:98（行数上限の文） |

28行目の注記の全文（1行。前後に何も足さない）:

```
> この節は入口 CLAUDE.md から写した決まり（doc-agenda-nav 段3b）。節の中の「このファイル」は入口の CLAUDE.md を指す。
```

結果は40行。ファイルの最後は改行1つで終える。

### 4-2. CLAUDE.md から :86-98 の13行を消す（Edit）

消した後は、:84 ADR 優先の文、:85 空行、:86 `## UIガバナンス遵守（ADR-144）` と続く。結果は88行。

## 5. 確かめ方

担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage3b/impl4/ に保存する。

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-index && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-0. 起点が §2 の F1・F2 と合うかを確かめる。
- `git show "${B}:CLAUDE.md" | sed -n 83,101p` と `git show "${B}:docs/INDEX.md" | sed -n 20,24p` の出力を保存して照らす。
- `git show "${B}:CLAUDE.md" | wc -l` が 101、`git show "${B}:docs/INDEX.md" | wc -l` が 24 であること。
- 違えば何も変えずに NEEDS_DECISION:。

5-1. 写しが一字一句同じかを確かめる。3本の diff がすべて出力なしであること:

```
I=docs/INDEX.md
diff <(git show "${B}:CLAUDE.md" | sed -n 86,87p) <(sed -n 26,27p "$I")
diff <(git show "${B}:CLAUDE.md" | sed -n 88,98p) <(sed -n 30,40p "$I")
diff <(git show "${B}:docs/INDEX.md") <(sed -n 1,24p "$I")
```

あわせて `sed -n 28p "$I"` を保存して報告に貼る（§4-1 の注記の全文と同じであること）。

5-2. K11（消した13行のうち空行以外が、移す先にあるか）:

```
k11() { git show "${B}:$1" | sed -n "$2p" | while IFS= read -r l; do [ -z "$l" ] && continue; if grep -Fxq -- "$l" "$3"; then echo "OK"; else echo "MISSING $1:$2 :: $l"; fi; done; }
k11 CLAUDE.md 86,98 "$I" > /tmp/CC報告ファイル/an-stage3b/impl4/k11.txt
grep -c '^OK' /tmp/CC報告ファイル/an-stage3b/impl4/k11.txt; grep -c '^MISSING' /tmp/CC報告ファイル/an-stage3b/impl4/k11.txt
```

期待は OK 11・MISSING 0。

5-3. 入口から消した中身が想定どおりかを確かめる（出力なしであること）: `diff <(git show "${B}:CLAUDE.md" | sed 86,98d) CLAUDE.md`。あわせて `wc -l CLAUDE.md "$I"` が 88・40 であること。

5-4. 移す先の差分: `diff <(git show "${B}:$I") "$I"` が「24a25,40」と §4-1 の16行だけであること。

5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待は、どの数も増えないこと。

5-6. 名前での参照: `git grep -n -E 'このファイルにルールを追加|ルールを追加する前に' -- . ':!docs/handoff/'` の全文を保存する。期待は docs/INDEX.md:26 の1件だけ。

5-7. `git status --short` と `git diff "$B" --stat` を実行する。期待は §3 のファイルだけ。

5-8. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けて1回だけ実行し、結果を貼る（待たない）。

## 6. 分岐ごとの対処

- 5-0 で起点が合わない → 何も変えずに NEEDS_DECISION:（行番号は Opus が出し直す）。
- 5-1・5-3・5-4 で差が出る → 写し方か消す範囲の誤り。直して 5-1 からやり直す。2回直しても合わなければ BLOCKED:。
- 5-2 で MISSING が出る → 一覧を貼って BLOCKED:。
- 5-5 で数が増える、または 5-6 で他の行が出る → 一覧を貼って NEEDS_DECISION:（担当は直さない）。
- `scripts/dev/validate-pr-body.sh` に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行する。3回で通らなければ BLOCKED:。
- コミットのときに CLAUDE.md サイズチェックで止められた → 言い換えずに BLOCKED:。
- 見張りや自動判定に止められた → 言い換えずに、止まった手順、最後のコマンド、理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 写した節が、移す先に一字一句ある | §5-1 の3本の diff がすべて出力なし |
| K11: 入口から外した13行（空行以外の11行）が、移す先に 100% ある | §5-2 で OK 11・MISSING 0 |
| 入口から消えたのは :86-98 の13行だけ | §5-3 |
| 移す先に足したのは §4-1 の16行だけで、既存の24行は変わらない | §5-1 の3本目の diff と §5-4 |
| 目次から届かない文書、行き先の無いリンクが増えない | §5-5 |
| 触ったのは §3 のファイルだけ | §5-7 |

## 8. 戻し方

この PR の revert を main にマージする（CLAUDE.md に13行が戻り、目次の末尾の16行が消える）。

## 9. PR

- 作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-index。Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage3b-index` で作成済み（段3b-3 マージ後の origin/main が起点）で、このカードのコミットも入っている。担当は作り直さない。
- push は `git push -u origin release/doc-agenda-nav-stage3b-index`。
  - commit の後に `git log -1 --oneline` で確かめる。
  - push の後に `git log origin/release/doc-agenda-nav-stage3b-index -1 --oneline` で確かめる。
- PR の作り方:
  - `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage3b/pr-body-4.md` を作り、`--body-file` で渡す。
  - 作る前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
  - ready で作る。base は main。担当はマージせず、GO 記録も書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` には次を書く。
  - `recon: docs/handoff/doc-agenda-nav/recon.md`
  - `設計: docs/handoff/doc-agenda-nav/design.md`
  - `対象ADR: ADR-1040（関連: ADR-076）`
  - `設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`
  - `触るファイル: CLAUDE.md, docs/INDEX.md, docs/handoff/doc-agenda-nav/card-stage3b-index.md`
  - `削除するファイル: CLAUDE.md`
  - `区分: A（ADR-1015。正本文書を触るため B 区分に当たらない。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`
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

END OF CARD
