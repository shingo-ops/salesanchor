# 実装カード 段3b-2 — ブランチ運用の決まりを入口2本からブランチ運用の仕様書へ写す（文は変えない）

> この文書は何か：doc-agenda-nav 段3b-2 の作業指示書です。CLAUDE.md と AGENTS.md の「ブランチ運用ルール」節の行を、docs/specs/branch-operations/README.md に新しい節「8. 日々の運用ルール」を作って一字も変えずに写します。入口の案文に要点が残らない行だけを入口から消し、要点が残る行は段3c で入口ごと入れ替えるまで入口にも残します。

- 設計: docs/handoff/doc-agenda-nav/design.md §5-2（CLAUDE.md の :50・:53-55・:58 の行、:56-57 の行、:60-66 の行。AGENTS.md の :130-146 の行）・§8（段3b の行「1PR に移動先1つ」）・§7（移動時に文が欠けるリスク）
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076・ADR-135・ADR-136・ADR-1003・ADR-1029
- 状態: 設計は審査済み（PR #4649）。PO の実装承認: 2026-10-23「1」（Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事）
- 危険便: CI の分類（scripts/check-process-artifacts.js の危険パス）には当たらない。ただし docs/ai-agents/executor-checklist.md §2 により CLAUDE.md・AGENTS.md に触る便は「危険ファイル変更 PR」として扱う。GO は ADR-1003 の委譲により Opus が PR コメントで出す（担当は GO を書かない・マージしない）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と確かめは Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、GO とマージは Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段3b-2 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れる: §3 の6ファイル。

入れない:
- 写す文の書き換え・言い回しの改善・古い記述の訂正。
- 入口の案文 docs/handoff/doc-agenda-nav/draft/AGENTS.entry.md に要点が残る行（§4-4 の表の「残す」行）の削除。段3c で入口ごと入れ替える。
- `.claude/agents/` 変更前の pull の行（CLAUDE.md 固有として段3c で案文 CLAUDE.entry.md へ）。
- scripts/check-process-artifacts.js:356 の案内文「CLAUDE.md §ブランチ運用ルール」（入口に同じ名前の節が段3c まで残る。段3c で直す）。
- 過去の記録の参照（docs/adr/ADR-136-cc-bot-github-identity.md:102、docs/research/guardrail-investigation-ADR-040.md:44・:161）と、別の古い記述を含む docs/runbooks/adr-019-english-ui-temporary-deploy.md:186（develop 前提の手順。段3c の参照洗い出しで扱う）。

Opus の設計判断（このカードで決めたこと）:
- 段3b では、移動先へ一字一句写し、入口から消すのは「入口の案文に要点が残らない行」だけにする。要点が残る行まで今消すと、段3c までの間、安全の決まりが入口から一時的に消えるため。その結果、§4-4 の「残す」行は段3c まで入口と移動先に二重にある（意図した一時的な二重）。
- AGENTS.md の2行（:37 PR 作成・:38 release→main）は CLAUDE.md の行と空白と記法だけが違う同義の文なので、移動先には CLAUDE.md 側の文を1つだけ写し、対応表（§4-2）で結ぶ。AGENTS.md の長命ブランチ節（:42-48）は CLAUDE.md の節と一字一句同じなので1つだけ写す。

## 2. 前提の事実（Opus が 2026-10-23 に確かめた。起点は段3b-1（PR #4703）のマージ後の origin/main f57a8193b。F1・F2・F5・F7 はこの起点の実物で再確認済み）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 段3b-1 の後の CLAUDE.md は114行。:38 `## ブランチ運用ルール`、:40-52 本文（:44 PR 作成・:46 release→main・:47-49 その下の3行・:50 ADR-135・:51 ADR-136・:52 リリース PR）、:53 空行、:54 `### 長命ブランチ消失防止（…）`、:55 空行、:56-60 本文5行、:61 空行 | origin/main 3b8124562 の CLAUDE.md :44-67 を6行上げた位置（段3b-1 で :20-25 の6行を消す） |
| F2 | AGENTS.md は段3b-1 の後も :1-64 が変わらない。:33 `## ブランチ運用ルール`、:35-40 本文、:42 長命ブランチの見出し、:44-48 本文 | origin/main 3b8124562 の AGENTS.md :30-50 |
| F3 | CLAUDE.md の長命ブランチ節（起点 :60-66）と AGENTS.md :42-48 は一字一句同じ | `diff` 出力なし（rc=0） |
| F4 | CLAUDE.md :50（起点）と AGENTS.md :37 の差は「でPR作成」と「で PR 作成」の空白だけ。CLAUDE.md :52（起点）と AGENTS.md :38 の差は太字・コード記法と「直 push」の空白だけ | `diff` 出力 |
| F5 | docs/specs/branch-operations/README.md は84行。:71 `## 7. 関連文書（…）`、:80 子2 の行、:81 空行、:82 `---`、:84 末尾の注記 | /tmp/CC報告ファイル/an-stage3b/recon/04-branchops.txt |
| F6 | 移動先に「squash」「break-glass」「Draft」「確認済み」「ADR-135」「ADR-136」「長命」の記述は0件（重複は生じない） | 同上 |
| F7 | 「break-glass」の行を入口の節名で指すのは docs/BRANCH_PROTECTION_SETUP.md:141、入口の節を読めと案内するのは docs/onboarding/claude-code.md:117 | `git grep -n -E 'ブランチ運用ルール' origin/main -- ':!docs/handoff'`（/tmp/CC報告ファイル/an-stage3b/refs-branch.txt） |

