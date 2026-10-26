# 実装カード 便M3: 入口の文書の週次点検スクリプトと試験（design.md §32 D3・D4・32-4 M3）

- 設計: docs/handoff/doc-agenda-nav/design.md §32（審査6回目 APPROVE on d2f244d70・PR #4797）。PO 実装承認 2026-10-26（PO 原文「1」）。
- 枝: release/doc-agenda-nav-maintain-m3（M2 #4802 マージ後の origin/main 8cf4c84d6 起点）。1便＝1PR。push まで。PR は手元（Opus）が作る。
- 発行: Opus（設計担当）2026-10-27。
- 定期実行の登録（ac-routine.mjs）と本物での1回目の実行は、マージ後に Opus 本体が手元で行う。このカードの範囲外。

## 0. 先に確かめること（実物点検。合わなければ止めて報告）

| # | 確かめる事実 | 期待 |
|---|---|---|
| P1 | `ls scripts/dev/doc-entry-weekly-check.sh scripts/dev/test_doc_entry_weekly_check.sh` | どちらも無い |
| P2 | `grep -n "^## " docs/handoff/doc-agenda-nav/baseline.md` | `## 全条件の測り直し（2026-10-26）` が1本だけ（:245）。`## 段8 の後の測り直し（2026-10-26）` が別に在る（:233） |
| P3 | `sed -n 47,65p docs/adr/ADR-1040-doc-agenda-nav-entry-index.md` | 「## 強制の仕組み」表に4行（行数検査 CI・到達検査 CI・登録の見張りの試験 CI・設計持ち込みの検査）。:64 が「- リポジトリ外の点検と K12 の時期は design §32 D3・D4 で作る予定（M3。まだ無い）。」 |
| P4 | `sed -n 34,40p docs/specs/doc-agenda-nav/kgi.md` | 「## 運用方針」の中に「- 合格後の点検: design.md §32。」の行が在る |
| P5 | `sed -n 328p docs/handoff/doc-agenda-nav/design.md` | 「- リポジトリ外（CI が見えない）の守り手（段7で新設案・PO の実装承認待ち）: ~/kb/scripts/patrol.sh …」で始まる行 |
| P6 | `ls scripts/agent-hooks/master-register-rules-guard.py; command -v python3` | どちらも在る |

P1〜P6 の生出力は §5 の証拠ファイルに貼る。

## 1. 変更（この範囲だけ）

### 1-1 新規 scripts/dev/doc-entry-weekly-check.sh（読むだけ。どのファイルも書き換えない）

- 先頭: `#!/usr/bin/env bash`・`set -u`（`-e` は付けない。1項目の失敗で他の項目を止めないため）。2行目以降のコメントに「入口の文書の週次点検（doc-agenda-nav design §32 D3・ADR-1040）。読むだけ。」と使い方1行。
- 先頭の定数（正本はここ1か所。kgi.md の合格線の写しであることをコメントに書く）:
  `K1_LIMIT=200`・`K9_LIMIT_TOKENS=6500`・`K12_DAYS=90`・`PEER_DAYS=7`
- 差し替えの口（既定は本物。設計 D3 のとおり5つだけ。これ以外を足さない）:
  - `HOME_DIR="${DOC_ENTRY_HOME:-$HOME}"`
  - `REPO="${DOC_ENTRY_REPO:-<このスクリプトの2つ上のディレクトリの絶対パス>}"`
  - `GH="${DOC_ENTRY_GH:-gh}"`
  - `TODAY="${DOC_ENTRY_TODAY:-<今日の YYYY-MM-DD>}"`
  - `DOC_ENTRY_SKIP_K9=1` なら K9 を測らない
- 日付の計算はすべて `python3 -I -c` で行う（macOS の date と GNU の date の違いを避ける）。JSON の読み取りも `python3 -I -c` で行う（jq は使わない。手元に無いことがあるため）。
- 出力は1項目1行の `名前=値`。順番は下の表のとおり。最後の行が `RESULT=`。

