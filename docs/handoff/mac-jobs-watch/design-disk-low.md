# 追補: Mac の空き容量の見張り（disk-low）

- 状態: 設計案作成済み・設計審査済み（同一AIの自己審査）・PO 実装承認待ち・実装未着手
- 起点: 2026-10-15 PO「y」（空きが 20GiB を切ったら知らせる見張りを足す）
- 関連: 本書 §1〜（PR #4315 の見張り役）、[recon 追補](recon-disk-low.md)、ADR-1009（通知先 webhook を共有）、ADR-114:161（disk-janitor）

## 1. 目的と KGI

10/13・10/14 に Mac のディスクが満杯（空き 143MB / 117Mi）になり、npm ci が ENOSPC、Bash の出力すら書けず全停止した。
毎日の自動片付け（disk-janitor）は動いていたが、空きが減っていくことを誰も知らなかった。

| ID | 基準（○×で判定） | 検証方法 |
|---|---|---|
| D1 | 空きが 20GiB 未満になった回に、Discord に「💾 空き容量が少なくなっています（いま N GiB）」が 1 通届く | 試験 ㉕（偽 df で 19GiB）＋設置後 `--dry-run` で `MJW_DISK_LOW_GIB=100` を与え problems=disk-low がログに出る |
| D2 | 20GiB 未満が続く間、同じ知らせは 24 時間に 1 回まで | 試験 ㉖ |
| D3 | 空きが 25GiB 以上に戻った回に「✅ 直りました」が 1 通届く。20〜25GiB の間では復旧を出さない（往復で何通も来ない） | 試験 ㉗㉘ |
| D4 | df が読めない回は、知らせも復旧も出さない（誤った「直りました」を出さない） | 試験 ㉙ |
| D5 | 既存の試験 ①〜㉔ がすべて通る | `bash scripts/tests/test-mac-jobs-watch.sh` が全 ok・終了 0 |
| D6 | 設置後の実機で `result=ok`（空き 48GiB の現状では送らない）が 1 行以上出る | `~/Library/Logs/mac-jobs-watch.log` の設置後の行 |

## 2. 現在地（recon 追補の要約・origin/main 基準）

- 点検は状態型 `mjw_detect_states`（scripts/mac-jobs-watch.sh:295-333）で DETECTED に名前を積む形。知らせ・24h 再通知・復旧は `mjw_classify`（:374-390）と :474-505 が名前単位で共通処理する。新しい点検は「名前を積む」「固定文を足す」だけで乗る。
- 再通知間隔 `MJW_REPEAT_SECONDS=86400`（:40）。点検間隔は plist の StartInterval 1800（ops/launchd/jp.salesanchor.mac-jobs-watch.plist:46-47）。
- 空き容量を判定している仕組みは無い。disk-janitor.sh は `df -h "${DJ_DF_PATH}"`（既定 /System/Volumes/Data、:42）をログに出すだけ（:502, :532）。
- 実機の空き（2026-10-15 22:5x）: `df -k /System/Volumes/Data` Available 47717140 KiB ≒ 45.5GiB。

## 3. 変更内容（scripts/mac-jobs-watch.sh だけ。plist・通知先・他の点検は触らない）

### 3-1 設定（mjw_config :20-43 に 4 行追加）
```bash
  : "${MJW_DISK_PATH:=/System/Volumes/Data}"
  : "${MJW_DISK_LOW_GIB:=20}"
  : "${MJW_DISK_OK_GIB:=25}"
  : "${MJW_DF:=df}"
```

### 3-2 測る関数（新設・mjw_dj_parse の後）
```bash
mjw_disk_parse() { # DISK_GIB に空き GiB（整数・切り捨て）。読めなければ空
  local kb
  DISK_GIB=""
  kb="$("${MJW_DF}" -k "${MJW_DISK_PATH}" 2>/dev/null | awk 'NR==2{print $4}')"
  case "${kb}" in ''|*[!0-9]*) return 0 ;; esac
  DISK_GIB=$(( kb / 1048576 ))
}
```

### 3-3 判定（mjw_detect_states の末尾に追加）
```bash
  # disk-low（知らせ済みなら 25GiB 以上に戻るまで続いている扱い）
  mjw_disk_parse
  if [ -n "${DISK_GIB}" ]; then
    if [ -n "$(prob_time disk-low)" ]; then lim="${MJW_DISK_OK_GIB}"; else lim="${MJW_DISK_LOW_GIB}"; fi
    if [ "${DISK_GIB}" -lt "${lim}" ]; then list_add DETECTED disk-low; fi
  fi
```
（`local` に `lim` を追加）

