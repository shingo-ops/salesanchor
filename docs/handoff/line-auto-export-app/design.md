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

## 追補 2026-10-07 ロック解除フローの起床待ち・キーパッド出現確認・リトライ

### 背景: 深いスリープからの起床後、スワイプしてもBouncer（数字キーパッド）が出ないことがある実機計測

2026-10-06/07、ADBで「起こしてからスワイプするまでの待ち時間」だけを変えて計測した（毎回 `mWakefulness=Dozing` からやり直し、`dumpsys window Bouncer` の `isVisible` を300ms間隔で観測）。

| スワイプのタイミング | 結果 |
|---|---|
| 起床 +64ms | Bouncer は25秒見ても出ない |
| 起床 +1546ms | スワイプの約580ms後に出現。以後9秒以上出たまま |
| `mWakefulness != Dozing` を待ってから（実際は+42ms） | 出ない |
| 起床 +3057ms | スワイプの約220ms後に出現。以後10秒以上出たまま |

確定した事実:
1. **状態での判定は使えない**。`keyevent 224` 直後に `mWakefulness=Awake` になるが、ロック画面はまだスワイプを受け付けない。`PowerManager#isInteractive()` も失敗した回で `screenOn=true` を返していた。実時間で待つしかない。
2. **早すぎるスワイプは「遅れて効く」のではなく失われる**（25秒待っても出なかった）。やり直しが必要。
3. **Bouncerが一度出れば消えない**（9〜10秒以上表示継続）。ロック画面が約5.3秒で消灯するのはBouncerが出なかった回だけ。待ち時間やリトライを足しても画面が消える心配はない。
4. AOD状態（`mWakefulness=Dreaming`）から実行した回は、既存コードのまま6桁＋Enterすべてアクセシビリティノードで取れて解除に成功した（5299ms）。キーパッドさえ出ればノード経路は実機で機能している。

### 設計・実装（`UnlockAccessibilityService`）

- `POST_WAKE_DELAY_MS` を 600ms → **1500ms** に変更（起床直後のスワイプが失われる事実を踏まえた安全側の待ち）。
- スワイプ後、固定700ms待ちで無条件に数字入力へ進んでいたのをやめ、**キーパッドの出現を確認してから**数字入力に進むようにした。
  - 確認は既存の `findNodeByLabel()` を再利用し、PINとは無関係な固定ラベル（`"1"`/`"3"`/`"7"`）を探して**2つ以上見つかればキーパッドが出ている**と判定する（`isKeypadVisible()`）。PINの桁を使うと値が挙動に漏れるため使わない。
  - ポーリング間隔 **150ms**、1回のスワイプあたりの確認期限 **1500ms**（`KEYPAD_CHECK_INTERVAL_MS` / `KEYPAD_CHECK_TIMEOUT_MS`）。
- 期限内に確認できなければ**スワイプをやり直す**。スワイプは**最大3回**（`KEYPAD_MAX_SWIPE_ATTEMPTS`）。3回とも出なければ、**数字入力とEnterを一切行わずに中止**し、失敗理由を既存の `Enter未検出` とは別の **`キーパッド未出現`** として通知する。空振りのタップでPINの誤入力が累積して端末がロックアウトされる事態を避けるため。
- 数字の座標フォールバック（`tapDigitByMeasuredGrid`）は残すが、`clickDigit(0)` はキーパッドの出現が確認できた後（`pollKeypadVisibility()` が `isKeypadVisible()==true` を検知した後）にしか呼ばれないため、キーパッド未確認のまま座標タップが行われることはない。
- 通知本文に「スワイプ何回目で出たか」（`keypadConfirmedAttempt`、0なら未出現）と「起床からキーパッド確認までの経過ms」（`keypadConfirmedElapsedMs`、-1なら未確認）を追加した。既存のtrace書式（`ノード`/`座標`、`dispatch=`/`cb=`）は変更していない。PINの値・桁数は引き続き一切出さない。
- 処理は従来どおり `Handler#postDelayed` のチェーンのみで組み、`Thread.sleep` やブロッキング待機は使っていない。

最悪ケースの待ち時間の目安: 起床待ち1500ms + スワイプ3回分（各確認期限1500ms、実際には出現確認で即時打ち切りだが上限で見積もる）4500ms + 数字6桁×200ms 1200ms + Enter後の結果判定待ち1500ms ≒ **8.7秒**（スワイプ3回がすべて期限いっぱいまで出現しなかった場合の上限値。実機ではBouncerが出れば数百ms以内に確認できるため、通常はこれより短い）。

### 未検証・今後の確認事項

