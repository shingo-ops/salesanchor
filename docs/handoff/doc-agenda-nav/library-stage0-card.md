# 実装カード: 段0 点検スクリプト `doc-library-check.sh`（図書館化）

作成: 2026-11-02 Opus（設計担当）。根拠: [library-design.md](./library-design.md) §4-1・§4-2・§5・§9 段0（3回目の審査 [library-review-3.md](./library-review-3.md) で APPROVE）。
PO 承認: 設計 2026-11-02 PO 原文「1」（設計を承認し段0 から）。この実装 2026-11-02 PO 原文「1」（直前の選択肢「毎週の点検の仕組みを新しく作ってよい」への返事）。
実装役: クラウドの Sonnet。ブランチ `release/doc-library-design`（origin から fetch して checkout）。PR は作らない。push まで。

## 1. 作るもの・触るもの（これ以外は触らない）

| ファイル | 種類 |
|---|---|
| `scripts/dev/doc-library-check.sh` | 新規（読むだけのスクリプト） |
| `scripts/dev/test_doc_library_check.sh` | 新規（試験。一時ディレクトリだけを使う） |
| `scripts/dev/doc-entry-weekly-check.sh` | 変更（K9 の節の後に呼び出しと NG の判定を足すだけ。K1 の節は変えない） |
| `scripts/dev/test_doc_entry_weekly_check.sh` | 変更（足した行の試験を足す。今の試験は全部通ったまま） |

触らない: `docs/` の全部（台帳 `library-ledger.md` は Opus が別に作る）、他の scripts、`.github/`、フック、settings、`~/.claude`・`~/kb`（クラウドには無い）。

## 2. `doc-library-check.sh` の出力（1項目1行。この順）

```
K1_DEF=<数>
K1_DEF_FILES=<カンマ区切り。~ 表記>
L2_CHANNEL=<数|unreadable>
L2_DUP_LEDGER=<数|unreadable>
L2_DUP_ID=<数>
L2_DUP_LINE=<数>
L2=<4つの和|unreadable>
L2_UNTAGGED=<数|unreadable>
L3_INDEX=<数>
L3_BOOKS=<数>
L3_LEDGER=<数|unreadable>
L3_MATCH=yes | L3_MATCH=no <欠けた R-nn をカンマ区切り>
BOOKS_IMPORTED=<数>
```

- 差し替えの口: `DOC_ENTRY_HOME`（既定 `$HOME`）・`DOC_ENTRY_REPO`（既定 スクリプトの2つ上）・`DOC_LIBRARY_LEDGER`（既定 `$REPO/docs/handoff/doc-agenda-nav/library-ledger.md`）・`DOC_LIBRARY_HOOK`（既定 `$HOME_DIR/kb/scripts/hooks/plain-lang/hook.py`）。
- 終了コードは常に 0（判定は weekly-check がする）。合格線はスクリプトの先頭に変数で置く（L2=0・L2_UNTAGGED=0・L3_MATCH=yes・BOOKS_IMPORTED=0）。
- 実装は bash ＋ `python3 -I -c` で可（weekly-check と同じ流儀）。外部パッケージを足さない。

### 2-1. `K1_DEF`（設計 §4-2 の走査の決まり (i)〜(iii)）
- 始まり: `$HOME_DIR/.claude/CLAUDE.md` と `$REPO/CLAUDE.md`。直接足す: `$HOME_DIR/.claude/rules/**/*.md` のうち frontmatter に `paths:` が無いもの（weekly-check の `has_paths` と同じ判定）と `$REPO/AGENTS.md`。
- 各ファイルの `@` を拾う: 行頭か空白の直後の `@`、後ろは最初の空白まで。後ろが `~/`・`/`・`./` で始まるか、`/` か `.md` を含むものだけを取り込みとみなす。バッククォート（`` ` ``）の中と ``` の囲みの中は拾わない。`~/` は `$HOME_DIR` に展開。相対パスは書いたファイルのフォルダからの相対。取り込まれたファイルの中の `@` も同じ決まりで4段まで追う。直接足すファイルの中の `@` も同じ決まりで追う。
- 1つのファイルは実際のパス（`realpath`）で一度だけ数える。行数は `wc -l`。存在しない取り込み先は数えず、`K1_DEF_MISSING=<カンマ区切り>` の行を `K1_DEF_FILES` の次に出す（無ければ `none`）。
- 手元の実物での期待値: 225（Opus が段0 で確かめる。クラウドでは試験の偽の家で確かめる）。