### 3-4 判定する回（mjw_judged の case に追加）
```bash
    disk-low) [ -n "${DISK_GIB}" ] ;;
```

### 3-5 固定文（mjw_text の case に追加）
```bash
    disk-low) printf '空き容量が少なくなっています（いま %s GiB。%s GiB を切ると知らせます）' "${DISK_GIB:-?}" "${MJW_DISK_LOW_GIB}" ;;
```
復旧時の文は既存の「✅ 復旧 … → 直りました」（:497-505）がこの固定文を使う。

### 触らない範囲
- 通知先・送信関数 `mjw_send`・ロック・状態ファイルの形式・ログ書式・plist・disk-janitor.sh・他の点検名。
- 自動で消す動作は足さない（知らせるだけ）。

## 4. 試験（scripts/tests/test-mac-jobs-watch.sh に ㉕〜㉙ を追加）
偽 df（`MJW_DF` に一時領域のスクリプト。`DF_KB` 環境変数の値を Available 列に出す）を使う。既存の setup では偽 df の既定値を 50GiB 相当にし、①〜㉔ が影響を受けないようにする。

| 番号 | 条件 | 期待 |
|---|---|---|
| ㉕ | 19GiB | 送信 1 回・本文に「空き容量が少なくなっています（いま 19 GiB」・problems=disk-low |
| ㉖ | ㉕の直後にもう一度（24h 未満） | 送信 0 回 |
| ㉗ | 知らせ済みで 22GiB | 送信 0 回・problems に disk-low が残る |
| ㉘ | 知らせ済みで 26GiB | 送信 1 回（直りました）・problems から消える |
| ㉙ | 知らせ済みで df が失敗（空出力） | 送信 0 回・problems に disk-low が残る |

## 5. 代替案と選択理由
| 案 | 採否 | 理由 |
|---|---|---|
| A. mac-jobs-watch に点検を 1 つ足す | 採用 | 知らせ・24h 再通知・復旧・送信失敗の再送が既にある。常駐を増やさない |
| B. disk-janitor に判定を足す | 不採用 | 1 日 1 回（04:00）しか動かない。10/14 は 1 日半で 17GiB 減っており間に合わない |
| C. macOS 標準の「空き不足」通知に任せる | 不採用 | 出る閾値を公式資料で確認していない（未確認）。Discord に残らない |

## 6. リスクと対処
| リスク | 対処 |
|---|---|
| 20GiB 前後を行き来して何通も来る | 復旧は 25GiB 以上（D3） |
| df が壊れて「直りました」が誤って出る | 読めない回は判定しない（D4） |
| 満杯寸前で見張り役自身が書けない | 20GiB は満杯の十分手前。見張り役自身の停止は既知の範囲外（mac_jobs_watch 残件） |
| 閾値が合わない | `MJW_DISK_LOW_GIB` / `MJW_DISK_OK_GIB` で変更でき、試験も環境変数で行う |

## 7. 戻し方・測り方
- 戻し方: 本 PR の revert（1 ファイル＋試験）。道具のコピー ~/.salesanchor-tools は origin/main から動くので、revert のマージで次の 30 分点検から元に戻る。
- 測り方: D6 を設置後に確認。以後、Discord の知らせ件数を週次で数える（0 件が続けば正常、多すぎれば閾値見直し）。

## 維持の仕組み
- 試験 ㉕〜㉙ は既存の試験ファイルに入る（CI では回っていない点は既知の残件のまま。本変更で悪化しない）。
- 閾値の正本は mjw_config の既定値。変えるときは本書 §1 の表と一緒に変える。

## 外部・過去事例の参照と我々への応用
- 外部事例: 直接の根拠になる外部事例は使わない（Mac 開発機の空き容量しきい値について、出典つきの実測値を確認していない）。
- 過去事例（社内）: 2026-10-02 prod1 のディスク満杯で DB が約 13 分停止。再発防止で「空き 5GB 未満ならデプロイ中止」（#3945）と「使用率 90% 超で警報」（#3947）を足した。応用: 満杯になってからでは遅く、手前で知らせる線が要る。Mac でも同じ考えで、満杯の十分手前（20GiB）で知らせる。
- 閾値 20/25GiB は本リポジトリの実測（10/13 片付け後 17GiB → 10/14 午後 117Mi、約 1.5 日で約 17GiB 減）から決めた。