## 3. 触るファイル（これ以外は触らない）

- 変更: `docs/specs/branch-operations/README.md`
- 変更: `CLAUDE.md`
- 変更: `AGENTS.md`
- 変更: `docs/BRANCH_PROTECTION_SETUP.md`（§4-5 の1行だけ）
- 変更: `docs/onboarding/claude-code.md`（§4-5 の1行だけ）
- 変更: `docs/handoff/doc-agenda-nav/card-stage3b-branchops.md`（このカード。担当は §11 報告欄の追記だけ）

## 4. 作り方

行番号はすべて作業場所の起点（`B=$(git merge-base origin/main HEAD)`）のもの。中身は `git show "${B}:CLAUDE.md" | sed -n 44p` のように起点から取り出して写す。1文字も変えない。zsh では必ず `"${B}:CLAUDE.md"` と書く。

### 4-1. docs/specs/branch-operations/README.md の :81（空行）の次に23行を足す（Edit）

| 足した後の行 | 中身 |
|---|---|
| 82 | `## 8. 日々の運用ルール（入口から写した決まり）` |
| 83 | 空行 |
| 84 | `入口（CLAUDE.md・AGENTS.md）の「ブランチ運用ルール」節から、文を変えずに写しました（2026-10-23・ADR-1040 段3b）。` |
| 85 | 空行 |
| 86 | CLAUDE.md:44（PR 作成） |
| 87 | CLAUDE.md:46（release→main） |
| 88-90 | CLAUDE.md:47-49（Draft・確認済みコメント・break-glass） |
| 91 | AGENTS.md:39（マージ方法は必ず "Create a merge commit"） |
| 92 | AGENTS.md:40（reviewer(opus) の VERDICT 行・ADR-1029） |
| 93-95 | CLAUDE.md:50-52（ADR-135・ADR-136・リリース PR） |
| 96 | 空行 |
| 97 | CLAUDE.md:54（`### 長命ブランチ消失防止（…）`） |
| 98 | 空行 |
| 99-103 | CLAUDE.md:56-60 |
| 104 | 空行 |

元の :82 `---` 以降は 105 行目から続く。結果は107行。

### 4-2. 同義の行の対応表（写さない行。審査役がこの表を確かめる）

| 入口の行 | 移動先で対応する行 | 差 |
|---|---|---|
| AGENTS.md:37 | README.md:86（CLAUDE.md:44 の写し） | 「でPR作成」と「で PR 作成」の空白だけ |
| AGENTS.md:38 | README.md:87（CLAUDE.md:46 の写し） | 太字・コード記法と「直 push」の空白だけ |
| AGENTS.md:42-48 | README.md:97-103 | 差なし（一字一句同じ） |

### 4-3. 入口から消す（Edit。下から順に消すと行番号がずれない）

| ファイル | 消す行 | 中身 |
|---|---|---|
| CLAUDE.md | :52 | リリース PR 作成時 |
| CLAUDE.md | :47-49 | Draft・確認済みコメント・break-glass（:46 の下の3行） |
| CLAUDE.md | :44 | PR 作成 |
| AGENTS.md | :39-40 | マージ方法・reviewer の VERDICT 行 |
| AGENTS.md | :37 | PR 作成 |

結果は CLAUDE.md 109行・AGENTS.md 110行。

### 4-4. 入口に残す行（段3c まで二重。消さない）