- 上記の計測はADBからのキー注入とアプリ内Handlerで実時間の扱いが異なる可能性があるため、本変更後の実機でのBouncer出現までの実測（本番ログの新診断フィールド）で裏取りする。
- `KEYPAD_PROBE_LABELS`（"1"/"3"/"7"）がBouncer以外の画面（電卓等）に偶然出現して誤判定しないかは本番ログで継続観察する。

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

## 2026-10-01 追補: 診断ログ（1024字打ち切りの原因特定用）

### 目的

2026-09-30の実装で、`talk-*.txt`/`raw-*.jsonl` に記録した本文（`android.messages` 最後の要素の `text`）が **1024文字ちょうどで打ち切られる例が3件**実測で確認された（原本1127字/1183字/3540字 → いずれも記録1024字）。推測で直さず、まず事実を集めるための診断ログ機構を追加した。**送信機能は追加していない。`android.permission.INTERNET` は引き続き付与していない**（`aapt dump badging` で確認。下記）。

### 実測で判明した「2種類の通知」の仕様

対象端末では、LINEは1件の着信メッセージに対して**2つの別々の `StatusBarNotification`** を飛ばす。`id`/`tag` が異なるため、通知リスナーからは別々の `onNotificationPosted` 呼び出しとして届く。

1. **BigTextStyle側**: `id=16880000`, `tag=null`。`extras` の `android.template` が `"android.app.Notification$BigTextStyle"`。
   - `android.title` = **送信者名**（1対1の個別送信者名、またはグループ内の発言者名）
   - `android.subText` = **グループ名**
   - `android.text` = 折りたたみ時の本文（短縮版のことがある）
   - `android.bigText` = 展開時の本文
   - `android.messages` は存在しない。
2. **MessagingStyle側**: `id=1351171955`, `tag` に `NOTIFICATION_TAG_MESSAGE` を含む。`extras` の `android.template` が `"android.app.Notification$MessagingStyle"`。
   - `android.title` = `"グループ名: 送信者名"` の形
   - `android.conversationTitle` = グループ名
   - `android.messages` = `Parcelable[]`（要素は `Bundle`。`text`/`sender`/`time` を持つ）
   - これまでの実装はこちら側の `android.messages` 最後の要素のみから記録しており、1024字打ち切りが観測されたのもこちら側。

さらに、グループの未読が溜まったときの**集約通知**（`android.summaryText` が `"NNNN件の新規通知"`、`android.text` が `"999+件の新規メッセージ"` のようなもの）も届く。`android.messages` も `android.bigText` も持たないため、個別メッセージの本文としては扱えない。

この整理を踏まえ、グループ名・送信者名の決定順を変更した（`LineNotifyListenerService#resolveGroup`/`handle`）:
- グループ名: `android.conversationTitle` → `android.subText` → `android.title` の `": "` より前
- 送信者: `android.messages` 該当要素の `sender` → `android.title` の `": "` より後 →（templateがBigTextStyleのときは `android.title` 全体）

`talk-*.txt`/`raw-*.jsonl` への書き出しは **tag に `NOTIFICATION_TAG_MESSAGE` を含む通知（MessagingStyle側）だけ**に限定した。BigTextStyle側は診断ログと、下記の「本文の最長採用」の比較材料としてのみ使い、二重記録はしない。集約通知（`messages` も `bigText` も無いもの）は診断ログにのみ記録し、`raw`/`talk` には一切書かない。

### 診断JSONL（`diag-YYYYMMDD.jsonl`）

`LineNotifyListenerService#appendDiagRecord` が、`jp.naver.line.android` の通知を受けたら**対象グループの絞り込みより前に**、集約通知も含めて全件を1行追記する（絞り込みをかけると比較対象が欠けるため）。フィールド:

- `postTime`（記録処理時刻, ISO8601）、`key`（`sbn.getKey()`）、`id`（`sbn.getId()`）、`tag`（`sbn.getTag()`）、`template`（`android.template`）、`flags`（`notification.flags` の整数）、`when`（`notification.when`, ISO8601）
- `len_text`/`len_bigText`/`len_title`/`len_subText`/`len_conversationTitle`/`len_summaryText`/`len_tickerText`: 各フィールドの文字数
- `messagesCount`、`messages`: `android.messages` の各要素を `{sender, len, time}` の配列にしたもの（**全要素**。従来は最後の1件のみだった）
- `longestField`/`longestLen`: `text`/`bigText`/`messages[i]` のうち最長のものの名前と文字数
- `longestText`: その最長フィールドの全文（1024字打ち切りの有無を比較するために全文を入れる。本文を通知にもログにも出さない従来方針の例外として、診断目的でここだけ全文を記録する）
- `interactive`（`PowerManager#isInteractive()`）、`keyguardLocked`（`KeyguardManager#isKeyguardLocked()`）
- `title`/`subText`/`conversationTitle`: 全文（グループ名・送信者名の判定根拠を後から追えるようにするため）

