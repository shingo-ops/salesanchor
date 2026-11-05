# card: 合格の線の写しのずれを見つける見張りを作る（クラウドの Sonnet 向け）

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§5） |
| 4 | 目的は 1 つ | ○ 合格の線の写しが正本（kgi.md）とずれたら CI と週次点検で止まる |
| 5 | 土台のブランチ | ○ このカードがあるブランチ `release/kgi-line-copy-guard`（`origin/main` a7c5713c4 から作成済み） |
| 6 | 形は例で示す | ○ 設計 §3 に読み方の正規表現・出力の形・終了コード |
| 7 | 合格基準に出力 | ○ §3 |
| 8 | 対象の名前 | ○ §2 の6ファイルと報告 1 つ |
| 9 | 出力の上限 | ○ tail -60 |
| 10 | 終わりの合図 | ○ 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-05 の origin/main a7c5713c4 の実物 |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Edit の道具・見張りで止まったら言い換えない | ○ |

- 設計: [line-copy-guard-design.md](line-copy-guard-design.md)（§3 が作るものの全部。読んでから始める）
- PO の承認: 2026-11-05 PO 原文「1,2を順番に実装」。
- 作業ブランチ: `release/kgi-line-copy-guard`。このブランチにコミットして push する。main には触らない。
- 公開リポジトリ。個人の決まりの本文を書き写さない。routines.json の本物はクラウドに無い。試験の偽物だけを使う。

## §0 着手前の点検（違えば NEEDS_DECISION で止まる。結果を報告に貼る）

| 確かめること | 想定 |
|---|---|
| `grep -n -E "^K1_LIMIT=\|^K9_LIMIT_TOKENS=\|K9>" scripts/dev/doc-entry-weekly-check.sh` | `7:K1_LIMIT=210`・`8:K9_LIMIT_TOKENS=7500`・`89:      add_ng "K9>7.5k"` の3件 |
| `grep -n "K1>" scripts/dev/test_doc_entry_weekly_check.sh` | 95 行目の1件（`K1>210` が2か所） |
| `grep -n "^| L1 " docs/handoff/doc-agenda-nav/library-requirements.md` | 12 行目に `~~6.5k~~ **7.5k**` と `~~200~~ **210**` |
| `grep -c -E "^\| K(1\|9\|12) \|" docs/specs/doc-agenda-nav/kgi.md` | `3` |
| `ls scripts/ci/check_kgi_line_copies.py scripts/tests/test_check_kgi_line_copies.py .github/workflows/kgi-line-copies.yml` | 3つとも無い |

## §1 作るもの・直すもの（設計 §3 のとおり。Write と Edit の道具で）

（１）新規 `scripts/ci/check_kgi_line_copies.py`（設計 §3-1）
（２）新規 `scripts/tests/test_check_kgi_line_copies.py`（設計 §3-2。書き方は `scripts/tests/test_check_rule_registry.py` にそろえる）
（３）新規 `.github/workflows/kgi-line-copies.yml`（設計 §3-3。`name: KGI Line Copies`、job の `name: kgi line copies`）
（４）`scripts/dev/doc-entry-weekly-check.sh` の 6 行目の説明と、写しの段（設計 §3-4）
（５）`scripts/dev/test_doc_entry_weekly_check.sh` に T1 の1行・T-LC1・T-LC2（設計 §3-5。偽の HOME の routines.json は `{"version":1,"items":[{"name":"入口の文書 週次点検","promptText":"…18/20 以上（docs/specs/doc-agenda-nav/kgi.md の K12）…"}]}` の形）

## §2 触らないもの

§1 の5つと §5 の報告以外のすべて。特に: 線の値（210・7500・7.5k）・判定の式・ほかの段・`.github/workflows/` のほかのファイル・`required-checks.txt`・書類（kgi.md・要件・設計・このカード）。

## §3 合格の確かめ（Linux のクラウドで流す。生出力を報告に貼る）

（１）`python3 -I scripts/ci/check_kgi_line_copies.py --root . > /tmp/g1.txt 2>&1; echo "rc=$?" >> /tmp/g1.txt; cat /tmp/g1.txt` → `SUMMARY same=6 diff=0 missing=0`・`rc=0`
（２）`python3 -I scripts/tests/test_check_kgi_line_copies.py -v > /tmp/g2.txt 2>&1; echo "rc=$?" >> /tmp/g2.txt; tail -60 /tmp/g2.txt` → `OK`・`rc=0`
（３）`bash scripts/dev/test_doc_entry_weekly_check.sh > /tmp/g3.txt 2>&1; echo "rc=$?" >> /tmp/g3.txt; tail -60 /tmp/g3.txt` → FAIL の行が 0・`rc=0`・`PASS T1 LINE_COPY=skipped`・T-LC1 と T-LC2 の PASS
（４）ずれの実地（§1 の commit の後に行う）: 台本の 7 行目を一時的に `K1_LIMIT=200` に書き換えて（１）を流し、`COPY C1 expected=210 found=200 DIFF`・`rc=1` を貼る。そのあと `git checkout -- scripts/dev/doc-entry-weekly-check.sh` で戻し、`git status --short` が空であることを貼る（この書き換えは commit しない）
（５）`python3 -I scripts/ci/check_doc_index.py --root . --strict | tail -5` → 失敗しない（設計とカードは Opus が目次から届くようにしてある。失敗したら NEEDS_DECISION）
（６）`git diff --stat origin/main...HEAD` → §1 の5つ・報告 1 つと、Opus が先にコミット済みの書類（設計・このカード・k12-fix-design.md）だけ

## §4 止まる条件

- 1 段目（NEEDS_DECISION）: §0 の想定と違う。§3 が設計と違う形でないと通らない。週次点検の既存の試験が Linux で通らない（自分の変更の前から落ちるなら、そのことを生出力で示して止まる）。
- 2 段目（BLOCKED）: 見張り（フック）に止められた。言い換えて通そうとしない。止められた命令と文面をそのまま報告に書く。

## §5 報告

`docs/handoff/doc-library-one-tree/impl-report-line-copy-guard.md` に、§0 と §3 の生出力（要約しない）と commit の SHA を書く。最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` のどれか。

## §6 作業の決まり

- commit 文は Write でファイルに書いて `git commit -F <ファイル>` で流す。git は1命令ずつ流す。
- §1 の5つで1つの commit、報告で1つの commit にして、`git push origin release/kgi-line-copy-guard` する。
- sleep を使わない。
