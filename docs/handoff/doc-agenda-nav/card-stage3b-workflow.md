# 実装カード 段3b-3 — 「成果物の完了定義」を CLAUDE.md から標準ワークフローへ移す（文は変えない）

> この文書は何か：doc-agenda-nav 段3b-3 の作業指示書です。CLAUDE.md の「### 成果物の完了定義（必須）」の7行のうち、docs/STANDARD-WORKFLOW.md にまだ無い3行を同じ文書の「2. 成果物の完了定義」へ一字も変えずに写し、既に同じ意味の文がある4行は対応表で結んだうえで、見出しごと CLAUDE.md から消します。

- 設計: docs/handoff/doc-agenda-nav/design.md §5-2（CLAUDE.md :70-80 の行「1行を案文 AGENTS.entry.md、本文は docs/STANDARD-WORKFLOW.md（正本）。:75（フルパス:行番号）・:77（PR 本文の「標準ワークフロー確認」必須）・:78（recon/design を git add）は STANDARD-WORKFLOW に現物の記述が無い＝段3b で足す」）・§8（段3b の行「1PR に移動先1つ」）・§7（移動時に文が欠けるリスク）
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076
- 状態: 設計は審査済み（PR #4649）。PO の実装承認: 2026-10-23「1」（Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事）
- 危険便: CI の分類（scripts/check-process-artifacts.js の危険パス）には当たらない。ただし docs/ai-agents/executor-checklist.md §2 により CLAUDE.md に触る便は「危険ファイル変更 PR」として扱う。GO は ADR-1003 の委譲により Opus が PR コメントで出す（担当は GO を書かない・マージしない）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と確かめは Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、GO とマージは Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段3b-3 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れる: §3 の3ファイル。

入れない:
- 写す文の書き換え・言い回しの改善。docs/STANDARD-WORKFLOW.md の既存の文の変更。
- CLAUDE.md の「## 標準開発フロー（正本: docs/STANDARD-WORKFLOW.md）」の見出しと、その下の「作業開始前に … 必ず read すること。…」の1行（案文 AGENTS.entry.md :42 に要点が残る。段3c で入口ごと入れ替える）。
- AGENTS.md（この決まりは AGENTS.md に無い）。

Opus の設計判断（このカードで決めたこと）:
- 段3b では、移動先へ一字一句写し、入口から消すのは「入口の案文に要点が残らない行」だけにする。「成果物の完了定義」の7行は案文に1行も残らないので、見出しごと消す。
- 移動先に同じ意味の文が既にある4行（ADR 検索・design.md の要件・KGI/KPI の粒度・役割）と見出しは写さず、§4-2 の対応表で結ぶ（同じ決まりを2か所に置かない＝設計 §5-2 の「本文は STANDARD-WORKFLOW（正本）」）。現物に無い3行だけを写す。

## 2. 前提の事実（Opus が 2026-10-23 に確かめた。起点は段3b-2 のマージ後の origin/main c0dfb4a87）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 段3b-2 の後の CLAUDE.md は109行。:57 `---`、:58 空行、:59 `## 標準開発フロー（正本: docs/STANDARD-WORKFLOW.md）`、:60 空行、:61 「作業開始前に…」の1行、:62 `### 成果物の完了定義（必須）`、:63 ADR 検索、:64 recon.md のフルパス:行番号、:65 design.md、:66 PR本文の標準ワークフロー確認、:67 git add、:68 KGI/KPIの粒度、:69 役割、:70 空行、:71 `---` | `git show origin/main:CLAUDE.md \| sed -n 57,71p`（c0dfb4a87。/tmp/CC報告ファイル/an-stage3b/recon/06-claude-after2.txt） |
| F2 | docs/STANDARD-WORKFLOW.md は175行で、段3b の起点から変わっていない。:77 `## 2. 成果物の完了定義（"在るだけ"を認めない）`、:78 前文、:79 KGI、:80 recon証拠、:81 Phase 3 設計、:82 空行、:83 `## 完了の定義` | /tmp/CC報告ファイル/an-stage3b/recon/05-workflow.txt |
| F3 | 移動先に「フルパス」「標準ワークフロー確認」「git add」は0件 | `git show origin/main:docs/STANDARD-WORKFLOW.md \| grep -n -E 'フルパス\|標準ワークフロー確認\|git add'` 出力なし |
| F4 | 「成果物の完了定義」「標準開発フロー（正本」を名前で指すのは CLAUDE.md 自身の見出しと STANDARD-WORKFLOW.md:77 だけ（docs/handoff を除く） | `git grep -n -E '成果物の完了定義\|標準開発フロー（正本' origin/main -- ':!docs/handoff'` |
| F5 | AGENTS.md に STANDARD-WORKFLOW・recon・design.md・フルパスの記述は0件 | `git show origin/main:AGENTS.md \| grep -n -E 'STANDARD-WORKFLOW\|recon\|design\.md\|フルパス'` 出力なし |

