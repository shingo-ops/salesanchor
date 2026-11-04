# card: 便4 点検の台本に行番号の照合・たどれる範囲・説明の決まりの数を足す（クラウドの Sonnet 向け）

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§6） |
| 4 | 目的は 1 つ | ○ 決まりの木が崩れたら週1回の点検と CI で見つかるようにする |
| 5 | 土台のブランチ | ○ このカードがあるブランチ `release/doc-library-one-tree-checks`（`origin/main` から作成済み） |
| 6 | 形は例で示す | ○ §1〜§3 に変更後の形 |
| 7 | 合格基準に出力 | ○ §5 |
| 8 | 対象の名前 | ○ 触ってよいファイル 6 つ（§1 の 2・§2 の 1・§3 の 2・§6 の報告 1） |
| 9 | 出力の上限 | ○ tail -80 |
| 10 | 受付と終わりの合図 | ○ 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-04 の実物（PR #5108 の HEAD e9a33ebdf） |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Write/Edit・見張りで止まったら言い換えない | ○ |

- 設計: [design.md](design.md) §5-1・§5-2・§5-4・§9（設計 PR #5106 マージ済み。台帳の付け直しは PR #5108）
- PO の実装承認: 2026-11-04 チャット「1」（便1〜5）
- 作業ブランチ: `release/doc-library-one-tree-checks`。このブランチにコミットして push する。main には触らない。
- 公開リポジトリ。`~/.claude`・`~/kb` の決まりの本文を台本・試験・報告に書き写さない（ファイル名・見出し・行番号・件数だけ）。試験の偽の文書は「x」「l1」のような中身のない文で作る。

## §0 着手前の点検（違えば NEEDS_DECISION で止まる）
`grep -n` の結果を報告に貼る。
| ファイル | 想定 |
|---|---|
| `scripts/dev/doc-library-check.sh` | `def parse_loc(loc):` が 1 か所。その中に `m = re.match(r"^(.*):(\d+)$", rest)` があり、数字を使わずに捨てている |
| `scripts/dev/doc-library-check.sh` | `TAG_RE = re.compile(r"\s*\[(R-\d+)\]\s*$")` が 1 か所 |
| `scripts/dev/doc-library-check.sh` | `print("L2_UNTAGGED=" + L2_UNTAGGED)` が 1 か所 |
| `scripts/dev/test_doc_library_check.sh` | `"出力の順"` の試験があり、期待の並びが `... L2 L2_UNTAGGED L3_INDEX ...` |
| `scripts/ci/check_doc_index.py` | `scope = [f for f in md if f.startswith("docs/specs/") or f.startswith("docs/ai-agents/")]` が 1 か所 |
| `scripts/dev/doc-entry-weekly-check.sh` | `LV_BI="$(lib_val BOOKS_IMPORTED)"` と、最後の `RESULT=OK` / `RESULT=NG` の分かれ |
| `docs/ai-agents/codex-operations.md` | `docs/agents/generator.md` を含む行がある（PR #5108 の変更。無ければ main に #5108 が入っていない → NEEDS_DECISION） |
| `docs/handoff/doc-agenda-nav/library-ledger.md` | `## 話題の重なり表` の見出しと、`| 話題 | 個人の本の所在 | リポジトリの所在 | 正 |` の表の頭 |

## §1 台帳の行番号の照合（L2_LINE_NG）

(1) `scripts/dev/doc-library-check.sh`
- `parse_loc` は変えない（`L2_UNTAGGED` の照合が使っている）。すぐ下に新しい関数を足す。
```python
def parse_loc_line(loc):
    """ファイル:見出し:行番号 → (実パス, 見出し, 行番号 or None)。"""
    if ":" not in loc:
        return None
    f, rest = loc.split(":", 1)
    ln = None
    m = re.match(r"^(.*):(\d+)$", rest)
    if m:
        rest, ln = m.group(1), int(m.group(2))
    p = parse_loc(loc)
    return (p[0], p[1], ln) if p else None
```
- 台帳を読むところで、各行の名前（`c[1]`）も残す: `rows.setdefault(...)` の辞書に `"name": c[1]` を足す（最初の1回の値でよい）。
- `L2_UNTAGGED` を出した直後に、次の規則で数えて `print("L2_LINE_NG=" + 値)` を出す。台帳が読めないときは `unreadable`。
  - 見出しの行: `^(#{1,3})\s+(.*)$` に合う行（`# `・`## `・`### `）。段は `#` の数。見出しの文字は、`TAG_RE` で末尾の札 `[R-nn]` を外して前後の空白を除いたもの。囲み（```）の中の行は見出しとしない。
  - 台帳の所在1つごとに照らす（`<br>` と `; ` で分けた後の1つずつ）。
  - 合格: 行番号の行が見出しの行で、その文字が台帳の見出し（`parse_loc` で `#` を外したもの）と完全一致。
  - 言い直しの例外: 台帳の名前が `言い直し` で始まる行だけ、行番号の行が「その見出しの節の中」なら合格。節は、文字が一致する見出しの行（段 k）から、段が k 以下の次の見出しの前まで。行番号の行から上へ見て最初に出会う、段が k 以下の見出しが、一致する見出しであること。
  - NG に数えるもの: 上の合格に当たらない所在。行番号が無い所在。ファイルが無い所在。行番号がファイルの行数を超える所在。
  - 数は所在の数で数える（1つの R-nn に所在2つで両方ずれていれば 2）。
