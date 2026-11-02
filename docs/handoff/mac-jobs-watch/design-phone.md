# 設計: 実機スマホが Mac から見えなくなったら知らせる（phone-missing）

この文書は何か(専門用語なしの1行): PO が何もしなくても実機のスマホで確かめられる状態を保つため、AI の道具がスマホを名前で探すようにし、見えなくなったら Discord で知らせる設計。

親: [README](../../specs/mac-jobs-watch/README.md)／調べた事実: [docs/handoff/mac-jobs-watch/recon-phone.md](./recon-phone.md)／元の設計: [design.md](./design.md)

対象 ADR: ADR-1009（通知先 webhook を見張り役と共有・読むだけ）、ADR-1015（区分 A。元の設計 design.md と同じ）。スマホとのつなぎ方を決めた ADR は無い（recon-phone.md §1）。

状態: 設計案作成済み・設計審査済み（§8）。PO 承認 2026-11-02 チャット「1」（AI の選択肢「1. この3つで進める」に対して）。

## 1. 目的と合格条件

PO の言葉（2026-11-02）: 「恒久的に安定させる方法は？私がやらなくても自動もしくはあなたが対応できる形」

| # | 基準 | 検証方法 | 合格ライン |
|---|---|---|---|
| P1 | AI の道具が、番号を決め打ちせずスマホを見つける | `bash scripts/dev/phone-serial.sh` を本物の Mac で実行 | 終了 0・1 行。行は `._adb-tls-connect._tcp` で終わる（自動のつながりを選ぶ） |
| P2 | スマホが 1 時間以上見えなければ Discord に 1 通届き、見えたら「直りました」が 1 通届く | 試験（§4 の P㉞〜P㊸）と、本物の通知先での手動試験 1 回（§5） | 試験 FAIL 0。手動試験でログに `result=alert send=ok problems=phone-missing` と `result=recover send=ok` |
| P3 | 見張り役も道具も、つながりを切ったり入れ直したりしない | 差分の中の `kill-server`・`disconnect`・`connect `・`tcpip`・`usb`・`reconnect` を数える | 0 件（`adb devices -l` だけを使う） |
| P4 | スマホを再起動した後、PO が何もしなくても戻る | PO がスマホを 1 回再起動し、10 分後に P1 を実行 | 終了 0・1 行。PO の操作は再起動だけ |
| P5 | 既存の試験 ①〜D㉝ が今まで通り通る | `bash scripts/tests/test-mac-jobs-watch.sh` | FAIL 0 |

P4 は「このネットワークで常に許可」に印があることが前提（recon §4 未確認）。PO に 1 回だけ印を確かめてもらってから測る。

## 2. 対象と対象外

- 対象:
  - 新規 `scripts/dev/phone-serial.sh`（スマホの今のつなぎ先の名前を 1 行出す）
  - `scripts/mac-jobs-watch.sh` に状態型の問題 `phone-missing` を 1 つ足す
  - `scripts/tests/test-mac-jobs-watch.sh` に試験 P㉞〜P㊸ を足す
  - 文書: 本書、recon-phone.md、docs/specs/mac-jobs-watch/README.md（境界と状態）、docs/specs/mac-jobs-watch/kgi.md（P1〜P5）
