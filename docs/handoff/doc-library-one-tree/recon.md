# recon: 決まりを「1本の木」にする（説明の決まりを含む）

> この文書は何か（専門用語なしの1行）: AI が読む決まりが今どこに何か所あり、どこで食い違い、どこへたどれないかを数えた記録。

作成: 2026-11-04 Opus（設計パートナー）。基準: origin/main 996af2f0e（作業場所 HEAD と同じ、`git rev-list --count HEAD..origin/main` = 0）。
このリポジトリは公開されている。リポジトリの外の決まり（~/.claude・~/kb）は、ファイル名・行番号・件数だけを書き、本文は書き写さない。
生の出力はリポジトリの外のスクラッチパッド onetree/ にある（linecheck.txt・reach.txt・hooks.txt・mem-report.txt ほか）。

## 0. 既存の設計判断（ADR）の検索

- `docs/specs/doc-agenda-nav/kgi.md`（ADR-1040、PO 承認済み）: K1 毎回読む行数 ≤200、K5 段数 ≤3、K12 正しい手引きを開く率 ≥10/20。K5 は表紙（章）より下の子の文書を数えていない。
- `docs/handoff/doc-agenda-nav/library-design.md`（図書館化の設計）: 受け入れ L1〜L4・K11。MEMORY.md（覚え書きの目次）は対象外にした。
- `docs/handoff/doc-agenda-nav/library-ledger.md`: 決まりの台帳（83 の所在）。
- 説明の決まりそのものを扱う ADR は無い（`git grep -l -i -E "報告の型|chat-layout|chat-format|intent-reading" origin/main -- docs/adr` は 0 件、exit=1）。

## 1. 説明の決まり（PO への話し方）の置き場 — 9 種類

| # | 置き場 | 行 | 読まれ方 |
|---|---|---|---|
| E1 | ~/.claude/CLAUDE.md 報告の型 | 12〜34 | 毎回（自動で読み込み） |
| E2 | ~/kb/00-rules/chat-layout.md 区切り方 | 1〜9 | 毎回（E1 の 27 行目の取り込み） |
| E3 | ~/kb/00-rules/chat-format.md 言葉の選び方 | 1〜19 | 毎回（入力のたびに見張り ~/kb/scripts/hooks/plain-lang/hook.py 4・20・85〜108 行が表示） |
| E4 | ~/kb/00-rules/intent-reading.md 意図の読み方 | 1〜30 | **毎回は読まれない**。毎回読むのは指し示す1行（~/kb/AGENTS.md:16）だけ |
| E5 | 最初の指示 ~/.claude/prompts/salesanchor-designer.md【POへの説明】 | 35〜39 | 毎回（~/.claude/shell/ccopusgo.zsh 7〜8 行で付け足し） |
| E6 | 最初の指示 ~/.claude/prompts/salesanchor-claude-go.md | 54 | 毎回（同上） |
| E7 | `docs/ai-agents/design-partner.md` §3 | 88〜100 | 設計を始めるとき（`docs/INDEX.md:12`） |
| E8 | 覚え書き（自動メモリ）のうち話し方の決まりを持つもの | 10 ファイル | 目次の1行は毎回、本文は開いたときだけ |
| E9 | 見張り japanese-reply-guard.py・plain-lang/hook.py stop | — | 返事のたびに機械が点検 |

E8 の 10 ファイル: report_style・communication_style・always_japanese・agent_description_japanese・po_chat_three_lines・plain_language_session・session_rules_comprehensive・plain_explain_template・cost_in_yen・numeric_goal_rule。
このほか報告ファイルの置き場の覚え書きが 3 ファイル（report_file_output・report_output_dir・tmp_report_dir）あり、3 つとも同じ1つの決まり。

## 2. 食い違い — 6 件（事実）

公開リポジトリのため、文は引かず、行番号と話題だけを書く。覚え書きの行番号は各ファイルの実物（`grep -n`、2026-11-04 審査の指摘で付け直し）。

| # | 何が | 片方 | もう片方 |
|---|---|---|---|
| C1 | 返事の順番 | E1 19行（3段の型） | E5 36行（4段の型）、覚え書き plain_language_session 10行（3段で、E5 の4段のうち前の3段と同じ） |
| C2 | 選択肢の数と形 | E1 21行（番号つきの選択肢・数の上限・おすすめ印） | 覚え書き communication_style 20行（案を1つに絞って二択で聞く）、E7 94行（2案の形で推奨を添える） |
| C3 | 図 | E1 24行（返事に書かないものの一覧） | E7 91行（全体像の説明に図を付ける） |
| C4 | 表 | E1 24行（同上） | 覚え書き numeric_goal_rule 16行（表で示す） |
| C5 | 番号の欠け | E3 は 3 行目の項目の番号が 2 から始まり、1 が無い | — |
| C6 | 指し先の名前 | 覚え書き report_style 20行は E1 の中の見出しの名前を指す | その名前の見出しは無い（E1 26行の括弧書きにだけある） |

【推測ではなく未確認】C2〜C4 で PO がどちらを望むかは、まだ確かめていない（PO の言葉の日付は E1 が 2026-10-19、communication_style が 2026-09-29、numeric_goal_rule が 2026-10-27）。

## 3. 台帳の行番号 — 83 件のうち 5 件が見出しの行と合わない