## 3. 触るファイル（これ以外は触らない）

- 変更: `docs/STANDARD-WORKFLOW.md`
- 変更: `CLAUDE.md`
- 変更: `docs/handoff/doc-agenda-nav/card-stage3b-workflow.md`（このカード。担当は §11 報告欄の追記だけ）

## 4. 作り方

行番号はすべて作業場所の起点（`B=$(git merge-base origin/main HEAD)`）のもの。中身は `git show "${B}:CLAUDE.md" | sed -n 64p` のように起点から取り出して写す。1文字も変えない。zsh では必ず `"${B}:CLAUDE.md"` と書く。

### 4-1. docs/STANDARD-WORKFLOW.md の :81 の次に3行を足す（Edit）

| 足した後の行 | 中身 |
|---|---|
| 82 | CLAUDE.md:64（`- recon.md: フルパス:行番号 で引用（例: …）。短縮禁止。`） |
| 83 | CLAUDE.md:66（`- PR本文: `### 標準ワークフロー確認` セクション必須。`） |
| 84 | CLAUDE.md:67（`- recon.md と design.md は必ず git add してからコミットすること。`） |

元の :82 空行以降は 85 行目から続く。結果は178行。

### 4-2. 写さない行の対応表（移動先に同じ意味の文が既にある。審査役がこの表を確かめる）

| CLAUDE.md の行 | 移動先で対応する行 |
|---|---|
| :62 `### 成果物の完了定義（必須）` | STANDARD-WORKFLOW.md:77 `## 2. 成果物の完了定義（"在るだけ"を認めない）` |
| :63 着手前に既存 ADR を検索（git grep -i docs/adr/ ＋ FEATURE-INDEX.md。自動ロードされない。結果を recon.md に明記） | STANDARD-WORKFLOW.md:25（Phase 2 の行の「着手前に必ず既存 ADR を検索 … FEATURE-INDEX.md を引く。ADR は自動ロードされない＝指さないと見落とす」）と :80（「既存 ADR 検索の結果 … を明記すること。保存先 … recon.md」） |
| :65 design.md: recon/ADR 相互参照 ＋ 基準・検証方法の表 ＋ 外部事例欄 記入済み | STANDARD-WORKFLOW.md:81（「各受け入れ基準に検証方法 … のリンク」「設計→recon→ADR が相互参照」「外部・過去事例の参照と我々への応用欄が記入済み」） |
| :68 KGI/KPIの粒度（○×を一義に判定・抽象語禁止→観測可能な事象に分解） | STANDARD-WORKFLOW.md:102-103 |
| :69 役割（Generator は単純作業のみ・Planner が file:line＋変更前後コード＋触らない範囲まで設計・不備は設計粒度の責任） | STANDARD-WORKFLOW.md:109-111 |

### 4-3. CLAUDE.md から :62-69 の8行を消す（Edit）

消した後は :61 「作業開始前に…」の1行、:62 空行（起点の :70）、:63 `---`。結果は101行。

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage3b/impl3/ に保存）

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-workflow && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-0. 起点が §2 の F1・F2 と合うか: `git show "${B}:CLAUDE.md" | sed -n 57,71p` と `git show "${B}:docs/STANDARD-WORKFLOW.md" | sed -n 77,83p` を保存して照らす。違えば何も変えずに NEEDS_DECISION:。

5-1. 写しが一字一句同じか（3本の diff がすべて出力なし）:

```
W=docs/STANDARD-WORKFLOW.md
diff <(git show "${B}:CLAUDE.md" | sed -n 64p) <(sed -n 82p "$W")
diff <(git show "${B}:CLAUDE.md" | sed -n 66p) <(sed -n 83p "$W")
diff <(git show "${B}:CLAUDE.md" | sed -n 67p) <(sed -n 84p "$W")
```

5-2. K11（写した3行が移動先にあるか。対応表の5行は審査役が確かめる）:

```
k11() { git show "${B}:$1" | sed -n "$2p" | while IFS= read -r l; do [ -z "$l" ] && continue; if grep -Fxq -- "$l" "$3"; then echo "OK"; else echo "MISSING $1:$2 :: $l"; fi; done; }
{ k11 CLAUDE.md 64 "$W"; k11 CLAUDE.md 66,67 "$W"; } > /tmp/CC報告ファイル/an-stage3b/impl3/k11.txt
grep -c '^OK' /tmp/CC報告ファイル/an-stage3b/impl3/k11.txt; grep -c '^MISSING' /tmp/CC報告ファイル/an-stage3b/impl3/k11.txt
```
期待: OK 3・MISSING 0。あわせて §4-2 の対応先の行（`sed -n '25p;77p;80,81p;102,103p;109,111p' "$W"`）を保存し、報告に貼る。

5-3. 入口から消した中身が想定どおりか（出力なし）: `diff <(git show "${B}:CLAUDE.md" | sed 62,69d) CLAUDE.md`。あわせて `wc -l CLAUDE.md "$W"` が 101・178。

5-4. 移動先の差分: `diff <(git show "${B}:$W") "$W"` が「81a82,84」と §4-1 の3行だけ。

5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待: どの数も増えない。

5-6. 名前での参照: `git grep -n -E '成果物の完了定義' -- . ':!docs/handoff/'` の全文を保存。期待: STANDARD-WORKFLOW.md:77 の1件だけ。

5-7. `git status --short` と `git diff "$B" --stat`（期待: §3 のファイルだけ）。

5-8. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けたものを1回だけ実行して貼る（待たない）。

## 6. 分岐ごとの対処

- 5-0 で起点が合わない → 何も変えずに NEEDS_DECISION:（行番号を Opus が出し直す）。
- 5-1・5-3・5-4 で差が出る → 写しか消す範囲の誤り。直して 5-1 からやり直す（2回直しても合わなければ BLOCKED:）。
- 5-2 で MISSING が出る → 一覧を貼って BLOCKED:。
- 5-5 で数が増える・5-6 で他の行が出る → 一覧を貼って NEEDS_DECISION:（担当は直さない）。
- `scripts/dev/validate-pr-body.sh` に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行（3回で通らなければ BLOCKED:）。
- 見張りや自動判定に止められた → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 写した3行が移動先に一字一句ある | §5-1 の3本の diff がすべて出力なし |
| K11: 入口から外した8行が移動先に 100% ある（3行は同文・5行は同義） | §5-2 の OK 3・MISSING 0 と、§4-2 の対応表を審査役が実物で確かめる |
| 入口から消えたのは :62-69 の8行だけ | §5-3 |
| 移動先に足したのは3行だけ | §5-4 |
| 目次から届かない文書・行き先の無いリンクが増えない | §5-5 |
| 触ったのは §3 のファイルだけ | §5-7 |

## 8. 戻し方

この PR の revert を main にマージする（CLAUDE.md に8行が戻り、移動先の3行が消える）。

## 9. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-workflow は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage3b-workflow`（段3b-2 マージ後の origin/main 起点）で作成済みで、このカードのコミットも載っている。担当は作り直さない。
- push は `git push -u origin release/doc-agenda-nav-stage3b-workflow`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage3b-workflow -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage3b/pr-body-3.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る。base は main。担当はマージしない。GO 記録は書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` に `recon: docs/handoff/doc-agenda-nav/recon.md`、`設計: docs/handoff/doc-agenda-nav/design.md`、`対象ADR: ADR-1040（関連: ADR-076）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`触るファイル: CLAUDE.md, docs/STANDARD-WORKFLOW.md, docs/handoff/doc-agenda-nav/card-stage3b-workflow.md`、`削除するファイル: CLAUDE.md`、`区分: A（ADR-1015。正本文書を触るため B 区分に当たらない。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`、`PO承認: 「1」（2026-10-23）`、`Opus 審査記録: コード審査はこれから` を書く。§5-2 の OK と MISSING の数、§5-5 の SUMMARY 行を本文に貼る。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了報告に: 冒頭の受領文／§5-0〜5-8 の出力（長いものはファイルのパス）／PR の URL／新しい HEAD の sha／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 委任の定型: sleep しない／ファイルの作成と編集は Write/Edit ツールで行う／PR 作成前に validate-pr-body.sh で exit 0／フックや自動判定に止められたら言い換えて再試行しない

## 11. 報告欄（担当が追記）

- 5-0 起点一致（CLAUDE.md 109行・STANDARD-WORKFLOW.md 175行）。5-1 diff 出力なし。5-2 OK 3・MISSING 0。5-3 差なし・101行/178行。5-4 81a82,84 のみ。5-5 SUMMARY unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10（起点と同じ）。5-6 STANDARD-WORKFLOW.md:77 の1件のみ。

END OF CARD