### 本文選択を「最長」に変えた理由と実装

`talk-*.txt`/`raw-*.jsonl` に書く本文は、`messages[i].text` / `android.bigText` / `android.text` のうち最も長いものを採用するように変更した（`LineNotifyListenerService#pickLongest`）。理由: 1024字打ち切りが `android.messages` 側で起きている以上、同じ着信メッセージについて別経路（BigTextStyle側の `android.bigText`）に全文が残っている可能性があり、それを埋め合わせられるようにするため。

実装上の注意点（design.mdに明記が無かったための判断）: BigTextStyle側とMessagingStyle側は**別の `StatusBarNotification`**（`id`/`tag` が異なる）として届くため、同一メッセージであることを直接突き合わせる共通IDが存在しない。実装では、BigTextStyle側を処理した際に `(group, sender)` をキーに `text`/`bigText` を一時キャッシュ（`LineNotifyListenerService` 内の `BIGTEXT_CACHE`、最大20件のLRU）しておき、後続のMessagingStyle側の該当メッセージ処理時に同じ `(group, sender)` で取り出して比較する。**取り出したら即座にキャッシュから消費する**（同じ相手との会話が続いた場合に、古い候補を別の新しいメッセージへ誤って流用してしまう事故を避けるため。比較材料が見つからず素通りする方が、内容が化けるより害が小さいと判断した）。BigTextStyle側がMessagingStyle側より後に届いた場合は突き合わせに失敗し、`messages[i].text` がそのまま採用される＝**この順序ズレのケースは未対応・未検証**。

`raw-*.jsonl` の `source` フィールドには採用元（`messages[i]`/`bigText`/`text`）を入れる。既存フィールドは削除せず、`len_text`（比較に使った `android.text` 候補の文字数）、`len_bigText`（同 `android.bigText` 候補の文字数）、`len_messages_max`（`android.messages` 全要素中の最長文字数）を追加した。

### `android.messages` の全要素記録と重複排除

従来は `android.messages` の最後の1件のみを記録していたが、全要素をそれぞれ1レコードとして `raw-*.jsonl`/`talk-*.txt` に書くように変更した（`LineNotifyListenerService#handle` のループ処理）。各要素の `time` を時刻に使う。

同一要素が後続の通知更新で再度現れうるため（LINEの通知は会話が続くたびに `android.messages` を更新して再送してくるのが通例）、`NotifyStore` に `(key, time, sender) → 記録済み文字数` を最大50件のリングで保持し（`NotifyStore#getRecordedLen`/`recordLen`）、同じ `(key, time, sender)` で前回より本文が短いか同じなら書かず、長ければ書く。`raw-*.jsonl` の `supersedesLen` に前回記録時の文字数（無ければ0）を入れる。

実装上の判断（design.mdに永続化方法の指定が無かったため）: このリングは `SharedPreferences` へは永続化せず、`NotifyStore` 内の静的配列としてプロセス内メモリにのみ保持する。通知リスナーサービスのプロセスが再起動されればリングは空に戻り、直後の通知は `supersedesLen=0` として記録される＝まれに重複行が残り得るが、長さ比較の目的上「データが欠落する」より実害が小さいと判断した。

### 削除ログ（`removed-YYYYMMDD.jsonl`）と解釈上の注意

`onNotificationRemoved(StatusBarNotification sbn)` を実装し、`jp.naver.line.android` の通知が削除されたときに1行追記する（`LineNotifyListenerService#handleRemoved`）。フィールドは `postTime`、`key`、`id`、`tag`、`when`、`interactive`、`keyguardLocked`。

**解釈上の注意（実装コメントにも明記済み）**: この記録は「通知が消えた」事実だけを機械的に残すものであり、**メッセージの送信取消（アンセンド）と、ユーザーが通知を既読にした場合を区別できない**。どちらの場合も通知自体は同じように削除されるため、`removed-*.jsonl` 単体では判定できない。取消かどうかの判定は、同じ時間帯の端末操作ログや利用者の記憶などの他の手がかりと合わせて、人間が後から行う。

### INTERNET権限（変更なし）

今回の変更でも `android.permission.INTERNET` は付与していない。`aapt dump badging out/app-debug.apk` の `uses-permission`/`uses-implied-permission` 行:

```
uses-permission: name='android.permission.WAKE_LOCK'
uses-permission: name='android.permission.WRITE_EXTERNAL_STORAGE'
uses-permission: name='android.permission.READ_EXTERNAL_STORAGE'
uses-implied-permission: name='android.permission.READ_EXTERNAL_STORAGE' reason='requested WRITE_EXTERNAL_STORAGE'
```

