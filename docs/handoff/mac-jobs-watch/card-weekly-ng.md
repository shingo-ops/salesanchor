# card: 週次点検の NG と未実行を見張り役で知らせる（クラウドの Sonnet 向け）

## カードチェック（design-partner.md §5.5）
| # | 項目 | 結果 |
|---|---|---|
| 0 | 冒頭に ○× | ○ |
| 1 | 記号を `` ` `` で囲む | ○ |
| 2 | PR | ○ 担当は PR を作らない。Opus が差分を読んでから作る |
| 3 | 報告先 | ○ 生出力入りの報告ファイル（§5） |
| 4 | 目的は 1 つ | ○ 週次点検の NG と未実行が Discord に届く |
| 5 | 土台のブランチ | ○ このカードがあるブランチ `release/weekly-check-ng-notify`（`origin/main` a7c5713c4 から作成済み） |
| 6 | 形は例で示す | ○ 設計 §3 に足すコードの全部、§4 に試験の表、§5 に CI の全文 |
| 7 | 合格基準に出力 | ○ §3 |
| 8 | 対象の名前 | ○ §1 の3ファイルと報告 1 つ |
| 9 | 出力の上限 | ○ tail -40 |
| 10 | 終わりの合図 | ○ 最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` |
| 11 | 想定値は実測 | ○ §0 の想定は 2026-11-05 の origin/main a7c5713c4 の実物 |
| 12 | 止まる条件 2 段 | ○ §4 |
| 13 | sleep なし・Edit の道具・見張りで止まったら言い換えない | ○ |

- 設計: [design-weekly-ng.md](design-weekly-ng.md)（§3〜§5 が作るものの全部。読んでから始める）。recon: [recon-weekly-ng.md](recon-weekly-ng.md)
- PO の承認: 2026-11-05 PO 原文「1,2を順番に実装」の 2。
- 作業ブランチ: `release/weekly-check-ng-notify`。このブランチにコミットして push する。main には触らない。
- 公開リポジトリ。個人の決まりの本文を書き写さない。本物の通知先・本物の結果ファイルはクラウドに無い。試験は偽物だけを使う。
- 見張り役の試験は macOS の `date -j` を使うので Linux のクラウドでは流せない。試験は Opus が PR を作った後の GitHub の macOS の CI（設計 §5）で確かめる。クラウドでは §3 の静的な確かめだけを行う。

## §0 着手前の点検（違えば NEEDS_DECISION で止まる。結果を報告に貼る）

| 確かめること | 想定 |
|---|---|
| `wc -l scripts/mac-jobs-watch.sh scripts/tests/test-mac-jobs-watch.sh` | `593` と `818` |
| `grep -n 'MJW_PHONE_GRACE:=\|^ST_PHONE=0\|^mjw_commit_events\|C_DKICK="\${ST_DKICK}"$\|^  mjw_phone_check$' scripts/mac-jobs-watch.sh` | 51・72・457・515・380 行目 |
| `grep -n '^echo "----"' scripts/tests/test-mac-jobs-watch.sh` | 816 行目 |
| `grep -rn 'weekly' scripts/mac-jobs-watch.sh scripts/tests/test-mac-jobs-watch.sh \| wc -l` | `0` |
| `ls .github/workflows/mac-jobs-watch-test.yml` | 無い |

## §1 作るもの・直すもの（Write と Edit の道具で）

（１）`scripts/mac-jobs-watch.sh`: 設計 §3-1〜§3-8 のとおり。コードは設計の通りに写す。変えたいところが出たら NEEDS_DECISION で止まる。
（２）`scripts/tests/test-mac-jobs-watch.sh`: 設計 §4 の W1〜W17 を、:815 の後・`echo "----"` の前に足す。既存の `setup`・`mk_state`・`stv`・`has_prob`・`ncalls`・偽の curl（`curl.stdin.N` に本文）をそのまま使う。weekly_seen は `mk_state` の後に `printf 'weekly_seen=%s\n' … >> "${D}/state/state"` で足す。各試験の最後に `unset MJW_WEEKLY_DIR` で戻す。1 行目〜:3 の説明に W1〜W17 を足す。
（３）新規 `.github/workflows/mac-jobs-watch-test.yml`: 設計 §5 の全文のとおり。

## §2 触らないもの

§1 の3つと §5 の報告以外のすべて。特に: 既存の試験の期待値・ほかの点検の判定・`mjw_send`・plist・`scripts/dev/doc-entry-weekly-check.sh`・`.github/workflows/` のほかのファイル・`required-checks.txt`・書類（設計・recon・このカード）。

## §3 合格の確かめ（Linux のクラウドで流す。生出力を報告に貼る）

（１）`bash -n scripts/mac-jobs-watch.sh; echo "rc=$?"` と `bash -n scripts/tests/test-mac-jobs-watch.sh; echo "rc=$?"` → どちらも `rc=0`
（２）`shellcheck` があれば `shellcheck scripts/mac-jobs-watch.sh scripts/tests/test-mac-jobs-watch.sh > /tmp/s.txt 2>&1; echo "rc=$?" >> /tmp/s.txt; tail -40 /tmp/s.txt`。変更の前（`git stash` は使わない。`git show origin/main:scripts/mac-jobs-watch.sh > /tmp/old.sh` で取り出して同じ命令）と比べ、増えた指摘が 0 件であること。shellcheck が無ければ「無い」と書く
（３）`python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/mac-jobs-watch-test.yml')); print('yaml ok')"`（yaml が無ければ `ruby -ryaml -e "YAML.load_file('.github/workflows/mac-jobs-watch-test.yml'); puts 'yaml ok'"`）→ `yaml ok`
（４）`grep -c 'W1[0-7]\? \|W[1-9] ' scripts/tests/test-mac-jobs-watch.sh` と、W1〜W17 のそれぞれの `eq`/`ok` の行の番号の一覧（`grep -n '"W[0-9]*-' scripts/tests/test-mac-jobs-watch.sh`）
（５）`git diff --stat origin/main...HEAD` → §1 の3つ・報告 1 つと、Opus が先にコミット済みの書類（設計・recon・このカード）だけ

## §4 止まる条件

- 1 段目（NEEDS_DECISION）: §0 の想定と違う。設計のコードのままでは書けない（行番号のずれ以外）。§3 の（１）〜（３）が通らない。
- 2 段目（BLOCKED）: 見張り（フック）に止められた。言い換えて通そうとしない。止められた命令と文面をそのまま報告に書く。

## §5 報告

`docs/handoff/mac-jobs-watch/impl-report-weekly-ng.md` に、§0 と §3 の生出力（要約しない）と commit の SHA を書く。最後の行は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` のどれか。

## §6 作業の決まり

- commit 文は Write でファイルに書いて `git commit -F <ファイル>` で流す。git は1命令ずつ流す。
- §1 の3つで1つの commit、報告で1つの commit にして、`git push origin release/weekly-check-ng-notify` する。
- sleep を使わない。