- 対象外（触らない）:
  - ops/launchd/*.plist（間隔は今の 30 分のまま。§3-3）
  - adb の待ち受け役の起動・停止・つなぎ直し（P3）
  - スマホの設定の変更（PO の手で 1 回だけ確かめてもらう）
  - colima・disk-janitor・disk-low の判定と文

## 3. 変更の中身

### 3-1. scripts/dev/phone-serial.sh（新規）

```bash
#!/bin/bash
# phone-serial.sh — 実機スマホ（既定 SC-51G）の今のつなぎ先の名前を 1 行出す
# 設計: docs/handoff/mac-jobs-watch/design-phone.md §3-1
#
# 使い方: adb -s "$(bash scripts/dev/phone-serial.sh)" shell ...
# 見るだけ。つながりを切る・入れ直す命令は使わない（adb devices -l だけ）。
# adb の待ち受け役が動いていなければ、adb devices が待ち受け役を起動する（adb の標準の動き）。
# 終了コード: 0=見つかった / 1=見えない / 2=adb が無い
#
# 設定: PHONE_MODEL（既定 SC_51G。adb devices -l の model: の値）、PHONE_ADB（既定 adb。試験用）
set -u
model="${PHONE_MODEL:-SC_51G}"
adb_cmd="${PHONE_ADB:-adb}"
command -v "${adb_cmd}" >/dev/null 2>&1 || exit 2
list="$("${adb_cmd}" devices -l 2>/dev/null | awk -v m="model:${model}" '$2=="device"{for(i=3;i<=NF;i++) if($i==m){print $1; break}}')"
[ -n "${list}" ] || exit 1
# 名前で探すつながり（番号が変わっても追従する）を先に選ぶ
pick="$(printf '%s\n' "${list}" | grep -m1 -F '._adb-tls-connect._tcp' || true)"
[ -n "${pick}" ] || pick="$(printf '%s\n' "${list}" | head -n 1)"
printf '%s\n' "${pick}"
```

### 3-2. scripts/mac-jobs-watch.sh（追記だけ。既存の行の意味は変えない）

| 場所 | 足すもの |
|---|---|
| `mjw_config`（:20-49）の末尾 | `: "${MJW_PHONE_CMD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/dev/phone-serial.sh}"`（コロン無しの `=`。空を入れたときは既定で上書きしない）、`: "${MJW_PHONE_GRACE:=3600}"`。`MJW_PHONE_CMD` を空にすると phone の点検をしない |
| 先頭の変数群 | `ST_PHONE=0`、`C_PHONE=0`、`PHONE_JUDGED=0` |
| `mjw_judged`（:178）の case | `phone-missing) [ "${PHONE_JUDGED}" -eq 1 ] ;;` |
| `mjw_text`（:190）の case | `phone-missing) printf 'スマホ（実機）が 1 時間以上 Mac から見えません。スマホが家の Wi-Fi に入っているか、設定 → 開発者向けオプション → ワイヤレスデバッグ が入っているかを見てください' ;;` |
| `mjw_read_state`（:230） | `ST_PHONE="$(mjw_num "$(mjw_st_get phone_gone)")"`（無い初回は 0） |
| `mjw_write_state`（:252） | `printf 'phone_gone=%s\n' "${C_PHONE}"` |
| `mjw_detect_states`（:318）の末尾 | 下の `mjw_phone_check` を呼ぶ |
| `mjw_main` の `C_SEEN=…; C_DKICK=…` の行（判定の直後） | `C_PHONE` は `mjw_phone_check` が決める（下）。dry-run では状態を書かないので変化なし |

```bash
# phone-missing（実機スマホが MJW_PHONE_GRACE 秒以上見えない。design-phone §3-2）
mjw_phone_check() {
  PHONE_JUDGED=0
  C_PHONE="${ST_PHONE}"
  [ -n "${MJW_PHONE_CMD}" ] || return 0
  [ "${AWAKE}" -eq 1 ] || return 0          # 眠っていた回は判定しない（前回を持ち越す）
  local rc=0
  bash "${MJW_PHONE_CMD}" >/dev/null 2>&1 || rc=$?
  case "${rc}" in
    0) PHONE_JUDGED=1; C_PHONE=0 ;;
    1) PHONE_JUDGED=1
       if [ "${ST_PHONE}" -eq 0 ]; then C_PHONE="${NOW}"; fi
       if [ $(( NOW - C_PHONE )) -ge "${MJW_PHONE_GRACE}" ]; then list_add DETECTED phone-missing; fi ;;
    *) return 0 ;;                          # adb が無い等。判定しない
  esac
}
```

- 振り分け（新規・続き・復旧）と送信は既存の `mjw_classify`・`mjw_main` をそのまま使う。新しい送り方は作らない。
- 復旧は `mjw_judged phone-missing` が真の回（起きていて、adb で見た回）だけ出る。

### 3-3. 間隔を変えない理由
- 見張り役は 30 分ごと（plist:46-47）。1 時間の猶予を足すので、知らせが届くのは見えなくなってから 60〜90 分後になる。
- 10 分ごとの別の常駐を作る案（§6 案 B）は、送り方・状態・ロックを二重に持つことになる。SSOT を守るため採らない。

## 4. 試験（scripts/tests/test-mac-jobs-watch.sh に P㉞〜P㊸ を足す）

偽 `adb` を `${BIN}/adb` に置き、`PHONE_ADB` で向ける。偽 adb は `${FAKE}/adb.out` の中身を出し、呼ばれた引数を `${FAKE}/adb.calls` に書く。既存の試験は `MJW_PHONE_CMD=""` で動かして今まで通りにする（P5）。

| # | 入力 | 期待 |
|---|---|---|
| P㉞ | phone-serial: 2 行（`192.168.0.2:40000 device … model:SC_51G`、`adb-X-Y._adb-tls-connect._tcp device … model:SC_51G`） | 終了 0・`adb-X-Y._adb-tls-connect._tcp` だけ |
| P㉟ | phone-serial: 番号の行 1 行だけ | 終了 0・その行の名前 |
| P㊱ | phone-serial: `offline` / `unauthorized` の行だけ、または別の機種だけ | 終了 1・出力なし |
| P㊲ | phone-serial: PHONE_ADB が存在しない | 終了 2 |
| P㊳ | phone-serial: 偽 adb の引数 | `devices -l` だけ（他の引数で呼ばれていない） |
| P㊴ | 見張り: 起きていた回、見えない 1 回目 | 送らない。state に `phone_gone=<NOW>` |
| P㊵ | 見張り: 続けて 3600 秒後も見えない | alert 1 通・problems に phone-missing・文にワイヤレスデバッグ |
| P㊶ | 見張り: その後見える | recover 1 通・`phone_gone=0` |
| P㊷ | 見張り: 眠っていた回（AWAKE=0）に見えない／見える | 判定しない。`phone_gone` も problems も前回のまま。復旧も出ない |
| P㊸ | 見張り: phone-serial が 2 を返す（adb が無い） | 判定しない・送らない・前回のまま |

## 5. 設置と手動試験（Opus が行う。本物の状態には触れない）
1. マージ後、道具のコピーは翌朝 04:00 に disk-janitor が更新する（plist は変えないので読み込み直しは不要）。
2. 手動試験（P2）: 一時フォルダの `MJW_STATE_DIR`・`MJW_LOG`・`MJW_LOCK_DIR` と、偽の phone コマンド（終了 1 を返す小さな台本）で `MJW_NOW` を 2 回進めて動かし、本物の通知先で alert 1 通を出す。次に偽の phone コマンドを終了 0 にして recover 1 通。K4 と同じ形（design.md §4 K4）。
3. P1 を本物の Mac で実行。P4 は PO が印を確かめたあとに測る。

## 6. 代替案

| 案 | 中身 | 採否 |
|---|---|---|
| A（採用） | 既存の見張り役に 1 項目足す＋名前で探す道具 | 送り方・状態・試験を 1 か所で持てる |
| B | 10 分ごとの別の常駐を作る | 送り方と状態が二重になる。採らない |
| C | 見えなければ自動で `adb connect` し直す | 番号が分からず、自動のつながりと重なる。P3 に反する。採らない |
| D | ケーブルでつなぎっぱなし | PO が選択肢 2 として見送り（2026-11-02） |

## 外部・過去事例の参照と我々への応用

- 外部事例: 使わない。理由: 本件は adb 公式の自動接続（docs/dev/adb_wifi.md「Auto-connect」）と Android 公式の「always allow on this network」（developer.android.com/tools/adb、2026-11-02 取得）で足り、他社の数値事例を設計の成功の証明に使う必要がないため（recon §3）。
- 過去事例（同じリポジトリ）: 空き容量点検 design-disk-low.md は、既存の見張り役に状態型の点検を 1 つ足し、送り方・状態ファイル・試験を共有した。応用: 本件も同じ形で `phone-missing` を足し、新しい常駐や送り方を作らない（§6 案 B を採らない理由）。

## 7. 危険と対処・戻し方・維持
- 外出のたびに知らせが届く: 1 時間の猶予で短い外出は知らせない。長い外出では 1 通と、戻ったときの「直りました」1 通が届く。24 時間続けば「まだ続いています」が 1 通。多すぎると PO が言えば `MJW_PHONE_GRACE` を伸ばす。
- adb devices が待ち受け役を起動する: adb の標準の動き。つながりは切らない（P3）。自動のつながりにはむしろ必要（recon §4）。
- 戻し方: この PR を revert する。plist は変えていないので、翌朝 04:00 の更新で元に戻る。
- 維持: 下の「維持の仕組み」。

## 維持の仕組み

- 担当: Mac の見張り役（launchd が 30 分ごとに動かす）。手で動かす人は要らない。
- 仕組み: 試験 `scripts/tests/test-mac-jobs-watch.sh`（P㉞〜P㊸）が判定の形を守る。ログ `~/Library/Logs/mac-jobs-watch.log` に毎回 1 行残る。台本は毎日 04:00 に origin/main へ更新される写し ~/.salesanchor-tools から動く。
- AI の決まり: AI が実機を使うときは `adb -s "$(bash ~/.salesanchor-tools/scripts/dev/phone-serial.sh)"` を使い、決め打ちの番号を書かない。

## 8. 設計審査（同じ AI による自己審査。独立した第二者審査ではない）

VERDICT: APPROVE（2026-11-02 Opus）
- 既存との整合: 状態型の問題の流れ（mjw_classify・mjw_main）をそのまま使い、新しい送り方を作らない。plist・他の判定は触らない。
- 根拠: 自動のつながりと既定値は adb 公式文書（recon §3）、行番号は origin/main 3bfc5d555 の実物（recon §5）。
- 検証可能性: P1〜P5 はすべてコマンドの終了コードかログの行で ○× が決まる。
- 範囲: §2 の対象 6 ファイルのみ。
- 未解決: SC-51G の「常に許可」の印（P4 の前提）。PO に 1 回確かめてもらう。名前の末尾が変わらないかは未確認だが、§3-1 は機種名で探すので名前が変わっても動く。