| ファイル | 行 | 案文 AGENTS.entry.md の要点の行 |
|---|---|---|
| CLAUDE.md | :40-41・:43・:45-46 | :32-34 |
| CLAUDE.md | :42（.claude/agents の pull） | 案文 CLAUDE.entry.md |
| CLAUDE.md | :50-51 | :36 |
| CLAUDE.md | :54-60 | :35 |
| AGENTS.md | :35-36・:38 | :32・:34 |
| AGENTS.md | :42-48 | :35 |

### 4-5. 入口の節名で指す2行を直す（Edit。各1行だけ）

`docs/BRANCH_PROTECTION_SETUP.md:141`（1行目が変更前、2行目が変更後）

```
**このルールは CLAUDE.md ブランチ運用ルール§緊急 break-glass に同期記載。**
**このルールは docs/specs/branch-operations/README.md §8（日々の運用ルール）の緊急 break-glass に同期記載。**
```

`docs/onboarding/claude-code.md:117`（1行目が変更前、2行目が変更後）

```
詳細は `<repo>/CLAUDE.md` の「ブランチ運用ルール」を読むこと。要点:
詳細は `<repo>/docs/specs/branch-operations/README.md` の「8. 日々の運用ルール」を読むこと。要点:
```

行番号がずれていたら、変更前の文を含む行が各ファイルに1行だけであることを確かめてから直す。2行以上・0行なら NEEDS_DECISION:。

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage3b/impl2/ に保存）

すべて `cd /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-branchops && B=$(git merge-base origin/main HEAD) && ...` の形で行う。

5-0. 起点が §2 の F1・F2・F5 と合うか: `git show "${B}:CLAUDE.md" | sed -n 38,61p`・`git show "${B}:AGENTS.md" | sed -n 33,48p`・`git show "${B}:docs/specs/branch-operations/README.md" | sed -n 78,84p` を保存して照らす。違えば何も変えずに NEEDS_DECISION:。

5-1. 写しが一字一句同じか（6本の diff がすべて出力なし）:

```
F=docs/specs/branch-operations/README.md
diff <(git show "${B}:CLAUDE.md" | sed -n 44p)    <(sed -n 86p "$F")
diff <(git show "${B}:CLAUDE.md" | sed -n 46,49p) <(sed -n 87,90p "$F")
diff <(git show "${B}:AGENTS.md" | sed -n 39,40p) <(sed -n 91,92p "$F")
diff <(git show "${B}:CLAUDE.md" | sed -n 50,52p) <(sed -n 93,95p "$F")
diff <(git show "${B}:CLAUDE.md" | sed -n 54,60p) <(sed -n 97,103p "$F")
diff <(git show "${B}:AGENTS.md" | sed -n 42,48p) <(sed -n 97,103p "$F")
```

5-2. K11（入口の「ブランチ運用ルール」節の全行が移動先にあるか。4-2 の同義の2行は別に数える）:

```
k11() { git show "${B}:$1" | sed -n "$2p" | while IFS= read -r l; do [ -z "$l" ] && continue; if grep -Fxq -- "$l" "$3"; then echo "OK"; else echo "MISSING $1:$2 :: $l"; fi; done; }
{ k11 CLAUDE.md 44 "$F"; k11 CLAUDE.md 46,52 "$F"; k11 CLAUDE.md 54,60 "$F"; k11 AGENTS.md 39,40 "$F"; k11 AGENTS.md 42,48 "$F"; } > /tmp/CC報告ファイル/an-stage3b/impl2/k11.txt
grep -c '^OK' /tmp/CC報告ファイル/an-stage3b/impl2/k11.txt; grep -c '^MISSING' /tmp/CC報告ファイル/an-stage3b/impl2/k11.txt
```
期待: OK 22・MISSING 0。あわせて AGENTS.md:37・:38 と CLAUDE.md:44・:46 の `diff` を保存し、差が §4-2 の表の通りであること。

5-3. 入口から消した中身が想定どおりか（どちらも出力なし）:

```
diff <(git show "${B}:CLAUDE.md" | sed -e 44d -e 47,49d -e 52d) CLAUDE.md
diff <(git show "${B}:AGENTS.md" | sed -e 37d -e 39,40d) AGENTS.md
```
あわせて `wc -l CLAUDE.md AGENTS.md "$F"` が 109・110・107。

5-4. 移動先の差分: `diff <(git show "${B}:$F") "$F"` が §4-1 の23行の追加だけ（diff の表記の行番号が前後にずれても、足した行の中身が §4-1 と同じならよい。その場合は表記をそのまま報告に書く）。