`INTERNET` は含まれない。`READ_EXTERNAL_STORAGE` は `WRITE_EXTERNAL_STORAGE` に伴う implied permission であり新規追加ではない。

### 未対応・不明点（本追補分）

- BigTextStyle側とMessagingStyle側の到着順序が逆転した場合（MessagingStyle側が先に届く場合）の突き合わせは未対応。その場合は `messages[i].text` がそのまま採用される（従来どおりの1024字打ち切りが残る可能性がある）。
- `(group, sender)` が同一の別メッセージが短時間に連続した場合、BigTextStyleキャッシュの取り違えが起きないかは実機ログでの確認が望ましい（設計上は取り出し消費で誤流用を防いでいるが、2通知が並行して複数組届く状況は未実測）。
- 集約通知の判定条件（`messages` も `bigText` も無い）は実測1パターンのみに基づく簡易判定であり、将来LINEが集約通知に `bigText` を持たせる変更をした場合は誤判定しうる。
- `longestText`（診断ログ）は本文の全文を記録するため、他のログと同様に `Download/sa-line-notify/` 配下にのみ保存され、送信・外部転送は一切行われない点を運用時に再確認すること。

## 追補 2026-10-08 段階2の設計（LINE操作をアプリへ移す）

### 判断の根拠（recon 2026-10-07〜08、推測なし）

1. **ADB版はLINEの要素をすべてノードのテキストで特定している**。`/root/line-auto-export/flow.sh:52,54,57,60,64` の `tap_by`/`find_scroll` に渡す正規表現は
   `text="WeGo売ります・BOX`（ホームのショートカット、前方一致）／`content-desc="Menu ボタン"`／`text="設定"`／`text="トーク履歴を送信"`／`text="Termux"`。
   座標は `tap_by()` が `uiautomator dump` の `bounds` からその場で計算している（`flow.sh:19,23`）＝固定座標ではない。
   `uiautomator dump` が読むのは **AccessibilityService が読むのと同じノードツリー**であり、この経路は本番で 2026-10-07 に44回成功している。
   → **LINEの各画面のノードは取得できると実証済み**。アプリ側は `ACTION_CLICK`（クリック可能な祖先へ委譲）で同じ操作ができ、座標計算が不要になるぶん ADB版より堅い。
2. **例外が1つある**: Termuxの保存ダイアログの `EDIT` ボタンは **uiautomator に露出しない**（`/root/line-auto-export/auto-export.sh:13` のコメント、2026-09-17 スクリーンショットで確認）。
   ADB版も固定座標 `EDIT_X=872, EDIT_Y=1237`（画面1080x2340）でタップしている。
   → アプリ側も**この1点だけは座標ジェスチャ**にする（比率 x=0.8074, y=0.5287）。ADB版と同じ脆さであり、悪化はしない。
3. 送信（salesanchorへのPOST）は Termux内の `client.py` が担い、宛先は固定HTTPS（`client.py:22`）。Wi-Fi/モバイルを区別するコードは1行も無い。
   → **アプリにINTERNET権限は追加しない**（誤送信の構造的防止を維持）。段階2でもアプリは「LINEのUIを操作してTermuxへ渡す」までを担う。

### 実装範囲（段階2のみ。スケジューラ・使用中スキップ・再ロックは段階3）