方法: 台帳の所在 `ファイル:見出し:行番号` を全件、今の実物のその行に見出しの文字があるかで照合（onetree/linecheck.txt）。
結果: ROWS=83 OK=78 NG=5 MISSING=0。
NG の 5 件（R-15・R-91 → chat-layout.md 5行、R-92 → CLAUDE.md 20行、R-93 → CLAUDE.md 25行、R-94 → kb/AGENTS.md 16行）は、どれも見出しの行ではなく本文の行を指している。台帳の「行番号」が2つの意味（見出しの行／本文の行）で使われている。
機械の点検 `scripts/dev/doc-library-check.sh` は行番号を読み捨てている（parse_loc が切り離して使わない）。

## 4. 入口からたどれるか — 子の文書まで数えた

方法: AGENTS.md・CLAUDE.md から、文書の中のリンクと docs/...md の書き方をたどる（onetree/reach.py、onetree/reach.txt）。フォルダを指す行（`docs/INDEX.md:14` lessons.d、`:28` runbooks）は中身まで追っていない。

数え方で数が変わる。2通りで数えた（どちらも生出力あり）。

| 数え方 | たどれない手引き（docs/ai-agents・docs/agents・docs/runbooks） | 生出力 |
|---|---|---|
| (1) リンクと、逆引用符で囲んだ docs/…md の書き方だけ | 11（docs/agents/ の 6、docs/ai-agents/ の aeon-delivery・aeon-release・agent-roles・design-partner-preamble・task-template） | onetree/reach.txt |
| (2) (1) ＋ 囲まない docs/…md の書き方 ＋ 同じフォルダのファイル名だけの書き方 | **1**（docs/agents/generator.md） | onetree/reach2.txt |

- (1) の 11 のうち 10 は、ほかの手引きが (1) の拾わない書き方（逆引用符で囲まない根からのパス、またはファイル名だけ）で書いていた（例: `docs/ai-agents/design-partner.md:367` が design-partner-preamble.md を囲まない根からのパスで書く）。PO に最初に伝えた「11」は (1) の数で、(2) では 1 になる。設計では (2) を正式な数え方にする（design.md §5）。
- (2) でもフォルダの中を見ないとたどれないもの: lessons.d 19。
- (2) での深さ: 手引きは入口から 1〜5 段。4 段以上は runbooks 9・lessons.d 1。ただし runbooks は `docs/INDEX.md:28` がフォルダを指すので、フォルダ経由なら 2 段。K5（≤3）は表紙までしか数えていない。
- **正式な数え方（既存の CI）で数え直した結果（これを正とする）**: 既存の点検 `scripts/ci/check_doc_index.py`（K4 の CI、`.github/workflows/doc-index-reachability.yml:30`）は、範囲が docs/specs・docs/ai-agents だけ（同ファイル 142 行）で、今は unreached=0。範囲だけを docs/agents・docs/runbooks まで広げた写し（onetree/cdi_wide.py、142 行の範囲だけを変更）で数えると、**unreached=1（docs/agents/generator.md）**、broken_link=8（onetree/docindex-wide.txt）。
  - 切れたリンク 8 件の内訳: `docs/runbooks/adr-019-english-ui-temporary-deploy.md` 84・94・195 行（PR 本文の例の中のリンクで、リポジトリの根から書いている）、`docs/runbooks/discord-role-order-guide.md` 43・54・63・84・93 行（画像ファイル。`git ls-files | grep -c discord-role-order-0` = 0 で、画像そのものが無い）。
  - docs/agents/ は Codex 用の担当の定義（例: generator.md 4 行目でモデル名が GPT 系）。`.github/workflows/aeon-script-check.yml:20・35・74` が使っている。`docs/ai-agents/codex-operations.md:51` は `docs/agents/*` という書き方で、ファイル名を1つずつ書いていない。generator.md 以外の 6 件は、ほかの手引きが名前を書いているのでたどれる。
  - PO に最初に伝えた「11」は、この正式な数え方ではなく (1) の数だった。

## 5. 2つの根の重なり — 5 話題

根は2つ: (A) リポジトリの入口 → `docs/INDEX.md` の木、(B) 個人の目録（~/.claude/CLAUDE.md:60〜65）→ 本（~/.claude/books/）。

| 話題 | (B) 個人の本 | (A) リポジトリ |
|---|---|---|
| commit の文 | R-21 git-workflow.md:8 | INDEX:9 実行役のチェックリスト（commit の前） |
| PR を作る | R-22 git-workflow.md:17 | INDEX:9・INDEX:10 |
| 担当を呼ぶ | R-31 agents.md:8 | INDEX:12・INDEX:13 |
| 並行に分ける | R-32 agents.md:15 | INDEX:11 並行ターミナル |
| PO への話し方 | E1〜E4 | E7 design-partner §3 |

R-22 は「リポジトリ側が正」と書いてある（CLAUDE.md:62）。ほかの4話題は、どちらが正かが書かれていない。中身が食い違うかは「PO への話し方」だけ確かめた（§2）。

## 6. 今の数（毎週の点検 `scripts/dev/doc-entry-weekly-check.sh`、2026-11-04）

K1=166 行、K9=6.3k、L2=0、L3 一致、K12 最終 2026-10-26。

## 7. 次の一手

この数をもとに、数で測る合格条件（KGI）の案を PO に出し、承認をもらってから設計（design.md）を書く。
