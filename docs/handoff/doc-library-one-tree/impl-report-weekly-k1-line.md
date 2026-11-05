# 報告: 週次点検の K1 の線を 200 から 210 にそろえる

- 枝: `release/weekly-check-k1-line`
- 着手時 `git rev-parse HEAD` = `4e9952b0d481b492d6560a3ed149172e3ecafab2`（4e9952b0d で始まる。一致）
- commit の SHA: 最後の返事の `git ls-remote` の出力に記す（この報告自身を含む commit のため、ここには書けない）

## §0 着手前の点検（生出力）

```
$ grep -n -E "^K1_LIMIT=" scripts/dev/doc-entry-weekly-check.sh
7:K1_LIMIT=200
$ grep -n "K1>200" scripts/dev/test_doc_entry_weekly_check.sh
95:check "T2 RESULT=NG K1>200" has_re '^RESULT=NG.*K1>200'
```

想定どおり。

## §3 合格の確かめ（生出力）

（１）
```
7:K1_LIMIT=210
```

（２）
```
0
```

（３）`tail -40 /tmp/t1.txt`
```
PASS T20 K1_MISSING=none
PASS T21 K1=30
PASS T21 K1_FILES に ~/kb/n1.md
PASS T22 K1=28
PASS T22 repo/AGENTS.md が1回
PASS T23 K1=28
PASS T23 ~/kb/AGENTS.md が1回
PASS T24 K1=28
PASS T24 K1_MISSING=none
PASS T24 RESULT=OK
PASS T-G1 G1_OUTSIDE=0
PASS T-G1 G3_INTENT=yes
PASS T-G1 G6_NO_OWNER=0
PASS T-G1 K4_WIDE_UNREACHED=0
PASS T-G1 L2_LINE_NG=0
PASS T-G1 RESULT=OK
PASS T-G2 G1_OUTSIDE=1
PASS T-G2 G1_TABLE に E7:1
PASS T-G2 RESULT=NG
PASS T-G3 G1_OUTSIDE=0
PASS T-G4 Why の行は数えない
PASS T-G4 How to apply の行は数える
PASS T-G5 G1_OUTSIDE=0
PASS T-G5 report_style は 0
PASS T-G6 G1_TABLE に missing
PASS T-G6 G1_OUTSIDE=0
PASS T-G7 G1_OUTSIDE=unreadable
PASS T-G7 RESULT=NG
PASS T-G8 見出しなし → G3_INTENT=no
PASS T-G8 RESULT=NG
PASS T-G8 取り込みなし → G3_INTENT=no
PASS T-G9 G6_NO_OWNER=1
PASS T-G9 RESULT=NG
PASS T-G9 節なし → unreadable
PASS T-G10 K4_WIDE_UNREACHED=2
PASS T-G10 RESULT=NG
PASS T-G11 L2_LINE_NG=1
PASS T-G11 RESULT=NG
PASS 89 / FAIL 0
rc=0
```

FAIL の行は 0、`rc=0`。

（４）`git diff --stat origin/main...HEAD`（commit 前。台本・試験・この報告は未 commit のため、commit 後は下の 7 ファイルになる）
```
 .../handoff/doc-agenda-nav/library-requirements.md |  6 ++-
 .../doc-library-one-tree/card-weekly-k1-line.md    | 57 ++++++++++++++++++++++
 .../handoff/doc-library-one-tree/k12-fix-design.md | 25 ++++++++++
 docs/specs/doc-agenda-nav/kgi.md                   |  4 +-
 4 files changed, 89 insertions(+), 3 deletions(-)
```
作業ツリーを含む `git diff --stat origin/main`（台本・試験の 1 行ずつの変更を確認）:
```
 .../handoff/doc-agenda-nav/library-requirements.md |  6 ++-
 .../doc-library-one-tree/card-weekly-k1-line.md    | 57 ++++++++++++++++++++++
 .../handoff/doc-library-one-tree/k12-fix-design.md | 25 ++++++++++
 docs/specs/doc-agenda-nav/kgi.md                   |  4 +-
 scripts/dev/doc-entry-weekly-check.sh              |  2 +-
 scripts/dev/test_doc_entry_weekly_check.sh         |  2 +-
 6 files changed, 91 insertions(+), 5 deletions(-)
```

DONE
