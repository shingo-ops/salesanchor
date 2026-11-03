# 実装カード: 段2a K1 の数え方を定義どおりに直す（図書館化）

作成: 2026-11-03 Opus（設計担当）。根拠: [library-design.md](./library-design.md) §4-2・§9 段2a・§11 P4（3回目の審査 [library-review-3.md](./library-review-3.md) で APPROVE）。
PO 承認: 2026-11-03 PO 原文「1」（直前の選択肢「この一覧のとおり（１）から順に進める」への返事。（１）＝決まりの行数の数え方を正しく直す。直した直後だけ 204行と出て不合格になると先に示した）。
実装役: クラウドの Sonnet。ブランチ `release/doc-library-stage2a`（origin から fetch して checkout）。PR は作らない。push まで。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 図書館化 段2a の実行結果である」と書くこと。

## 読んだ節（カードの注意書きとの照合）

- docs/handoff/design-partner-card-ops/guards/00-common.md: 埋めずに残した値は無い（パスと期待値は全部実名で書いた）・報告に無い出力を成功と扱わない（§4 で git log を確かめる）。○
- docs/handoff/design-partner-card-ops/guards/03-file.md: 触るファイルを §1 で全部挙げた。入れる形は §2-2 に全文で書いた。○
- docs/handoff/design-partner-card-ops/guards/04-worktree.md: ブランチは Opus が公式の手順で作り済み。追加の push も `git push -u origin HEAD`。○
- docs/handoff/design-partner-card-ops/guards/10-executor.md: 散文で組み立てを頼まない（§2・§3 で形と期待値を全部書いた）。○

## 1. 触るもの（これ以外は触らない）

| ファイル | 種類 |
|---|---|
| `scripts/dev/doc-entry-weekly-check.sh` | 変更（K1 の節を置き換え、図書館の点検の呼び出しを K1 の節へ移す） |
| `scripts/dev/test_doc_entry_weekly_check.sh` | 変更（T18〜T24 を足す。今の T1〜T17 は1字も変えずに全部通ったまま） |

触らない: `scripts/dev/doc-library-check.sh`（走査はここ1か所。変えない）・`scripts/dev/test_doc_library_check.sh`・`docs/` の全部・他の scripts・`.github/`・フック・settings。

## 2. `doc-entry-weekly-check.sh` の変更

### 2-1. 消すもの
今の 28行目 `# ---- K1 ----` から 81行目 `[ "$K1_TOTAL" -gt "$K1_LIMIT" ] && add_ng "K1>$K1_LIMIT"` まで（`disp`・`count_file`・`has_paths`・`CLAUDE_MD` の行頭 `@` の読み取り・`rules` の find・リポジトリの2ファイル・`join_by`・K1 の出力と判定）。これらの関数を他で使っていないことを `grep -n` で確かめる（使っていれば止まる。§6）。

### 2-2. 同じ場所に入れるもの（この形のまま）

```bash
# ---- K1（数え方は doc-library-check.sh の K1_DEF の走査1か所だけ。library-design §4-2・段2a） ----
LIB_OUT="$(DOC_ENTRY_HOME="$HOME_DIR" DOC_ENTRY_REPO="$REPO" bash "$SELF_DIR/doc-library-check.sh")"
lib_val() { printf '%s\n' "$LIB_OUT" | sed -n "s/^$1=//p" | head -n 1; }
K1_TOTAL="$(lib_val K1_DEF)"
case "$K1_TOTAL" in ''|*[!0-9]*) K1_TOTAL=unreadable ;; esac
K1_FILES_V="$(lib_val K1_DEF_FILES)"
K1_MISS_V="$(lib_val K1_DEF_MISSING)"
[ -z "$K1_MISS_V" ] && K1_MISS_V=unreadable
echo "K1=$K1_TOTAL"
echo "K1_FILES=$K1_FILES_V"
echo "K1_MISSING=$K1_MISS_V"
[ "$K1_MISS_V" != none ] && add_ng "K1_MISSING=$K1_MISS_V"
if [ "$K1_TOTAL" = unreadable ]; then add_ng "K1=unreadable"
elif [ "$K1_TOTAL" -gt "$K1_LIMIT" ]; then add_ng "K1>$K1_LIMIT"; fi
```

### 2-3. 図書館の点検の節（今の 132〜147行目）
- 今の 137行目 `LIB_OUT="$(...)"` と 139行目 `lib_val() {...}` の2行を消す（2-2 へ移したので2回呼ばない）。
- 138行目 `printf '%s\n' "$LIB_OUT"` と 140〜147行目は残す（出力の順は今と同じ: K1 の3行 → K2 → K9 → 図書館の点検の行 → BOOKS_IN_CONTEXT → …）。

### 2-4. 変えないこと
`K1_LIMIT=200`・他の項目・出力の書式・`RESULT=` の書式・終了コード。

