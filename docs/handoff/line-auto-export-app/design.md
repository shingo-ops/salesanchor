# LINE自動書き出しアプリ（ユーザー補助）

この文書は、ADB・Wi-Fiに依存せず端末内だけで、画面消灯＋PINロック状態から自動でLINEトーク履歴を書き出し既存取り込みへ渡す自作アプリの設計。
現状: [recon.md](recon.md)。親: [商品マスタ](../../specs/product-master/README.md)。対象ADR: ADR-072・ADR-154（backend/DB/API変更なし）。

## KGI（PO合意 2026-09-17）

| # | 基準 | 検証方法 |
|---|---|---|
| 1 | Wi-Fiオフ・モバイル通信のみで、画面消灯＋PINロックから「解除→書き出し→取り込み→再ロック」が通る | ワイヤレスデバッグをオフにして5回連続成功、outbox events に auto ok 5件 |
| 2 | ADBを使わない | 試験中はADB切断。起動は端末内スケジューラのみ |
| 3 | 失敗時に「どの段階で・なぜ」を通知し履歴に残す | ユーザー補助を無効化して実行し、失敗通知＋履歴を確認 |
| 4 | スマホ使用中（画面オン＋ロック解除）は実行せず見送りを記録 | 使用中に起動 |
| 4b | 定時取得：毎時ちょうど付近（例 1:00,2:00…）に起動する | AlarmManager setExactAndAllowWhileIdle。数回の実測で各実行が毎時00分±数分に入る |
| 4c | スキップ後の再試行：使用中で見送ったら5分後に再試行し、成功するまで5分ごとに繰り返す。再試行で取得しても次の定時は毎時ちょうどに戻す | 使用中に定時起動→5分後アラーム→…→成功後、次は次の毎時00分に復帰することを実測 |
| 5 | 実行後は必ず再ロック | 毎回 keyguard 状態を記録 |
| 6 | PINは画面・履歴・リポジトリに出さない | 端末・リポジトリを検索 |

## 方式（PIN渡し方=設計A）

- 自作アプリ「SA LINE Export」（applicationId 例: jp.salesanchor.lineexport）。
  - **AccessibilityService**：クリック等の操作主体。ロック解除（PIN入力）とLINE操作を担う。
  - **設定Activity**：PINを一度だけ入力し、アプリ私有の EncryptedSharedPreferences に保存（アプリ外に出さない）。ショートカット名・グループ名の期待値もここで持つ。
  - **起動口**：Termuxの1時間ごとジョブから `am start`/`am broadcast` で「今すぐ実行」を通知。extra にPINは載せない。
- **取り込み判定**：従来どおり client.py が書き込む outbox.sqlite3 の送信結果を正とする。アプリはLINEの「Termux→EDIT」まで担い、取り込み完了はTermux側履歴で確認。ランナー（proot）が events に stage='auto' を記録。SSOTは outbox.sqlite3 の1か所を維持。

## 段階的計画（各段階で実機検証してから次へ）

1. **最小アプリ**：ユーザー補助サービス＋PIN保存UI。動作は「画面ウェイク→keyguard上でPIN入力→解除できたら通知」だけ。KGIの最大の未確認点（ロック画面クリック可否・APKビルド可否）を検証。
2. LINE操作を追加：ホーム→ショートカット→Menu→設定→トーク履歴を送信→Termux→EDIT（ADB版 flow.sh と同じ順・同じ判定）。開いたトークが期待グループかを検証してから書き出す（誤爆防止）。
3. 端末内スケジューラから起動。使用中スキップ・再ロック・失敗通知を実装。
4. Wi-Fiオフで5回連続の実証。結果を本書と evidence-registry に記録。
5. 合格後、ADB方式（job 4203）を停止しアプリへ切替。

## スケジューリング（PO要望 2026-09-17）

termux-job-scheduler は「およそ○分ごと」しか指定できず（最短15分・実測15〜25分のばらつき）、時刻ちょうどの指定と5分間隔の再試行はできない。よって定時実行はアプリ内の AlarmManager で行う。
- 定時：毎時00分に `setExactAndAllowWhileIdle`（Doze中も発火）でアラームを張り、発火のたびに次の毎時00分へ張り直す。
- 再試行：定時起動時にスマホ使用中（画面オン＋ロック解除）なら見送り、5分後に単発アラームを張る。再試行時も使用中ならさらに5分後。成功したら、その回の再試行アラームは張らず、次は通常の毎時00分アラームに戻す（＝再試行成功でも定時列は毎時ちょうどを維持）。
- Android 12+ の正確アラームは `SCHEDULE_EXACT_ALARM`/`USE_EXACT_ALARM` 権限に留意（targetSdk23では旧扱いで setExact が使える見込みだが実機で要確認＝不明点）。
- 起動口は当面 Termux ジョブからの `am broadcast` も併存可能だが、最終形はアプリ内アラームを正とする。

