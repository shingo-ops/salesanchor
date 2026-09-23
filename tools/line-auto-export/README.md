# LINEトーク履歴の自動書き出し（ADB方式・稼働中）

スマホが**自分自身をADBで操作**して、LINEのトーク履歴を定期的に書き出し、Termux経由で
salesanchor へ送るための一式。端末上にしか無かったものをここに登録した（2026-09-19）。

## 何が動いているか

```
Androidのジョブスケジューラ（約15分ごと）
  └─ Termux: ~/bin/line-auto-export            … termux/line-auto-export
       └─ proot（Ubuntu）: auto-export.sh       … 解除・共有・送信結果の待ち受け
            ├─ flow.sh                          … LINEのUI操作（端末の /data/local/tmp へ転送して実行）
            └─ adb-discover.sh                  … ADBの接続先が変わったときに探し直す
```

このセッションやPCは不要で、端末だけで完結する。結果は既存の outbox（`~/line-import/state/outbox.sqlite3`）
の events に `stage='auto'` で記録され、失敗時は通知（id 4203）が出る。

## 配置（端末側）

| リポジトリ | 端末での配置先 |
| --- | --- |
| `auto-export.sh` / `flow.sh` / `adb-discover.sh` | proot内 `/root/line-auto-export/` |
| `termux/line-auto-export` | Termux `~/bin/line-auto-export`（実行権限を付ける） |

暗証番号は `~/line-import/state/unlock-pin`（権限600）に置く。スクリプトには埋め込まない。
`auto-export.sh` は起動時に権限が600でなければ実行を中止する。

## ジョブの登録（Termuxで実行）

```
termux-job-scheduler --job-id 4203 --period-ms 900000 \
  --script /data/data/com.termux/files/home/bin/line-auto-export \
  --persisted true --network none --battery-not-low false
```

- `--period-ms` の下限は 900000（15分）。**Android N以降の制約**で、10分は指定できない。
  実測: 600000 を指定すると `PERIODIC: interval=+15m0s0ms flex=+10m0s0ms` として登録される。
- `--network none --battery-not-low false` は必須。既定は「ネットワーク接続時のみ・電池残量低下時は実行しない」で、
  圏外や電池残量が少ないときに止まってしまう。
- 登録した瞬間に1回実行され、そこが周期の起点になる。

## ADB接続先の自動復旧（adb-discover.sh）

Wi-Fi が切れて復帰すると、Android はワイヤレスデバッグを**新しいポート**で起動し直す。
保存済みの接続先では復帰できず、2026-09-23 は 40359 → 44861 に変わって約6時間止まった。

- `auto-export.sh` は保存済みの接続先で繋がらないとき `adb-discover.sh` を呼ぶ。
- ローカルの 30000-55000 を走査し、`adb connect` して `adb devices` が `device` になった先を採用する。
  成功したら `endpoint` ファイルを更新する。実測 約97秒（走査64秒＋検証）。
- 候補の検証に `adb shell` を使うと `offline` 相手で数分待たされる（実測24分）。`devices` の状態で判定すること。
- `adb mdns services` はこの端末で何も返さず、`getprop` は proot から権限が無く使えない（どちらも実測）。

## 実行時刻について

termux-job-scheduler は時刻を指定できず、1回あたり約0.6分ずつ後ろにずれる（実測 平均間隔15.6分）。
**時刻を揃える仕組みは持たない。** 2026-09-19 に「次の15分境界まで待ってから登録し直す」方式を入れたが、
待機プロセスがジョブ終了後に Android に停止され、22回中21回が完走しなかったため 2026-09-23 に廃止した。
15分ごとに動いていれば1回の失敗は次の回で埋まるため、時刻の揃えに実用上の意味は無いと判断した。

## 実測（2026-09-19、15分周期へ変更後 約11時間・48回）

| 項目 | 実測 |
| --- | --- |
| 成功 | 44回（92%） |
| 見送り（使用中） | 2回 |
| 失敗 | 2回（いずれもLINEのUI操作の途中。次の回で成功し取りこぼしなし） |
| 発火間隔 | 最小5分 / 最大25分 / 平均15.6分 |
| 1回の所要 | 最小36秒 / 最大67秒 / 平均40秒 |

失敗の内訳は `FAIL export: LINEの書き出し画面まで進めない（shortcut）` と `（open_menu）`。
`shortcut` はホーム画面のショートカットを押す段階、`open_menu` はLINEのメニューを開く段階。

1時間周期だった頃は、接続断が続くと長時間の空白になった（2026-09-18 01:33〜07:33 の7回連続失敗）。
15分周期では単発の失敗が次の回で埋まる。

## 既知の弱点

- **ワイヤレスデバッグの接続が切れると全滅する**。2026-09-18 は深夜に切れ、01:33〜07:33 の7回が
  `ADBに接続できない` で失敗した（朝に復帰）。`auto-export.sh` は `endpoint` ファイルに最後の接続先を
  保存し、毎回再接続を試みる。
- スマホ使用中（画面オン＋ロック解除）は見送る。前面の操作を奪わないための判断。
- LINEやOSの更新でUIの配置が変わると `flow.sh` の調整が要る。
- Termuxの「EDIT」ボタンだけは座標直打ち（`EDIT_X/EDIT_Y`）。この画面は uiautomator に出ないため。
- Termux に「他のアプリの上に重ねて表示」権限が無いと、共有後のセッション起動が遅れる
  （2026-09-23 実測: 90秒を超えて失敗扱いになり、端末を触った時点で溜まっていた8件が一斉に処理された。
  ログ: `Termux:PermissionUtils: com.termux does not have Display over other apps (SYSTEM_ALERT_WINDOW) permission`）。
  送信結果の待ちを4分に延ばして誤判定を減らしているが、根本対策は端末設定での権限付与。

ADBに依存しない代替（自作アプリ方式）は `tools/line-auto-export-app/` で検証中。2026-09-19 時点では
ロック画面へのタップが届かず未達（`docs/handoff/line-auto-export-app/evidence-20260919-unlock.md`）。