| 行 | 求め方 | NG の条件 |
|---|---|---|
| `K1=<合計>` | 次の各ファイルの `wc -l` の合計。(1) `$HOME_DIR/.claude/CLAUDE.md`。(2) その中の `@` で始まる行が指すファイル（行頭の `@` を外し、先頭の `~/` を `$HOME_DIR/` に置き換える。今は `@~/kb/AGENTS.md` の1本）。(3) `$HOME_DIR/.claude/rules/` 配下（下の階層も含む）の `*.md` のうち、1行目が `---` で、次の `---` までの間に `paths:` で始まる行が無いもの（1行目が `---` でないファイルも「paths なし」として数える）。(4) `$REPO/CLAUDE.md`・`$REPO/AGENTS.md`。無いファイルは数えず、`K1_MISSING=` に並べる | 合計 > K1_LIMIT |
| `K1_FILES=<パス,パス,…>` | 上で数えたファイルを `,` 区切り。`$HOME_DIR` は `~` に置き換えて表示 | — |
| `K1_MISSING=<パス,…>|none` | (1)(2)(4) のうち無かったもの | none 以外なら NG（数えられなかった） |
| `K2_COPY=SAME|DIFF|missing` | `cmp -s "$HOME_DIR/.claude/scripts/master-register-rules-guard.py" "$REPO/scripts/agent-hooks/master-register-rules-guard.py"`。どちらかが無ければ missing | DIFF か missing |
| `K9=<値>k|unreadable|skipped` | `DOC_ENTRY_SKIP_K9=1` なら skipped。それ以外は `$REPO` を作業場所にして `claude -p "/context" --no-session-persistence` を実行し、出力の表の `| Memory files | <値> |` の行の値から、`### Memory Files` の表で パスが `/MEMORY.md` で終わる行の値を引く（値は `16.8k` なら 16800、`221` なら 221 として計算し、結果を `%.1fk` で出す。例: 16.8k−10.7k → `6.1k`）。claude が無い・rc≠0・どちらかの行が見つからない場合は unreadable | unreadable か 値 > K9_LIMIT_TOKENS。skipped は判定に使わない |
| `DOC_INDEX_CI=success|failure|pending|none|unreadable` | `$GH run list --workflow doc-index-reachability.yml --branch main -L 1 --json status,conclusion` の JSON を読む。空の配列なら none。status が completed でなければ pending。completed で conclusion が success なら success、それ以外（failure・cancelled など）は failure。gh の rc≠0 か JSON が読めなければ unreadable | failure か unreadable（pending と none は NG にしない） |
| `K12_LAST=<YYYY-MM-DD>|none` | `$REPO/docs/handoff/doc-agenda-nav/baseline.md` の行のうち `^## 全条件の測り直し（[0-9]{4}-[0-9]{2}-[0-9]{2}）$` に合うものの日付の最大値（「段8 の後の測り直し」などほかの見出しは拾わない） | — |
| `K12_DUE=yes|no` | K12_LAST が none、または TODAY − K12_LAST > K12_DAYS（日数）なら yes | NG にしない（D4 で扱う） |
| `K12_OPEN_PR=<URL>|none|unreadable` | `$GH pr list --state open -L 200 --json headRefName,url` の JSON のうち headRefName が `release/doc-entry-k12-` で始まる最初の1件の url。無ければ none。gh の rc≠0 か JSON が読めなければ unreadable（設計 D3 の `-q` の絞り込みを python3 で行う。`--head` は使わない） | NG にしない |
| `PEER_LAST=<YYYY-MM-DD>|none` | `$HOME_DIR/CC報告ファイル-keep/consent-weekly/` のファイル名のうち `^[0-9]{8}\.txt$` に合うものの最大の日付（ファイル名から読む。更新時刻は使わない） | none か TODAY − PEER_LAST ≥ PEER_DAYS（日数） |
| `RESULT=OK` か `RESULT=NG <理由>` | 上の NG の条件に当たったものを、当たった順に半角空白区切りで理由に並べる（例: `RESULT=NG K1>200 K2_COPY=DIFF`。理由の書き方は `<行名>=<値>` か `K1>200`・`K9>6.5k` の形） | — |

