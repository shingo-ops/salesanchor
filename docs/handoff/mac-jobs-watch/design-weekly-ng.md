# 追補: 入口の文書の週次点検の NG を Discord で知らせる（weekly-ng・weekly-missing）

- 状態: 設計案作成済み・設計審査済み（同じ AI による自己審査。独立した第二者審査ではない）・PO 承認済み（下の起点）・実装未着手
- 起点: 2026-11-05 PO 原文「1,2を順番に実装」の 2。2 は Opus が示した「週次点検で NG が出たら Discord に知らせる」
- 関連: [recon 追補](recon-weekly-ng.md)、本テーマの [design.md](design.md)・[design-disk-low.md](design-disk-low.md)、ADR-1040（週次点検の定義 docs/adr/ADR-1040-doc-agenda-nav-entry-index.md:58）、ADR-1009（通知先 webhook を共有）、[k12-fix-design.md §17](../doc-library-one-tree/k12-fix-design.md)（「NG の知らせが作業画面に残るだけ」の記録）

## 1. 目的と KGI

毎週月曜 16:00 の週次点検は、NG でも結果をファイルに書いて作業画面に残すだけだった。11/02 の NG（K1>200 K9>6.5k）は、人が画面を見るまで誰も知らなかった。
NG が出たら Discord に 1 通届くようにする。点検そのものが動かなかったときも黙らないようにする（NG が出ない＝合格、と取り違えないため）。

| ID | 基準（○×で判定） | 検証方法 |
|---|---|---|
| W1 | 新しい結果ファイル（`YYYYMMDD.txt`）に `RESULT=NG …` が書かれたら、次の見張りの回（30 分以内）に Discord に 1 通届く。本文に点検日と NG の項目が入る | 試験 W1・設置後の本物の通知先での試し（§8） |
| W2 | 同じ結果ファイルは 2 回知らせない。`RESULT=OK` は知らせない | 試験 W2・W3 |
| W3 | 設置した直後に、すでにある 11/02 の NG を知らせない | 試験 W4・W5・設置後のログ |
| W4 | 月曜 16:00 から 2 時間たっても、その日の結果ファイルが無いか `RESULT=` 行が無ければ 1 通届く。出たら「直りました」が 1 通届く。続く間は 24 時間に 1 回まで | 試験 W8〜W10・W15 |
| W5 | 送るのに失敗したら、次の回に送り直す（取りこぼさない） | 試験 W7 |
| W6 | NG の項目は英数字と `_ . : > = / -`・空白だけを 200 字まで載せる（`@` や `<` を載せない） | 試験 W13 |
| W7 | 既存の試験がすべて通り、GitHub の macOS の機械で毎回流れる | 新しい CI「mac jobs watch test」が緑・`PASS=… FAIL=0` |
| W8 | 通知先の URL がログに出ない（既存 K5 と同じ） | 設置後の K5 と同じ検索で 0 行 |

## 2. 現在地（recon 追補の要約）

- 週次点検の結果は `~/CC報告ファイル-keep/doc-entry-weekly/YYYYMMDD.txt`。11 行目が `RESULT=OK` か `RESULT=NG <項目…>`。名前に `-trial` などが付いた試しのファイルが同じ場所にある。
- 見張り役（scripts/mac-jobs-watch.sh）は 30 分ごとに動き、状態型（続く問題。24h 再通知・復旧つき）と出来事型（1 回だけ知らせる）の 2 つの形を持つ。
- 見張り役の試験は macOS でしか動かず、CI で流れていない。

## 3. 変更内容（scripts/mac-jobs-watch.sh）

2 つの名前を足す。
- `weekly-ng`: 出来事型。新しい結果ファイルが NG なら 1 回だけ知らせる。復旧は無い（次の週の OK で済む）。
- `weekly-missing`: 状態型。締め切りを過ぎても結果が無い間、続く問題として扱う。

### 3-1 設定（mjw_config の :51 `MJW_PHONE_GRACE` の次に 3 行）
```bash
  : "${MJW_WEEKLY_DIR:=${home_dir}/CC報告ファイル-keep/doc-entry-weekly}"
  : "${MJW_WEEKLY_HOUR:=16}"
  : "${MJW_WEEKLY_GRACE:=7200}"
```
曜日は月曜に固定する（定期実行の指示書が月曜。変えるときは本書と一緒に変える）。

