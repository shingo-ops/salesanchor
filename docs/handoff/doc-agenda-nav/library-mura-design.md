# 図書館化: 本とリポジトリの手順書の重なりによるムラを無くす（設計の草案 第2版）

作成: 2026-11-03 Opus（設計担当）。状態: **設計案作成済み・Fable 評価 REVISE を反映済み・再審査前**。置き場は PO 承認済み（2026-11-03 PO 原文「1」＝§4-1 の P1）。
対象ADR: ADR-1040。現在地: [recon.md](./recon.md)（docs/handoff/doc-agenda-nav/recon.md）。
根拠: [library-errors.md](./library-errors.md)（練習の組の記録）、[library-design.md](./library-design.md) §4-1・§7、[library-ledger.md](./library-ledger.md)、[library-tasks.md](./library-tasks.md)。
このリポジトリは公開されている。~/.claude の決まりの本文は書かない。ファイル名・行番号・数・要点だけを書く。生出力と Fable の評価全文は「~/CC報告ファイル-keep/doc-library-20261102/」に置く（mura-eval-fable.md）。
リポジトリ側の根拠は origin/main bfcaaa29b を `git show origin/main:<path>` で読んだもの。

## 1. 目的（PO の言葉）

PO 2026-11-03:「無理なく無駄とムラを無くしてくれ」。ムラ＝同じ場面でも、AI が読む場所によって守られる決まりが変わること。無駄＝同じ決まりが2か所以上にあること。

## 2. 観測した事実

