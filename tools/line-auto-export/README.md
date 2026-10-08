# LINEトーク履歴の自動書き出し（既定: アプリ合図方式／切り戻し: ADB方式）

スマホが**自分自身へ合図を送る**（既定の `MODE=app`）か、**自分自身をADBで操作**する（`MODE=adb`）かで
LINEのトーク履歴を定期的に書き出し、Termux経由で salesanchor へ送るための一式。
端末上にしか無かったものをここに登録した（2026-09-19）。ADBのワイヤレスデバッグが鍵失効で再発停止するため、
2026-10-08 に既定を `MODE=app` へ切り替えた（詳細: `docs/handoff/line-auto-export-runtime/design-app-trigger.md`）。

> **⚠️ ADB方式（`MODE=adb`）は障害発生時の緊急手段専用（PO決定 2026-10-08）。通常運用では使わない。**
> **かつ「いざという時に即使える」状態ではない**: 2026-10-08 時点でADBは接続不能（ワイヤレスデバッグの
> ペア設定が失効し、`adb connect` が `offline` になる）。緊急手段として使う**前**に、端末で**再ペアリング**
> （利用者がペア設定コードを読み上げる作業、実測1〜2分）が必要。「`LINE_AUTO_EXPORT_MODE=adb` に切り戻せば
> 即動く」と誤解すると、障害対応中にその分の時間を失う。事前に再ペアリングし直しておくかはPOで保留中
> （アプリが壊れる状況では利用者が端末を触れるため、必要時に実施で足りるとの判断。詳細は design-app-trigger.md
> 追補「ADB方式の位置づけ（PO決定）」）。

## 何が動いているか（MODE=app・既定）

```
Androidのジョブスケジューラ（約15分ごと）
  └─ Termux: ~/bin/line-auto-export            … termux/line-auto-export
       └─ proot（Ubuntu）: auto-export.sh       … アプリへブロードキャストで合図 → events を待ち受け
            └─ 自作アプリ（jp.salesanchor.lineexport, RunReceiver）
                 … 解除・LINE書き出し・Termux共有・送信・再ロックまでアプリ側で行う
```

ADBは使わない。`flow.sh` と `adb-discover.sh` は `MODE=adb`（切り戻し）専用で、app モードでは呼ばれない。

## 何が動いているか（MODE=adb・切り戻し用）

```
Androidのジョブスケジューラ（約15分ごと）
  └─ Termux: ~/bin/line-auto-export            … termux/line-auto-export
       └─ proot（Ubuntu）: auto-export.sh       … 解除・共有・送信結果の待ち受け
            ├─ flow.sh                          … LINEのUI操作（端末の /data/local/tmp へ転送して実行）
            └─ adb-discover.sh                  … ADBの接続先が変わったときに探し直す
```

どちらのモードでも、このセッションやPCは不要で端末だけで完結する。結果は既存の outbox
（`~/line-import/state/outbox.sqlite3`）の events に `stage='auto'` で記録され、失敗時は通知（id 4203）が出る。

## モード切替

- `auto-export.sh` 先頭の `MODE=${LINE_AUTO_EXPORT_MODE:-app}`。既定は **app**。
- ADB方式へ切り戻すときは、`termux/line-auto-export` の起動コマンドに環境変数を渡す
  （または `~/bin/line-auto-export` 先頭に `export LINE_AUTO_EXPORT_MODE=adb` を追記する）:
  ```
  LINE_AUTO_EXPORT_MODE=adb /data/data/com.termux/files/usr/bin/proot-distro login ubuntu -- \
    bash /root/line-auto-export/auto-export.sh
  ```
- `MODE=adb` のときは本章「MODE=adb・切り戻し用」の従来フロー（ADB探索・解除・`flow.sh`・EDITタップ・
  再ロック）がそのまま動く。アプリ方式の実績が浅いため、コードは削除せず残している。
- **`MODE=adb` は障害発生時の緊急手段専用**（PO決定 2026-10-08）。通常運用には使わない。
  切り戻す前に端末での**再ペアリングが必要**（冒頭の警告を参照）。
- `MODE=app` のとき、PINファイル（`unlock-pin`）の権限チェックは行わない（PINはアプリ側が持つため）。
- `MODE=app` のとき `fail()` は `adb shell` を撃たない（ADBが無い環境で無駄なエラーを出さないため）。

## アプリへの合図（MODE=app）

```
CLASSPATH=/data/data/com.termux/files/usr/libexec/termux-am/am.apk \
/system/bin/app_process -Xnoimage-dex2oat / com.termux.termuxam.Am \
  broadcast --user 0 -n jp.salesanchor.lineexport/.RunReceiver \
  -a jp.salesanchor.lineexport.RUN_ALL
```