## ビルド手順（proot内、確定した道具）

javac `--release 8` → dalvik-exchange で classes.dex → aapt でリソース＋Manifestを base.apk 化 → dex 同梱 → zipalign → apksigner（keytoolのデバッグ鍵）で署名。android.jar は API23。端末へは `adb install`（初回検証時）または Termux 共有でインストール。

## 弊害・トレードオフ

- 生体認証を外しPIN運用にするため、端末の物理的な盗難時リスクが上がる。実行時のみ解除し即再ロックで緩和。
- PINはアプリ私有領域に保存。アプリのデータ領域を読める権限（root等）があれば露出しうる。
- ユーザー補助は強力な権限。対象を当該アプリの操作に限定し、他アプリの内容は読まない実装にする。
- LINE/OSの更新でUI座標・遷移が変わると再調整が必要（ADB版と同じ弱点）。
- 「制限付き設定を許可」とユーザー補助の有効化は、ユーザーの手動操作が必要。

## 外部・過去事例の参照と我々への応用

- Android公式 AccessibilityService（developer.android.com）: `canPerformGestures`/click は標準。ロック画面上の操作可否は明記なし→自作最小アプリで実測（段階1）。
- Google Play ポリシー: 非アクセシビリティ用途のユーザー補助はPlay配布時に制限。→本アプリはPlay配布せず自己利用のサイドロードのみ。制限付き設定はユーザーが許可。
- 過去試作 line-notification-probe（2026-09-11）: 通知傍受は全文取得できず0件で中止。→本方式は「履歴書き出し」を自動化する点で通知傍受の欠落問題を回避する。

## 維持の仕組み

- 守り手: docs/handoff/line-auto-export-app/design.md（本書・実機検証記録）、tools/termux-line-import/test_android_import.py（取り込み側の回帰）
- 人手で守る: APKのビルド・署名・インストール、ユーザー補助と制限付き設定の許可、LINE更新時のUI座標再調整。理由：端末上のGUI状態・権限はCIから検証できない。

## 追補 2026-09-18 ロック画面の数字キー座標を実測

ロック画面（Bouncer）はスクリーンショットが真っ黒になる（secure window）ため、uiautomator/screencap では座標を取れない。`adb shell getevent -lt /dev/input/event6`（sec_touchscreen、値は0-4095スケール）で利用者のタップを記録して求めた。利用者に各キーを1秒長押ししてもらい、hold>=500ms のタッチだけを採用。1・3・7・9・0 を2回測って一致を確認した（ばらつき最大42px、キー間隔は横253px・縦220px）。2・4・5・6・8 は格子計算による導出。

実測値（画面 1080x2340、2回の平均）:

| | 1回目 (x,y) | 2回目 (x,y) | 採用値 | 比率 |
| --- | --- | --- | --- | --- |
| 1 | 325, 1190 | 326, 1188 | 315, 1182 | 0.2917, 0.5051 |
| 3 | 822, 1174 | 825, 1175 | 816, 1182 | 0.7556, 0.5051 |
| 7 | 310, 1628 | 297, 1646 | 315, 1632 | 0.2917, 0.6974 |
| 9 | 827, 1618 | 788, 1634 | 816, 1632 | 0.7556, 0.6974 |
| 0 | 567, 1872 | 547, 1856 | 565, 1864 | 0.5231, 0.7966 |

列 x=315/565/816、行 y=1182/1407/1632、0 のみ (565,1864)。`UnlockAccessibilityService` のフォールバックが持っていた推測グリッド（keypadTop=0.42, keypadBottom=0.95 等）は 7/8/9 の行が実測より126pxずれており、キー間隔（縦220px）の半分を超えるため隣のキーを押す計算だった。実測比率に差し替え、メソッド名も `tapDigitByMeasuredGrid` に変更した。Enterのフォールバック座標は未実測のまま（推測）。

測り直すときの注意点:

1. ADB注入の `KEYCODE_SLEEP` / `KEYCODE_POWER` では安全ロックにならない（暗証番号なしでスワイプ解除できてしまう）。**物理の電源ボタン**を押してもらう必要がある。その後 `input keyevent KEYCODE_WAKEUP` → `input swipe 540 1900 540 600 250` で Bouncer を表示できる。
2. `getevent` の出力はブロックバッファで遅れて現れるため `stdbuf -o0` を付ける。付けないと「0バイト＝録れていない」と誤判定する。
3. 通常のタップは75〜160ms。Termuxのソフトキーボードのタップが y≈1150〜1200 と y≈1800〜1840 に出て数字キーと紛らわしいので、長押し（hold>=500ms）だけを採用して選り分ける。
4. 測定中は `flock /root/line-auto-export/lock` を握って毎時の自動書き出しを止める（割り込みでタップが混ざるため）。

