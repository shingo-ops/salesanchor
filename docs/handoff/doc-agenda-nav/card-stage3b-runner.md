# 実装カード 段3b-1 — 「VPS コンテナの落とし穴」を入口2本から運用コマンド集へ移す（文は変えない）

> この文書は何か：doc-agenda-nav 段3b-1 の作業指示書です。CLAUDE.md と AGENTS.md の両方にある同じ文の節「VPS コンテナの落とし穴」を、docs/ops/runner-commands.md の1か所へ一字も変えずに移し、入口2本から消します。

- 設計: docs/handoff/doc-agenda-nav/design.md §5-2（CLAUDE.md :20-24 の行・AGENTS.md の同じ節の行。どちらも「docs/ops/runner-commands.md に節を足して移す（1か所に）」）・§8（段3b の行「1PR に移動先1つ」）・§7（移動時に文が欠けるリスク）
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076
- 状態: 設計は審査済み（PR #4649）。PO の実装承認: 2026-10-23「1」（Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事）
- 危険便: CI の分類（scripts/check-process-artifacts.js の危険パス）には当たらない。ただし docs/ai-agents/executor-checklist.md §2 により CLAUDE.md・AGENTS.md に触る便は「危険ファイル変更 PR」として扱う。GO は ADR-1003 の委譲により Opus が PR コメントで出す（担当は GO を書かない・マージしない）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と確かめは Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、GO とマージは Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段3b-1 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れる: §3 の4ファイル。

入れない:
- 移す文の書き換え・言い回しの改善。
- 段3b の他の便（ブランチ運用・成果物の完了定義・判定木・i18n・UI ガバナンス）。
- docs/INDEX.md の変更（F 章の行「サーバーで使うコマンド｜VPS・本番のコンテナで作業するとき」が既に移動先を指しているため足さない）。
- docs/research/guardrail-investigation-ADR-040.md:51（「CLAUDE.md に『VPS コンテナの落とし穴』セクション…は存在する」）。調査した時点の観察の記録で、行き先を案内する文ではないので直さない。

Opus の設計判断（このカードで決めたこと）:
- 段3b では、移動先へ一字一句写し、入口から消すのは「入口の案文 docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md に要点が残らない行」だけにする。この節は案文に1行も無い（`grep -n -E 'コンテナ|/app|tmpfs'` が0件）ので、入口2本から消す。
- 入口に行き先の1行は足さない。入口の10行目（段3a で入れた行）から目次 docs/INDEX.md に辿れ、目次の F 章の行が移動先を「VPS・本番のコンテナで作業するとき」付きで指しているため。

## 2. 前提の事実（Opus が 2026-10-23 に origin/main 3b8124562 で確かめた）

| # | 事実 | 出典 |
|---|---|---|
| F1 | CLAUDE.md は120行。:18 `---`、:19 空行、:20 `## VPS コンテナの落とし穴`、:21 空行、:22-24 本文3行、:25 空行、:26 `## VPS 直作業禁止（技術的にも制限付き鍵のみ）` | /tmp/CC報告ファイル/an-stage3b/recon/01-claude.txt |
| F2 | AGENTS.md は121行。:63 i18n の文、:64 空行、:65 `---`、:66 空行、:67 `## VPS コンテナの落とし穴`、:68 空行、:69-71 本文3行、:72 空行、:73 `---` | 02-agents.txt |
| F3 | CLAUDE.md :20-24 と AGENTS.md :67-71 は見出しも本文3行も一字一句同じ | 01-claude.txt・02-agents.txt |
| F4 | docs/ops/runner-commands.md は373行。`/app`・`tmpfs`・`exec -T` は0件。:364-365 が §10 の最後の文、:366 空行、:367 `---`、:368 空行、:369 `## 関連 doc` | 03-runner.txt |
| F5 | 名前でこの節を指すのは入口2本の見出しと、docs/research/guardrail-investigation-ADR-040.md:51 の過去の観察だけ（docs/handoff を除く） | `git grep -n -E 'コンテナの落とし穴' origin/main -- ':!docs/handoff'` |
| F6 | 目次 docs/INDEX.md :22 は `| F 運用・本番 | [サーバーで使うコマンド](ops/runner-commands.md) | VPS・本番のコンテナで作業するとき |` | 07-index.txt |
| F7 | 行数の検査（frontend/scripts/check-claude-size.js の LIMITS）は CLAUDE.md 120。この便で CLAUDE.md は114行に減る | 13-size |