5-5. `git diff "$B" -- docs/BRANCH_PROTECTION_SETUP.md docs/onboarding/claude-code.md` が §4-5 の2行の置き換えだけ。

5-6. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待: どの数も増えない。

5-7. 名前での参照: `git grep -n -E 'ブランチ運用ルール|break-glass' -- . ':!docs/handoff/'` の全文を保存。期待: §1 の「入れない」に挙げた行・入口2本の見出し・§4-5 で直した2行・移動先の行・docs/DEVELOPMENT_GUIDE_FOR_SHINGO.md:46（その文書自身の見出し）・BRANCH_PROTECTION_SETUP.md の §4-A の見出しと本文以外に、入口の節を行き先として指す行が無いこと。あれば一覧を貼って NEEDS_DECISION:（担当は直さない）。

5-8. `git status --short` と `git diff "$B" --stat`（期待: §3 のファイルだけ）。

5-9. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けたものを1回だけ実行して貼る（待たない）。

## 6. 分岐ごとの対処

- 5-0 で起点が合わない → 何も変えずに NEEDS_DECISION:（行番号を Opus が出し直す）。
- 5-1・5-3・5-4・5-5 で差が出る → 写しか消す範囲の誤り。直して 5-1 からやり直す（2回直しても合わなければ BLOCKED:）。
- 5-2 で MISSING が出る → 一覧を貼って BLOCKED:。
- 5-6 で数が増える → 一覧を貼って NEEDS_DECISION:。
- `scripts/dev/validate-pr-body.sh` に止められた → 止まった欄と理由の原文を報告に書き、本文を直して再実行（3回で通らなければ BLOCKED:）。
- 見張りや自動判定に止められた → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 写した文が移動先に一字一句同じ並びで在る | §5-1 の6本の diff がすべて出力なし |
| K11: 入口の節の行が移動先に 100% ある | §5-2 の OK 22・MISSING 0 と、同義2行の差が §4-2 の通り |
| 入口から消えたのは §4-3 の行だけで、§4-4 の行は残る | §5-3 |
| 移動先に足したのは §4-1 の23行だけ | §5-4 |
| 入口の節名で指していた2行が移動先を指す | §5-5 |
| 目次から届かない文書・行き先の無いリンクが増えない | §5-6 |
| 触ったのは §3 のファイルだけ | §5-8 |

## 8. 戻し方

この PR の revert を main にマージする（入口2本に消した行が戻り、移動先の23行と2行の置き換えが元に戻る）。

## 9. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage3b-branchops は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage3b-branchops`（PR #4703 マージ後の origin/main 起点）で作成済みで、このカードのコミットも載っている。担当は作り直さない。
- push は `git push -u origin release/doc-agenda-nav-stage3b-branchops`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage3b-branchops -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage3b/pr-body-2.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る。base は main。担当はマージしない。GO 記録は書かない。
- 本文は PR テンプレートに沿い、欄は平打ちで埋める。`### 標準ワークフロー確認` に `recon: docs/handoff/doc-agenda-nav/recon.md`、`設計: docs/handoff/doc-agenda-nav/design.md`、`対象ADR: ADR-1040（関連: ADR-076）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`触るファイル: AGENTS.md, CLAUDE.md, docs/specs/branch-operations/README.md, docs/BRANCH_PROTECTION_SETUP.md, docs/onboarding/claude-code.md, docs/handoff/doc-agenda-nav/card-stage3b-branchops.md`、`削除するファイル: AGENTS.md, CLAUDE.md, docs/BRANCH_PROTECTION_SETUP.md, docs/onboarding/claude-code.md`、`区分: A（ADR-1015。正本文書を触るため B 区分に当たらない。KGI と実装は PO 承認済み。GO は ADR-1003 の委任で Opus が出す）`、`PO承認: 「1」（2026-10-23）`、`Opus 審査記録: コード審査はこれから` を書く。§5-2 の OK と MISSING の数、§5-6 の SUMMARY 行を本文に貼る。§4-4 の「段3c まで入口と移動先に二重にある行」があることも本文に1行書く。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了報告に: 冒頭の受領文／§5-0〜5-9 の出力（長いものはファイルのパス）／PR の URL／新しい HEAD の sha／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 委任の定型: sleep しない／ファイルの作成と編集は Write/Edit ツールで行う／PR 作成前に validate-pr-body.sh で exit 0／フックや自動判定に止められたら言い換えて再試行しない

## 11. 報告欄（担当が追記）

END OF CARD
