# 実装カード 段3a — Codex の運用と開発コマンドを入口から2本の文書へ移す（文は変えない）

> この文書は何か：doc-agenda-nav 段3a の作業指示書です。入口（AGENTS.md・CLAUDE.md）にある「Codex の役割分担・AEON・UI/UX補助・引き継ぎ」と「venv・セットアップ・実行コマンド」を、新しく作る docs/ai-agents/codex-operations.md と docs/ai-agents/dev-commands.md へ、一字も変えずに移します。入口には目次への1行だけを残し、目次 docs/INDEX.md の章A に2行を足します。

- 設計: docs/handoff/doc-agenda-nav/design.md §5-2（:137-152 AGENTS.md の行き先の表・:110 CLAUDE.md:10 の行）・§8（:190 段3a の行）・§7（:166 移動時に文が欠けるリスク）
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076
- 状態: 設計は審査済み（PR #4649）。PO の実装承認: 2026-10-23「1」（Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事）
- 危険便: CI の分類（scripts/check-process-artifacts.js:115-128 の危険パス）には当たらない。ただし docs/ai-agents/executor-checklist.md §2 により CLAUDE.md・AGENTS.md に触る便は「危険ファイル変更 PR」として扱う。GO は ADR-1003 の委譲により Opus が PR コメントで出す（担当は GO を書かない・マージしない）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と確かめは Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、GO とマージは Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段3a の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5 の B） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れる: §3 の5ファイルと、このカードの報告欄。

入れない:
- 移す文の書き換え・言い回しの改善・古い記述（例: CLAUDE.md:10 の「Hikky-dev」）の訂正。移すだけ（設計 :190「新設2本・移動のみ」）。
- AGENTS.md :40-42（ADR-082 の廃止注記）の削除、:44-50・:97-99・:130-146（:133 を除く）・:150-169・:198-218・:259-281 の扱い。これらは段3b・3c。
- 移した後に AGENTS.md の「### Generator Executor 切り替え（ADR-082）」が「---」の直後に来る見出しの並びは直さない（段3c で入口ごと入れ替える）。

## 2. 前提の事実（Opus が 2026-10-23 に origin/main 3bed6a5f2 で確かめた）

| # | 事実 | 出典 |
|---|---|---|
| F1 | AGENTS.md は281行、CLAUDE.md は120行。どちらも 5e1193a39 以降変わっていない | /tmp/CC報告ファイル/an-stage3a/recon/00-log.txt・01-agents.txt・02-claude.txt |
| F2 | 移す範囲の端はすべて見出しか空行の切れ目と合っている（下の §4-3 の表の「最初の行」「最後の行」） | 01-agents.txt |
| F3 | docs/ai-agents/codex-operations.md と docs/ai-agents/dev-commands.md はまだ無い | 04-exist.txt |
| F4 | `AGENTS.md#` のアンカー参照は0件。`AGENTS.md:数字` の引用30件はすべて docs/handoff の過去の記録（直さない） | 05a・05b |
| F5 | AGENTS.md の中の文字列を探す検査（scripts・.github）は無い。当たるのは check-claude-size.yml:23 のファイル名のパス指定だけ | 06 |
| F6 | 行数の検査（frontend/scripts/check-claude-size.js:22-28 の LIMITS）は CLAUDE.md 120 を持ち、AGENTS.md は未登録（AGENTS.md の行数では止まらない）。この便で CLAUDE.md は120行のまま（1行を1行に置き換える） | origin/main frontend/scripts/check-claude-size.js:22-28 |
| F7 | 目次 docs/INDEX.md の章A は :8-13、最後の章A の行は :13（教訓メモのフォルダ） | 07-index.txt |
| F8 | 目次から届くかの検査 docs/handoff/doc-agenda-nav/check_doc_index.py は PR #4698 で main に入った後にこの作業場所を作る（作業場所の起点に台本がある） | PR #4698 |

## 3. 触るファイル（これ以外は触らない）

- 新設: `docs/ai-agents/codex-operations.md`
- 新設: `docs/ai-agents/dev-commands.md`
- 変更: `AGENTS.md`
- 変更: `CLAUDE.md`
- 変更: `docs/INDEX.md`
- 変更: `docs/PARALLEL_TERMINAL_GUIDE.md`（改訂1で追加。§4-7 の1行だけ）
- 変更: `tasks/todo.md`（改訂1で追加。§4-7 の1行だけ）
- 変更: `docs/handoff/doc-agenda-nav/card-stage3a.md`（このカード。担当は §11 報告欄の追記だけ）