- 終了コード: RESULT=OK なら 0、NG なら 1。

### 1-2 新規 scripts/dev/test_doc_entry_weekly_check.sh

- 一時ディレクトリ（`mktemp -d`。終わりに `trap` で消す）に偽の HOME・偽の REPO・偽の gh を作り、`DOC_ENTRY_HOME`・`DOC_ENTRY_REPO`・`DOC_ENTRY_GH`・`DOC_ENTRY_TODAY=2027-01-31`・`DOC_ENTRY_SKIP_K9=1` で 1-1 を動かす。本物の ~/.claude・~/CC報告ファイル-keep・gh には触れない。
- 偽の gh: 引数の1つ目が `run` なら環境変数 `FAKE_RUN_JSON` を、`pr` なら `FAKE_PR_JSON` を標準出力に出して rc=0（`FAKE_GH_RC` が在ればその rc で終わる）。
- 基本の形（各場合はここから1点だけ変える）:
  - 偽の HOME: `.claude/CLAUDE.md`（10行。最後の行が `@~/kb/AGENTS.md`）・`kb/AGENTS.md`（5行）・`.claude/rules/common/a.md`（paths なし・3行）・`.claude/rules/common/b.md`（1行目 `---`、2行目 `paths:`、3行目 `  - "**/*.py"`、4行目 `---`、計20行）・`.claude/scripts/master-register-rules-guard.py`（中身 `x`）・`CC報告ファイル-keep/consent-weekly/20270131.txt`
  - 偽の REPO: `CLAUDE.md`（2行）・`AGENTS.md`（4行）・`scripts/agent-hooks/master-register-rules-guard.py`（中身 `x`）・`docs/handoff/doc-agenda-nav/baseline.md`（`## 全条件の測り直し（2027-01-01）` を含む）
  - `FAKE_RUN_JSON='[{"status":"completed","conclusion":"success"}]'`・`FAKE_PR_JSON='[]'`
- 場合（1行ごとに `check "<名前>" <条件>` で PASS/FAIL を出し、最後に `PASS n / FAIL m` を出して FAIL が1件でもあれば exit 1）:

| # | 変える1点 | 期待 |
|---|---|---|
| T1 | 基本の形のまま | `K1=24`（10+5+3+2+4。b.md は数えない）・`K1_FILES=` に b.md が無い・`K2_COPY=SAME`・`K9=skipped`・`DOC_INDEX_CI=success`・`K12_LAST=2027-01-01`・`K12_DUE=no`・`K12_OPEN_PR=none`・`PEER_LAST=2027-01-31`・`RESULT=OK`・rc=0 |
| T2 | 偽の HOME の `.claude/CLAUDE.md` を 200 行にする | `K1=214`・`RESULT=NG` で理由に `K1>200`・rc=1 |
| T3 | 偽の HOME の写しの中身を `y` にする | `K2_COPY=DIFF`・`RESULT=NG` |
| T4 | baseline.md の見出しを `## 全条件の測り直し（2026-11-01）`（TODAY の91日前）にする | `K12_DUE=yes`・`RESULT=OK` |
| T5 | T4 に加えて `## 段8 の後の測り直し（2027-01-30）` を足す | `K12_LAST=2026-11-01`・`K12_DUE=yes` |
| T6 | 見出しを `## 全条件の測り直し（2026-11-02）`（90日前）にする | `K12_DUE=no` |
| T7 | `FAKE_RUN_JSON='[{"status":"completed","conclusion":"failure"}]'` | `DOC_INDEX_CI=failure`・`RESULT=NG` |
| T8 | `FAKE_RUN_JSON='[{"status":"in_progress","conclusion":""}]'` | `DOC_INDEX_CI=pending`・`RESULT=OK` |
| T9 | consent-weekly を `20270124.txt`（7日前）だけにする | `PEER_LAST=2027-01-24`・`RESULT=NG` |
| T10 | consent-weekly を `20270125.txt`（6日前）だけにする | `RESULT=OK` |
| T11 | consent-weekly を `20270124.txt` と `20270131-guard-blocked-analysis.md` にする | `PEER_LAST=2027-01-24`・`RESULT=NG`（付属ファイルを拾わない） |
| T12 | `FAKE_PR_JSON='[{"headRefName":"release/doc-entry-k12-20270101","url":"https://example.invalid/pull/1"}]'` | `K12_OPEN_PR=https://example.invalid/pull/1`・`RESULT=OK` |
| T13 | `FAKE_PR_JSON='[{"headRefName":"release/other","url":"https://example.invalid/pull/2"}]'` | `K12_OPEN_PR=none` |
| T14 | 偽の HOME の `kb/AGENTS.md` を消す | `K1_MISSING=` に `~/kb/AGENTS.md`・`RESULT=NG` |
| T15 | `FAKE_GH_RC=1` | `DOC_INDEX_CI=unreadable`・`K12_OPEN_PR=unreadable`・`RESULT=NG` |