- `L2`（合計）には足さない。`L2_LINE_NG` は別の行として出す。
- NG のときに、どの所在かを出す行は足さない（ファイルの中身を出さないため。数だけ）。

(2) `scripts/dev/test_doc_library_check.sh`
- `"出力の順"` の期待の並びの `L2_UNTAGGED` の後に `L2_LINE_NG` を足す。
- 新しい試験（偽の HOME・REPO の中だけで作る。見出しの文字は `H1` `H2` のような中身のない文）:
  - T-L1: 見出し `## H1` が 3 行目、台帳 `| R-01 | 一 | AGENTS.md:H1:3 | 目録 | 0 |` → `L2_LINE_NG=0`
  - T-L2: 同じ台帳で、見出しを 4 行目にずらす → `L2_LINE_NG=1`
  - T-L3: 見出しの文字を1字変える（`## H9`）→ `L2_LINE_NG=1`
  - T-L4: 本 `~/.claude/books/gw.md` の見出し `## H1 [R-01]`、台帳の所在がその行 → `L2_LINE_NG=0`
  - T-L5: `# H0`（1段目）を指す → `L2_LINE_NG=0`
  - T-L6: 名前が `言い直し 一` の行が、`## H1` の節の中の本文の行（下に `### H1a` があり、その下の行でもよい）を指す → `L2_LINE_NG=0`
  - T-L7: 名前が `言い直し 一` の行が、次の `## H2` の後の行を指す → `L2_LINE_NG=1`
  - T-L8: 行番号の無い所在（`AGENTS.md:H1`）→ `L2_LINE_NG=1`
  - T-L9: 台帳が無い → `L2_LINE_NG=unreadable`
  - T-L10: 囲み（```）の中の `## H1` を指す → `L2_LINE_NG=1`

## §2 たどれる範囲を広げる（CI の点検）

`scripts/ci/check_doc_index.py`
- `scope` の行は変えない（broken_link・deep・ほかの数え方は今のまま）。
- `unreached = ...` の行だけを、範囲を広げた一覧で数える形にする。
```python
    WIDE_PREFIXES = ("docs/specs/", "docs/ai-agents/", "docs/agents/", "docs/runbooks/")
    wide = [f for f in md if f.startswith(WIDE_PREFIXES)]
    unreached = sorted(f for f in wide if f not in depth)
```
- 2026-11-04 に Opus が写しで試した結果: PR #5108 の後の実物で `unreached=0`、#5108 の前の main で `UNREACHED docs/agents/generator.md` の 1 件。
- 試験は既存の見本 `scripts/tests/rule-fixtures/doc-index/`（`reached-new-doc`・`unreached-new-spec`）の形をまねて 1 つ足す: `unreached-new-runbook`（docs/runbooks/ にどこからも指されない .md を足すと UNREACHED が1件）。見本の形が読めないときは足さずに報告に理由を書く。

## §3 週1回の点検に足す（doc-entry-weekly-check.sh）

(1) `scripts/dev/doc-entry-weekly-check.sh`
- 先頭の変数に足す: `MEMDIR="${DOC_ENTRY_MEMDIR:-$HOME_DIR/.claude/projects/-Users-tanizawashingo-salesanchor/memory}"`
- 「図書館の点検」の節で `LV_BI` の次に `L2_LINE_NG` を読み、`0` でなければ `add_ng "L2_LINE_NG=${値:-unreadable}"`。
- 新しい節を「DOC_INDEX_CI」の前に足す。出力の行と NG の条件:

| 出力 | 数え方 | NG |
|---|---|---|
| `G1_TABLE=` | 置き場ごとに `名前:本文の行の数` を `,` でつなぐ（例 `E1:0,E5:0,...`）。読めない置き場は `名前:unreadable`、無い覚え書きは `名前:missing` | なし（表示だけ） |
| `G1_OUTSIDE=` | 本文の行が1行以上ある置き場の数。E1・E5・E6・E7 のどれかが読めなければ `unreadable` | 0 以外 |
| `G3_INTENT=` | `$HOME_DIR/kb/00-rules/chat-layout.md` に `## 答える前に` の行があり、かつ `$HOME_DIR/.claude/CLAUDE.md` に前後の空白を除くと `@~/kb/00-rules/chat-layout.md` になる行があれば `yes`、どちらか無ければ `no` | `yes` 以外 |
| `G6_NO_OWNER=` | 台帳 `$REPO/docs/handoff/doc-agenda-nav/library-ledger.md` の `## 話題の重なり表` の節の、頭が `| 話題 |` の表のデータ行で、4 列目（正）が空の行の数。節か表が無ければ `unreadable` | 0 以外 |
| `K4_WIDE_UNREACHED=` | `python3 -I "$REPO/scripts/ci/check_doc_index.py" --root "$REPO"` の `SUMMARY` 行の `unreached=` の数。読めなければ `unreadable` | 0 以外 |

- G1 の数え方（design §5-4・kgi G1。語の一覧はここが正）:
  - 置き場（7 + 覚え書き 10）:
    - `E1`: `$HOME_DIR/.claude/CLAUDE.md` の `## 報告の型` の次の行から、次の `## ` の前まで
    - `E5`: `$HOME_DIR/.claude/prompts/salesanchor-designer.md` の `【POへの説明】` で始まる行の次の行から、次の `【` で始まる行の前まで
    - `E6`: `$HOME_DIR/.claude/prompts/salesanchor-claude-go.md` の `POへの説明` を含む行（全部）
    - `E7`: `$REPO/docs/ai-agents/design-partner.md` の `## 3. ` で始まる行の次の行から、次の `## ` の前まで
    - 覚え書き `M:<名前>`: `$MEMDIR/feedback_<名前>.md`。名前は `report_style` `communication_style` `always_japanese` `agent_description_japanese` `po_chat_three_lines` `plain_language_session` `session_rules_comprehensive` `plain_explain_template` `cost_in_yen` `numeric_goal_rule` の 10。頭の `---` で囲まれた部分を飛ばす。`**Why:**` で始まる行から、`**How to apply:**` で始まる行の前までを飛ばす（`**How to apply:**` の行は数える）。
  - 本文の行: 次の語を1つ以上含み、かつ次の正本の名前を1つも含まない行。
    - 語: `【おすすめ】` `選択肢には` `選択肢を3` `番号付きの選択肢` `結論を最初` `結論から` `結論ファースト` `要点→結論` `専門用語` `日常語` `決めることはありません` `1行目` `2行目`
    - 正本の名前: `chat-layout.md` `chat-layout「` `chat-format.md` `chat-format「`
  - 置き場の始まりの行が見つからないときは、その置き場を `unreadable` にする（E1・E5・E7）。E6 は含む行が 0 なら 0。
- 出力は件数と置き場の名前だけ。ファイルの中身・行の文字は出さない。

(2) `scripts/dev/test_doc_entry_weekly_check.sh`
- `setup` に、G1・G3・G6 が合格になる偽の文書を足す（中身のない文。語の一覧の語を入れない）:
  - `$H/.claude/CLAUDE.md` の末尾に `## 報告の型` と `  @~/kb/00-rules/chat-layout.md` の行（K1 の数が変わるので、既存の試験 T1〜T24 の K1 の期待値を実物に合わせて直す。直した値と理由を報告に書く）
  - `$H/kb/00-rules/chat-layout.md` に `## 答える前に`
  - `$H/.claude/prompts/salesanchor-designer.md` に `【POへの説明】`・`- x`・`【次】`
  - `$H/.claude/prompts/salesanchor-claude-go.md` に `x`
  - `$R/docs/ai-agents/design-partner.md` に `## 3. x`・`- x`・`## 4. y`
  - `$H/.claude/projects/-Users-tanizawashingo-salesanchor/memory/feedback_<名前>.md` を 10 個（頭 `---`/`name: x`/`---`、本文 `x`）
  - 台帳に `## 話題の重なり表` と、頭 `| 話題 | 個人の本の所在 | リポジトリの所在 | 正 |`・区切り・データ行 `| a | b | c | d |`
  - `$R/scripts/ci/check_doc_index.py` は偽のもの（`print("SUMMARY unreached=0 deep=0")` だけ）を置く。値を変える試験では中身を差し替える。
  - 既存の T1 で `RESULT=OK` のままであること。
