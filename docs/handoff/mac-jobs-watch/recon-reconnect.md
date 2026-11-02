# 調べた事実: 再起動したあと、実機スマホがつながり直さない（2026-11-02）

設計: docs/handoff/mac-jobs-watch/design-reconnect.md

## 1. 元の設計と約束

- 再起動の後の約束（P4）: docs/handoff/mac-jobs-watch/design-phone.md:20 「スマホを再起動した後、PO が何もしなくても戻る」
- P4 の前提: docs/handoff/mac-jobs-watch/design-phone.md:23 「このネットワークで常に許可」の印
- 道具は見るだけ: docs/handoff/mac-jobs-watch/design-phone.md:48
- 結果の表: docs/specs/mac-jobs-watch/kgi.md:25 （P4 未測定）

## 2. 観測（生出力は /tmp/CC報告ファイル/adb-auto/）

| 時刻 (JST) | 観測 | 生出力 |
|---|---|---|
| 18:50 | スマホの記録 `dumpsys adb` の keystore に `wifiAP` が 2 件。今つながる Wi-Fi のアクセスポイントの印（`dumpsys wifi` の mWifiInfo）はそのうちの 1 件と同じ → 「常に許可」は付いていた | dumpsys-adb.txt・dumpsys-wifi.txt |
| 18:50:44 | `adb reboot`（PO の許可「操作も許可する」） | p4.txt |
| 18:51〜19:01 | 30 秒ごと 20 回、名前のつながりは 0 件。10 分後の道具は `rc=1` → P4 不合格 | p4.txt |
| 19:2x | PO の目視: 再起動のあと、ワイヤレスデバッグのスイッチは切れていた。PO が入れ直した | チャット |
| 19:28〜19:30 | スイッチを入れたあとも `adb devices` は 0 件、`adb mdns services` も 0 件（10 秒ごと 12 回） | p4-mdns.txt |
| 19:33 | PO が画面の番号 33815 を伝えた。`adb connect 192.168.10.106:33815` → `connected`、道具は `192.168.10.106:33815`・`rc=0` | p4.txt |
| 19:34 | Mac の仕組み `dns-sd -B _adb-tls-connect._tcp` には `adb-RFGL61DLQCW-IwMTz9` が出る。同じ時刻の `adb mdns services` は 0 件 | p4-mdns2.txt |
| 19:34 | `settings get global adb_wifi_enabled` は `1`。起動から 43 分 | p4-mdns2.txt |
| 19:34 | adb の待ち受け役は 10:29:20 から動いている。adb 37.0.1 | adb-ver.txt |
| 21:44 | `dns-sd -L adb-RFGL61DLQCW-IwMTz9 _adb-tls-connect._tcp local.` → `can be reached at Android.local.:33815`・`name=SC-51G` | dnssd-L.txt |
| 21:44 | `dns-sd -G v4 Android.local.` → `192.168.10.106` | dnssd-G.txt |

## 3. 分かったことと未確認

- 事実: 再起動でスイッチが切れる（PO 目視）。PO の操作が 1 回は要る
- 事実: スイッチを入れたあと、Mac の仕組み（dns-sd）はスマホを見つけるが、adb 自身の探し方は見つけない。番号が分かれば `adb connect` でつながる
- 未確認: adb 自身の探し方が見つけなくなった理由（待ち受け役を止めて試していない）
- 未確認: 再起動のあともスイッチを入れたままにする方法