## 10. 設計審査（Architect・同一AIの自己審査）
- 判定: APPROVE
- 根拠: 追加は既存の状態型点検と同じ形（:295-333 の list_add、:168-176 の case、:179-191 の case）。通知・再送・復旧の共通処理（:374-390, :474-505）を変えない。PROB は mjw_read_state で detect 前に読まれる（:444→:448 の順）ため、prob_time disk-low を判定で使える。
- 未解決: なし（実装承認のみ PO 待ち）。

## 11. 改訂1: 知らせる前に自動片付けをその場で走らせる（2026-10-15 PO「y」）

起点: Opus の問い「空きが20Gを切ったら、見張り役が自動片付けをその場で走らせるようにしますか？」への PO 回答「y」。
消してよい範囲は 2026-10-13 の PO 承認（disk-janitor の根5か所×R1〜R4）のまま。本改訂は**走らせる時刻を早めるだけ**で、消す範囲は増やさない。

### 11-1 流れ
1. 空きが 20GiB 未満、かつ disk-low をまだ知らせていない回:
   - 直近 24 時間に片付けを走らせていなければ → `launchctl kickstart gui/<uid>/jp.salesanchor.disk-janitor`（`-k` は付けない＝動いている最中なら二重に起こさない）。Discord には送らない。
   - 走らせてから 25 分（1500 秒）以上たっても 20GiB 未満 → disk-low を知らせる（§3 の通常の流れ）。
   - 走らせてから 25 分未満 → 待つ（送らない）。
2. 知らせ済みの間は §3 のまま（25GiB 以上で「直りました」、24h ごとに「まだ続いています」）。
3. 直近 24 時間に走らせ済みで再び 20GiB 未満になったら、走らせずにすぐ知らせる（直前に片付けた後なので、消せる物が残っていない見込みのため）。
4. 片付けの起動に失敗しても、起動を試した時刻として記録する → 25 分後に知らせが出る（失敗で知らせが止まらない）。

### 11-2 変更（scripts/mac-jobs-watch.sh）
- 設定に追加: `MJW_DJ_LABEL:=jp.salesanchor.disk-janitor`、`MJW_DISK_KICK_WAIT:=1500`、`MJW_DISK_KICK_COOLDOWN:=86400`
- 状態ファイルに `disk_kick=<最後に起動を試した時刻>` を追加（mjw_read_state で `ST_DKICK`、mjw_write_state で `C_DKICK` を書く。既定 0）
- §3-3 の判定を置き換え:
```bash
  # disk-low（知らせる前に、片付けをその場で走らせる。改訂1）
  mjw_disk_parse
  DISK_KICK=0
  if [ -n "${DISK_GIB}" ]; then
    if [ -n "$(prob_time disk-low)" ]; then
      [ "${DISK_GIB}" -lt "${MJW_DISK_OK_GIB}" ] && list_add DETECTED disk-low
    elif [ "${DISK_GIB}" -lt "${MJW_DISK_LOW_GIB}" ]; then
      if [ "${ST_DKICK}" -eq 0 ] || [ $(( NOW - ST_DKICK )) -ge "${MJW_DISK_KICK_COOLDOWN}" ]; then
        DISK_KICK=1
      elif [ $(( NOW - ST_DKICK )) -ge "${MJW_DISK_KICK_WAIT}" ]; then
        list_add DETECTED disk-low
      fi
    fi
  fi
```
- 起動は dry-run 判定（`exit 0`）の**後**、「起動後の点検」の前に置く（dry-run では走らせない）:
```bash
  # 空き不足 → 片付けをその場で走らせる（改訂1）
  if [ "${DISK_KICK}" -eq 1 ]; then
    if "${MJW_LAUNCHCTL}" kickstart "gui/$(id -u)/${MJW_DJ_LABEL}" >/dev/null 2>&1; then
      any_sent=1; mjw_log_now disk-kick ok
    else
      any_sent=1; mjw_log_now disk-kick fail
    fi
    C_DKICK="${NOW}"
  fi
```
  （`C_DKICK` は既定で `ST_DKICK` を引き継ぐ。`any_sent=1` は「result=ok を重ねて書かない」ための既存の印で、送信はしない。send 列は `ok/fail` を片付け起動の成否として使う）