## 4. 作り方

以下、行番号はすべて作業場所の起点（`B=$(git merge-base origin/main HEAD)`）の AGENTS.md・CLAUDE.md の行番号。中身は `git show "$B:AGENTS.md" | sed -n 14,38p` のように起点から取り出して写す（作業ツリーのファイルを先に消してから写さない）。写すときは行の中身を1文字も変えない（全角・半角・行末の空白・コードブロックの記号もそのまま）。

### 4-1. 新設 docs/ai-agents/codex-operations.md（Write で作る。全140行）

| 新しいファイルの行 | 中身 |
|---|---|
| 1 | `# Codex の運用（役割分担・AEON・UI/UX補助・引き継ぎ）` |
| 2 | 空行 |
| 3 | `> この文書は何か：Codex（ChatGPT・Codex app / CLI）と Claude Code の役割分担、AEON の呼び出し方、Codex app の許可と禁止、会話をまたぐ引き継ぎの決まりです。2026-10-23 に入口（AGENTS.md・CLAUDE.md）から文を変えずに移しました（ADR-1040 段3a）。目次 [docs/INDEX.md](../INDEX.md) の章A から辿ります。` |
| 4 | 空行 |
| 5 | `## 役割の一覧` |
| 6 | 空行 |
| 7 | `（下の1行目は CLAUDE.md、2行目は AGENTS.md にあった文です。2つの食い違いは移した時点のままにしています。）` |
| 8 | CLAUDE.md:10 |
| 9 | AGENTS.md:10 |
| 10 | 空行 |
| 11-35 | AGENTS.md:14-38（「## 役割分担（ChatGPT / Claude Code / Codex）」から「- 「本番障害3日間・売上損失¥2,000万（Who: 某EC、When: 2022年）」→ ✅」まで25行） |
| 36 | 空行 |
| 37-76 | AGENTS.md:54-93（「## AI Agent Pipeline」から「詳細手順: `docs/ai-agents/aeon-operation.md` / ルーティング定義: `docs/ai-agents/aeon-routing.md`」まで40行） |
| 77 | 空行 |
| 78 | `## Codex のブランチ名` |
| 79 | 空行 |
| 80 | AGENTS.md:133 |
| 81 | 空行 |
| 82-103 | AGENTS.md:173-194（「## Codex app UI/UX補助運用」から「> i18n、PageLayout、CSS変数、E2E更新ルールは …（`frontend/AGENTS.md` 参照）。」まで22行） |
| 104 | 空行 |
| 105-140 | AGENTS.md:222-257（「## 引き継ぎルール（忘れ防止）」から「CI（task-state-check.yml）が PR ごとに自動実行する。」まで36行） |

ファイルの最後は改行1つで終える（141行目は作らない）。

### 4-2. 新設 docs/ai-agents/dev-commands.md（Write で作る。全32行）

| 新しいファイルの行 | 中身 |
|---|---|
| 1 | `# 開発コマンド（手元の venv・セットアップ・実行）` |
| 2 | 空行 |
| 3 | `> この文書は何か：手元の Python の venv の作り方と、frontend・backend のセットアップ・検査・試験のコマンドです。2026-10-23 に AGENTS.md から文を変えずに移しました（ADR-1040 段3a）。目次 [docs/INDEX.md](../INDEX.md) の章A から辿ります。` |
| 4 | 空行 |
| 5 | `## 手元の venv` |
| 6 | 空行 |
| 7 | AGENTS.md:46 |
| 8 | 空行 |
| 9-32 | AGENTS.md:103-126（「## セットアップ & 実行コマンド」から「> 仮想マシンが要る試験は Mac で作らず docs/ops/runner-commands.md の該当節（§10）に従う。」まで24行） |

### 4-3. AGENTS.md から消す（Edit で行う。下から順に消すと行番号がずれない）

| 消す範囲（起点の行番号） | 最初の行 | 最後の行 |
|---|---|---|
| :221-257 | 空行（:220 の `---` の次） | `CI（task-state-check.yml）が PR ごとに自動実行する。` |
| :172-196 | 空行（:171 の `---` の次） | `---`（:197 の空行の前） |
| :133 | `- Codex が自動生成するブランチ名（例: `abc123-codex/fix-inbox`）はそのまま使ってよい` | 同じ行 |
| :102-128 | 空行（:101 の `---` の次） | `---`（:129 の空行の前） |
| :53-95 | 空行（:52 の `---` の次） | `---`（:96 の空行の前） |
| :46 | `- 手元の venv は ...`（venv の決まりの1行） | 同じ行 |
| :14-39 | `## 役割分担（ChatGPT / Claude Code / Codex）` | 空行（:40 の「### Generator Executor 切り替え（ADR-082）」の前） |