### 3-2 変数（:72 `ST_PHONE=0` などの並びに足す）
```bash
ST_WSEEN=0     # 知らせ済みの最新の結果ファイルの日付（YYYYMMDD）
WK_INIT=0      # 状態ファイルに weekly_seen が無い（設置直後）
C_WSEEN=0
N_WSEEN=0
WK_NEWEST=0    # RESULT= 行がある日付ファイルの最新（YYYYMMDD。無ければ 0）
WK_ISNG=0
WK_NG=""
WK_EXPECT=0    # 締め切りを過ぎた直近の月曜（YYYYMMDD）
WEEKLY_JUDGED=0
```

### 3-3 状態の読み書き
- mjw_read_state の状態ファイルがある側（:240-247）に:
```bash
    WK_RAW="$(mjw_st_get weekly_seen)"
    if [ -z "${WK_RAW}" ]; then WK_INIT=1; else WK_INIT=0; fi
    ST_WSEEN="$(mjw_num "${WK_RAW}")"
```
- 無い側（:249-257）に `ST_WSEEN=0`。
- mjw_write_state（:263-271）に `printf 'weekly_seen=%s\n' "${C_WSEEN}"`。
- mjw_commit_events（:457）に `C_WSEEN="${N_WSEEN}"`。
- mjw_main の :515 の行の末尾に `C_WSEEN="${ST_WSEEN}"` を足す（detect_events の後で読む。detect_events が設置直後の基準を ST_WSEEN に入れるため）。

### 3-4 読む関数（新設・mjw_disk_parse の後）
```bash
mjw_weekly_parse() { # WK_NEWEST / WK_ISNG / WK_NG。置き場が無ければ WEEKLY_JUDGED=0
  local f b line
  WK_NEWEST=0; WK_ISNG=0; WK_NG=""; WEEKLY_JUDGED=0
  [ -d "${MJW_WEEKLY_DIR}" ] || return 0
  WEEKLY_JUDGED=1
  while IFS= read -r b; do
    [ -n "${b}" ] || continue
    f="${MJW_WEEKLY_DIR}/${b}"
    line="$(grep '^RESULT=' "${f}" 2>/dev/null | tail -1)"
    [ -n "${line}" ] || continue
    WK_NEWEST="${b%.txt}"
    case "${line}" in
      RESULT=NG*)
        WK_ISNG=1
        WK_NG="$(printf '%s' "${line#RESULT=NG}" | LC_ALL=C tr -cd 'A-Za-z0-9_.:>=/ -' | cut -c1-200)"
        WK_NG="${WK_NG# }"
        [ -n "${WK_NG}" ] || WK_NG="-" ;;
    esac
    break
  done < <(ls -1 "${MJW_WEEKLY_DIR}" 2>/dev/null | grep -E '^[0-9]{8}\.txt$' | sort -r)
}

mjw_weekly_expect() { # WK_EXPECT: 「16:00＋猶予」を過ぎた直近の月曜。計算できなければ WEEKLY_JUDGED=0
  local u mid day
  WK_EXPECT=0
  u="$(mjw_num "$(date -j -r "${NOW}" +%u 2>/dev/null)")"
  mid="$(mjw_num "$(date -j -r "${NOW}" -v0H -v0M -v0S +%s 2>/dev/null)")"
  if [ "${u}" -lt 1 ] || [ "${mid}" -eq 0 ]; then WEEKLY_JUDGED=0; return 0; fi
  day=$(( mid - (u - 1) * 86400 ))
  if [ $(( day + MJW_WEEKLY_HOUR * 3600 + MJW_WEEKLY_GRACE )) -gt "${NOW}" ]; then day=$(( day - 7 * 86400 )); fi
  WK_EXPECT="$(mjw_num "$(date -j -r "${day}" +%Y%m%d 2>/dev/null)")"
  if [ "${WK_EXPECT}" -eq 0 ]; then WEEKLY_JUDGED=0; fi
}
```
- `RESULT=` 行がまだ無い結果ファイル（点検の途中）は飛ばす。その日は「まだ出ていない」扱い。
- 一番新しい 1 つだけを見る（何週か溜まっても知らせは 1 通）。

### 3-5 状態型の判定（mjw_detect_states の末尾 :380 `mjw_phone_check` の後）
```bash
  # weekly-missing（月曜 16:00＋猶予を過ぎても、その日の結果が無い。design-weekly-ng §3-5）
  mjw_weekly_parse
  mjw_weekly_expect
  if [ "${WEEKLY_JUDGED}" -eq 1 ] && [ "${WK_NEWEST}" -lt "${WK_EXPECT}" ]; then list_add DETECTED weekly-missing; fi
```
- mjw_judged の case に `weekly-missing) [ "${WEEKLY_JUDGED}" -eq 1 ] ;;`（置き場が無い回・日付が計算できない回は復旧も出さない）。

