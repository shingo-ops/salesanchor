# 合格の線の写しのずれを見つける見張り（ADR-1040・doc-library-one-tree）

- 状態: 設計案作成済み・設計審査済み（同じ AI による審査で、独立した第二者の審査ではない。§10）
- PO の承認: 2026-11-05 PO 原文「1,2を順番に実装」。1 は [k12-fix-design.md](k12-fix-design.md) §17 の「範囲外で見つかった足りない仕組み」のうち「合格の線の写しのずれを見つける見張りが無い」「週次点検の試験が CI に入っていない」を指す。
- 実装カード: [card-line-copy-guard.md](card-line-copy-guard.md)

## 1. 目的と、利用者に見える変化

- 目的: 合格の線（kgi.md の K1・K9・K12）を変えたのに写しを直し忘れたとき、PR の段階で赤が出て止まる。定期実行の指示書の写しも週次点検で見つかる。
- 変更前: 線を変えた PR でも写しの直し忘れは CI で見つからない。§15（K9）・§17（K1）で2回、審査役か人が見つけた。定期実行の指示書の「10/20」の直し忘れも [design.md](design.md) 209 行目に記録がある。
- 変更後: 写しが1つでも正本と違うと、新しい CI「kgi line copies」が赤になる。AI のマージは赤の確かめがあると見張りが止める（merge_red_check_guard、既存）。定期実行の指示書のずれは週次点検の結果に `LINE_COPY=DIFF` と `RESULT=NG` が出る。

## 2. 現在地（2026-11-05 origin/main a7c5713c4 の実物）

| 写し | 場所（行） | 今の値 | 正本（kgi.md） |
|---|---|---|---|
| C1 週次点検の K1 の線 | `scripts/dev/doc-entry-weekly-check.sh:7` `K1_LIMIT=210` | 210 | K1「**210行以下**」（`docs/specs/doc-agenda-nav/kgi.md:28` の4つ目の欄） |
| C2 週次点検の K9 の線 | 同 `:8` `K9_LIMIT_TOKENS=7500` | 7500 | K9「7.5k 以下」（同 `:36`）×1000 |
| C3 週次点検の K9 の NG の文字 | 同 `:89` `add_ng "K9>7.5k"` | 7.5 | K9 |
| C4a 要件 L1 の K9 | `docs/handoff/doc-agenda-nav/library-requirements.md:12` 「K9 ≤ ~~6.5k~~ **7.5k**」 | 7.5（取り消し線を除く） | K9 |
| C4b 要件 L1 の K1 | 同 `:12` 「K1 ≤ ~~200~~ **210**」 | 210 | K1 |
| C5 週次点検の試験の K1 | `scripts/dev/test_doc_entry_weekly_check.sh:95` `K1>210`（2か所） | 210 | K1 |
| C6 定期実行「入口の文書 週次点検」の指示書 | agent-console の routines.json（リポジトリの外・Mac の中）。`items[].name` が「入口の文書 週次点検」の `promptText` に「18/20 以上（docs/specs/doc-agenda-nav/kgi.md の K12）」 | 18 | K12「**18/20 以上**」（同 `:39`） |

- 週次点検の台本の 6 行目の説明は「合格線の正本はここ1か所（kgi.md の写し）」で、正本が2か所あるように読める。
- 週次点検の試験 `scripts/dev/test_doc_entry_weekly_check.sh` を流す CI は無い（`.github/workflows/` に名前が出てこない）。
- 試験の偽のリポジトリには kgi.md が無い（同 `:31-77` の setup）。
- 6.5k・200 などの古い線は、経緯の記録（design.md・card-*.md・impl-report-*.md・library-*.md など）に残っている。その時点の記録なので見張りの対象にしない。

## 3. 作るもの（変更後）

### 3-1. 見張りの台本 `scripts/ci/check_kgi_line_copies.py`（新規・標準ライブラリのみ）

- 呼び方: `python3 -I scripts/ci/check_kgi_line_copies.py --root <リポジトリ> [--routines <routines.json のパス>]`
- 正本の読み方: kgi.md の行のうち `| K1 |`・`| K9 |`・`| K12 |` で始まる行を `|` で区切り、4つ目の欄（合格ライン）だけを読む。
  - K1 = 最初の `(\d+)行以下`
  - K9 = 最初の `(\d+(?:\.\d+)?)k 以下`
  - K12 = 最初の `(\d+)/20 以上`
  - 1つでも読めなければ `BASE <K名> unreadable` を出して終了コード 2。
