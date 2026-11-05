# 実装報告: 合格の線の写しのずれを見つける見張り（card-line-copy-guard）

- 作業ブランチ: `release/kgi-line-copy-guard`。着手時の `git rev-parse HEAD` = `f09600c5e9af393d074a80d35fd5eebd06df5616`（`f09600c5e` で始まる。想定どおり）
- §1 の5ファイルの commit: `426ec8df0`
- 報告の commit: この報告を含む次の commit（SHA は最後の返事の `git ls-remote` の出力に書く）
- PR は作っていない。

## 注記（事実）

- `./scripts/dev/executor-preflight.sh` はクラウドで `PREFLIGHT FAIL`（[1/3] api.github.com に到達不可、[2/3] gh の shingo-cc への切り替え失敗。[3/3] [4/4] は OK）。この作業は gh を使わず push だけなので、そのまま続けた。
- commit 時のフックの警告: `tools/claude-channels/intake/CLAUDE.md: LIMITS 未登録`（今回の変更と無関係。commit は通った）。
- 表に無いファイルは作っていない。active-work.d は commit していない。

## §0 着手前の点検（生出力）

```
7:K1_LIMIT=210
8:K9_LIMIT_TOKENS=7500
89:      add_ng "K9>7.5k"
---
95:check "T2 RESULT=NG K1>210" has_re '^RESULT=NG.*K1>210'
---
12:| L1 | 毎回読む量 K9 ≤ ~~6.5k~~ **7.5k**（2026-11-05 に変更。下の注記）、行数 K1 ≤ ~~200~~ **210**（2026-11-05 に変更。下の注記） | `bash scripts/dev/doc-entry-weekly-check.sh` の K1= と K9= |
---
3
---
ls: cannot access 'scripts/ci/check_kgi_line_copies.py': No such file or directory
ls: cannot access 'scripts/tests/test_check_kgi_line_copies.py': No such file or directory
ls: cannot access '.github/workflows/kgi-line-copies.yml': No such file or directory
```

すべて想定どおり。

## §3 合格の確かめ（生出力）

### （１）

```
BASE K1=210 K9=7.5 K12=18
COPY C1 expected=210 found=210 SAME
COPY C2 expected=7500 found=7500 SAME
COPY C3 expected=7.5 found=7.5 SAME
COPY C4a expected=7.5 found=7.5 SAME
COPY C4b expected=210 found=210 SAME
COPY C5 expected=210 found=210,210 SAME
SUMMARY same=6 diff=0 missing=0
rc=0
```

### （２）

```
test_all_same (__main__.LineCopies.test_all_same) ... ok
test_bad_args (__main__.LineCopies.test_bad_args) ... ok
test_base_unreadable (__main__.LineCopies.test_base_unreadable) ... ok
test_each_copy_diff (__main__.LineCopies.test_each_copy_diff) ... ok
test_missing_k1_line (__main__.LineCopies.test_missing_k1_line) ... ok
test_real_repo (__main__.LineCopies.test_real_repo) ... ok
test_routines_broken_json (__main__.LineCopies.test_routines_broken_json) ... ok
test_routines_diff (__main__.LineCopies.test_routines_diff) ... ok
test_routines_file_missing (__main__.LineCopies.test_routines_file_missing) ... ok
test_routines_name_differs (__main__.LineCopies.test_routines_name_differs) ... ok
test_routines_same (__main__.LineCopies.test_routines_same) ... ok
test_struck_through_old_value_ignored (__main__.LineCopies.test_struck_through_old_value_ignored) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.616s

OK
rc=0
```

### （３）

FAIL の行は 0 件（`grep -c '^FAIL'` = 0）。末尾と該当行:

```
PASS T1 LINE_COPY=skipped
PASS T-LC1 LINE_COPY=SAME
PASS T-LC1 RESULT=OK
PASS T-LC2 LINE_COPY=DIFF
PASS T-LC2 RESULT=NG に LINE_COPY=DIFF
PASS T-LC2 rc=1
PASS 95 / FAIL 0
rc=0
```

### （４）ずれの実地（commit の後。台本 7 行目を一時的に `K1_LIMIT=200` にして実行 → `git checkout --` で戻した）

```
BASE K1=210 K9=7.5 K12=18
COPY C1 expected=210 found=200 DIFF
COPY C2 expected=7500 found=7500 SAME
COPY C3 expected=7.5 found=7.5 SAME
COPY C4a expected=7.5 found=7.5 SAME
COPY C4b expected=210 found=210 SAME
COPY C5 expected=210 found=210,210 SAME
SUMMARY same=5 diff=1 missing=0
rc=1
--- git status --short:
--- end
```

（`git status --short` は空）

### （５）

```
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

### （６）`git diff --stat origin/main...HEAD`（報告の追加前）

```
 .github/workflows/kgi-line-copies.yml              |  39 +++++
 .../doc-library-one-tree/card-line-copy-guard.md   |  70 +++++++++
 .../handoff/doc-library-one-tree/k12-fix-design.md |   5 +
 .../doc-library-one-tree/line-copy-guard-design.md | 139 ++++++++++++++++++
 scripts/ci/check_kgi_line_copies.py                | 157 +++++++++++++++++++++
 scripts/dev/doc-entry-weekly-check.sh              |  16 ++-
 scripts/dev/test_doc_entry_weekly_check.sh         |  26 ++++
 scripts/tests/test_check_kgi_line_copies.py        | 145 +++++++++++++++++++
 8 files changed, 596 insertions(+), 1 deletion(-)
```

§1 の5つ＋Opus が先にコミット済みの書類（設計・カード・k12-fix-design.md）だけ。

## 未確認

- CI（`kgi line copies`）の GitHub 上での実行はまだ（PR を作っていないため）。
- 実機の routines.json での `same=7` はマージ後に Mac で確認する（設計 §8）。

DONE