| 手順 | 操作 | 判定（到達確認） | 失敗時の段階名 |
|---|---|---|---|
| 1 | ホームへ（`performGlobalAction(GLOBAL_ACTION_HOME)`） | 1.5秒待つ（ADB版 flow.sh:51 と同値） | - |
| 2 | ショートカットをクリック（テキスト**前方一致** `WeGo売ります・BOX`） | ノードが見つかること | `shortcut` |
| 3 | トーク画面（LINE）の到達 | **アクティブウィンドウのパッケージ名が `jp.naver.line.android` になること**（`getRootInActiveWindow().getPackageName()`。ノード経路のみで到達を判定できる＝ショートカットのタップが空振りした場合と、別グループが開いた場合を区別するため） | `open_chat` |
| 3b | **誤爆防止**: 開いたトークが期待グループか検証 | 期待グループ名（既定 `WeGo売ります掲示板グループ`、`NotifyStore` の対象グループ名設定を流用）のノードが在ること。無ければ**ここで中止し、Menu以降へ進まない** | `group_mismatch` |
| 4 | Menuボタン（`content-desc` 完全一致 `Menu ボタン`） | - | `menu_button` |
| 5 | メニュー到達 | `設定` のノードが見つかること | `open_menu` |
| 6 | `設定` をクリック（見つからなければスクロールして再探索、最大4回） | - | `settings_item` |
| 7 | 設定画面の到達 | `トーク履歴を送信` のノードが見つかること | `open_settings` |
| 8 | `トーク履歴を送信` をクリック（同じくスクロール再探索） | - | `export_item` |
| 9 | 共有シートの到達 | `Termux` のノードが見つかること | `share_sheet` |
| 10 | `Termux` をクリック | - | `termux_target` |
| 11 | `EDIT` を**座標タップ**（比率 0.8074, 0.5287） | ダイアログはノードに露出しないため、ウィンドウのクラス名 `TermuxFileReceiverActivity` を **最大5秒**ポーリング（ADB版 auto-export.sh:154 の `seq 1 10`×`sleep 0.5`＝5秒と同値）→ 検出したら**1秒待って**タップ（同:156 の `sleep 1` と同値）。5秒で検出できなくても**タップは行い**、診断に `editクラス未検出` を残す（ADB版はここで失敗扱いにするが、このダイアログはそもそもノードに露出しないため、アプリ側はクラス名が読めないことを失敗とみなさない） | `edit_button` |
| 12 | 後片付けは**何もしない** | ADB版の BACK×3（flow.sh:75-78）は**本番では実行されない**: `auto-export.sh:143` は `flow.sh 1 keep` と呼び、`flow.sh:73` の `keep` 分岐で後片付けの手前で `exit 0` する。本番は EDIT タップ後、`outbox.sqlite3` の送信結果を最大240秒待ってから HOME+SLEEP する（auto-export.sh:159-170）。**EDITタップ直後にBACKを撃つと保存ダイアログを取り消す恐れがある**ため、段階2では画面をそのまま残す。HOME・再ロックは段階3の範囲 | - |

段階名は **ADB版 flow.sh と同じ語**（`shortcut`/`open_chat`/`menu_button`/`open_menu`/`settings_item`/`open_settings`/`export_item`/`share_sheet`）に揃える。
理由: 既存の `auto-export.log` の失敗履歴（例 2026-10-07 07:03 の `open_settings`）と直接比較できるようにするため。`group_mismatch`・`termux_target`・`edit_button` は段階2で新設。

### 画面遷移の判定方法（重要な設計判断）

ADB版は `dumpsys window | grep mCurrentFocus`（flow.sh:7）でActivity名を見ているが、**アプリは dumpsys を実行できない**。代替として:

- **判定は「次の画面にある既知のノードが見つかること」で行う**（上表の「判定」列）。ノード取得が実証済みの手段であり、これだけで遷移を待てる。
- `onAccessibilityEvent` の `TYPE_WINDOW_STATE_CHANGED` から得られる `event.getClassName()` は **記録（診断）と、手順11のTermuxダイアログ待ちにのみ**使う。この経路は本端末で未検証のため、判定の本筋には置かない。
- **プライバシー**: 記録するのはクラス名とパッケージ名のみ。LINEのメッセージ本文・ノードのテキストは一切記録しない。記録はフロー実行中のみ行い、終了時に破棄する。

### 待ち時間（ADB版と同値に揃える）

- ノード待ちのポーリングは300ms間隔・期限10秒（ADB版 `wait_focus` の 20×0.5秒＝10秒と同じ予算。flow.sh:37-45）
- スクロール再探索は最大4回（flow.sh:26-36 の `find_scroll`）。スクロールは `ACTION_SCROLL_FORWARD` を先に試し、できなければ `GestureCompat.swipe` で比率 (0.5,0.7265)→(0.5,0.4701)・800ms（flow.sh:31 の `input swipe 540 1700 540 1100 800` と同値）
- クリック後の安定待ちは1秒（flow.sh:29,63 と同値）
- **実装形式**: `Handler#postDelayed` の連鎖のみ。AccessibilityServiceのコールバックはメインスレッドで動くため、`Thread.sleep` でのブロックは禁止（既存のロック解除フローと同じ作法）

### 起動口（既存の RUN は変えない）

| アクション | 動作 |
|---|---|
| `jp.salesanchor.lineexport.RUN` | **従来どおりロック解除のみ**（2026-10-07 に実機10/10で確認済みの経路。回帰比較用に温存する） |
| `jp.salesanchor.lineexport.EXPORT` | LINE操作のみ（解除済み前提。段階2の単体検証用） |
| `jp.salesanchor.lineexport.RUN_ALL` | ロック解除 → 成功したらLINE操作（本番の形） |

Termux(proot)内からADBなしで撃てることは 2026-10-07 に実測済み:
`CLASSPATH=/data/data/com.termux/files/usr/libexec/termux-am/am.apk /system/bin/app_process -Xnoimage-dex2oat / com.termux.termuxam.Am broadcast --user 0 -a <action>`
（`--user 0` を省くと `SecurityException: … asks to run as user -2 … requires INTERACT_ACROSS_USERS` で失敗する）。**アプリが受信したかは未確認**（検証にはADB復旧後の `dumpsys notification` が必要）。