- `--user 0` と `-n`（宛先名指し）は両方必須。2026-10-08 実測で、`-n` の無い暗黙ブロードキャストは
  一度も届かなかった（09:23・09:28の2回とも無反応）。
- このコマンドの**標準出力は捨てる**（`Broadcasting: Intent ...` 等、成功時も毎回出るため。2026-10-08
  実機ログで `say()` の行に混ざって読みにくいことが分かった）。**標準エラーは残す**。終了コードが0以外、
  または標準エラーに出力があれば、合図そのものを撃てなかったとみなして `fail app "アプリへの合図を送れない（…）"`
  で止める（この場合は `events` のポーリングへは進まない）。
- 合図を送った後、最大180秒・3秒間隔で outbox の `events` を見る。`stage='send'` の終端結果が増えていれば、
  それを `stage='auto'` の結果として採る:
  - `accepted` / `pending_review`（受理） / `duplicate`（取り込み済みで送信なし） /
    `skipped`（新規が無いため送信なし。送信量の絞り込み機能で新設）→ **`ok`**。
    `duplicate`・`skipped` は正常な無操作であり失敗ではない。`failed` にすると、送信量の絞り込み導入後は
    「新規なし」が最多の結果になり、失敗通知が鳴り続けて2026-10-06の連続失敗通知改修が逆効果になる。
  - それ以外（`auth_required` / `rejected` / `retry` 等、送信が完了していない）→ **`failed`**（理由はその
    `send` 行の理由）。
- 180秒待っても `send` 行が増えなければ `skipped` として記録する（理由:
  「アプリが実行しなかった（スマホ使用中か、アプリ側の失敗。アプリの通知を確認）」）。
  スマホ使用中の見送りとアプリ側の失敗をスクリプトからは区別できないため、`failed` にはしない
  （`failed` にすると使用中の見送りでも失敗通知が鳴り続けてしまう）。
  - このとき、最後に `stage='auto' result='ok'` が記録された時刻から**3時間以上**経っていれば、
    「LINE自動書き出し：3時間以上成功していません」を通知（id 4204、`--alert-once`付きの静かな通知）。
    `client.py` の詰まり通知（stall, id 4202）はジョブが残っている場合しか鳴らず、appモードでアプリが
    一切動かなくなると何も鳴らないまま静かに止まるため、この見張りをスクリプト側に追加した。
- 再ロックはスクリプトでは行わない。アプリ側が `RUN_ALL` の最後に施錠する。
- 実機を使わずに合図送信以降の処理だけを検証したい場合、環境変数 `LINE_AUTO_EXPORT_BROADCAST_CMD` に
  差し替えコマンド（例: `echo` や events へのダミー書き込み）を設定すると、実際のブロードキャストの代わりに
  それが実行される（リポジトリの設計書には無い、テスト用の追加口）。

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

## ADB接続先の自動復旧（adb-discover.sh・MODE=adb専用）

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

## 実測（MODE=adb・2026-09-19、15分周期へ変更後 約11時間・48回）

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

## 既知の弱点（MODE=adb）

- **ワイヤレスデバッグの接続が切れると全滅する**。2026-09-18 は深夜に切れ、01:33〜07:33 の7回が
  `ADBに接続できない` で失敗した（朝に復帰）。さらに2026-10-07 17:36からは**鍵の失効**で接続不能になり、
  再ペアリングには人の操作が必要（再発する型）。これが `MODE=app` へ切り替えた理由（上記参照）。
  `auto-export.sh` は `endpoint` ファイルに最後の接続先を保存し、毎回再接続を試みるが、鍵失効自体は直せない。
- スマホ使用中（画面オン＋ロック解除）は見送る。前面の操作を奪わないための判断。
- LINEやOSの更新でUIの配置が変わると `flow.sh` の調整が要る。
- Termuxの「EDIT」ボタンだけは座標直打ち（`EDIT_X/EDIT_Y`）。この画面は uiautomator に出ないため。
- Termux に「他のアプリの上に重ねて表示」権限が無いと、共有後のセッション起動が遅れる
  （2026-09-23 実測: 90秒を超えて失敗扱いになり、端末を触った時点で溜まっていた8件が一斉に処理された。
  ログ: `Termux:PermissionUtils: com.termux does not have Display over other apps (SYSTEM_ALERT_WINDOW) permission`）。
  送信結果の待ちを4分に延ばして誤判定を減らしているが、根本対策は端末設定での権限付与。

ADBに依存しない代替（自作アプリ方式、`release/line-auto-export-app`）は2026-10-08に実機で書き出し〜送信を
通し、`auto-export.sh` の既定を `MODE=app` に切り替えた。本章の内容は `MODE=adb`（切り戻し時）にのみ適用される。