## 3. 触るファイル（これ以外は触らない）

- 変更: `docs/ops/runner-commands.md`
- 変更: `CLAUDE.md`
- 変更: `AGENTS.md`
- 変更: `docs/handoff/doc-agenda-nav/card-stage3b-runner.md`（このカード。担当は §11 報告欄の追記だけ）

## 4. 作り方

行番号はすべて作業場所の起点（`B=$(git merge-base origin/main HEAD)`）のもの。中身は `git show "${B}:CLAUDE.md" | sed -n 20,24p` のように起点から取り出して写す。写すときは1文字も変えない（全角・半角・行末の空白・記号もそのまま）。zsh では `"$B:CLAUDE.md"` の `:C` が修飾子に読まれるので、必ず `"${B}:CLAUDE.md"` と書く。

### 4-1. docs/ops/runner-commands.md の :366（空行）の次に10行を足す（Edit）

| 足した後の行 | 中身 |
|---|---|
| 367 | `---` |
| 368 | 空行 |
| 369 | CLAUDE.md:20（`## VPS コンテナの落とし穴`） |
| 370 | 空行 |
| 371 | `入口（CLAUDE.md・AGENTS.md）の同じ名前の節から、文を変えずに移しました（2026-10-23・ADR-1040 段3b）。` |
| 372 | 空行 |
| 373-375 | CLAUDE.md:22-24（本文3行） |
| 376 | 空行 |

元の :367 `---` 以降（`## 関連 doc` の節）は 377 行目から続く。結果は383行。

### 4-2. CLAUDE.md から :20-25 を消す（Edit）

消す6行: `## VPS コンテナの落とし穴`／空行／本文3行／空行。消した後は :18 `---`、:19 空行、:20 `## VPS 直作業禁止（技術的にも制限付き鍵のみ）`。結果は114行。

### 4-3. AGENTS.md から :65-72 を消す（Edit）

消す8行: `---`／空行／`## VPS コンテナの落とし穴`／空行／本文3行／空行。消した後は :63 i18n の文、:64 空行、:65 `---`（起点の :73）。結果は113行。

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage3b/impl1/ に保存）

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-runner && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-1. 写しが一字一句同じか（4本の diff がすべて出力なし）:

```
diff <(git show "${B}:CLAUDE.md" | sed -n 20p)    <(sed -n 369p docs/ops/runner-commands.md)
diff <(git show "${B}:CLAUDE.md" | sed -n 22,24p) <(sed -n 373,375p docs/ops/runner-commands.md)
diff <(git show "${B}:AGENTS.md" | sed -n 67p)    <(sed -n 369p docs/ops/runner-commands.md)
diff <(git show "${B}:AGENTS.md" | sed -n 69,71p) <(sed -n 373,375p docs/ops/runner-commands.md)
```

5-2. 移した行が移動先に在るかを1行ずつ数える（K11 の合格ライン 100%）:

```
k11() { git show "${B}:$1" | sed -n "$2p" | while IFS= read -r l; do [ -z "$l" ] && continue; if grep -Fxq -- "$l" "$3"; then echo "OK"; else echo "MISSING $1:$2 :: $l"; fi; done; }
{ k11 CLAUDE.md 20,24 docs/ops/runner-commands.md; k11 AGENTS.md 67,71 docs/ops/runner-commands.md; } > /tmp/CC報告ファイル/an-stage3b/impl1/k11.txt
grep -c '^OK' /tmp/CC報告ファイル/an-stage3b/impl1/k11.txt; grep -c '^MISSING' /tmp/CC報告ファイル/an-stage3b/impl1/k11.txt
```
期待: OK 8・MISSING 0（grep -c は 0 を出して exit 1 になるが、それで正しい）。

5-3. 入口から消した中身が想定どおりか（どちらも出力なし）:

```
diff <(git show "${B}:CLAUDE.md" | sed 20,25d) CLAUDE.md
diff <(git show "${B}:AGENTS.md" | sed 65,72d) AGENTS.md
```
あわせて `wc -l CLAUDE.md AGENTS.md docs/ops/runner-commands.md` が 114・113・383。

5-4. 移動先の差分: `diff <(git show "${B}:docs/ops/runner-commands.md") docs/ops/runner-commands.md` が「366a367,376」と §4-1 の10行だけ。

5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、SUMMARY 行を起点の値（PR #4700 のマージ時 = 起点 3b8124562 の値 `unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待: どの数も増えない。

5-6. 名前での参照: `git grep -n -E 'コンテナの落とし穴' -- . ':!docs/handoff/'` の全文を保存。期待: docs/ops/runner-commands.md:369 と docs/research/guardrail-investigation-ADR-040.md:51 の2件だけ。

5-7. `git status --short` と `git diff "$B" --stat`（期待: §3 のファイルだけ）。

5-8. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けたものを1回だけ実行して貼る（待たない）。

## 6. 分岐ごとの対処

- 5-1・5-3・5-4 で差が出る → 写しか消す範囲の誤り。直して 5-1 からやり直す（2回直しても合わなければ BLOCKED:）。
- 5-2 で MISSING が出る → 一覧を貼って BLOCKED:。
- 5-5 で数が増える → 一覧を貼って NEEDS_DECISION:。
- 5-6 で §5-6 の2件以外が出る → 一覧を貼って NEEDS_DECISION:（担当は直さない）。
- 起点の行の中身が §2 の F1・F2・F4 と違う（土台が進んでいた）→ 何も変えずに NEEDS_DECISION:（行番号を Opus が出し直す）。
- `scripts/dev/validate-pr-body.sh` に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行（3回で通らなければ BLOCKED:）。
- 見張りや自動判定に止められた → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 移した文が移動先に一字一句同じ並びで在る | §5-1 の4本の diff がすべて出力なし |
| K11: 入口から外した決まりが移動先に 100% ある | §5-2 の OK 8・MISSING 0 |
| 入口2本から消えたのはこの節だけ | §5-3 |
| 移動先に足したのは §4-1 の10行だけ | §5-4 |
| 目次から届かない文書・行き先の無いリンクが増えない | §5-5 |
| この節を名前で指す生きた参照が古い場所に残らない | §5-6 |
| 触ったのは §3 のファイルだけ | §5-7 |

## 8. 戻し方

この PR の revert を main にマージする（入口2本に節が戻り、移動先の10行が消える）。

## 9. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-runner は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage3b-runner`（origin/main 3b8124562 起点）で作成済みで、このカードのコミットも載っている。担当は作り直さない。
- push は `git push -u origin release/doc-agenda-nav-stage3b-runner`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage3b-runner -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage3b/pr-body-1.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る。base は main。担当はマージしない。GO 記録は書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` に `recon: docs/handoff/doc-agenda-nav/recon.md`、`設計: docs/handoff/doc-agenda-nav/design.md`、`対象ADR: ADR-1040（関連: ADR-076）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`触るファイル: AGENTS.md, CLAUDE.md, docs/ops/runner-commands.md, docs/handoff/doc-agenda-nav/card-stage3b-runner.md`、`削除するファイル: AGENTS.md, CLAUDE.md`、`区分: A（ADR-1015。正本文書を触るため B 区分に当たらない。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`、`PO承認: 「1」（2026-10-23）`、`Opus 審査記録: コード審査はこれから` を書く。§5-2 の OK と MISSING の数、§5-5 の SUMMARY 行を本文に貼る。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了報告に: 冒頭の受領文／§5-1〜5-8 の出力（長いものはファイルのパス）／PR の URL／新しい HEAD の sha／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 委任の定型: sleep しない／ファイルの作成と編集は Write/Edit ツールで行う／PR 作成前に validate-pr-body.sh で exit 0／フックや自動判定に止められたら言い換えて再試行しない

## 11. 報告欄（担当が追記）

END OF CARD