### 検証方法（段階2の合否）

| # | 基準 | 検証方法 |
|---|---|---|
| 2-1 | APKがビルドできる | `tools/line-auto-export-app/build.sh` が成功し、`aapt dump badging` に `INTERNET` が**無い**ことを確認 |
| 2-2 | 既存のロック解除が変わらない | `RUN` の経路のコード差分が「ノード検索ヘルパーの移動のみ」であること（タイミング定数・ラベル・判定順を変えない）＋実機で `RUN` 3回成功 |
| 2-3 | LINE操作が通る | 解除済み状態で `EXPORT` を5回。共有シートまで到達し、Termuxの保存画面に遷移し、`outbox.sqlite3` の `events` に送信結果が入る |
| 2-4 | 失敗段階が分かる | ショートカット名を誤った値に変えて `EXPORT` → 通知に `shortcut` が出る |
| 2-5 | 誤爆防止が効く | 期待グループ名を別の文字列に変えて `EXPORT` → `group_mismatch` で中止し、Menu以降へ進まない |
| 2-6 | 通し運転 | `RUN_ALL` を画面消灯＋ロック状態から5回。解除→書き出し→取り込みまで通る |

2-3以降は**実機とADB（インストール・通知の読み取り）が必要**。2026-10-08 03時点でADBは接続不能（ペア設定の再実施待ち）のため、本追補の実装ではビルド（2-1）と差分レビュー（2-2）までを行い、実機検証は復旧後に行う。

### 弊害・未確認（段階2分）

- Termuxの `EDIT` だけは座標タップのままで、端末の画面サイズ・Termuxの更新で位置が変わると失敗する（ADB版と同じ弱点）。
- トーク画面に期待グループ名のノードが実際に見えるかは未検証。見えない場合は `group_mismatch` で毎回中止するため、最初の実機検証で必ず確認する（見えない場合はタイトル以外の手がかりへ設計変更が必要）。
- `TYPE_WINDOW_STATE_CHANGED` のクラス名が取れるかは未検証。取れなくても手順11以外は判定に影響しない。
- LINEのUI（ラベル文字列）が変わると失敗する。ADB版と同じ弱点であり、ラベルは定数として1箇所にまとめる。

## 追補 2026-10-08 実機1回目の結果：不具合2件（アプリ経路の初回通し）

ADBが接続不能のまま、**ADBを一切使わずに**実機検証を行った初回。経路は「proot内から Termux同梱 `am` で宛先名指しブロードキャスト → アプリ」。

### 確定した事実

- **合図はアプリに届く**（10:39:56 の `DIAG_WINDOWS` で通知タイトルが `画面診断 v0.2.0-stage2` になり、版付きの新APKが応答したことで確定）。
  版が同じAPKだと入替を判定できず切り分けが止まったため、**APKの `versionName` を上げ、診断通知のタイトルに版を出す**ようにした（`UnlockAccessibilityService#versionLabel`）。以後、実機に入れる版は必ず上げる。
- **ショートカットのクリック→LINE起動→対象トークの表示までは、アプリのノードクリックだけで動く**（実機で目視確認）。`shortcut:1547ms`。
- 失敗は `段階: open_chat`（`open_chat:10004ms` でタイムアウト、全体11551ms）。`outbox.sqlite3` に新規行なし、Termuxの `~/downloads` にも新しい書き出しファイルは届かず。

### 不具合1: 前面アプリの判定（`NodeOps.activePackageName`）

`getWindows()` の**先頭ウィンドウのrootのパッケージ名**を返す実装になっていたため、ステータスバー等（`com.android.systemui`）を拾って `jp.naver.line.android` と一致しなかった。
画面上はLINEが開いているのに `open_chat` で10秒待ち続けたのはこれが原因。

**直し方**: 「先頭のウィンドウのパッケージ名を返す」ではなく「**いずれかのウィンドウのrootが期待パッケージか**」を判定する（`getWindows()` の全ウィンドウ＋`getRootInActiveWindow()` のフォールバック）。
後段でグループ名のノードを確認するため、ここを緩めても誤爆防止は損なわれない。

### 不具合2: グループ名の照合（完全一致では通らない）

実機のトーク画面のタイトルは **「WeGo売り... (480)」**＝**途中で省略され、末尾に人数が付く**。期待値 `WeGo売ります掲示板グループ` の完全一致では一致しない。