## 3. 試験（`test_doc_entry_weekly_check.sh` の T17 の後、`echo "PASS $PASS / FAIL $FAIL"` の前に足す）
今の `setup` の偽の家では K1＝24（~/.claude/CLAUDE.md 10行・~/kb/AGENTS.md 5行・rules/common/a.md 3行・リポジトリの CLAUDE.md 2行・AGENTS.md 4行。b.md は paths 付きで数えない）。各場合は `setup` の後に1つだけ手を加えて `run`。

| 番号 | 手を加えること | 確かめること |
|---|---|---|
| T18 字下げ | `~/.claude/CLAUDE.md` の末尾に `  @~/kb/x.md`（空白2つで字下げ）。`~/kb/x.md` を3行で作る | `K1=28`・`K1_FILES=` の行に `~/kb/x.md` が入る |
| T19 行の途中 | `~/.claude/CLAUDE.md` の末尾に `見る @~/kb/y.md を読む`。`~/kb/y.md` を2行で作る | `K1=27` |
| T20 囲みの中 | `~/.claude/CLAUDE.md` の末尾に3行 ```` ``` ````・`@~/kb/z.md`・```` ``` ```` と1行 `` `@~/kb/w.md` ``。`~/kb/z.md`・`~/kb/w.md` を5行ずつ作る | `K1=28`（足した4行だけ増える）・出力に `z.md` と `w.md` が無い・`K1_MISSING=none` |
| T21 入れ子 | `~/kb/AGENTS.md` の末尾に `@./n1.md`。`~/kb/n1.md` を2行で作る | `K1=27`・`K1_FILES=` の行に `~/kb/n1.md` が入る |
| T22 リポジトリの CLAUDE.md の `@AGENTS.md` | リポジトリの `CLAUDE.md` の末尾に `@AGENTS.md` | `K1=25`・`K1_FILES=` の行で `repo/AGENTS.md` がちょうど1回 |
| T23 同じファイルを2回 | `~/.claude/CLAUDE.md` の末尾にもう1行 `@~/kb/AGENTS.md` | `K1=25`・`K1_FILES=` の行で `~/kb/AGENTS.md` がちょうど1回 |
| T24 ファイルでない `@` | `~/.claude/CLAUDE.md` の末尾に `連絡 x@example と ` + `` `hitoshi@host` `` | `K1=25`・`K1_MISSING=none`・`RESULT=OK` |

「ちょうど1回」は、T22 なら `printf '%s\n' "$OUT" | grep '^K1_FILES=' | grep -o -- 'repo/AGENTS.md' | wc -l | tr -d ' '` が `1`（T23 は `'~/kb/AGENTS.md'` に替える）。

## 4. 確かめてから push（実装役が流し、生の出力を報告に貼る）
- `bash scripts/dev/test_doc_entry_weekly_check.sh` → `FAIL 0`（今の T1〜T17 の45件と足した分の全部）
- `bash scripts/dev/test_doc_library_check.sh` → 全部 PASS（変えていないことの確かめ）
- `bash -n scripts/dev/doc-entry-weekly-check.sh`。`shellcheck` があれば流す（無ければ無いと書く）
- `grep -nE 'count_file|has_paths|join_by|K1_LIST|K1_MISS=|K1_MISS\+' scripts/dev/doc-entry-weekly-check.sh` → 0件
- `grep -c 'doc-library-check.sh' scripts/dev/doc-entry-weekly-check.sh` → 呼び出しは1か所（コメントの行は数に入れてよい。`bash "$SELF_DIR/doc-library-check.sh"` の行が1つ）
- `git diff --stat origin/main` が §1 の2ファイルとこのカードだけ
- commit 文は Write で `/tmp/commit-stage2a.txt` に書いて `git commit -F /tmp/commit-stage2a.txt`。文: `fix: count K1 with doc-library-check scan (stage 2a)`。commit の後に `git log --oneline -1` で載ったことを確かめる。同じブランチへ `git push -u origin HEAD`。PR は作らない

## 5. 手元で Opus が確かめること（クラウドでは `~/.claude` が無いので測れない）
- `DOC_ENTRY_SKIP_K9=1 bash scripts/dev/doc-entry-weekly-check.sh` で `K1=204`（`K1_DEF=204` と同じ値）・`K1_FILES=` に `~/kb/00-rules/chat-layout.md` が入り、リポジトリの AGENTS.md は1回だけ・`RESULT=NG` に `K1>200` が入る（P4 で示した値）。

## 6. 停止する条件（推測で進めない。停止したら報告の最後の行で知らせる）
- 設計 §4-2・§9 段2a とこのカードが食い違う、消す関数を K1 の節の外で使っている、試験の期待値がこのカードと違う値になる、§1 以外のファイルを触る必要が出た → 触らずに `NEEDS_DECISION:` と理由を最後の行に書いて止まる。
- 最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 理由`。

END OF CARD
