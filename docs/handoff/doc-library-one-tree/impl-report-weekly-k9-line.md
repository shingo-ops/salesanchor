# 報告: 週次点検の K9 の線を 7.5k にそろえる

- 枝: `release/weekly-check-k9-line`。作業開始時の `git rev-parse HEAD` は `1951e733fa70eb31d656c4a42c54eef3ec493329`（`1951e733f` で始まる）。
- この commit の SHA は commit 自身には書けないため、最後の返事の `git ls-remote` の出力を見る。
- 触ったのは `scripts/dev/doc-entry-weekly-check.sh` の 8 行目と 89 行目だけ。

## §0 着手前の点検（生出力）
```
$ grep -n -E "K9_LIMIT_TOKENS=|K9>" scripts/dev/doc-entry-weekly-check.sh
8:K9_LIMIT_TOKENS=6500
89:      add_ng "K9>6.5k"
```
想定どおり（2件）。

## §3 合格の確かめ（生出力）
### （１）
```
8:K9_LIMIT_TOKENS=7500
89:      add_ng "K9>7.5k"
```
### （２）
```
0
```
### （３）`tail -40`（出力先はスクラッチパッドのファイル。カードの `/tmp/t1.txt` の代わり）
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
FAIL 0・`rc=0`。

### （４）`git diff --stat origin/main...HEAD`（commit 前の実測）
```
 .../doc-library-one-tree/card-weekly-k9-line.md    | 56 ++++++++++++++++++++++
 .../handoff/doc-library-one-tree/k12-fix-design.md | 19 ++++++++
 2 files changed, 75 insertions(+)
```
commit 前なので台本と本報告は未計上（`git status --short` は ` M scripts/dev/doc-entry-weekly-check.sh` のみ）。commit 後は台本 1・報告 1 が加わる。

DONE