消した合計は160行。

### 4-4. AGENTS.md:10 を1行で置き換える（Edit）

変更前: AGENTS.md:10（`- **Dev**: Claude Code / Sonnet (Hikky-dev) — 主Generator・…` の行）
変更後（この1行そのまま）:

```
- **役割分担・Codex の運用・開発コマンド**: [docs/ai-agents/codex-operations.md](docs/ai-agents/codex-operations.md)・[docs/ai-agents/dev-commands.md](docs/ai-agents/dev-commands.md)（目次 [docs/INDEX.md](docs/INDEX.md) の章A から辿る）
```

結果の AGENTS.md は 281 − 160 = 121行。

### 4-5. CLAUDE.md:10 を1行で置き換える（Edit）

変更前: CLAUDE.md:10（`- **Dev**: Hikky-dev（Claude Code）— 設計・実装・PR起票`）
変更後（この1行そのまま）:

```
- **役割分担**: [docs/ai-agents/codex-operations.md](docs/ai-agents/codex-operations.md)（目次 [docs/INDEX.md](docs/INDEX.md) の章A から辿る）
```

理由（Opus の判断）: 今の CLAUDE.md には目次への入口がまだ無い（段3c で入る）。行を消すだけにすると、Claude Code の入口から役割の文に辿れなくなるため、消した行の場所に行き先を1行残す。結果の CLAUDE.md は120行のまま。

### 4-6. docs/INDEX.md の :13 の次に2行を足す（Edit）

```
| A 開発の進め方 | [Codex の運用（役割分担・AEON・UI/UX補助・引き継ぎ）](ai-agents/codex-operations.md) | 役割分担を確かめるとき、Codex で作業する・Codex に作業を渡すとき、会話をまたいで作業を引き継ぐとき |
| A 開発の進め方 | [開発コマンド（venv・セットアップ・実行）](ai-agents/dev-commands.md) | 手元で venv を作るとき、frontend・backend の検査や試験を動かすとき |
```

### 4-7. 改訂1: 消した節を古い場所で指す2行を直す（Edit。各1行だけ）

経緯: PR #4700 の審査（HEAD a3bd9e98a・REQUEST_CHANGES R1）で、§5-6 の検索語（見出しの全文）に掛からない省略形の参照が2件見つかった。Opus が消した見出し16個（`git diff "$B" a3bd9e98a -- AGENTS.md CLAUDE.md | grep '^-#'`）の語で入口名つきの参照を探し直し、行き先として生きているのはこの2件だけと確かめた（docs/adr/ADR-012・ADR-039、questions/Q02、docs/handoff/format-work-parent/recon.md の当たりは過去の記録なので直さない）。生出力: /tmp/CC報告ファイル/an-stage3a/refsearch.txt

`docs/PARALLEL_TERMINAL_GUIDE.md:81`（変更前 → 変更後）

```
`tasks/todo.md` は作業完了・ブロック発生時に**手動で更新する**（ルール: `AGENTS.md §引き継ぎルール`）。
`tasks/todo.md` は作業完了・ブロック発生時に**手動で更新する**（ルール: `docs/ai-agents/codex-operations.md §引き継ぎルール（忘れ防止）`）。
```

`tasks/todo.md:3`（変更前 → 変更後）

```
タスク台帳の正本。セッション開始時に必ず読むこと（`AGENTS.md §引き継ぎルール` 参照）。
タスク台帳の正本。セッション開始時に必ず読むこと（`docs/ai-agents/codex-operations.md §引き継ぎルール（忘れ防止）` 参照）。
```

（変えるのは各行の `AGENTS.md §引き継ぎルール` を `docs/ai-agents/codex-operations.md §引き継ぎルール（忘れ防止）` に置き換える部分だけ。各ブロックの1行目が変更前、2行目が変更後。Edit の old_string には `AGENTS.md §引き継ぎルール` を含む行をファイルから読んだまま使う。行番号がずれていたら、その語を含む行が各ファイルに1行だけであることを確かめてから直す。2行以上・0行なら NEEDS_DECISION:。）

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage3a/impl/ に保存）

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3a && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-1. 写しが一字一句同じか（K11 の本体。6つの diff がすべて出力なし・exit 0）:

```
diff <(git show "$B:CLAUDE.md"  | sed -n 10p)      <(sed -n 8p      docs/ai-agents/codex-operations.md)
diff <(git show "$B:AGENTS.md"  | sed -n 10p)      <(sed -n 9p      docs/ai-agents/codex-operations.md)
diff <(git show "$B:AGENTS.md"  | sed -n 14,38p)   <(sed -n 11,35p  docs/ai-agents/codex-operations.md)
diff <(git show "$B:AGENTS.md"  | sed -n 54,93p)   <(sed -n 37,76p  docs/ai-agents/codex-operations.md)
diff <(git show "$B:AGENTS.md"  | sed -n 133p)     <(sed -n 80p     docs/ai-agents/codex-operations.md)
diff <(git show "$B:AGENTS.md"  | sed -n 173,194p) <(sed -n 82,103p docs/ai-agents/codex-operations.md)
diff <(git show "$B:AGENTS.md"  | sed -n 222,257p) <(sed -n 105,140p docs/ai-agents/codex-operations.md)
diff <(git show "$B:AGENTS.md"  | sed -n 46p)      <(sed -n 7p      docs/ai-agents/dev-commands.md)
diff <(git show "$B:AGENTS.md"  | sed -n 103,126p) <(sed -n 9,32p   docs/ai-agents/dev-commands.md)
```
（9本。どれか1本でも出力があれば、写しを直して 5-1 からやり直す。）

5-2. 移した行が移動先に在るかを1行ずつ数える（K11 の合格ライン 100%）:

```
k11() { git show "$B:$1" | sed -n "$2p" | while IFS= read -r l; do [ -z "$l" ] && continue; if grep -Fxq -- "$l" "$3"; then echo "OK"; else echo "MISSING $1:$2 :: $l"; fi; done; }
{ k11 CLAUDE.md 10 docs/ai-agents/codex-operations.md
  for r in 10 14,38 54,93 133 173,194 222,257; do k11 AGENTS.md "$r" docs/ai-agents/codex-operations.md; done
  for r in 46 103,126; do k11 AGENTS.md "$r" docs/ai-agents/dev-commands.md; done; } > /tmp/CC報告ファイル/an-stage3a/impl/k11.txt
grep -c '^OK' /tmp/CC報告ファイル/an-stage3a/impl/k11.txt; grep -c '^MISSING' /tmp/CC報告ファイル/an-stage3a/impl/k11.txt
```
期待: MISSING が 0（grep -c は 0 を出して exit 1 になるが、それで正しい）。OK の数を報告に書く。

5-3. 入口から消した中身が想定どおりか（どちらも出力なし）:

```
diff <(git show "$B:AGENTS.md" | sed -e 10d -e 14,39d -e 46d -e 53,95d -e 102,128d -e 133d -e 172,196d -e 221,257d) <(sed 10d AGENTS.md)
diff <(git show "$B:CLAUDE.md" | sed 10d) <(sed 10d CLAUDE.md)
```
あわせて `sed -n 10p AGENTS.md`・`sed -n 10p CLAUDE.md` が §4-4・§4-5 の1行と同じであること、`wc -l AGENTS.md CLAUDE.md docs/ai-agents/codex-operations.md docs/ai-agents/dev-commands.md` が 121・120・140・32 であること。

5-4. 目次: `diff <(git show "$B:docs/INDEX.md") docs/INDEX.md` が「13a14,15」と §4-6 の2行だけ。

5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、起点で同じものを実行した結果と SUMMARY を並べて書く。期待: unreached・blank_when・no_when_column・broken_link が起点より増えない。新設2本が UNREACHED・DEEP・BROKEN_LINK に出ない。

5-6. 外から見出しの名前で入口の節を指している文書が無いか: `git grep -n -F -e '役割分担（ChatGPT' -e 'AI Agent Pipeline' -e 'AEON 呼び出し' -e 'セットアップ & 実行コマンド' -e 'Codex app UI/UX補助運用' -e '引き継ぎルール（忘れ防止）' -- . ':!docs/handoff/' ':!docs/ai-agents/codex-operations.md' ':!docs/ai-agents/dev-commands.md'` の全文を保存する。当たった行のうち「AGENTS.md の〜節を見よ」のように入口の節を行き先として指すものがあれば NEEDS_DECISION:（一覧を貼る）。無ければその旨を書く。