- 写しの一覧はこの台本の中の1か所だけに書く（§2 の C1〜C6）。読み方:
  - C1: 週次点検の台本で `^K1_LIMIT=(\d+)$` に当たる行。期待 = K1
  - C2: 同 `^K9_LIMIT_TOKENS=(\d+)$`。期待 = K9×1000（整数）
  - C3: 同 `K9>(\d+(?:\.\d+)?)k` のすべて。期待 = K9
  - C4a・C4b: 要件の `| L1 ` で始まる行から `~~…~~` を消したあと、`K9 ≤\s*\*\*(\d+(?:\.\d+)?)k\*\*` と `K1 ≤\s*\*\*(\d+)\*\*`。期待 = K9・K1
  - C5: 週次点検の試験の `K1>(\d+)` のすべて。期待 = K1
  - C6（`--routines` のときだけ）: JSON の `items` のうち `name` が「入口の文書 週次点検」の `promptText` の `(\d+)/20 以上（docs/specs/doc-agenda-nav/kgi.md の K12）` のすべて。期待 = K12。ファイルが無い・JSON が読めない・その名前が無い・当たりが0件は MISSING。
- 出力（1行ずつ）: `BASE K1=<値> K9=<値> K12=<値>`、写しごとに `COPY <名前> expected=<値> found=<値をカンマ区切り> SAME|DIFF|MISSING`、最後に `SUMMARY same=<数> diff=<数> missing=<数>`。
- 当たりが0件は MISSING。1件でも期待と違えば DIFF。数は小数として比べる（7.5 と 7.50 は同じ）。
- 終了コード: すべて SAME なら 0、DIFF か MISSING が1つでもあれば 1、正本が読めない・引数が違うときは 2。
- 指示書の本文（promptText）は出力しない。出すのは取り出した数だけ。

### 3-2. 試験 `scripts/tests/test_check_kgi_line_copies.py`（新規・unittest・一時フォルダで完結）

- 正本と写しがそろった偽のリポジトリで終了コード 0・`SUMMARY same=6 diff=0 missing=0`
- C1〜C5 をそれぞれ1つずつずらすと、その名前が DIFF・終了コード 1
- 台本から `K1_LIMIT=` の行を消すと C1 が MISSING・終了コード 1
- 要件の取り消し線の中の古い値（~~200~~）は読まない
- `--routines`: 18/20 で C6 SAME、10/20 で C6 DIFF、ファイル無し・名前違いで C6 MISSING。promptText に入れた目印の文字が出力に出ない
- kgi.md の K9 の行が無いと終了コード 2・`BASE K9 unreadable`
- 本物のリポジトリ（`--root` に試験のファイルから2つ上）で終了コード 0

### 3-3. CI `.github/workflows/kgi-line-copies.yml`（新規）

- 動く時: main への pull_request と、main への push。paths を付けない（doc-index-reachability.yml と同じ理由で常に動かす）。
- ubuntu-latest・timeout-minutes 5・`actions/checkout@v5`・`actions/setup-python@v5`（3.12）。doc-index-reachability.yml と同じ書き方。
- 手順: （１）`python3 -I scripts/tests/test_check_kgi_line_copies.py -v`（２）`python3 -I scripts/ci/check_kgi_line_copies.py --root .`（結果の SUMMARY を `$GITHUB_STEP_SUMMARY` に書く）（３）`bash scripts/dev/test_doc_entry_weekly_check.sh`（週次点検の試験を CI に入れる）
- 必須の確かめには登録しない（登録は Ruleset の変更で、このセッションでは禁止）。赤のときに AI のマージが止まるのは既存の見張り（merge_red_check_guard）で働く。

### 3-4. 週次点検の台本 `scripts/dev/doc-entry-weekly-check.sh` の変更

- 6 行目の説明（変更前 → 変更後）:
  - `# 合格線の正本はここ1か所（docs/specs/doc-agenda-nav/kgi.md の写し）`
  - → `# 合格線の正本は docs/specs/doc-agenda-nav/kgi.md。下の値はその写しで、ずれは scripts/ci/check_kgi_line_copies.py が見つける`
- `# ---- PEER ----` の段の後、`if [ -z "$NG" ]` の前に、写しの段を足す:
  - 調べる先のリポジトリに kgi.md（`docs/specs/doc-agenda-nav/kgi.md`）があれば `python3 -I "$SELF_DIR/../ci/check_kgi_line_copies.py" --root "$REPO" --routines "${DOC_ENTRY_ROUTINES:-$HOME_DIR/Library/Application Support/agent-console/routines.json}"` を流す。出力は捨てない（そのまま結果ファイルに残る）。
  - 終了コード 0 → `LINE_COPY=SAME`、1 → `LINE_COPY=DIFF` と `add_ng "LINE_COPY=DIFF"`、それ以外 → `LINE_COPY=error` と `add_ng "LINE_COPY=error"`
  - kgi.md が無ければ `LINE_COPY=skipped`（NG にしない）
- ほかの段・判定・線の値は変えない。

### 3-5. 週次点検の試験 `scripts/dev/test_doc_entry_weekly_check.sh` の追加

