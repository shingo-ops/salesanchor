# card: 週次点検の K1 の線を 200 から 210 にそろえる（クラウドの Sonnet 向け）

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§5） |
| 4 | 目的は 1 つ | ○ 週次点検の K1 の線を kgi.md（210 行）にそろえる |
| 5 | 土台のブランチ | ○ このカードがあるブランチ `release/weekly-check-k1-line`（`origin/main` 38cfb213d から作成済み） |
| 6 | 形は例で示す | ○ §1 に変更前と変更後の行を全文 |
| 7 | 合格基準に出力 | ○ §3 |
| 8 | 対象の名前 | ○ 触ってよいファイルは台本 1 つ・試験 1 つ・報告 1 つ |
| 9 | 出力の上限 | ○ tail -40 |
| 10 | 終わりの合図 | ○ 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-05 の origin/main 38cfb213d の実物 |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Edit の道具・見張りで止まったら言い換えない | ○ |

- 設計: [k12-fix-design.md](k12-fix-design.md) §17。合格ライン: [kgi.md](../../specs/doc-agenda-nav/kgi.md) K1（210 行以下、PO 決定 2026-11-05）。
- PO の承認: 2026-11-05 チャット「1」（行数の上限を 200 行から 210 行に上げる）。
- 作業ブランチ: `release/weekly-check-k1-line`。このブランチにコミットして push する。main には触らない。
- 公開リポジトリ。個人の決まりの本文を書き写さない。

## §0 着手前の点検（違えば NEEDS_DECISION で止まる）
結果を報告に貼る。

| 確かめること | 想定 |
|---|---|
| `grep -n -E "^K1_LIMIT=" scripts/dev/doc-entry-weekly-check.sh` | `7:K1_LIMIT=200` の1件 |
| `grep -n "K1>200" scripts/dev/test_doc_entry_weekly_check.sh` | `95:check "T2 RESULT=NG K1>200" has_re '^RESULT=NG.*K1>200'` の1件 |

## §1 直す2行（Edit の道具で。ほかの行は変えない）
（１）`scripts/dev/doc-entry-weekly-check.sh` 7 行目 `K1_LIMIT=200` → `K1_LIMIT=210`
（２）`scripts/dev/test_doc_entry_weekly_check.sh` 95 行目 `check "T2 RESULT=NG K1>200" has_re '^RESULT=NG.*K1>200'` → `check "T2 RESULT=NG K1>210" has_re '^RESULT=NG.*K1>210'`

## §2 触らないもの
§1 の2行と §5 の報告以外のすべて。台本 42 行目の判定の式、試験 93〜94 行目の T2 の入力（K1=214）も変えない。

## §3 合格の確かめ（生出力を報告に貼る）
（１）`grep -n -E "^K1_LIMIT=" scripts/dev/doc-entry-weekly-check.sh` → `7:K1_LIMIT=210` の1件だけ
（２）`grep -c "K1>200" scripts/dev/test_doc_entry_weekly_check.sh` → `0`
（３）`bash scripts/dev/test_doc_entry_weekly_check.sh > /tmp/t1.txt 2>&1; echo "rc=$?" >> /tmp/t1.txt; tail -40 /tmp/t1.txt` → FAIL の行が 0・`rc=0`
（４）`git diff --stat origin/main...HEAD` → 台本 1・試験 1・報告 1 と、Opus が先にコミット済みの書類 4 つ（kgi.md・library-requirements.md・k12-fix-design.md・このカード）だけ

## §4 止まる条件
- 1 段目（NEEDS_DECISION）: §0 の想定と違う。§3 が §1 以外を変えないと通らない。
- 2 段目（BLOCKED）: 見張り（フック）に止められた。言い換えて通そうとしない。止められた命令と文面をそのまま報告に書く。

## §5 報告
`docs/handoff/doc-library-one-tree/impl-report-weekly-k1-line.md` に、§0 と §3 の生出力（要約しない）と commit の SHA を書く。最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` のどれか。

## §6 作業の決まり
- commit 文は Write でファイルに書いて `git commit -F <ファイル>` で流す。git は1命令ずつ流す。
- 台本 1 つ・試験 1 つ・報告 1 つを1つの commit にして、`git push origin release/weekly-check-k1-line` する。
- sleep を使わない。
