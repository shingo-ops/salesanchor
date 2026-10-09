# 実機エビデンス 2026-10-06 ADB経路の停止（Wi-Fi切断でワイヤレスデバッグがOFF）と Termux 権限の付与

対象端末: Galaxy SC-51G（Android 16、`samsung/SC-51G/m1q:16/BP4A.251205.006`）。本機（Ubuntu proot）は同じ端末の中で動いており、ADBは `127.0.0.1` で端末自身につないでいる。
取得はすべて `adb` の読み取りコマンドとローカルのログによる実測。推測は「推測」と明記した箇所のみ。

## 結論

- 自動書き出し（ADB経路）が **03:26:46 から 09:46 まで約6時間20分停止**した。原因は **03:53:25 のWi-Fi切断**で、Androidが**ワイヤレスデバッグをOFFにした**こと（E1〜E3）。
- Wi-Fiは 04:02:50 に復帰したが、**ワイヤレスデバッグは復帰しなかった**。走査範囲に待ち受けが1つも無く、`adb-discover.sh`（ポート走査）では原理的に復旧できない（E3）。**復旧には利用者がトグルをONにする操作が必須**。
- これは既知の2型（2026-09-23 ポート変更／2026-09-28 ペアリング鍵の失効）とは**別の第3の型**。切り分けの判定材料は E3 の表にまとめた。
- 併せて、2026-10-04・10-05 の停止原因だった **Termux の SYSTEM_ALERT_WINDOW を許可**した。Termuxが前面に無い状態で EDIT→送信完了まで4秒を実測（E5）。
- 失敗通知が利用者に気づかれなかった理由は `--alert-once` と判明（E6）。
- 作業中に **実行中のスクリプトを同一inodeで上書きして定期実行を落とす事故**を起こした（E7）。

## E1. 停止の経緯（`/root/line-auto-export/auto-export.log` と outbox events）

```
2026-10-06 03:26:46 done: accepted          ← 最後の成功
2026-10-06 03:53:26 接続先を探索            ← 以後、接続先探索→失敗を繰り返す
2026-10-06 03:55:27 FAIL adb: ADBに接続できない（ワイヤレスデバッグ/Wi-Fiを確認）
...
2026-10-06 09:41:00 FAIL adb: ADBに接続できない（ワイヤレスデバッグ/Wi-Fiを確認）
```

`stage='auto'` の `result='failed'` は 03:55:28 / 04:03:42 / 04:20:29 / 04:58:28 / 05:53:22 / 06:50:40 / 07:21:16 / 07:28:35 / 08:00:34 / 08:34:02 / 09:04:01 / 09:19:13 / 09:41:00 の **13回**。
失敗段階はすべて `adb`（接続）であり、画面操作・書き出し・送信の段階には1回も到達していない。

## E2. 引き金はWi-Fi切断（`adb shell dumpsys wifi`）

```
10-06 03:53:25.245 FIRMWARE_ALERT lastScore=60 txSuccessDelta=9 txRetriesDelta=4 firmwareAlertCode=12 screenOn=false
10-06 03:53:25.375 NETWORK_DISCONNECTION_EVENT local_gen=false reason=-1:UNSPECIFIED lastRssi=-57 lastFreq=5180 lastLinkSpeed=720 screenOn=false
 rec[5]: time=10-06 03:53:25.454 processed=CompletedState org=CompletedState dest=DisconnectedState
 rec[6]: time=10-06 04:02:50.628 processed=DefaultState   org=DisconnectedState dest=HandshakeState
10-06 04:02:50.583 MAC_CHANGE
10-06 04:02:51.015 NETWORK_CONNECTION_EVENT
10-06 04:02:55.903 CMD_IP_CONFIGURATION_SUCCESSFUL  (IP 192.168.10.106/24, 5500MHz)
```