（記録時の注意: 利用者が画面を書き写した文字列はカタカナ「リ」になっていたが、**実機はひらがな「り」(U+308A)** で正しい。
根拠: LINE自身が 2026-10-07 17:36 に書き出したファイル名 `[LINE] WeGo売ります掲示板グループのトーク.txt` の文字コードを確認した。
したがって**カナ揺れの吸収は実装しない**。`String.contains()` は符号位置が厳密一致なので、もし将来カナ表記が実際に揺れたら別途対処が必要。）

**直し方**: 正規化してから**双方向の部分一致**で判定する。
1. 比較前に、末尾の `(数字)`・`…`/`...`・前後の空白を落とす
2. 正規化後の「ノードの文字列」と「期待グループ名」の**どちらかが他方を含む**なら一致とみなす
3. 誤爆防止が骨抜きにならないよう、**比較に使う文字列が6文字未満の場合は一致とみなさない**

### 失敗通知に足す診断

`open_chat` で失敗したとき、**実際に見えていたパッケージ名**（最大3件、重複除去）を通知本文に載せる。今回これが載っていれば原因は一目で分かった。パッケージ名のみでメッセージ本文は含めない。

## 追補 2026-10-08 実機2回目：到達判定とスクロール探索を混同していた（設計の誤り）

修正版 `0.2.1-stage2` での結果（通知より）: `段階: open_menu / 13379ms / shortcut:1535ms open_chat:1665ms …`

- **不具合1（前面アプリ判定）と不具合2（グループ名の照合）はどちらも直った**: `open_chat` は1665msで通過し、グループ照合も失敗段階になっていない。`menu_button`（右上メニューのクリック）も通過。
- 失敗は `open_menu`＝「メニュー画面の到達判定」。

### 誤りの内容

手順表で `open_menu` の到達判定を「`設定` のノードが見つかること」とし、その**次の**手順6で「`設定` を見つからなければスクロールして再探索」と書いていた。
これは**判定と探索を二重化した設計ミス**。メニューは縦に長いシートで、`設定` は**最初の表示範囲より下にあることがある**。
アクセシビリティのノードツリーには**画面外の項目は載らない**ため、スクロールする前の到達判定で10秒待っても見つからず、スクロール再探索に進む前に失敗していた。

ADB版はこの2つを分けられていた: `wait_focus ChatMenuActivity`（Activity名で到達を見る、flow.sh:55）→ `find_scroll 'text="設定"'`（flow.sh:57）。
**アプリはActivity名を判定に使えない**（dumpsysが無く、`TYPE_WINDOW_STATE_CHANGED` のクラス名は本端末で未検証のため判定の本筋に置かない方針）。

### 直し方（確定）

**到達判定を別手順として持たず、スクロール探索に統合する。**

| 旧 | 新 |
|---|---|
| 手順5 `open_menu`（`設定` のノードを10秒待つ）＋手順6 `settings_item`（スクロール再探索してクリック） | **手順5を削除**。1秒の落ち着き待ち → `設定` をスクロール探索してクリック（即時探索＋最大4回スクロール、flow.sh:26-36 と同値）。失敗段階は **`settings_item`** |
| 手順7 `open_settings`（`トーク履歴を送信` のノードを10秒待つ）＋手順8 `export_item` | **手順7を削除**。同様に1秒待ち → スクロール探索してクリック。失敗段階は **`export_item`** |

手順9（共有シート＝`Termux` のノードを待つ）は変更しない。ADB版も共有シートではスクロールせずに `text="Termux"` を探しているため（flow.sh:64、auto-export.sh:150）。

**段階名 `open_menu` と `open_settings` は、アプリ経路では到達不能になる**（ADB版のログと語を揃える方針は維持するが、この2語はアプリでは出ない）。コードにその旨をコメントで残す。

### 失敗通知に足す診断（クラス名の検証も兼ねる）

失敗時に、記録済みの**ウィンドウのクラス名を最新3件まで**通知本文に載せる（例: `ChatMenuActivity`）。
これで「`TYPE_WINDOW_STATE_CHANGED` のクラス名がこの端末で実際に取れるのか」も同時に実測できる。取れることが分かれば、将来 ADB版と同じ粒度の到達判定に戻せる。クラス名のみで、ノードのテキストやメッセージ本文は含めない。

## 追補 2026-10-08 段階3の設計：アプリ内タイマー（コアタイム5分・夜間30分）

### PO合意

- 2026-10-08「このまま任せていい？更新を5分おきにしたい」→「コアタイムは5分サイクルにしたい」。
- 15分の縛りは `termux-job-scheduler --period-ms` の下限900000（OSの定期ジョブの制約）によるもので、**アプリ内 AlarmManager にすれば消える**。

### 時間帯の根拠（実測 2026-10-08）

端末の実履歴 3,306件・42日分を時刻別に集計した（`parse_android_export` で解析）。