### 3-6 出来事型の判定（mjw_detect_events）
:405 `N_ERR="${ST_ERR}"` の次、:406 の FIRST の判定より前に:
```bash
  N_WSEEN="${ST_WSEEN}"
  if [ "${FIRST}" -eq 1 ] || [ "${WK_INIT}" -eq 1 ]; then ST_WSEEN="${WK_NEWEST}"; N_WSEEN="${WK_NEWEST}"; fi
```
:435 の dj-err の判定の後（関数の最後）に:
```bash
  if [ "${WK_NEWEST}" -gt "${ST_WSEEN}" ]; then
    N_WSEEN="${WK_NEWEST}"
    if [ "${WK_ISNG}" -eq 1 ]; then list_add EV_LIST weekly-ng; fi
  fi
```
- 設置直後（状態ファイルに weekly_seen が無い）と初回は、今ある最新を「知らせ済み」として基準にする。だから 11/02 の NG は送らない（W3）。
- 置き場が一時的に読めない回は WK_NEWEST=0 なので、既読位置は戻らない。
- 送るのに失敗した回は既存の流れ（:551-559）で既読位置を進めないので、次の回に送り直す（W5）。

### 3-7 固定文（mjw_text の case に追加）
```bash
    weekly-ng) printf '入口の文書の週次点検（%s）が NG でした（%s）。結果: %s.txt' "$(mjw_ymd "${WK_NEWEST}")" "${WK_NG}" "${WK_NEWEST}" ;;
    weekly-missing) printf '入口の文書の週次点検（毎週月曜 %s:00）の結果が、%s 時間たっても出ていません（%s の分）' "${MJW_WEEKLY_HOUR}" "$(( MJW_WEEKLY_GRACE / 3600 ))" "$(mjw_ymd "${WK_EXPECT}")" ;;
```
共通の小さな関数（mjw_num の次）:
```bash
mjw_ymd() { local v="${1:-}"; case "${v}" in [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) printf '%s-%s-%s' "${v:0:4}" "${v:4:2}" "${v:6:2}" ;; *) printf '%s' "${v}" ;; esac; }
```

### 3-8 先頭の説明
:2・:5 の説明に「入口の文書の週次点検の NG と未実行」を足す。

### 触らない範囲
- 週次点検の台本（scripts/dev/doc-entry-weekly-check.sh）・定期実行の指示書（agent-console）・通知先・送信関数 `mjw_send`・ロック・ログの書式・plist・他の点検名とその判定。
- 結果ファイルを書き換えたり消したりしない（読むだけ）。

## 4. 試験（scripts/tests/test-mac-jobs-watch.sh の末尾 :815 の後、`echo "----"` の前）

置き場は `${D}/weekly`（`export MJW_WEEKLY_DIR="${D}/weekly"`）。既存の setup には足さない（置き場が無い＝判定しないので、既存の試験は影響を受けない）。基準の時刻は 2026-11-09（月）19:00。