### 2-2. `L2_CHANNEL`
- `DOC_LIBRARY_HOOK` から2行だけ読む: `CHAT_FORMAT = ` で始まる行（中の `"~/..."` の文字列を1つ取り、`~/` を `$HOME_DIR` に展開）と `SECTION = ` で始まる行（`"..."` の中を取る）。どちらかが無い・2つ以上ある・hook.py が無い → `L2_CHANNEL=unreadable`。
- 2-1 の走査で取り込まれたファイル（直接足すファイルは含めない）のうち、`realpath` が CHAT_FORMAT と同じで、中に SECTION と完全一致する行があるものの数。

### 2-3. 台帳を使う3項目（`L2_DUP_LEDGER`・`L2_UNTAGGED`・`L3_LEDGER`）
- 台帳は markdown の表。`| R-nn | 節の名前 | 所在 | 種別 | 移した段 |`。所在は `ファイル:見出し:行番号` を `<br>` か `; ` で区切って複数書ける。ファイルは `~/` 表記またはリポジトリからの相対。種別は `目録`・`本`・`表示`・`paths`。
- 台帳が無い → 3項目とも `unreadable`（`L2` も `unreadable`）。
- `L2_DUP_LEDGER` ＝ 所在が2つ以上ある `R-nn` の数。
- `L2_UNTAGGED` ＝ 対象ファイル（2-1 で数えたファイル全部＋`~/.claude/books/*.md`＋CHAT_FORMAT＋`~/.claude/rules/` の paths 付き .md）の `## `・`### ` の見出しのうち、台帳の所在に「同じファイル:同じ見出し文字列」が無いものの数。行番号は照らさない。本の見出しの末尾の ` [R-nn]` は外して照らす。
- `L3_LEDGER` ＝ 台帳で種別が `本` の `R-nn` の数。

### 2-4. `L2_DUP_ID`・`L2_DUP_LINE`
- `L2_DUP_ID` ＝ `~/.claude/books/*.md` の見出し末尾の `[R-nn]` が2冊以上に出た番号の数。
- `L2_DUP_LINE` ＝ 対象ファイル（2-3 と同じ）の本文行を正規化（先頭の `-`・`*`・数字と `.`・空白を除く。全角空白を半角に。末尾の `。` を除く）し、20文字以上で2ファイル以上に同一の行の数。数えない行: `- 本:` で始まる行・frontmatter・見出し行・2-1 で取り込みとみなした `@` を含む行・``` の囲みの中。

### 2-5. `L3_*`（設計 §5）
- A ＝ `~/.claude/CLAUDE.md` の行で正規表現 `^- 本:([a-z0-9-]+)#(R-[0-9]{2,3}) .+ → (\S+)$` に合うもの。B ＝ `~/.claude/books/*.md` の見出し末尾 `[R-nn]`。
- `L3_MATCH=yes` の条件: A の番号の集合＝B の集合かつ |A|＝|B|／A の各パスが存在し frontmatter の `book:` が id と一致／A の各番号がそのパスの本にある／台帳が読めるときは台帳の種別 `本` の集合＝B。欠けた番号を `no` の後ろに出す。本が無く A も空なら `yes`。

### 2-6. `BOOKS_IMPORTED`
- 2-1 の始まりと直接足すファイルの中で、2-1 の決まりで取り込みとみなした `@` のうち `books/` を含むものの数。

