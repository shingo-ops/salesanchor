# recon: 実機スマホが Mac から見えなくなったら知らせる（phone-missing）

この文書は何か(専門用語なしの1行): PO のスマホ（Galaxy SC-51G）と Mac のつながりが、今どう作られていて、どこで切れるかを実物で確かめた記録。

親: [design-phone.md](./design-phone.md)／読み取り時の本線: origin/main 3bfc5d555（2026-11-02）

## 1. 既存の決まり（ADR）
- `git grep -i -E 'adb|wireless debug|ワイヤレスデバッグ|SC-51G' -- docs/adr` は 0 件。スマホとのつなぎ方を決めた ADR は無い。
- 本テーマは既存の Mac の見張り役（[README](../../specs/mac-jobs-watch/README.md)）に 1 項目足すだけなので、新しい ADR は起こさない（空き容量点検 [design-disk-low.md](./design-disk-low.md) と同じ扱い）。

## 2. Mac とスマホのつながり（2026-11-02 実測。生出力 /tmp/CC報告ファイル/adb-auto/now.txt・props.txt）
- adb は `/opt/homebrew/bin/adb`、Version 37.0.1-15733141。
- `adb devices -l` に同じスマホが 2 行出る:
  - `192.168.10.106:43569 device product:SC-51G model:SC_51G …`（番号を決め打ちしたつながり）
  - `adb-RFGL61DLQCW-IwMTz9._adb-tls-connect._tcp device product:SC-51G model:SC_51G …`（Mac が自動で作ったつながり）
- `adb mdns services` は `_adb-tls-connect._tcp 192.168.10.106:43569` と `_adb._tcp 192.168.10.106:5555` を返す。
- スマホは Android 16。`settings get global adb_wifi_enabled` = 1、`getprop service.adb.tcp.port` = 5555。`getprop persist.adb.wifi.guid` は空で返った（読めない。名前の末尾 `IwMTz9` が変わらないかは未確認）。

## 3. 公式の説明（出典）
- adb の開発文書（Context7 `/git_android_googlesource_com/platform_packages_modules_adb`、docs/dev/adb_wifi.md「Auto-connect」）: Mac 側の adb は起動すると `_adb-tls-connect` を探し続け、ペア済みのスマホが見つかれば自動でつなぐ。§2 の 2 行目がこれ。
- 同 docs/user/adb.1.md: `ADB_MDNS_AUTO_CONNECT` の既定は `adb-tls-connect`（何も設定しなくても自動接続が効く）。
- developer.android.com/tools/adb（2026-11-02 取得）: ワイヤレスデバッグの「always allow on this network」に印を付けると、その Wi-Fi に入るたびにワイヤレスデバッグが許可される。ペアは取り消すまで続く。
- 同ページに「再起動や Wi-Fi の切り替えでワイヤレスデバッグが切れる」とは書かれていない。切れる条件は未確認。

## 4. 切れる所（事実と未確認）
- 事実: 番号 43569 はスマホが決める。決め打ちした道具（この会話の /tmp/a2-eval の台本）は番号が変わるとつながらない。自動のつながり（2 行目）は名前で探すので番号の変化に追従する（§3 の仕組み）。
- 事実: Mac の adb の待ち受け役が動いていなければ、自動のつながりも作られない（§3。待ち受け役が探す側のため）。
- 未確認: SC-51G で「このネットワークで常に許可」に印が付いているか。スマホの再起動後に自動で戻るか。

## 5. 足す先の見張り役（実物）
- `scripts/mac-jobs-watch.sh`（565 行）。設定は `mjw_config`（:20-49）に 1 か所。判定する回の決まり `mjw_judged`（:178）、知らせる文 `mjw_text`（:190）、状態の読み書き `mjw_read_state`（:230）・`mjw_write_state`（:252）、状態型の判定 `mjw_detect_states`（:318）、新規・続き・復旧の振り分け `mjw_classify`（:411）、本体 `mjw_main`（:436、判定呼び出し :485・:490）。
- 本物の通知先での手動試験の型は元の設計の K4（`docs/handoff/mac-jobs-watch/design.md:157`）。一時フォルダに入力を全部置き、本物の状態・ログには触れない。
- 状態型の問題は「新しく出た → ⚠️ 異常」「24 時間続く → まだ続いています」「消えた → ✅ 復旧」を既に持っている（:411-）。
- 30 分ごと＋ログイン時（ops/launchd/jp.salesanchor.mac-jobs-watch.plist:46-47 `StartInterval 1800`）。台本は道具のコピー ~/.salesanchor-tools から動き、コピーは毎日 04:00 に disk-janitor が origin/main へ更新する（ops/launchd/jp.salesanchor.disk-janitor.plist:34）。plist の PATH に /opt/homebrew/bin がある（mac-jobs-watch.plist の EnvironmentVariables）。
- 試験 `scripts/tests/test-mac-jobs-watch.sh`（653 行）。一時フォルダと偽 launchctl・偽 curl・偽 df で動く。
- 本線に adb を呼ぶ台本は 0 件（`git grep -n -E '\badb\b' origin/main` 0 件）。