| 時刻帯 | 1日平均 |
|---|---|
| 11〜15時 | 6.9〜8.8件/時（ピーク） |
| 9〜21時 | **全体の84%** |
| 9〜23時 | 全体の91% |
| 3〜7時 | 0.0〜0.5件/時（ほぼ皆無） |

→ **コアタイム 9:00〜21:00 を5分間隔、それ以外を30分間隔**とする。夜間を5分で回しても拾うものが無く、画面点灯の代償だけが残るため。

| 方式 | 1日の実行回数 | 1日の画面点灯（1回30秒換算） |
|---|---|---|
| 一律15分（現状） | 96回 | 約40分 |
| **コア5分＋夜30分（採用）** | **168回** | **約1時間20分** |
| 一律5分 | 288回 | 約2時間20分 |

### 方式

- **新規 `RunScheduler`**（クラス名は任意）: `AlarmManager#setExactAndAllowWhileIdle` で次回を1回だけ張り、**発火のたびに次を張り直す**（固定周期APIは使わない。間隔を時間帯で変えるため）。
- 間隔は発火時刻のローカル時刻で決める。定数は**1か所にまとめる**:
  `CORE_START_HOUR = 9` / `CORE_END_HOUR = 21` / `CORE_INTERVAL_MS = 5*60*1000` / `OFF_PEAK_INTERVAL_MS = 30*60*1000`。
- **次回を張るのは、実行を始める前**（実行中に落ちても連鎖が切れないようにする）。
- 発火時の動作は `RUN_ALL` と同じ（ロック解除 → LINE操作 → 施錠）。`RunReceiver` 経由ではなく
  `UnlockAccessibilityService.requestRunAll(context)` を直接呼ぶ。
- **多重起動の防止**: 既存の `running` ガードを必ず通す（アプリ内タイマーとTermuxの15分ジョブの両方から合図が来るため）。
- **再起動後**: `BOOT_COMPLETED` を受けて張り直す（`android.permission.RECEIVE_BOOT_COMPLETED` を追加。**INTERNET は引き続き付与しない**）。
  加えて `onServiceConnected()`（ユーザー補助の接続時）でも張り直す。アプリ更新・プロセス再生成を安全に拾うための二重化。
- **ON/OFF の手動スイッチ**: 設定画面にトグルを追加し、OFFならアラームを解除する。**暴走時に利用者が自分で止められる手段を必ず用意する**（強い権限で画面を操作する仕組みのため）。既定はOFF（インストール直後に勝手に動き出さない）。
- **Android 12+ の正確アラーム**: targetSdk 23 のため旧扱いで `setExactAndAllowWhileIdle` が使える見込み。
  実行時に使えない場合は `setAndAllowWhileIdle`（不正確）へ落とし、**その旨を結果通知に出す**（黙って精度が落ちるのを防ぐ）。

### 既知の制約（利用者へ説明済み）

- **深いスリープ（Doze）中は、この種のアラームが約9分に1回までに絞られる**（Android公式の仕様）。
  したがって「コア5分」は画面使用中・充電中の値で、**夜間や放置中は9分前後に伸びうる**。
  回避手段として `setAlarmClock()`（Dozeの制限を受けない）があるが、**ステータスバーに常時アラームのアイコンが出る**ため採用しない。
  **まず実測し、9分が許容できない場合に再検討する**。
- 実測の方法: 夜間の `events` の `send` 行の間隔を見る（送信が発生した回の間隔＝実際の発火間隔）。

### Termux の15分ジョブは残す

- アプリ内タイマーに移っても、Termuxの15分ジョブは**記録役と見張り役として残す**:
  `stage='auto'` の履歴、連続失敗の通知、**3時間以上成功が無いときの通知（id 4204）**。
- 二重に合図が飛ぶが `running` ガードで無害。アプリ内タイマーが死んでも15分ジョブが動く＝**二重の安全網**になる。

### 検証方法

| # | 基準 | 検証方法 |
|---|---|---|
| 3-1 | コアタイムに5分間隔で発火する | 画面を消して放置し、`events` の `send` 行の間隔を1時間ぶん確認。**実測値を本書に追記する** |
| 3-2 | 夜間は30分間隔になる | 同じく夜間で確認 |
| 3-3 | 深いスリープでの実際の間隔 | 夜間の間隔を実測し、9分制限の影響を数値で記録 |
| 3-4 | 利用者がOFFにできる | 設定画面でOFF → アラームが解除され発火しない |
| 3-5 | 再起動後も動く | 端末を再起動して発火を確認 |
| 3-6 | 多重に動かない | タイマー発火中にTermuxの15分ジョブが合図を出しても二重実行されない |