- 固定文を変更: `disk-low) 空き容量が少ないままです（いま N GiB。自動片付けを走らせた後も 20 GiB 未満）`
- dry-run のログに起動予定が分かるよう、DISK_KICK=1 の回は events 列に `disk-kick` を出す（dry-run の行だけ）。

### 11-3 試験（D㉕〜D㉙ を置き換え・追加）
| 番号 | 条件 | 期待 |
|---|---|---|
| D㉕ | 19GiB・起動歴なし | 偽 launchctl に `kickstart gui/<uid>/jp.salesanchor.disk-janitor` が 1 回・送信 0・ログ `result=disk-kick send=ok`・状態 disk_kick=NOW |
| D㉖ | D㉕ の 10 分後も 19GiB | kickstart 増えない・送信 0 |
| D㉗ | D㉕ の 30 分後も 19GiB | 送信 1（本文「空き容量が少ないままです（いま 19 GiB」）・problems=disk-low・kickstart 増えない |
| D㉘ | 知らせ済みで 22GiB → 26GiB | 22 では送らない、26 で「直りました」1 通 |
| D㉙ | 知らせ済みで df が読めない | 送らない・problems に残る |
| D㉚ | 19GiB → 片付け後 30 分で 40GiB | 送信 0・problems 空（片付けで直れば知らせない） |
| D㉛ | kickstart が失敗（偽 launchctl の rc=1） | ログ `result=disk-kick send=fail`・30 分後 19GiB なら送信 1 |
| D㉜ | dry-run・19GiB | kickstart 0・状態不変・ログ events に disk-kick |
| D㉝ | 起動から 2 時間後（24h 未満）、一度 40GiB に戻った後に再び 19GiB | kickstart 増えない・すぐ送信 1 |

### 11-4 受入条件の追加
| ID | 基準 | 検証方法 |
|---|---|---|
| D7 | 20GiB 未満になった回に片付けが 1 回だけ起動し、直れば Discord に何も来ない | 試験 D㉕ D㉚ |
| D8 | 片付けても 20GiB 未満なら、起動から 25〜55 分の間に知らせが 1 通届く | 試験 D㉗ D㉛ |
| D9 | dry-run では片付けを起動しない | 試験 D㉜ |

### 11-5 対象外（次の段）
- Discord の知らせを受けて Claude に整備を指示させること。2026-10-15 調査（/tmp/CC報告ファイル/disk-20261015/recon-ops/）で、ADR-1009 の受付は本番監視チャンネルの許可 webhook だけを通し（~/sa-ops-intake/tools/claude-channels/discord-ops/lib.ts:29-34、access.json に見張り役の webhook ID 0 件）、担当 ops-worker は書き込み・実行不可（tools/claude-channels/intake/agents/ops-worker.md:4-8）、受付側 settings は `Bash(scripts/*)` 等を deny（~/sa-ops-intake/.claude/settings.local.json:19-23）。つなぐには受付の許可リスト・委任表の変更が要り、ADR-1009 の改訂として別に設計する。

### 11-6 リスクの追加
| リスク | 対処 |
|---|---|
| 片付けが 1 日に何度も走る | 24h に 1 回まで（MJW_DISK_KICK_COOLDOWN） |
| 片付け中に見張り役が動く | 実機の plist は片付けの使用中の印が 120 分以内なら見張り役自体を見送る（recon §見張り役）。`kickstart` に `-k` を付けないので動作中の片付けは止めない |
| 消す範囲が広がる | 片付けの中身（disk-janitor.sh）は変えない。起動経路は既存の LaunchAgent と同じ（--execute・道具のコピー） |

### 11-7 設計審査（改訂1・同一AIの自己審査）
- 判定: APPROVE
- 根拠: 起動は既存 LaunchAgent（ops/launchd/jp.salesanchor.disk-janitor.plist:17 の label、docs/ops/runner-commands.md:254 の kickstart 手順）をそのまま使い、削除範囲は不変。状態追加は既存キーと同じ形（mjw_write_state :244-255）。dry-run は exit 0（:475-477）より後に起動するので走らない。
- 未解決: なし。