### 1-3 ADR-1040（docs/adr/ADR-1040-doc-agenda-nav-entry-index.md）

- 「## 強制の仕組み」表の「登録の見張りの試験 CI」の行の後に1行足す:
  `| 週次点検 | scripts/dev/doc-entry-weekly-check.sh・agent-console の定期実行「入口の文書 週次点検」（月曜 16:00） | リポジトリの外の入口の行数（K1）・登録の見張りの写しのずれ（K2）・会話の始まりの読み込み量（K9）・到達検査 CI の最新結果・同意の週次点検が動いているかを毎週見て、外れたら PO へ知らせる。K12 は90日ごとに測り直す（design §32 D3・D4） |`
- 「## 維持の仕組み」の1行目の「守り手は上の表の4つ（行数検査 CI・到達検査 CI・登録の見張りの試験 CI・設計持ち込みの検査）。」を「守り手は上の表の5つ（行数検査 CI・到達検査 CI・登録の見張りの試験 CI・設計持ち込みの検査・週次点検）。」に直す。
- :64 の行を「- リポジトリ外の点検は週次点検（月曜 16:00）。K12 は週次点検の `K12_DUE=yes`（前回から90日超）で定期実行の会話が測り直し、baseline.md に `## 全条件の測り直し（YYYY-MM-DD）` の見出しで書く（design §32 D3・D4）。週次点検と同意の週次点検は互いの保存先の日付を見張る。」に置き換える。他の行は変えない。
- `node scripts/generate-adr-index.js` を実行し、docs/adr/README.md に差分が出たら同じコミットに入れる。

### 1-4 kgi.md（docs/specs/doc-agenda-nav/kgi.md）

- 「- 合格後の点検: design.md §32。」の行の直後に1行足す:
  `- K12 を測り直したら baseline.md に `## 全条件の測り直し（YYYY-MM-DD）` の見出しで書く（週次点検がこの見出しの日付で90日ごとの時期を決める。design §32 D4）。`

### 1-5 design.md（docs/handoff/doc-agenda-nav/design.md）:328

- P5 の行を次の1行に置き換える（32-4 M3「本文 §維持の仕組みの『リポジトリ外の守り手（段7で新設案）』を書き換える」）:
  `- リポジトリ外（CI が見えない）の守り手: scripts/dev/doc-entry-weekly-check.sh を agent-console の定期実行「入口の文書 週次点検」（月曜 16:00）が動かす（K1・K2 の写し・K9・到達検査 CI の最新結果・同意の週次点検の見張り。K12 は90日ごと）。~/kb/scripts/patrol.sh に足す旧案は採らない（§32-8 (a)）。詳細は §32 D3・D4`
- design.md の他の行は変えない。

### 1-6 触らない範囲