| 番号 | 条件 | 期待 |
|---|---|---|
| W1 | weekly_seen=20261102・`20261109.txt` に `RESULT=NG K1>210` | 送信 1・本文に「入口の文書の週次点検（2026-11-09）が NG でした（K1>210）」・weekly_seen=20261109・ログ `result=alert send=ok` と `events=weekly-ng` |
| W2 | W1 の 30 分後 | 送信 0 |
| W3 | weekly_seen=20261102・`20261109.txt` が `RESULT=OK` | 送信 0・weekly_seen=20261109 |
| W4 | 状態ファイルに weekly_seen が無い（設置直後）・`20261102.txt` が NG・11/05 12:00 | 送信 0・weekly_seen=20261102 |
| W5 | 状態ファイルが無い（初回）・`20261102.txt` が NG | 送った本文のどれにも「週次点検」が無い・weekly_seen=20261102 |
| W6 | weekly_seen=20261102・`20261102.txt`（`RESULT=OK`）がある・`20261109.txt` に `RESULT=` 行が無い・16:30 → 行を足して 30 分後（`20261102.txt` が無いと 16:30 の時点で 11/02 の分の weekly-missing が正しく出るので、前の週の結果を置く。2026-11-05 PR #5154 の macOS の CI で W6-1 実際=1 を見て追記） | 1 回目は送信 0・weekly_seen=20261102。2 回目は送信 1（NG） |
| W7 | W1 と同じで送信失敗（curl.rc=1）→ 次の回は成功 | 1 回目 weekly_seen=20261102。2 回目に送信され weekly_seen=20261109 |
| W8 | weekly_seen=20261102・`20261102.txt` だけ・18:30 | 送信 1・本文に「結果が、2 時間たっても出ていません（2026-11-09 の分）」・problems に weekly-missing |
| W9 | W8 と同じで 17:30（締め切り前） | 送信 0・problems に weekly-missing が無い |
| W10 | W8 の後に `20261109.txt`（`RESULT=OK`）が出た・19:00 | 「直りました」が 1 通・problems から weekly-missing が消える・weekly-ng は無い |
| W11 | W8 の後に `20261109.txt`（`RESULT=NG K9>7.5k`）が出た | 送信 2（NG の知らせと「直りました」） |
| W12 | 置き場が無い・月曜 19:00 | weekly-missing を出さない |
| W13 | `RESULT=NG K1>210 <@everyone> \`x\`` | 本文に `@`・`<`・バッククォートが無い・`K1>210` はある |
| W14 | dry-run で W1 と同じ | 送信 0・状態ファイルが変わらない・ログ `result=dry-run` と `events=weekly-ng` |
| W15 | W8 の 25 時間後（火曜 19:30）もまだ無い | 「まだ続いています」が 1 通 |
| W16 | 日曜 2026-11-08 12:00・`20261102.txt` だけ | 送信 0（締め切りは 11/02 の分で、それはある） |
| W17 | `20261109-trial.txt` に NG・`20261109.txt` は無い・19:00 | weekly-ng を出さない（試しのファイルは読まない）・weekly-missing は出る |

## 5. CI（新規 `.github/workflows/mac-jobs-watch-test.yml`）

```yaml
name: Mac Jobs Watch Test
# scripts/mac-jobs-watch.sh の試験を GitHub の macOS の機械で流す（PO の Mac では流さない）。設計: docs/handoff/mac-jobs-watch/design-weekly-ng.md §5
on:
  pull_request:
    branches: [main]
    paths:
      - 'scripts/mac-jobs-watch.sh'
      - 'scripts/tests/test-mac-jobs-watch.sh'
      - 'scripts/dev/phone-serial.sh'
      - '.github/workflows/mac-jobs-watch-test.yml'
  push:
    branches: [main]
    paths:
      - 'scripts/mac-jobs-watch.sh'
      - 'scripts/tests/test-mac-jobs-watch.sh'
      - 'scripts/dev/phone-serial.sh'
      - '.github/workflows/mac-jobs-watch-test.yml'
permissions:
  contents: read
jobs:
  test:
    name: mac jobs watch test
    runs-on: macos-latest
    timeout-minutes: 10
    env:
      TZ: Asia/Tokyo
    steps:
      - uses: actions/checkout@v5
        with:
          persist-credentials: false
      - name: Run test
        run: /bin/bash scripts/tests/test-mac-jobs-watch.sh
```
- 必須チェックには登録しない（Ruleset に触れない）。
- `[self-hosted, macOS]` は使わない（PO の Mac で回さない決まり）。
- 既存の試験が GitHub の macOS の機械で通るかは、まだ確かめていない。最初の PR の CI で確かめる。通らない試験があれば、原因の生のログを報告して止まる（推測で試験を消したり緩めたりしない）。

## 6. 代替案と選択理由

| 案 | 採否 | 理由 |
|---|---|---|
| A. 見張り役に 2 つの名前を足す | 採用 | 送信・失敗時の送り直し・24h 再通知・復旧・URL を出さない作りが既にある。点検が動かなかったことも見つけられる |
| B. 週次点検の台本から Discord に送る | 不採用 | 送る仕組みを 2 つにすると通知先の読み方が分かれる（SSOT が崩れる）。点検が動かなかったときは台本自体が動かないので知らせられない |
| C. 定期実行の指示書に「NG なら Discord へ」と書く | 不採用 | agent-console の変更はこの作業の範囲外（PO の禁止）。AI が指示を読み落とすと知らせが出ない |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 設置した瞬間に古い NG が届く | 設置直後と初回は今ある最新を基準にする（W3・試験 W4・W5） |
| 点検の途中（RESULT 行が出る前）に読んで取りこぼす | RESULT 行が無いファイルは飛ばし、既読位置を進めない（W6） |
| 試しのファイルで誤って知らせる | 名前が日付 8 桁＋`.txt` のものだけ読む（W17） |
| NG の文に Discord の呼び出し（@everyone）が混ざる | 載せる文字を絞る（W6・W13） |
| Mac が月曜 16:00 に眠っていて、点検が後で動く | 18:00 を過ぎても無ければ知らせ、出たら「直りました」。眠っていた事実を知らせるのは正しい |
| 試験が GitHub の macOS の機械で落ちる | §5 のとおり生のログで止まる |