生の記録には利用者の実際の暗証番号入力が混ざるため、解析後に削除した。生記録はリポジトリに入れない。

## 2026-09-30 追補: 通知リスナー方式（記録のみ・送信なし）

### 目的

段階2（LINE操作の自動化）とは別経路として、`NotificationListenerService` でLINEの通知を横取りし、本文を端末内に記録するだけの機能を追加した。**送信機能は実装していない**（本番配線・Termuxへの受け渡しは別作業）。誤送信を構造的に防ぐため、このアプリには `android.permission.INTERNET` を一切付与していない（`AndroidManifest.xml` に理由をコメントで明記）。

### 実測で判明した通知の形

対象端末で `jp.naver.line.android` の会話通知を実際に受信して確認した extras の形（前提として記載済みの実測に基づく。詳細は本アプリの実装依頼メモを参照）:

- `android.conversationTitle`: グループ名（例「WeGo買います専用」）。1対1トークでは無いことがある。
- `android.title`: `"グループ名: 送信者名"` の形。`conversationTitle` が無い場合のフォールバック元。
- `android.text`: 本文。改行を含む長文がそのまま入る（実測: 484字・改行11個・絵文字入りが欠けずに入っていた）。
- `android.bigText`: 展開時の本文（`android.text` より優先度は下だが `android.messages` が無い場合の次点）。
- `android.messages`: `Parcelable[]`（要素は `Bundle`）。各要素は `text`(CharSequence) / `time`(long) / `sender`(CharSequence) を持つ。**`sender_person` は `android.app.Person`（API28追加）のため一切参照しない。**
- `sbn.getNotification().when`: 通知の到着時刻(epoch ms)。0のことがある。
- グループのサマリ通知（`FLAG_GROUP_SUMMARY`）も別に飛んでくるため除外が必要。

値の決定順（`LineNotifyListenerService#handle`）:
1. グループ名: `android.conversationTitle` → 無ければ `android.title` の `": "` より前（無ければ title 全体）
2. 送信者: `android.messages` 最後の要素の `sender` → 無ければ `android.title` の `": "` より後 → 無ければ空文字
3. 本文: `android.messages` 最後の要素の `text` → 無ければ `android.bigText` → 無ければ `android.text`
4. 時刻: `android.messages` の `time` → 0/未設定なら `notification.when` → それも0なら `sbn.getPostTime()`

### API23ビルド制約への対処

このビルド環境の `javac` は API23 の `android.jar` にリンクしているため、API24以降に追加されたシンボルは**コンパイル時に参照できない**（実行時の端末はAndroid 16でも無関係）。`javap -p -constants` で確認した結果、`Notification.EXTRA_CONVERSATION_TITLE` と `Notification.EXTRA_MESSAGES` はAPI23の `android.jar` に存在しない（`EXTRA_TITLE`/`EXTRA_TEXT`/`EXTRA_BIG_TEXT` は存在する）。そのため `LineNotifyListenerService` では `"android.conversationTitle"` / `"android.messages"` をリテラル文字列で直読みしている。`android.app.Person`（API28）・`NotificationChannel`（API26、既存の `NotificationCompat` のリフレクション方式を流用）にも一切触れていない。`NotificationListenerService` / `StatusBarNotification` はAPI18で存在するため、リフレクション不要で直接使用できた。

### 記録先とファイル形式

記録先ディレクトリは `Environment.getExternalStorageDirectory() + "/Download/sa-line-notify"` を優先し、作成/書き込みができなければ `getFilesDir() + "/sa-line-notify"` にフォールバックする（`LineNotifyListenerService#resolveStorageDir`）。実際に使ったパスは `NotifyStore` に保存し、設定画面に表示する。

- `raw-YYYYMMDD.jsonl`（検証用）: 1行1レコードのJSON。フィールドは `postTime`（記録処理を行った時刻, ISO8601+タイムゾーンオフセット）、`when`（本文決定に使った到着時刻, 同形式）、`key`（`sbn.getKey()`）、`group`、`sender`、`text`、`textLen`、`messagesCount`、`titleRaw`、`source`（`messages`/`bigText`/`text` のどれから本文を取ったか）。ISO8601はオフセットを `+0900` のようなbasic形式で出す（`+09:00` のextended形式にはしていない。どちらもISO8601として有効）。
- `talk-YYYYMMDD.txt`（既存の Android LINE 書き出し取り込み形式。`tools/termux-line-import/android_parser.py` がそのまま読める）: 日付が変わる最初の1件の前に `YYYY/M/D(曜)` 行（曜は日本語1文字）、各メッセージは `H:MM<TAB>送信者<TAB>本文`。本文中の改行はエスケープせず、CharSequenceの `\n` をそのまま書き込むだけで既存パーサの継続行（タブなしの生の行）と同じ形になる。日付行の重複を防ぐため、最後に書いた日付ヘッダを `NotifyStore` に保持し、変わったときだけ出力する。
- ファイル名の `YYYYMMDD` は記録処理を行った時刻（`postTime`）のローカル日付。`talk-*.txt` 内の `YYYY/M/D(曜)` ヘッダは本文決定に使った到着時刻（`when`）のローカル日付（通常は同じ日になるはずだが、日付境界をまたいだ遅延通知では一致しないことがあり得る＝未検証）。
- 両ファイルとも UTF-8、1件ごとに追記直後に flush、書き込みは `LineNotifyListenerService` 内の `synchronized (WRITE_LOCK)` ブロックで直列化している。

