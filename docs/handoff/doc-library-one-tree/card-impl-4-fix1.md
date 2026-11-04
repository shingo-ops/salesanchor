# card: 便4 直し1 — 試験の `sed -i` を Mac でも動く形にする（クラウドの Sonnet 向け）

## カードチェック
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 目的は 1 つ | ○ 週1回の点検の試験が Mac（BSD sed）でも同じ結果になる |
| 2 | 土台 | ○ `release/doc-library-one-tree-checks` の先頭（この直しカードの commit） |
| 3 | PR | ○ 作らない |
| 4 | 報告先 | ○ `docs/handoff/doc-library-one-tree/impl-report-4.md` の末尾に「## 直し1」を足す |

## §0 着手前の点検
`grep -n "sed -i" scripts/dev/test_doc_entry_weekly_check.sh` の結果が次の 1 行だけであること。違えば NEEDS_DECISION:。

```
setup; sed -i 's/| a | b | c | d |/| a | b | c |  |/' "$LG"; run
```

（観測: 2026-11-04 Opus 手元。変更前の試験 2 本に `sed -i` は 0 件だった。`git show e2822d2ec:scripts/dev/test_doc_entry_weekly_check.sh` で確認）

## §1 変える所（この 1 行だけ）
変更前:
```
setup; sed -i 's/| a | b | c | d |/| a | b | c |  |/' "$LG"; run
```
変更後:
```
setup; sed 's/| a | b | c | d |/| a | b | c |  |/' "$LG" > "$LG.tmp" && mv "$LG.tmp" "$LG"; run
```
触らない範囲: ほかの行・ほかのファイルすべて。

## §2 確かめ
- `bash scripts/dev/test_doc_entry_weekly_check.sh > <scratchpad>/t2.txt 2>&1; echo rc=$?` → rc=0、最後の行 `PASS 89 / FAIL 0`
- `grep -n "sed -i" scripts/dev/test_doc_entry_weekly_check.sh` → 0 件
- 生出力の末尾 5 行を報告に貼る

## §3 報告
impl-report-4.md の末尾に「## 直し1」を足し、§0・§2 の生出力を貼る。commit して push。最後の行は DONE / BLOCKED: <理由> / NEEDS_DECISION: <問い>。