## 3. `doc-entry-weekly-check.sh` に足すこと
- K9 の節の後で `bash "$SELF_DIR/doc-library-check.sh"` を同じ環境変数のまま呼び、出力をそのまま出す。
- NG を足す: `L2` が 0 でない（`unreadable` も）→ `add_ng "L2=<値>"`／`L2_UNTAGGED` が 0 でない → `add_ng "L2_UNTAGGED=<値>"`／`L3_MATCH` が yes でない → `add_ng "L3_MATCH=no"`／`BOOKS_IMPORTED` が 0 でない → `add_ng "BOOKS_IMPORTED=<値>"`。`K1_DEF` では NG にしない。
- `BOOKS_IN_CONTEXT=`: K9 を測ったときは `/context` の出力の Memory files の表で `/.claude/books/` を含む行の数（0 でなければ NG）。`K9=skipped` なら `BOOKS_IN_CONTEXT=skipped`（NG にしない）。`K9=unreadable` なら `BOOKS_IN_CONTEXT=unreadable`。
- 既存の出力の行・順・`RESULT=` の書式は変えない。新しい行は `RESULT=` の前に出す。

## 4. 試験（`test_doc_library_check.sh`。一時ディレクトリに偽の家・偽のリポジトリ・偽の hook.py・偽の台帳を作る。本物には触れない）
最低でも次の場合を1つずつ PASS/FAIL で出し、最後に `PASS n/n`。1つでも FAIL なら終了コード 1。
1. 字下げした `@~/kb/x.md` を数える（K1_DEF に入る）
2. 行の途中の `@~/kb/y.md` を数える
3. バッククォートの中・``` の囲みの中の `@` は数えない
4. 入れ子（取り込んだファイルの中の `@`）を数える。5段目は数えない
5. リポジトリ CLAUDE.md の `@AGENTS.md` と直接足す AGENTS.md が二重にならない
6. 同じファイルを2回 `@` しても1回
7. `` `hitoshi@host` `` と ` x@example` は数えず `K1_DEF_MISSING=none`
8. 取り込み先＝hook の CHAT_FORMAT で SECTION の行あり → `L2_CHANNEL=1`。取り込み先を別ファイルに → 0
9. 偽の hook.py に `CHAT_FORMAT = ` の行が2つ → `L2_CHANNEL=unreadable`
10. 台帳の1つの番号に所在2つ → `L2_DUP_LEDGER=1`
11. 台帳に無い見出し1つ → `L2_UNTAGGED=1`
12. 台帳が無い → `L2=unreadable`
13. 同じ `[R-01]` が2冊 → `L2_DUP_ID=1`
14. 同じ20文字以上の行が2ファイル → `L2_DUP_LINE=1`。`- 本:` の行だけ同じ → 0
15. 目録の番号と本の番号が食い違う → `L3_MATCH=no R-..`。合う → yes
16. 目録に囲みの外の `@~/.claude/books/x.md` → `BOOKS_IMPORTED=1`。囲みの中 → 0
weekly-check の試験に足す: `DOC_ENTRY_SKIP_K9=1` で `BOOKS_IN_CONTEXT=skipped` が出て、それだけでは NG にならない／L2 が 0 でない偽の家で `RESULT=NG` に `L2=` が入る。

## 5. 確かめてから push（実装役が流し、生の出力を報告に貼る）
- `bash scripts/dev/test_doc_library_check.sh` → `PASS n/n`
- `bash scripts/dev/test_doc_entry_weekly_check.sh` → 全部 PASS（今の試験も）
- `bash -n` を2本の新規・変更のスクリプトに。`shellcheck` があれば流す（無ければ無いと書く）
- `git diff --stat origin/release/doc-library-design` が §1 の4ファイルだけ
- commit `feat: add doc-library-check for entry-doc library (stage 0)`、同じブランチへ push。PR は作らない

## 6. 止まる条件（推測で進めない）
- 設計 §4・§5 とこのカードが食い違う、試験の期待値が設計から決められない、§1 以外のファイルを触る必要が出た → 触らずに `NEEDS_DECISION:` と理由を最後の行に書いて止まる。
- 最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 理由`。