- `local_gen=false` ＝端末側から切ったのではない。`lastRssi=-57` ＝電波は良好で、圏外による切断でもない。
- auto-export の最初の失敗（03:53:26 の探索開始）は**切断の1秒後**。時刻の一致は偶然ではない。
- 復帰は **9分25秒後**（03:53:25 → 04:02:50）。SSID `aterm-552b47-5p`、BSSID `36:38:39:01:f8:5f`。
- `firmwareAlertCode=12` の意味はベンダ定義で、公開情報からは特定できなかった（未確認）。

## E3. Wi-Fi復帰後もワイヤレスデバッグは戻らない

```
$ adb connect 127.0.0.1:44861
failed to connect to '127.0.0.1:44861': Connection refused

$ (127.0.0.1 の 30000-55000 を全数走査、07:25)
hits: []
```

`Connection refused` ＝そのポートで待ち受けが無い。走査でも待ち受けは**1つも見つからない**。
利用者が端末で ワイヤレスデバッグ を ON にした直後に同じ走査をすると:

```
hits: [34013, 35152]
$ adb connect 127.0.0.1:34013 → connected
$ adb devices → 127.0.0.1:34013  device     （ペア設定は有効だった＝鍵の再登録は不要）
```

ポートは **44861 → 34013** に変わった（ONにするたびに変わる）。

ワイヤレスデバッグがWi-Fi接続に紐付いていることは `dumpsys adb` の保存内容から確認できる:

```
$ adb shell dumpsys adb
debugging_manager={ connected_to_adb=true  user_keys=QAAAAAG2... @localhost
  keystore=... wifiAP/ bssid 34:38:39:01:f0:9b / 36:38:39:01:f8:5f ... }
```

端末は再起動していない（`adb shell uptime` ＝ `up 18 days, 18:37`）ので、OFFになったのは再起動が原因ではない。
「Wi-Fi接続が失われるとAndroidがワイヤレスデバッグを無効化する」部分は、該当するシステムログの保持期間が短く（E4）**ログ行としては取得できていない**。取得できたのは上記の事実（切断→1秒後に失敗開始、復帰後も待ち受け0個、許可済みBSSIDを保存している）であり、仕様側の挙動との整合という位置づけ。

### 3つの停止パターンの切り分け

| 判定 | 症状 | 原因 | 復旧 |
|---|---|---|---|
| 走査で候補が見つかり `device` になる | ポートが変わっただけ | Wi-Fi復帰でadbdが別ポートで再起動（2026-09-23: 40359→44861） | `adb-discover.sh` が自動復旧 |
| 走査で候補は見つかるが `device` にならない | TLSで端末が鍵を拒否（`SSLV3_ALERT_CERTIFICATE_UNKNOWN`） | ペアリング鍵の失効（2026-09-28） | 利用者がペア設定コードを表示 → `adb pair` |
| **走査で候補が1つも無い（`Connection refused`）** | **待ち受け自体が無い** | **Wi-Fi切断でワイヤレスデバッグがOFF（2026-10-06）** | **利用者がトグルをON（ポートは毎回変わる）** |

## E4. proot からの調査で使えない手段（次回のため）

| 手段 | 結果 |
|---|---|
| `/proc/net/tcp`, `/proc/net/tcp6` | **空**（Android 10以降の制限）。LISTENポートの一覧は取れない → ポート走査で代替する |
| `/proc/uptime` | **固定値が返る**（124.08 が92秒あけて2回同値）。**再起動の判定に使えない**。端末の稼働時間は `adb shell uptime` を使う |
| `logcat -b all` | 保持が極端に短い（確認時点で最古のエントリが数秒前）。**数時間前の事象は残らない** → `dumpsys wifi` の `rec[]`・イベント履歴から取る |
| `ss` / `netstat` / `ip` | proot に無い（`netstat` は Termux 側のパスにのみ存在） |

## E5. Termux の SYSTEM_ALERT_WINDOW 付与とその効果

2026-10-04・10-05 の停止（EDIT押下後にTermuxが自分のセッションを起動できず共有が溜まる）に対する根本対策。利用者の承認を得て付与した。