5-6b.（改訂1）省略形の参照も含めて探し直す: `git grep -n -E 'AGENTS\.md ?(§|「|の)' -- docs tasks scripts .github ':!docs/handoff/' ':!docs/adr/'` の全文を保存し、当たった行のうち §4-3 で消した節（引き継ぎ・役割分担・AI Agent Pipeline・AEON・セットアップ・Codex app UI/UX）を指すものが 0 件であること。あわせて `git grep -n -F 'AGENTS.md §引き継ぎルール'` が 0 件、`git diff "$B" -- docs/PARALLEL_TERMINAL_GUIDE.md tasks/todo.md` が §4-7 の2行の置き換えだけであること。

5-7. `git status --short` と `git diff "$B" --stat`（期待: §3 のファイルだけ）。

5-8. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けたもの を1回だけ実行して貼る（待たない）。「Check CLAUDE.md sizes」が skipping でなく実行されているか（pending・pass のどちらでもよい）を書く。

## 6. 分岐ごとの対処

- 5-1・5-3・5-4 で差が出る → 写しか消す範囲の誤り。直して 5-1 からやり直す（2回直しても合わなければ BLOCKED:）。
- 5-2 で MISSING が出る → 5-1 が合っていれば起こらない。出たら一覧を貼って BLOCKED:。
- 5-5 で警告が増える・新設2本が出る → 一覧を貼って NEEDS_DECISION:。
- 5-6 で入口の節を指す文書がある → NEEDS_DECISION:（直すかどうかは Opus が決める。担当は直さない）。§4-7 の2件は改訂1で直すと決めたので対象外。
- 5-6b で §4-7 以外に消した節を指す行が出る → 一覧を貼って NEEDS_DECISION:（担当は直さない）。
- `### 標準ワークフロー確認` などの本文の検査（validate-pr-body.sh）に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行（3回で通らなければ BLOCKED:）。
- 見張りや自動判定に止められた → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 移した文が移動先に一字一句同じ並びで在る | §5-1 の9本の diff がすべて出力なし |
| K11: 入口から外した決まりが移動先に 100% ある | §5-2 の MISSING 0 件 |
| 入口から消えたのは設計の範囲だけで、目次への1行が残っている | §5-3 |
| 目次の章A に新設2本が「いつ読むか」付きで載る | §5-4 |
| 目次から届かない文書・行き先の無いリンクが増えない | §5-5 |
| CLAUDE.md が120行以下（行数の検査が通る） | §5-3 の wc と PR の「Check CLAUDE.md sizes」 |
| 消した節を古い場所で指す参照が残らない（改訂1） | §5-6b |
| 触ったのは §3 のファイルだけ | §5-7 |

## 8. 戻し方

この PR の revert を main にマージする（入口の文が元の場所に戻り、新設2本と目次の2行が消える）。

## 9. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3a は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage3a`（#4698 マージ後の origin/main を起点）で作成済みで、このカードのコミットも載っている。担当は作り直さない。以後はすべてそこに `cd` してから行う。
- push は `git push -u origin release/doc-agenda-nav-stage3a`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage3a -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage3a/pr-body.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る。base は main。担当はマージしない。GO 記録は書かない（Opus が PR コメントで出す）。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める（executor-checklist §2）。`### 標準ワークフロー確認` に設計: docs/handoff/doc-agenda-nav/design.md、`対象ADR: ADR-1040（関連: ADR-076）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`PO承認: 「1」（2026-10-23）`、`Opus 審査記録: コード審査はこれから` を書く。§5-2 の OK と MISSING の数、§5-5 の SUMMARY 行（起点と HEAD）を本文に貼る。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了報告に: 冒頭の受領文／§5-1〜5-8 の出力（長いものはファイルのパス）／PR の URL／新しい HEAD の sha／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 委任の定型: sleep しない／ファイルの作成と編集は Write/Edit ツールで行う／PR 作成前に validate-pr-body.sh で exit 0／フックや自動判定に止められたら言い換えて再試行しない

## 11. 報告欄（担当が追記）

- 5-1: 9本の diff すべて出力なし（impl/5-1.txt）
- 5-2: OK 117・MISSING 0（impl/k11.txt）
- 5-3: 2本の diff 出力なし・AGENTS.md 121行・CLAUDE.md 120行・codex-operations.md 140行・dev-commands.md 32行（impl/5-3.txt）
- 5-4: 13a14,15 と2行だけ（impl/5-4.txt）
- 5-5: 起点 SUMMARY unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 / HEAD（新設ファイルを git add した後）は同じ数字。add 前は新設ファイルが git ls-files に無く broken_link=13 だった（impl/5-5-*.txt）
- 5-6: 1件（aeon-routing.md:46 の一般文。入口の節を指す文ではない）（impl/5-6.txt）
- 5-7: impl/5-7.txt

END OF CARD