- 他の scripts/・workflow・~/.claude・~/kb・agent-console の設定（routines.json）。
- CI の job は足さない（設計にない）。
- 必須チェック（Ruleset）への登録はしない。

## 2. 作る順

1. 枝と HEAD を確かめる（クラウドでは executor-preflight.sh を使わない。preflight は手元の実行役用で、クラウドからは api.github.com に届かないため）。
2. §0 を実行して証拠に貼る。
3. §1-1・§1-2 を作り、`bash scripts/dev/test_doc_entry_weekly_check.sh; echo rc=$?` が FAIL 0・rc=0 になるまで直す（直すのは 1-1・1-2 だけ。期待の値を変えたくなったら止めて `NEEDS_DECISION:`）。
4. `bash -n scripts/dev/doc-entry-weekly-check.sh scripts/dev/test_doc_entry_weekly_check.sh` と、在れば `shellcheck` を2本に当てる（無ければ「shellcheck なし」と書く）。
5. §1-3〜§1-5 を作る。
6. `python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?` が rc=0（rc≠0 なら commit しない・止めて報告）。
7. コミットを1つ（`feat: add doc-entry weekly check script and tests (ADR-1040 M3)`）。証拠ファイルを別コミットにして push。

## 3. 試験（担当の範囲）

- §2-3 の試験の全出力（PASS/FAIL の全行と最後の集計）。
- 1-1 を基本の形の偽の環境で1回だけ手で動かした出力（`DOC_ENTRY_SKIP_K9=1`）。
- 本物の ~/.claude を使う実行（32-6 (b)）はクラウドでは行わない。マージ後に Opus が手元で行う。

## 4. マージ後に Opus 本体が手元で行うこと（担当は行わない）

- 本物で1回動かす（`DOC_ENTRY_SKIP_K9` なし）。同じ時に別に `wc -l` で数えた同じ範囲の合計と `K1` が一致、`K2_COPY=SAME`、同じ条件で手で取った `/context` の値と `K9` が一致、`RESULT=OK`（32-6 (b)）。
- `ac-routine.mjs add` で「入口の文書 週次点検」（月曜 16:00・closeWhenIdle true。手順は design §32 D3・D4）。`ac-routine.mjs update` で「同意と権限の週次点検」に doc-entry-weekly の8日の項目を足す。`ac-routine.mjs list` で確かめる。

## 5. 証拠ファイル

- docs/handoff/doc-agenda-nav/evidence-maintain-m3.md（新規）。§0 の生出力・§2-3 の試験の全出力と rc・§2-4・§2-6 の rc・§3 の手での実行の出力。要約しない。

## 6. 報告

- 最後の行は `DONE <HEAD の sha40>`・`BLOCKED: <理由>`・`NEEDS_DECISION: <内容>` のどれか。

## 7. 直し1（2026-10-27・手元 macOS で T14 が落ちた）

- 事実: 手元の /bin/bash は 3.2.57。HEAD 308c883c2 で `bash scripts/dev/test_doc_entry_weekly_check.sh` → `FAIL T14 K1_MISSING`・`PASS 37 / FAIL 1`・rc=1。3.2 では `"${1/#$HOME_DIR/\~}"` が `\~/kb/AGENTS.md` を返す（バックスラッシュが残る）。定期実行はこの Mac の bash 3.2 で動くので直す。
- 変更はこの1か所だけ: scripts/dev/doc-entry-weekly-check.sh の `disp()` を次にする。試験・期待の値は変えない。
  ```
  disp() { local t='~'; printf '%s' "${1/#$HOME_DIR/$t}"; }
  ```
  （変数の中の `~` は展開されないので、bash 3.2 と 5 のどちらでも `~/…` になる。手元 3.2 で `~/kb/AGENTS.md`・`/other/a` を確認済み）
- 確かめ: クラウドの bash で試験を回し `PASS 38 / FAIL 0`・rc=0。生出力を evidence-maintain-m3.md の末尾に「## 直し1」として足す。手元 3.2 の確認は Opus が行う。
