# 実装報告: 週次点検の NG と未実行（weekly-ng・weekly-missing）

カード: [card-weekly-ng.md](card-weekly-ng.md) / 設計: [design-weekly-ng.md](design-weekly-ng.md)

## 起点の確認
- `git rev-parse HEAD` = `9006fbf6211c59327ee50ac973b5476501242e1b`（`9006fbf62` で始まる。`origin/release/weekly-check-ng-notify` と一致）

## §0 着手前の点検（実測。すべて想定どおり）
- `wc -l`: 593 行（mac-jobs-watch.sh）・818 行（試験）
- `grep -n`: `51:MJW_PHONE_GRACE`・`72:ST_PHONE=0`・`380:  mjw_phone_check`・`457:mjw_commit_events`・`515:C_DKICK=…`
- `echo "----"`: 816 行目
- `grep -rn 'weekly' … | wc -l`: `0`
- `.github/workflows/mac-jobs-watch-test.yml`: 無い

## 作ったもの
- `scripts/mac-jobs-watch.sh`: 設計 §3-1〜§3-8 のとおり（設定 3 行・変数・状態の読み書き・`mjw_ymd`・`mjw_weekly_parse`・`mjw_weekly_expect`・weekly-missing の判定と `mjw_judged`・weekly-ng の判定・固定文・先頭の説明）。設計のコードをそのまま写した
- `scripts/tests/test-mac-jobs-watch.sh`: W1〜W17 を `echo "----"` の前に追加。ヘッダに説明を足した。補助関数 `wk_ts`・`wk_setup`・`wk_file` を足した（既存の関数は変えていない）
- `.github/workflows/mac-jobs-watch-test.yml`: 設計 §5 の全文

## §3 の確かめ（Linux のクラウド）
（１）構文
```
bash -n scripts/mac-jobs-watch.sh; echo "rc=$?"            → rc=0
bash -n scripts/tests/test-mac-jobs-watch.sh; echo "rc=$?"  → rc=0
```
（２）shellcheck: このクラウドには無い（`which shellcheck` が何も返さない）。増えた指摘の数は未確認。GitHub の CI で確かめる
（３）`python3 -c "import yaml…"` → `yaml ok`
（４）`grep -c 'W1[0-7]\? \|W[1-9] ' scripts/tests/test-mac-jobs-watch.sh` → `20`。W1〜W17 の `eq`/`ok` の行は、`grep -n '"W[0-9]*-\|"W[0-9]* '` で 832〜926 行目に 49 行（W1-1 が 832、W17-2 が 926）
（５）`git diff --stat origin/main...HEAD`（報告の commit の前）
```
 .github/workflows/mac-jobs-watch-test.yml       |  32 +++
 docs/handoff/mac-jobs-watch/card-weekly-ng.md   |  68 ++++++
 docs/handoff/mac-jobs-watch/design-weekly-ng.md | 263 ++++++++++++++++++++++++
 docs/handoff/mac-jobs-watch/recon-weekly-ng.md  |  31 +++
 scripts/mac-jobs-watch.sh                       |  70 ++++++-
 scripts/tests/test-mac-jobs-watch.sh            | 113 ++++++++++
 6 files changed, 575 insertions(+), 2 deletions(-)
```

## 流していないもの（未確認）
- 見張り役の試験本体（macOS の `date -j` を使うため Linux では流せない）。W1〜W17 が実際に通るかは、PR の macOS の CI で確かめる
- 試験 W11・W15 の「送信数」は、設計の表の「送信 2」「1 通」を、その回の前後の差で書いた。CI で落ちたら期待の取り方を見直す

## commit
- 変更の 3 ファイル: `2cc1ccc815dbe4523a9b6b788743492ef9ed9c4c`
- 報告: この報告を含む commit（SHA は push 後に `git log` で確認）

## push 前の `git log --oneline -3`
```
2cc1ccc81 feat(mac-jobs-watch): 週次点検の NG と未実行を Discord で知らせる
9006fbf62 docs: design and card for weekly check NG notice in mac-jobs-watch
a7c5713c4 Merge pull request #5148 from shingo-ops/release/weekly-check-k1-line
```
`git status --short` は、この報告の追加前は空（active-work.d は commit していない）。push の後の結果はこの下の追記を見る。

DONE