```
（付与前）$ adb shell appops get com.termux SYSTEM_ALERT_WINDOW
SYSTEM_ALERT_WINDOW: default; rejectTime=+18d8h19m32s967ms ago

$ adb shell appops set com.termux SYSTEM_ALERT_WINDOW allow

（付与後）SYSTEM_ALERT_WINDOW: allow; rejectTime=+18d8h19m54s538ms ago
```

付与直後の実行（**Termuxは前面に無い**。`mCurrentFocus=com.sec.android.app.launcher`、`mWakefulness=Dozing`）:

```
09:46:17 start
09:46:23 unlocked
         run 1 OK sec=24.8
09:46:52 EDIT tapped
09:46:56 done: accepted        ← EDIT押下から4秒
```

outbox events: `received → store → cleanup(1件削除) → send started → send accepted http_code=200`（送信1.78秒、全体39秒）。digest `f17ffd06…` は新規＝重複ではなくサーバーが取り込んだ。
`window_hours=0`（全文取り込み）のため、停止していた約6時間20分ぶんもこの1回に含まれる。**取りこぼしは0件。**

未確認: 効果の確認は**この1回のみ**。Termux非前面での継続的な成功は長期観測が必要。`com.termux.api` の `SYSTEM_ALERT_WINDOW` は `default` のまま（変更していない）。

## E6. 失敗通知が気づかれなかった理由

- 通知は13回すべて**投稿に成功**している（`stage='notify'` の失敗記録は0件。`client.Outbox._notify` は通知コマンドが失敗したときのみ記録する）。
- `tools/termux-line-import/client.py` の `termux_notify()` は `--id 4203` と **`--alert-once` が固定**。`--alert-once` は「そのIDで最初の1回だけ鳴らす」指定なので、2回目以降の12回は無音で通知欄の同じ1件が書き換わるだけだった。

`--alert-once` の有無は通知レコードのフラグで確認できる（テスト通知 id=4299 を1件出して比較、出した通知はすぐ削除）:

```
$ adb shell dumpsys notification --noredact
tag=4203 ... Notification(channel=termux-notification ... flags=ONLY_ALERT_ONCE|AUTO_CANCEL ...)   pri=0   ← 従来
tag=4299 ... Notification(channel=termux-notification ... flags=AUTO_CANCEL ...)                  pri=1   ← --alert-once なし
```

鳴り方そのものは **Android 8以降は通知チャンネルが決める**ため、通知1件ごとの `--vibrate` / `--priority` は効かない:

```
effectiveNotificationChannel=NotificationChannel{mId='termux-notification', mImportance=3,
  mSound=content://settings/system/notification_sound, mVibrationEnabled=false, mVibrationPattern=null,
  mAudioAttributes=AudioAttributes: usage=USAGE_NOTIFICATION ... flags=0x800(FLAG_MUTE_HAPTIC)}
```

→ **音は鳴る水準（importance=3・音URIあり）だが、振動はチャンネル側で無効**。振動も必要なら利用者が端末の設定（アプリ→Termux:API→通知→Termux API notification channel）でONにする必要がある。
未確認: テスト通知で実際に音が鳴ったかどうかの利用者確認は取得できていない。

## E7. 事故：実行中のシェルスクリプトを上書きした

10:40:3x に開始していた定期実行の最中に `auto-export.sh` を**同じinodeに上書き**したため、bash が続きを読み直した位置がずれて落ちた。

```
2026-10-06 10:41:06 EDIT tapped
/root/line-auto-export/auto-export.sh: line 170: syntax error near unexpected token `)'
/root/line-auto-export/auto-export.sh: line 170: `print('' if r is None else r[0])")'
```

- 影響: その回の `stage='auto'` の結果行が残らなかった。**データは無事**（outbox events に `10:41:08 send accepted http_code=200`）。
- 対策: 実行中かもしれないシェルスクリプトは in-place で書き換えない。**一時ファイルに書いて `mv` で差し替える**（走っている bash は古い inode を読み続けるため影響を受けない）。