| # | 事実 | 根拠 |
|---|---|---|
| F1 | 練習で本を開かなかった4回（B2・B4）は、どれも最初の応答の中で docs/INDEX.md を読み、リポジトリの手順書で答えた（B2-1 は同じ応答の中で別の手順書の読みと並べて出した） | practice/B2-*.jsonl・B4-*.jsonl の tool_use の順と応答 id。AGENTS.md:45（写し b492b3f1c） |
| F2 | B4 の2回とも、答えに「/security-review」が無い。B2 の2回とも「試験の計画」「全部の commit を見る」に当たる語が無い。B2-2 は「git diff」も無い | practice/*.jsonl の result を語で照合（Opus と Fable が別々に実行し一致） |
| F3 | 安全の点検の決まりは、同じ趣旨が3か所（本 agents.md:14・~/.claude/rules/common/code-review.md:24・同:52-60）、同じ語がさらに2か所（~/.claude/CLAUDE.md:7・code-review.md:78）にある。CLAUDE.md:7 はきっかけが違う別の決まり（問題を見つけたとき）。本の行はファイル名の形、code-review.md:52-60 はコードの中身で判定し、軸が違う | `grep -rn "security-review"`（.bak 除く）の4行。mura-eval-fable.md §1 F3・§2 C1 |
| F4 | code-review.md は paths 付き（拡張子8つ: .py・.ts・.tsx・.js・.mjs・.sh・.sql・.css）。paths 付きの決まりは、当てはまるファイルを Read・Write・Edit したとき、または1ファイルの cat/head のときに読み込まれる。grep・sed は読み込まれる例に無い。B4 の2回は grep と sed だけだった | code-review.md:1-11。公式 code.claude.com/docs/en/memory「Path-specific rules」（Context7 で 2026-11-03 確認） |
| F5 | リポジトリには PR 本文の自動検査がある（「### 標準ワークフロー確認」・「触るファイル:」を求め、git diff と照合） | scripts/dev/validate-pr-body.sh:31-35・:85-102・:105-170 |
| F6 | PR のひな形に試験のチェック1つ（:43）がある。変更一覧の確認（:19）は release PR だけの欄（:17） | .github/PULL_REQUEST_TEMPLATE.md |
| F7 | マージ前の reviewer は見張り review-gate が HEAD の sha 付きの記録を求め、HEAD が変わると同じ記録では通らない | ADR-1029:17・:28。library-design.md:311 |
| F8 | クラウドの担当には、既定では ~/.claude が無い。setup script で ~/.claude/CLAUDE.md を書ける道は公式にある（rules/・books/ を同じ道で置けるかは未確認） | library-tasks.md:20。公式 code.claude.com/docs/en/cloud-environments（Fable が Context7 で確認） |
| F9 | 本 R-22 は PR のひな形を持たない作業場所でも使われる。agent-console・~/kb の .github/ は workflows だけ | `ls <repo>/.github/` の結果 |
| F10 | リポジトリ側の手順書（AGENTS.md・CLAUDE.md・docs/ai-agents/・docs/STANDARD-WORKFLOW.md・docs/INDEX.md・.claude/agents/）に「/security-review」「security review」の語は0件。「試験の計画」「commit 履歴」に当たる語も（AGENTS.md・docs/ai-agents・STANDARD-WORKFLOW.md・PR ひな形・branch-operations/README.md で）0件 | `git grep -n -i` を origin/main bfcaaa29b に実行（Opus が手元で実行・当たり0） |
| F11 | リポジトリの実装役の点検の正本は docs/ai-agents/executor-checklist.md（「ここ以外に複製しない」と冒頭に書いてある）。CLAUDE.md の最終行から必読として指される。リポジトリの .claude/ に rules/ は無い（agent-config.sh・agents・hooks・settings.json だけ） | executor-checklist.md:1-5。CLAUDE.md（origin/main）。`git ls-tree origin/main .claude/` |
| F12 | 重なりの点検 doc-library-check.sh が数える範囲は ~/.claude/CLAUDE.md・リポジトリ CLAUDE.md・AGENTS.md・~/.claude/rules・~/.claude/books。executor-checklist.md は範囲外 | doc-library-check.sh:99-113・:162-164・:242 |

## 3. ムラと無駄の出どころ

| 場面 | 手元の AI に届く道 | クラウドの担当に届く道 | ムラ・無駄 |
|---|---|---|---|
| (a) 安全の点検 | 本 agents.md:14（開けば）。code-review.md:24・:52-60（コードを Read したときだけ） | 無し（F8・F10） | 3か所に同じ趣旨（無駄）。読み方でどれも届かない（ムラ。F2・F4） |
| (b) PR の作り方 | ひな形・自動検査（必ず）。本 R-22（開けば） | ひな形・自動検査だけ（F10） | R-22 の項目1「全 commit を見る」・項目4「試験の計画」はリポジトリ側の誰も担っていない（mura-eval-fable.md §2 C2 の表）→ 本を開かないと抜ける（F2） |
| (c) マージ前の審査 | 見張りが止める（F7） | 同じ（見張りは合流の時に止める） | ムラ無し |
| (d) 担当の呼び方 | 本 agents.md:11（条件付きで planner）。development-workflow.md:29（条件なしで planner）・:41 と code-review.md:26 と本:13（マージ前に reviewer） | 無し | 条件の違う決まりが2つ（ムラ）。同じ決まりが3か所（無駄） |
| (e) commit の形 | 本 R-21。development-workflow.md:47（同じ趣旨）・:48（rules/common/git-workflow.md へのリンク。段2b で本へ移したので切れている） | 無し | 2か所（無駄）。切れたリンク |

## 4. 変える案

### 4-1 置き場の原則（PO の判断が要る点）

クラウドの担当はコードを書く（PO 方針: 手元で起動してよいのは reviewer・evaluator だけ）。(a)(b) はコードを書く担当に要る。F8・F10 から、~/.claude に置く限りクラウドには届かない。届く道は3つ:

| 案 | 届く範囲 | 弱み |
|---|---|---|
| P1 リポジトリの executor-checklist.md に、リポジトリの言葉で書き足す | 手元・クラウドの両方（CLAUDE.md の必読） | 公開リポジトリに載る。~/.claude の本文を写さず、リポジトリ独自の文で書く必要がある |
| P2 ~/.claude のまま（今のまま） | 手元だけ | クラウドの担当は (a)(b) を受け取らない |
| P3 クラウドの setup script で ~/.claude を書く | 両方（rules/・books/ は未確認） | クラウド環境の設定の変更になり、今回の禁止（settings 等）に当たるかどうか確かめていない |

設計の推奨は P1。理由: 両方に届く道で、リポジトリの「ここ以外に複製しない」正本（F11）にそろえられる。

**PO の決定: P1**（2026-11-03 PO 原文「1」。選択肢「アプリの手順書に新しい文で書く」）。

### 4-2 変更（P1 の場合）

| # | 何を | 変える前 | 変えた後 | 誰が |
|---|---|---|---|---|
| C1 | 安全の点検を、リポジトリでは executor-checklist.md の1か所にする | リポジトリ側0か所（F10）。~/.claude に3か所（F3） | executor-checklist.md の §2 実装便に1行（文は §4-2b の最終形。リポジトリの言葉で新しく書く）。~/.claude 側は本 agents.md:14 を消し、そのファイル名の形を code-review.md:52-60 の列挙に足して1か所にする（他の作業場所のため残す） | リポジトリ: クラウドの Sonnet（docs のみ）。~/.claude: PO が `!` で台本 |
| C2 | PR の作り方の抜け2項目を、リポジトリでも担う | 項目1・4 はリポジトリの誰も担っていない | executor-checklist.md の §2 実装便に1行（文は §4-2b の最終形）。目録 R-22 の行に M5 の注記を足す（ひな形の無い場所では本のまま） | 同上 |
| C3 | 担当の呼び方と commit の形の重なりを消す | development-workflow.md:29・:41・:47-48 と本の R-21・R-31 | development-workflow.md:29 を本の条件に合わせる（または消して本を指す）。:41・:47 を消して本を指す。:48 の切れたリンクを本の目録の行に直す | PO が `!` で台本 |
| C4 | 練習に1題足す | B1〜B4 の4題 | B1〜B4 は変えない（90日後の比較のため。library-tasks.md:24-31）。B5「backend/app/auth/passwords.py を Read してから、マージ前に要る点検を答えて」を足す。§7 の3分類とは別の列「要る決まり（/security-review）が答えに入ったか」で数える | Opus（docs）と PO の `!` 台本 |

- 対の記録: library-design.md §4-1（:173・:181）どおり、言い直しの対は pairs.txt に書き、両方に同じ R-nn を付け、消えたことを `grep -F` で確かめる。台帳 library-ledger.md の該当行（R-31・R-101〜R-108・development-workflow.md の行）の状態を直す。
- 触らない: フック・settings・permits・agent-console・Ruleset（PO の禁止）。CLAUDE.md:7（別の決まりとして残す）。本の他の行。
- 消した行は「~/CC報告ファイル-keep/doc-library-20261102/」の写しのフォルダに残す。

### 4-2b 変える文（最終形）

リポジトリ（公開。リポジトリの言葉で新しく書いた文。~/.claude の文の写しではない）:

- docs/ai-agents/executor-checklist.md の §2 実装便の、「編集後、commit前に重複検査」の行の直後に2行を足す:
  - `- コードを直した便は、PR を出す前に /security-review を流す。対象は、パスに auth/・token・password・payment を含むファイルと、認証・権限・決済・暗号・秘密の値を扱うコード。結果の要点を PR 本文の「概要」に書く。流せないときは §3 で止まる。`
  - `- PR 本文の「概要」は、ブランチの全部の commit（最後の1つだけでなく）を読んで書く。試験の計画（流した試験とその結果、まだ流していない試験は TODO）も書く。`
- 危険ファイル（§2 の「正本・統治ファイル」）として扱う。GO は ADR-1003 の委任で Opus が出す。

~/.claude（PO が `!` で流す台本。場所は「~/CC報告ファイル-keep/doc-library-20261102/mura-run.sh」。文は目印の文字列で1か所だけ置き換え、目印が1か所でなければ何も書かずに止まる。目印は行全体（字下げから行末まで）とする。~/.claude/rules/common/development-workflow.md の「./git-workflow.md」へのリンクは :14 と :48 の2か所にあるため、語だけを目印にしない。書く前に写しを同じフォルダの mura/ に取る）:

| # | ファイル | 変更 |
|---|---|---|
| M1 | ~/.claude/books/agents.md | R-31 のうち /security-review の1行（:14）を消す |
| M2 | ~/.claude/rules/common/code-review.md | Security Review Triggers（:50-60）の列挙の最後に、パスに auth/・token・password・payment を含むファイルの1行を足す |
| M3 | ~/.claude/rules/common/development-workflow.md | :29（planner）を「本 agents の R-31 に従う」に、:41（reviewer）を「本 agents の R-31 に従う（マージ前。review-gate が強制）」に置き換える。:47-48（commit の形と切れたリンク）を1行「本 git-workflow の R-21・R-22 に従う」にする。:14 の切れたリンク（./git-workflow.md）を本のパスに直す |
| M4 | ~/.claude/books/git-workflow.md | :26-27 の切れたリンク（./development-workflow.md）を ~/.claude/rules/common/development-workflow.md に直す |
| M5 | ~/.claude/CLAUDE.md | 目録 R-22 の行の「→」の前に「（PR のひな形と実装役の点検表があるリポジトリではそちらが正）」を足す。点検の読み方（doc-library-check.sh:354 の `→ (\S+)$`）を崩さないため「→」の後ろには足さない |

- 台本のあと: 台帳 library-ledger.md の行番号を実物の見出しの行に合わせる（R-32・R-33 は1行上がる。R-105 以降は1行下がる。development-workflow.md の :48 より後の見出しは1行上がる）。pairs.txt に M1 の対（R-31 の消す側 → 残す側 code-review.md の足した行）を1行足す。
- M3 は「書いた直後に reviewer」を「マージ前に reviewer」にそろえる。書いた直後という時の指定は落ちる（review-gate が合流の前に必ず止めるので、抜けることはない）。

PR の手順（本 R-22 の5項目）を、M5 と executor-checklist のあとに誰が担うか（mura-eval-fable.md §2 C2 の表を更新）:

| 項目 | 担う場所（このリポジトリ） |
|---|---|
| 1 全部の commit を見る | executor-checklist.md §2（足す行） |
| 2 base...HEAD の変更を見る | validate-pr-body.sh:105-170 が機械で照合（触るファイルの宣言） |
| 3 PR の要約 | PULL_REQUEST_TEMPLATE.md:1-11 |
| 4 試験の計画（TODO 付き） | executor-checklist.md §2（足す行） |
| 5 新しいブランチは -u で push | AGENTS.md:43 |

- 範囲外: code-review.md:24（審査をするきっかけの一覧。安全の点検の道具を名指ししない別の決まりとして残す）。code-review.md:78（道具の一覧表）。CLAUDE.md:7（問題を見つけたときの別の決まり）。

### 4-3 落ちる範囲（変えても届かない場面）

- 手元で、コードのファイルを grep・sed だけで読み、本も開かない場面では、~/.claude 側の安全の点検は届かない（F4）。リポジトリで作業する場合は C1 の executor-checklist.md が必読なので届く。
- 他の作業場所（agent-console・~/kb）は ~/.claude 側だけ。今までと同じ。

## 5. 選ばなかった案

- 見張り（フック）で本の行を出す: 今回はフックの変更が禁止。
- スキル化: Fable の評価で REVISE（library-errors.md §3）。
- 本の R-22 を消す: ひな形の無い作業場所で決まりが無くなる（F9）。
- リポジトリの .claude/rules/ に paths 付きで置く: 両方に届くが、読み込まれるのはファイルを Read したときだけ（F4）で、executor-checklist.md の必読より届く場面が狭い。リポジトリに文書の置き場を1つ増やす。

## 6. 受入条件

| 基準 | 検証方法 |
|---|---|
| 安全の点検の決まりが ~/.claude で1か所 | `grep -rn "security-review" ~/.claude/CLAUDE.md ~/.claude/books ~/.claude/rules`（.bak 除く）の当たりが CLAUDE.md:7（別の決まり）と code-review.md の2行（:52 台・:78 の表）だけ。本は0 |
| リポジトリの手順書で1か所 | F10 と同じ範囲 `git grep -n -i -E "security-review|security review" origin/main -- AGENTS.md CLAUDE.md docs/ai-agents docs/STANDARD-WORKFLOW.md docs/INDEX.md .claude/agents` の当たりが executor-checklist.md の1行だけ（docs/handoff・docs/adr・docs/runbooks の記録は数えない） |
| PR の抜け2項目がリポジトリにある | executor-checklist.md に「全部の commit」「試験の計画」の語が各1回 |
| 切れたリンクが0 | ~/.claude/rules/common/development-workflow.md に「](./git-workflow.md)」が0件。~/.claude/books/git-workflow.md に「](./development-workflow.md)」が0件（固定文字列で数える） |
| 目録の読み方が崩れない | doc-library-check.sh で L3_MATCH=yes（M5 のあと） |
| 毎回読む量が増えない | `bash scripts/dev/doc-entry-weekly-check.sh` で K1≤200・K9≤6.5k・RESULT=OK |
| L2・L3 が崩れない | `bash scripts/dev/doc-library-check.sh` で L2=0・L2_UNTAGGED=0・L3_MATCH=yes |
| 場面でムラが無い | B5 を2回。「/security-review が答えに入った」回数を数える。合格線は測る前に PO に見せて決める。B1〜B4 は 2027-02-01 に同じ題・同じ台本で測り直す |

## 7. 確かめていないこと

- U1: B5 で code-review.md が本当に読み込まれたかは、答えの語でしか分からない（読み込みは tool_use に出ない。InstructionsLoaded hook で記録できるがフックの変更は禁止のため使わない）。
- U2: クラウドの担当が executor-checklist.md を実際に読むか（CLAUDE.md の必読の行に従うか）。次にクラウドへ実装を出すとき、実行記録で読んだかを数える。
- U3: P3（setup script）が今回の禁止に当たるか。P1 に決まったので確かめない。
- U4: クラウドの担当で /security-review が使えるか。使えないときは executor-checklist §3 で止まって報告するので、黙って抜けることは無い。最初のクラウドの実装便で確かめる。

## 8. 戻し方

- リポジトリ: revert の PR。
- ~/.claude: 写しのフォルダの元のファイルを戻す（PO の `!` 台本に戻す手順を入れる）。

## 9. 外部・過去事例の参照と我々への応用

外部事例は使わない。公式の読み込みの規則（F4・F8）と、このリポジトリでの実測（F1・F2・F10）で足りるため。
過去事例は1つ借りる。クラウドの担当には手元用の作業前点検を流させない形（card-maintain-m3.md §3-1）。本設計のカード §3-0 に入れた（第1回の実行は入れ忘れで止まった。2026-11-03）。

## 9-2. 維持の仕組み

守り手: 定期実行「入口の文書 週次点検」（ADR-1040）が毎週 `scripts/dev/doc-entry-weekly-check.sh` を流し、その中の `scripts/dev/doc-library-check.sh` が本の重なり（L2）を数えて 0 でなければ `RESULT=NG`。リポジトリ側の重なり（executor-checklist.md 以外の security-review の当たり）は機械では数えず人手で守る。理由: 当たりの対象が手順書の数か所に限られ、§6 の git grep 1本で確かめられるため。

- リポジトリ側: 決まりは docs/ai-agents/executor-checklist.md の1か所だけ（F11「ここ以外に複製しない」）。重なりは §6 の git grep で数える。
- ~/.claude 側: 本の重なりは doc-library-check（L2）と毎週の点検（doc-entry-weekly-check）が数える。0 でなければ週次の知らせで分かる。
- 練習の題 B5（§4-2 C4）で、手順書を読んだ答えにも security-review が入るかを測る。次の測り直しは 2027-02-01。

## 10. 審査の記録

- 第1版: Fable REVISE（全文はリポジトリの外: mura-eval-fable.md）。§5 の6点を第2版で直した。
- 第2版: Fable REVISE（mura-eval-fable-2.md）。残り5点（担当表を設計に載せる・code-review.md:24 の扱い・§6 の grep の範囲・「PR 前」の節が無い・目印を行全体に）を直した。
- 第2版の直しの確かめ（Opus・同一 AI の自己審査。独立した第二者の審査ではない）: AGENTS.md:43 に push -u の形があることを origin/main bfcaaa29b で確かめた。§6 の grep の範囲は F10 と同じ範囲にした。判定 **APPROVE**。未解決: U1〜U4（合格前に事実にすべきものは無い。Fable 第2版 §6 の確かめ）。