## 8. 設置と確かめ（マージの後）

1. 道具のコピー `~/.salesanchor-tools` を origin/main に合わせる（次の 04:00 の自動更新を待つか、Opus が `git -C ~/.salesanchor-tools fetch` の後に origin/main を detached で取り出す。どちらも plist の「origin/main の祖先で、変更が無いこと」の確かめを満たす）。
2. 本物の Mac で `bash ~/.salesanchor-tools/scripts/mac-jobs-watch.sh --dry-run` → ログに `result=dry-run` で、weekly-ng・weekly-missing が出ない（11/02 の結果がある・今日は 11/05）。
3. 次の本番の回のログで `result=ok`、状態ファイルに `weekly_seen=20261102`（W3）。
4. 本物の通知先での試し: 状態・ログ・ロック・置き場をすべて一時フォルダに向け（`MJW_STATE_DIR`・`MJW_LOG`・`MJW_LOCK_DIR`・`MJW_WEEKLY_DIR`）、`weekly_seen=20261102` の状態と、`RESULT=NG 試験` 相当の結果ファイル（中身は `RESULT=NG TEST-ONLY`）を置いて 1 回動かす → ログに `result=alert send=ok` と `events=weekly-ng`。本物の状態・ログ・置き場には触れない。
5. W8（URL がログに出ない）を既存 K5 と同じ方法で数える。
6. 2026-11-09（月）16:00 の本物の点検の後、見張りのログで weekly-ng・weekly-missing が出ていないこと（OK のはず）を確かめる。

## 9. 戻し方・測り方
- 戻し方: 本 PR の revert。道具のコピーは origin/main から動くので、次の 04:00 から元に戻る。状態ファイルに残る `weekly_seen=` の行は元の台本が読まないので害は無い。
- 測り方: §1 の表。以後は毎週月曜の点検の後、見張りのログで weekly-ng・weekly-missing の件数を見る。

## 維持の仕組み
- 守り手: Mac の見張り役（launchd が 30 分ごとに動かす）と、新しい CI「mac jobs watch test」（`.github/workflows/mac-jobs-watch-test.yml`。見張り役の台本・試験・スマホの道具を変える PR と main への push で毎回流れる）。
- 仕組み: 試験 `scripts/tests/test-mac-jobs-watch.sh`（W1〜W17）が判定の形を守る。見張り役のログに毎回 1 行残る。台本は毎日 04:00 に origin/main へ更新される写し ~/.salesanchor-tools から動く。
- 決まりの正本: 締め切り（16:00＋2 時間）は mjw_config の既定値。点検の曜日・時刻を変えるときは、定期実行の指示書と本書 §3-1 を一緒に変える。

## 外部・過去事例の参照と我々への応用
- 外部事例: 直接の根拠になる外部事例は使わない（「点検の結果を通知する仕組み」の効果を数字で示した、出典つきの事例を確かめていない）。
- 過去事例（社内）: 11/02 の週次点検は NG だったが、作業画面に残っただけで、人が見たのは後だった（docs/handoff/doc-library-one-tree/k12-fix-design.md §17 の「NG の知らせが作業画面に残るだけ」）。同じ見張り役の disk-low・phone-missing は、知らせが届いて PO が直せた（kgi.md P2 の 2026-11-02 の試し）。応用: 新しく送る仕組みを作らず、届くことが確かめられている見張り役に乗せる。

## 10. 設計審査（Architect・同じ AI による自己審査）
- 判定: APPROVE
- 根拠:
  - 出来事型は既存の dj-err（:429-435）と同じ形（既読位置 N_→C_、送れたときだけ commit :555）。状態型は phone-missing（:383-398 と :190）と同じ形。
  - 共通の送信・再通知・復旧（:439-455、:551-582）を変えない。
  - mk_state（試験 :107-112）は weekly_seen を書かないが、置き場が無いので判定しない。既存の試験の期待は変わらない。
  - 初回（FIRST）は :516 で commit されるので、N_WSEEN＝最新が状態に入る。設置直後（WK_INIT）は ST_WSEEN 自体を最新にするので、他の出来事の送信に失敗して commit されない回でも、:515 で C_WSEEN＝最新になる。だから古い NG が次の回に送られることは無い。
- 未確認: 既存の試験が GitHub の macOS の機械で通るか（§5。CI で確かめる）。
- 未解決: なし。