絞り込み: `NotifyStore` に保存された対象グループ名（カンマ区切り、各要素をtrimしたうえで完全一致）のいずれかと一致する通知だけを記録する。保存値が空文字列のときは全グループを記録する。既定値は `WeGo売ります掲示板グループ`。設定画面（`SettingsActivity`）の入力欄で変更できる。

件数・最終記録時刻・最終記録グループ・記録先パスは `NotifyStore`（`PinStore` と同じ private SharedPreferences方式、別ファイル）に保存し、通知ID `4204` を「記録: N件 / 最後: HH:MM グループ名」の形で更新表示する。**本文は通知にもログにも出さない**（例外ログは種別と `textLen` のみ）。

### INTERNET権限を持たせない理由

この段階の目的は「本文を取り出して端末内に記録できるか」の検証であり、送信は別作業（PO確認・本番配線）で行う。実装ミスや将来の変更が万一あっても、このアプリ自体に `INTERNET` 権限が無ければ外部への送信が起こり得ない。`aapt dump badging out/app-debug.apk` で `INTERNET` のuses-permissionが出力に含まれないことを確認済み（`WRITE_EXTERNAL_STORAGE` に伴う `READ_EXTERNAL_STORAGE` のuses-implied-permissionのみ）。

### 動作確認の手順（未実施・実機で要確認）

1. APKをインストール（本アプリでは実施しない。POが実施）。
2. 設定 → アプリ → SA LINE Export → 通知の使用を許可（`SettingsActivity` の「通知アクセスの設定を開く」ボタンから `ACTION_NOTIFICATION_LISTENER_SETTINGS` を開ける）。
3. 「記録用ストレージ権限を許可」ボタンで `WRITE_EXTERNAL_STORAGE` を許可（Android 10+ではスコープドストレージの影響で `Download/` 配下への書き込みが制限される可能性があり未検証＝下記「未対応事項」）。
4. 設定画面の対象グループ欄を確認・保存（既定は `WeGo売ります掲示板グループ`）。
5. 対象グループ宛にLINEメッセージを送ってもらい、通知が届いた後に設定画面へ戻って「記録件数」「最終記録」「記録先」が更新されるか確認。
6. `adb shell run-as jp.salesanchor.lineexport ...` またはファイルマネージャで `Download/sa-line-notify/raw-YYYYMMDD.jsonl` と `talk-YYYYMMDD.txt` の中身を確認し、本文・改行・絵文字が欠落なく入っているか、`talk-*.txt` が `android_parser.py` でパースできる形式になっているかを確認する。

### 未対応・不明点

- 実機での動作確認は未実施（このアプリ側の実装はビルド確認のみ、実機検証はPOが担当）。
- Android 10+ のスコープドストレージが `Environment.getExternalStorageDirectory() + "/Download/sa-line-notify"` への書き込みにどう影響するか未検証。書き込めない場合は `getFilesDir()` フォールバックに自動的に切り替わるはずだが未確認。
- `android.messages` の実際のキー名（`text`/`time`/`sender`）は `Notification.MessagingStyle.Message#toBundle()` の実装に基づく想定であり、対象端末のLINEアプリが実際に `MessagingStyle` でこれらのキーを使っているかは実機ログでの再確認が望ましい（メモに記載の実測結果に基づき実装したが、本追補時点では実装者はその実測ログ自体を直接見ていない）。
- 対象グループ名のカンマ区切りは各要素をtrimして比較している（仕様上は「完全一致」とだけ指定されていたが、人力入力時のスペース混入を許容するためtrimを追加した。トリム無しの厳密一致に戻す場合は `LineNotifyListenerService#matchesTarget` を変更する）。
- 日付境界をまたぐ遅延通知（`talk-*.txt` のファイル名日付とヘッダ日付が食い違うケース）は未検証。
- LINEのアップデートで `android.messages`/`android.conversationTitle` の有無やキー名が変わる可能性があり、その場合は本追補の「値の決定順」を実機ログで再確認して調整が必要。