- T1 に `check "T1 LINE_COPY=skipped" has LINE_COPY=skipped`
- T-LC1: setup の後、偽のリポジトリに本物の kgi.md・要件・週次点検の台本・週次点検の試験を同じ相対パスで写し、偽の HOME に `Library/Application Support/agent-console/routines.json`（「入口の文書 週次点検」・`18/20 以上（docs/specs/doc-agenda-nav/kgi.md の K12）` を含む）を置く → `LINE_COPY=SAME`・`RESULT=OK`
- T-LC2: 同じで指示書を 10/20 にする → `LINE_COPY=DIFF`・`RESULT=NG` に `LINE_COPY=DIFF`・rc=1

## 4. 触らないもの

- 線の値そのもの（K1 210・K9 7.5k・K12 18/20）と、判定の式。
- 経緯の記録の古い値。
- agent-console・routines.json の中身（読むだけ）・フック・settings・permits・Ruleset・必須の確かめの一覧（`required-checks.txt`）。
- 本番・DB・deploy。

## 5. 代わりの案と選ばなかった理由

- 線を1つのファイル（例: JSON）に置き、台本も書類もそこから読む: 書類（kgi.md・要件）は人が読む文で、数だけを外に出すと読みにくくなる。指示書はリポジトリの外にあり、そこから読ませられない。写しを残して見張りで止めるほうが変更が小さい。
- 古い値（6.5k・200）が文書のどこかにあれば止める: 経緯の記録（その時点の正しい記録）まで止まる。
- 必須の確かめに登録する: Ruleset の変更で、このセッションでは禁止。赤のときは既存の見張りが AI のマージを止める。

## 6. 危ないことと対処

- 正本の書き方が変わり読めなくなる → 終了コード 2 で赤になり、気づける（黙って通らない）。
- 指示書の言い回しが変わり当たりが0件になる → MISSING で週次点検が NG になる。PO の確認が要る形で止まる（黙って通らない）。
- 週次点検の試験が Linux で通らない → 実装の担当がクラウド（Linux）で流して確かめる。通らなければ NEEDS_DECISION で止まる。
- 新しい CI が全 PR で動く → 標準ライブラリの短い台本で数秒。

## 7. 戻し方

この PR を revert する（新しい3ファイルが消え、台本と試験が元に戻る）。

## 8. 合格の確かめ方

| 基準 | 検証方法 |
|---|---|
| 今の本線で写しがそろっている | `python3 -I scripts/ci/check_kgi_line_copies.py --root .` が `SUMMARY same=6 diff=0 missing=0`・終了コード 0 |
| ずれると止まる | 試験 `python3 -I scripts/tests/test_check_kgi_line_copies.py -v` が FAIL 0（C1〜C6 のずれ・MISSING・正本読めずの各試験を含む） |
| 指示書の本文を出さない | 同じ試験の目印の文字の試験が PASS |
| 週次点検の試験が通る | `bash scripts/dev/test_doc_entry_weekly_check.sh` が FAIL 0・終了コード 0（T1 の LINE_COPY=skipped・T-LC1・T-LC2 を含む） |
| PR で動く | この PR の確かめに「kgi line copies」が出て success |
| マージ後に本線で動く | マージの後の main への push で同じ確かめが success |
| Mac の本物の指示書がそろっている | マージ後の origin/main の使い捨ての写しで `python3 -I scripts/ci/check_kgi_line_copies.py --root . --routines "$HOME/Library/Application Support/agent-console/routines.json"` が `same=7`・終了コード 0 |

## 9. 外部・過去事例の参照と我々への応用

- 数値つきの外部事例は使わない。理由: 直接の根拠は社内の再発（§15 K9・§17 K1・design.md 209 行目の指示書 10/20）で、3回とも「線を変えた PR で写しを直し忘れた」同じ形。外部の数で効果を証明する必要が無い。
- 過去事例: 同じ題の `scripts/ci/check_doc_index.py`（目次から届かない文書を CI で止める）と同じ形（標準ライブラリ・`--root`・SUMMARY 行・常に動く CI）にそろえる。

## 維持の仕組み

- 守り手: CI「kgi line copies」（`.github/workflows/kgi-line-copies.yml`。全 PR と main への push）と、毎週月曜 16:00 の週次点検（`scripts/dev/doc-entry-weekly-check.sh`。指示書の写し C6）。
- 新しい写しを足すとき: この台本の写しの一覧（§3-1）に1件足し、試験も1つ足す。一覧はこの台本の中の1か所だけ。
- 項目2（週次点検の NG を Discord に知らせる）がマージされると、`LINE_COPY=DIFF` の NG も Discord に届く。

## 10. 審査（同じ AI による審査で、独立した第二者の審査ではない）

- 判定: APPROVE
- 確かめたこと: §2 の行番号と値は作業場所（origin/main a7c5713c4）で grep・python で読んで確かめた。routines.json は形（`version`・`items[].name`・`items[].promptText`）と当たりの数だけを読み、本文は出していない。当たりは「入口の文書 週次点検」の 18 の1件。
- 受入条件はすべてコマンドの出力で ○× が付く。
- 未確認: 週次点検の試験が Linux（ubuntu）で通るか。実装の担当がクラウドで流して確かめる（カード §3）。
- 未解決の事業判断: なし。