- 新しい試験:
  - T-G1: 上の setup のまま → `G1_OUTSIDE=0`・`G3_INTENT=yes`・`G6_NO_OWNER=0`・`K4_WIDE_UNREACHED=0`・`L2_LINE_NG=0`・`RESULT=OK`
  - T-G2: E7 の節に `- 結論から` を足す → `G1_OUTSIDE=1`・`G1_TABLE=` に `E7:1`・`RESULT=NG`
  - T-G3: 同じ行に `chat-layout.md` も入れる → `G1_OUTSIDE=0`
  - T-G4: 覚え書き1つの `**Why:**` の行に `結論から` を入れる → `G1_OUTSIDE=0`。`**How to apply:**` の行に入れる → `G1_OUTSIDE=1`
  - T-G5: 覚え書き1つを「なぜ」の節だけにする（頭・`**Why:** x` だけ）→ そのファイルは 0、`G1_OUTSIDE=0`
  - T-G6: 覚え書き1つを消す → `G1_TABLE=` に `missing`、`G1_OUTSIDE=0`
  - T-G7: design-partner.md から `## 3. ` を消す → `G1_OUTSIDE=unreadable`・`RESULT=NG`
  - T-G8: chat-layout.md の `## 答える前に` を消す → `G3_INTENT=no`・`RESULT=NG`。CLAUDE.md の取り込みの行を消す → `G3_INTENT=no`
  - T-G9: 重なり表のデータ行の正を空に（`| a | b | c |  |`）→ `G6_NO_OWNER=1`・`RESULT=NG`。節を消す → `G6_NO_OWNER=unreadable`
  - T-G10: 偽の check_doc_index.py の出力を `unreached=2` に → `K4_WIDE_UNREACHED=2`・`RESULT=NG`
  - T-G11: 台帳の所在の行番号をずらす（§1 の T-L2 と同じ形）→ `L2_LINE_NG=1`・`RESULT=NG`

## §4 止まる条件
- 1 段目（NEEDS_DECISION で止まる）: §0 の想定と違う。触ってよいファイル以外を変えないと通らない。§5 の実物の数が 0 にならない（直してよいのは台本と試験だけ。台帳や文書を直して 0 にしない）。設計（design.md §5）の意図を変えないと書けない。
- 2 段目（BLOCKED で止まる）: 見張り（hook）に止められた（言い換えない）。push が断られた。§5 が 2 回直しても通らない（原因の生出力を報告に貼る）。

## §5 確かめ（出力はファイルへ。tail -80 で読む）
```
bash scripts/dev/test_doc_library_check.sh > /tmp/t1.txt 2>&1; tail -80 /tmp/t1.txt
bash scripts/dev/test_doc_entry_weekly_check.sh > /tmp/t2.txt 2>&1; tail -80 /tmp/t2.txt
python3 -I scripts/ci/check_doc_index.py --root . --strict > /tmp/t3.txt 2>&1; tail -80 /tmp/t3.txt
DOC_ENTRY_HOME=/nonexistent bash scripts/dev/doc-library-check.sh > /tmp/t4.txt 2>&1; tail -80 /tmp/t4.txt
bash scripts/dev/check-before-submit.sh > /tmp/t5.txt 2>&1; tail -80 /tmp/t5.txt
```
- 合格: t1・t2 の最後が `FAIL 0`。t3 が `unreached=0` で終了コード 0。t4 に `L2_LINE_NG=` の行がある（クラウドには実の HOME が無いので、値は数えない）。t5 が終了コード 0。
- 実の HOME での `L2_LINE_NG=0`・`G1_OUTSIDE=0` は、マージ前に Opus が手元で流して確かめる（担当はしない）。

## §6 報告
- `docs/handoff/doc-library-one-tree/impl-report-4.md` を作り、同じブランチにコミットして push する。
- 中身: §0 の grep の生出力、変えたファイルの一覧（`git diff --stat origin/main`）、§5 の tail の生出力、K1 の期待値を直した試験の一覧と理由、最後の HEAD の sha、最後の行に `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>`。
