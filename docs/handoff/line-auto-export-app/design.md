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
6. `adb shell run-as jp.salesanchor.lineexport ...` またはファイルマネージャで `Download/sa-line-notify/raw-YYYYMMDD.jsonl` と `talk-YYYYMMDD.txt` の中身を確認し、本文・改行・絵文字が欠落なく入っているか、`talk-*.txt` が `tools/termux-line-import/android_parser.py` でパースできる形式になっているかを確認する。

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
   座標は `tap_by()` が `uiautomator dump` の `bounds` からその場で計算している（`tools/line-auto-export/flow.sh:19,23`）＝固定座標ではない。
   `uiautomator dump` が読むのは **AccessibilityService が読むのと同じノードツリー**であり、この経路は本番で 2026-10-07 に44回成功している。
   → **LINEの各画面のノードは取得できると実証済み**。アプリ側は `ACTION_CLICK`（クリック可能な祖先へ委譲）で同じ操作ができ、座標計算が不要になるぶん ADB版より堅い。
2. **例外が1つある**: Termuxの保存ダイアログの `EDIT` ボタンは **uiautomator に露出しない**（`/root/line-auto-export/auto-export.sh:13` のコメント、2026-09-17 スクリーンショットで確認）。
   ADB版も固定座標 `EDIT_X=872, EDIT_Y=1237`（画面1080x2340）でタップしている。
   → アプリ側も**この1点だけは座標ジェスチャ**にする（比率 x=0.8074, y=0.5287）。ADB版と同じ脆さであり、悪化はしない。
3. 送信（salesanchorへのPOST）は Termux内の `tools/termux-line-import/client.py` が担い、宛先は固定HTTPS（`tools/termux-line-import/client.py:22`）。Wi-Fi/モバイルを区別するコードは1行も無い。
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
| 12 | 後片付けは**何もしない** | ADB版の BACK×3（flow.sh:75-78）は**本番では実行されない**: `tools/line-auto-export/auto-export.sh:143` は `tools/line-auto-export/flow.sh 1 keep` と呼び、`tools/line-auto-export/flow.sh:73` の `keep` 分岐で後片付けの手前で `exit 0` する。本番は EDIT タップ後、`outbox.sqlite3` の送信結果を最大240秒待ってから HOME+SLEEP する（auto-export.sh:159-170）。**EDITタップ直後にBACKを撃つと保存ダイアログを取り消す恐れがある**ため、段階2では画面をそのまま残す。HOME・再ロックは段階3の範囲 | - |

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

## 追補 2026-10-08 段階3の方式変更：固定間隔から「投稿の通知で起動」へ（PO決定A）

### 決定の根拠（実データ・2026-10-08）

端末の実履歴3,306件・42日でシミュレーションした結果、**固定間隔はすべて通知起動に劣る**。

| 方式 | 1日の実行回数 | 投稿→送信の平均待ち | 最大待ち |
|---|---|---|---|
| 一律15分（従来） | 96回 | 7.1分 | 14分 |
| コア9-21時5分＋夜30分 | 168回 | 3.9分 | 29分 |
| 一律5分 | 288回 | 2.0分 | 4分 |
| **通知で起動（最短3分間隔）** | **59回** | **0.9分** | **3分** |

理由: **投稿はバースト性が強い**（前の投稿から1分以内21%・5分以内46%・中央値6分）。投稿が無い時間に動いても何も拾えず、バーストは1回の実行でまとめて拾える。
また**「その日の最初の投稿」は42日中26日が0時台**で、時間帯で区切る設計そのものが実態に合わない。

PO決定 2026-10-08: **A（LINEの「メッセージ内容を表示」をONに戻し、対象グループの通知だけに反応する）**。

### 前提と、実測で判明した注意点

- アプリには `LineNotifyListenerService` が既にあり、**対象グループ名（`NotifyStore` の設定・既定 `WeGo売ります掲示板グループ`）に完全一致する通知だけ**を記録している。これをそのまま引き金に使う。
- **通知は投稿の7割前後しか来ない**（2026-10-01の実測: 10:56までに投稿17件に対し通知記録24件＝1投稿につき2レコード来るため実質12件）。トークを開いている間は通知が出ない等。
  → **通知だけに頼らない。保険のタイマーを必ず併用する。**
- **通知の中身が隠れている場合がある**: LINEの「メッセージ内容を表示」がOFFだと `conversationTitle` が空になり（実測 2026-10-08 17:00、title が `LINE` だけになる）、**どのグループか判別できない**。
  その場合は**引き金にしない**（保険タイマーに任せる）。判別できないものを引き金にすると他グループの投稿で無駄に起動する。
- **対象グループの通知が 2026-10-01 10:56 から 10-08 まで0件だった**（他グループは毎日届いていた＝リスナーは正常）。
  **通知が止まっていても送信は止まらない設計にすること**が、この実例から必須だと分かる。

### 方式

| 引き金 | 動作 |
|---|---|
| **対象グループの通知** | **最初の通知から30秒後**に実行（バーストをまとめる。その30秒の間に来た通知は無視して予約を延ばさない＝長いバーストで遅延が無限に伸びるのを防ぐ） |
| **最短間隔（床）** | 前回の実行開始から**3分**未満なら、3分経過時点へ予約を延ばす |
| **保険のタイマー** | 通知が来なくても**30分ごと**に1回実行（`RunScheduler` の間隔を30分固定に変更。コア/オフピークの区別は不要になる） |
| **使用中で見送ったとき** | **5分後に再試行**を予約（design.md KGI 4c の要求。使用中が続く間は5分ごとに再試行） |
| Termuxの15分ジョブ | **残す**（記録役・見張り役。三重の安全網） |

- **予約はすべて AlarmManager で行う**（`Handler#postDelayed` は使わない）。通知リスナーのプロセスはOSに殺されうるため、プロセスをまたいで生き残る必要がある。既存の `AlarmReceiver` に引き金の種別を extra で渡す。
- 前回の実行開始時刻は `SchedulerStore` に保存する（床の判定に使う）。
- **ON/OFFトグルは通知起動と保険タイマーの両方を支配する**（OFFなら何も起きない）。既定OFFは維持。
- 結果通知の本文に**何が引き金だったか**（通知／保険タイマー／再試行）を入れる（診断のため）。

### 期待値（実データからの見積り）

| | 1日の実行 | 平均待ち | 画面点灯（1回30秒換算） |
|---|---|---|---|
| 現状（15分固定） | 96回 | 7.1分 | 約40分 |
| **本方式** | **約60〜75回**（通知59＋保険の空振り分） | **約1分** | **約30〜38分** |

**回数も画面点灯も現状より減り、鮮度は約7倍になる。**

### 検証方法

| # | 基準 | 検証方法 |
|---|---|---|
| 3a-1 | 対象グループの投稿後1分以内に送信される | 投稿の時刻（トーク履歴）と `events` の `send` の時刻の差を10件測る |
| 3a-2 | バーストで無駄に連続実行しない | 1分以内に複数投稿があった回で、実行が1回にまとまっていること |
| 3a-3 | 通知が来なくても30分以内に実行される | 通知アクセスを切って放置し、30分以内に `send` が入ること |
| 3a-4 | 使用中は見送り、5分後に再試行する | 画面オン・ロック解除で放置し、5分間隔で見送りが記録されること |
| 3a-5 | 他グループの通知では起動しない | 対象外グループの投稿だけがあった時間帯に実行が走っていないこと |
| 3a-6 | 中身が隠れた通知では起動しない | `conversationTitle` が空の通知で起動しないこと（保険タイマーのみ） |

## 追補 2026-10-09 実行時間のばらつきと「実行中の帯」の相関（PO決定B：原因未確定のまま運用）

### 事実（実測）

`0.12.0-stage3` 投入（2026-10-09 13:40）の前後で、書き出しフローの所要時間が明確に変わった。

| | 投入前（10-09 の36回） | 投入後（4回） |
|---|---|---|
| 全体 | 中央 **17,618ms** / 最大 **118,436ms** / **16回（44%）が20秒超** | **8,637〜8,791ms**（ばらつき154ms） |
| `edit_button` の `settleMs`（1,000ms指定） | 最大 **54,822ms** | **1,001〜1,002ms** |
| メインスレッド停止の記録（`phase:"stall"`） | — | **監視80分で0件** |

**原因として除外できたもの（すべて実測）**: 深いスリープ（実時間＝起動時間で一致）／ウェイクロックの外れ（`wakeHeldAtEnd=true`）／ノード探索のコスト（`searchMsMax` 15〜31ms）／プロセス凍結（`vis F/ /BFGS`）／CPU不足（正常実行でもアプリのCPU消費は12秒で約60ms）／アクセシビリティイベントの洪水（`typeWindowStateChanged` へ絞った `0.9.0` でも遅い回が発生）／時計の飛び。

**決定的だった観測**: 同一実行・同一 `handler`・2秒差の2つの待ちで、**片方（1,000ms指定）が42,379ms に伸び、もう片方（2,000ms指定の `editLockDelayMs`）は2,002msで正確**だった。スレッド全体やCPU全体の問題では説明できない。

### 原因は確定していない（重要）

`0.12.0-stage3` には**3つの変更が同時に入っている**（①使用中でも即実行 ②常に施錠 ③実行中の帯の表示＋`NodeOps`での自パッケージ除外）。
**1つずつ測り直していないため、どれが効いたかは確定していない。**

**最も疑っているのは③の帯**。帯を出すとアプリが**画面に見えるウィンドウを持つ**ため、OSから見たプロセスの優先度が上がり、`Handler#postDelayed` の配送が後回しにされなくなった——という説明が数字と整合する。**ただし未検証の仮説である。**

### したがって守ること（PO決定 2026-10-09「B」）

- **「実行中の帯」（`RunStatusOverlay`）を安易に外さないこと。** 外すと実行時間のばらつき（最大118秒）が戻る可能性がある。
- 外す・変える必要が生じたら、**外した版で所要時間を10回以上測り直してから**判断する。
- **検知の手段は用意されている**: 実行ログの `overlayShown` が `false` の回に所要時間が伸びていれば、相関の証拠が自然に集まる。定期的に確認する。
- 因果を確定させたい場合の手順: 帯を出さない版を1つ作り、同条件で10回以上測る（PO判断で現時点では実施しない）。

### 再測定の方法（再利用可）
`/sdcard/Download/sa-line-notify/run-YYYYMMDD.jsonl` の `flow:"export", phase:"end"` 行から `elapsedMs`・各段階の `ms`/`upMs`・`settleMs`・`overlayShown` を読む。ADB接続時は `adb -s <endpoint> shell "grep ... run-*.jsonl"` で直接読める。

## 追補 2026-10-09 通知起動が捨てられていた原因（dumpsys alarmで確定）

### 事実（実測）

対象グループの該当通知71件に対し、`trigger=通知` での実行はわずか**9回**だった。15:48:55に通知引き金の実行が走った後、15:50:00〜18:03:34の間に来た該当通知**14件が全部捨てられた**（2時間13分、空白）。

`dumpsys alarm` のAddition historyに、この空白期間中の通知に対応する予約行が無く、待ち行列（pending alarms）にも通知引き金のアラームが無かった＝そもそも予約が作られていなかった（配送の遅延ではない）。

requestCode 2（通知引き金）のPendingIntentの実体は、15:48時点の `PI:aeb8457` から18:46時点の `PI:90af5ff` へ変わっていた。この間にアプリの再インストールは無い（`lastUpdateTime=2026-10-09 13:40:34` のまま）。通知引き金の実行が復帰したのは、この実体が変わったタイミングと一致していた。

### 原因

`RunScheduler.onQualifyingNotification()` は「通知引き金が予約済みか」を `PendingIntent.getBroadcast(..., FLAG_NO_CREATE)` の非nullで判定していた（旧 `isPending()`）。

しかし `AlarmManager#cancel(PendingIntent)` は**アラームを消すだけで、PendingIntent自体は消さない**。`buildPendingIntent()` が `FLAG_UPDATE_CURRENT` のため、cancelの直前にPendingIntentを作り直してはいるが、作り直した後のPendingIntentもcancelでは消えずに残る。このため、一度でも通知引き金のアラームを張ると、`FLAG_NO_CREATE` は以後ずっと非nullを返し続け、`isPending()` は常にtrueを返す＝「予約済み」と誤判定し続け、以後の対象グループ通知がすべて捨てられていた。

この残骸のPendingIntentがいつ・なぜ解放されるか（OS側の内部的な仕組み）は未確認である。実機では18:46に実体が変わって初めて通知引き金の実行が復帰したが、**残骸がOS側で解放される時刻は制御外**という事実までは言えるものの、解放の仕組みの詳細（何がトリガーか等）は未確認のまま断定しない。

### 対処

「予約済みか」の判定を、PendingIntentの有無ではなく、`SchedulerStore` に保存した「通知引き金アラームの発火予定時刻（絶対epoch ms）」で行うように変更した（`SchedulerStore#getNotificationReservedAt`/`setNotificationReservedAt`/`clearNotificationReservedAt`）。

判定は `reservedAt > now`（保存した予定時刻が**未来**のときだけ「予約中」とみなす）。過去の値が残っていても「予約中」とはみなさないため、予定時刻を過ぎたのに何らかの理由で未発火の残骸があっても、次に対象グループの通知が来た時点で新しい予約に張り直される（自己修復する）。`>=` や「0以外なら予約中」にはしていない（それだと発火直後の一瞬だけでなく、床で延ばした後の値がそのまま残るケースなどで誤判定しうるため）。

合わせて、床（FLOOR）で予約を延ばす経路・実行に進む経路・`cancelAll()`（OFF・再構成時）のそれぞれで、保存した予定時刻を更新／消去するようにした。

### 守ること

- **`FLAG_NO_CREATE` の非null/nullを「予約済みか」の状態として使わない。** `AlarmManager#cancel` はPendingIntentを消さないため、一度でもアラームを張ると以後ずっと非nullになり、状態として機能しない。
- 判定は必ず「自分で保存した予定時刻」で行い、「過去の値は予約中とみなさない」（`reservedAt > now`）を守る。
- 実行ログに `flow:"scheduler"` の単発行（`phase: reserve/skip_reserved/defer_floor/fire`）を追加した。今後、通知が捨てられているかどうかはこのログで診断できる（`skip_reserved` が連続していないか、`reserve` の間隔が異常に短くないか等）。

## 追補 2026-10-09 取り込み失敗後に30分空いていた問題（再試行を1回だけ張る）

### 事実（実機2026-10-09）

17:25:09に補完が発火して起動 → `unlock` が `result=failure, stage=PIN入力後もロック中` で終了（4.8秒）→ **その後何も再試行されず、次は17:55:09の補完**だった（丸30分空いた）。

### 原因

`RunScheduler.onAlarmFired()` は補完の発火時に、成功・失敗を問わず必ず `SchedulerStore.setLastComplementAttemptAt(context, now)` を記録する（1分ごとの暴走を防ぐための既存の仕組み。上の追補「取り込みの時間規則」参照）。このため `computeNextComplementAt()` の基準（`max(lastImportAt, lastComplementAttemptAt)`）が常に「今」になり、失敗しても次回の補完は丸々1間隔（コアタイム30分/コア外60分）後になる。

`recordSuccessfulImport()` のjavadocにある「失敗時は呼ばない＝起点が変わらない＝早めに次の補完が来る、安全側」という意図は、上記の `setLastComplementAttemptAt` の記録によって実質的に打ち消されていた。

### 対処

取り込み（ロック解除またはLINE操作）が失敗したら、**5分後に再試行**を予約する（`RunScheduler.scheduleRetryAfterFailure`）。ただし**連続の再試行は1回までに制限**する（`SchedulerStore` の連続再試行回数カウンタが上限 `MAX_CONSECUTIVE_RETRIES`（=1）に達していれば予約せず、元から張られている補完に任せる）。取り込み成功（`recordSuccessfulImport`）で回数をリセットする。

呼び出し元は2か所: `UnlockAccessibilityService#checkResult()` のロック解除失敗の分岐（RUN_ALLのときだけ）、`LineExportFlow#finish(false, ...)`（`lockOnFinish==true` のときだけ、つまりRUN_ALLのときだけ）。どちらも手動検証用の単体経路（RUN単体／EXPORT単体）では呼ばない。

### 1回に絞った理由（PINロックアウト対策）

失敗の型のひとつが `PIN入力後もロック中` であり、PIN入力の試行が増えるとAndroid側のロックアウト（誤入力の連続で待たされる状態）に近づく。30分あたりのPIN入力試行を最大2回（補完1回＋再試行1回）に抑えるため、意図的に1回に絞っている。上限を増やすのはPO判断。

### 守ること

- `computeNextComplementAt` と `setLastComplementAttemptAt` は触らない。これらは1分ごとの暴走を防いだ修正（上の追補「取り込みの時間規則」参照）であり、今回の対処はその上に積む形にした。
- `scheduleRetryAfterSkip`（使用中見送り用、既存）とは統合しない。見送りは使用中が続く限り無制限に5分ごと再試行するのに対し、失敗後の再試行は連続1回までに制限する、という役割の違いがあるため。

### 未決（PO判断待ち）

画面ONかつロック中のとき（PIN入力後もロック中になりやすい状況）に、そもそもPINを打たずに見送るかどうかは今回手を付けていない。PO判断待ち。


## recon

調査の記録は `docs/handoff/line-auto-export-app/recon.md`（確かめた事実と file:line 引用）。本設計はそこで確認した制約（UID分離によりTermux私有のPINを読めない／ユーザー補助は制限付き設定の解除が必要／API23のandroid.jarでは `canPerformGestures` が無い）を前提にしている。

## 追補 2026-10-10 使用中に起動した回は施錠しない／解除の計測を実行ログへ

### PO決定の変更（重要）

旧PO決定（`UnlockAccessibilityService.startUnlockFlow`のコード内コメントにあった表現）: 「終了後は必ず施錠する」＝開始時にロックされていなくても、終了時には施錠する（`lockOnFinish=true`）。

**新PO決定（2026-10-10）**: 利用者がスマホを使っている最中（＝開始時に既に解除済み）に起動した回は、**終了後に施錠しない**。画面消灯・ロック状態から起動した回は今のまま施錠する。

理由: 使用中に勝手に画面が消えると利用者の操作を妨げるため。「使用中でも即実行する」自体（2026-10-08 PO決定）は変えていない。施錠だけをやめた。

### `lockOnFinish` と `armRetryOnFailure` を分離した理由

`LineExportFlow.finish()` は、`lockOnFinish` を「施錠するかどうか」だけでなく「本番のRUN_ALL実行かどうか」の代用にも使っていた。`lockOnFinish==false` の経路（EXPORT単体の手動検証用）には、失敗後の再試行（`RunScheduler.scheduleRetryAfterFailure`）を張る処理が元から入っていない。

今回「開始時に既に解除済みだった回」も `lockOnFinish=false` にする必要があったため、単純に `false` を渡すと、この回（本番実行）でも再試行が張られなくなる退行が起きる。これを避けるため、施錠の有無（`lockOnFinish`）と「本番実行として失敗後の再試行を張るか」（`armRetryOnFailure`）を別のフラグに分けた。

呼び出し元の組み合わせ（`UnlockAccessibilityService#startExportFlow`）:

| 呼び出し元 | lockOnFinish | armRetryOnFailure |
|---|---|---|
| `requestExport`（EXPORT単体・手動検証） | false | false |
| `startUnlockFlow`の「既に解除済み」分岐（今回の変更） | false | true |
| `checkResult()`の解除成功後の続行 | true | true |

`LineExportFlow.finish()` 内の `RunScheduler.scheduleRetryAfterFailure` 呼び出しは、`!lockOnFinish` の経路（`armRetryOnFailure==true`のサブ分岐）と `lockOnFinish==true` の経路の両方に、`if (!success && armRetryOnFailure)` の条件で入れた。

**1回の`finish()`呼び出しで2回呼ばれないことの確認**: `finish()` は `if (!lockOnFinish) { ...; return; }` のブロックの中で、さらに `armRetryOnFailure` の真偽で分岐するが、どちらのサブ分岐も最後に `return` する。このブロック自体の末尾にも `return` があるため、`lockOnFinish==true` 用のコード（`scheduleRetryAfterFailure`呼び出しを含む）は `!lockOnFinish` のときには実行されない。したがって3つの分岐（`!lockOnFinish && armRetryOnFailure` / `!lockOnFinish && !armRetryOnFailure` / `lockOnFinish`）は常に排他であり、`scheduleRetryAfterFailure` は1回の`finish()`呼び出しにつき最大1回しか呼ばれない。

### `!lockOnFinish` でも待ち合わせ（`drainCallbackSummary`・`LOCK_DELAY_AFTER_EDIT_MS`）を残した理由

2026-10-08 実機（0.3.0-stage2）で、EDITタップ直後に施錠すると、`dispatchGesture` の再生が終わる前に画面がロックされてジェスチャが取り消され、Termuxの保存ダイアログのEDITが押されずに送信が止まる不具合があった。この教訓から、`lockOnFinish==true` の経路は `GestureCompat.drainCallbackSummary()` と `LOCK_DELAY_AFTER_EDIT_MS`（2秒）の待ちを通してから施錠するようになっている。

「開始時に既に解除済みだった回」（`armRetryOnFailure==true`、本番実行）は施錠自体をやめるが、EDITタップ直後に画面状態（ウェイクロック解放でスリープに入る等）が変わることによる同種のリスクは残るため、**施錠（`performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN)`）だけを行わず、`drainCallbackSummary()`と`LOCK_DELAY_AFTER_EDIT_MS`の待ちはそのまま通す**ようにした。EXPORT単体の手動検証（`armRetryOnFailure==false`）は元から即解放でよく、変えていない。

### 実行ログ `export` の `phase:"end"` への追加（`lockSkipped`）

`locked` フィールドは、施錠を試みていない回は（既存のまま）`null`（出さない）。`false` だと「施錠を試みて失敗した」と区別がつかないため。代わりに、**施錠を行わなかった回だけ** `lockSkipped: true` を出す（行った回は出さない）。これで「使用中に起動して施錠しなかった回」が後から数えられる。

### 解除の計測を実行ログへ追加した理由

`UnlockAccessibilityService` は `keypadConfirmedAttempt`（何回目のスワイプでキーパッドが出たか）と `keypadConfirmedElapsedMs`（起床からキーパッド確認までのms）を計算していたが、失敗通知の本文（`keypadDiag`）にしか出しておらず、実行ログからは「あと少しで間に合わなかったのか、全く別の原因か」が判別できなかった。

`logUnlockEnd`が書く`unlock`の`phase:"end"`行に、成功・失敗の両方で次を追加した:
- `keypadAttempt`: キーパッドを確認できたスワイプ回数（確認できなかった回は0のまま出す）
- `keypadMs`: 起床から確認までのms（未確認なら出さない＝フィールド自体を省略。`-1`は出さない）
- `swipeAttempts`: 実際に試したスワイプ回数
- `screenOnAtStart`・`keyguardAtStart`: 開始時の画面状態。既に`phase:"start"`行に`screenOn`/`keyguardLocked`として出ているが、end行だけを集計するときにrunIdでの突き合わせが要らないよう、end行にも持たせた

これに合わせ、`swipeAttempt`/`keypadConfirmedAttempt`/`keypadConfirmedElapsedMs`のリセットを、従来の「PIN読み込み成功後（wake直前）」から`startUnlockFlow`の先頭（分岐より前）に移した。見送り（`skipped`）や`skipped_to_export`、PIN未設定の失敗など、PIN入力に進まない分岐でも前回実行の値が残ったままログに出てしまうのを避けるため。

**定数は意図的に変えていない**: `POST_WAKE_DELAY_MS`・`KEYPAD_CHECK_TIMEOUT_MS`・`KEYPAD_MAX_SWIPE_ATTEMPTS`・`KEYPAD_CHECK_INTERVAL_MS`の値は今回変更していない。目的はまずデータを取ることで、粘りを増やすかどうかは実測データを見てから判断する（推測で変えない）。

### 実測の根拠（2026-10-10）

- `キーパッド未出現` の失敗の所要は約6.2〜6.4秒で、定数の合計（`POST_WAKE_DELAY_MS`=1500 ＋ `KEYPAD_CHECK_TIMEOUT_MS`=1500 × `KEYPAD_MAX_SWIPE_ATTEMPTS`=3 ＝ 6000ms）と一致する。成功回の`elapsedMs`は約5.9秒だが、これはPIN入力と検証を含む全体時間であり、キーパッド確認の余裕そのものは読み取れない。
- 開始時の画面状態ごとの成否（実機ログ集計）:
  - 10-09: 消灯ロックで成功43・失敗1 ／ 点灯ロックで成功10・失敗1
  - 10-10: 消灯ロックで成功24・失敗20 ／ 点灯ロックで成功0・失敗3

## 追補 2026-10-11 遮断モードの帯（検証用）

### 目的

使用中の衝突（3日間で33回、うち失敗5回＝失敗率15%。消灯からの1.5%の約10倍）を、見送りではなく「実行中は操作させない」で解決できるかを確かめる。PO方針は「取り込み優先」。

### 確かめる事実

全画面でタッチを消費する`TYPE_ACCESSIBILITY_OVERLAY`を出したとき、`dispatchGesture`のタップが帯に吸われるか。吸われるならこの方式は不可。

### 実装

`RunStatusOverlay.show(Context, boolean blocking)`に遮断モードを追加した。`blocking==false`（既定）は従来どおり上端の細い帯・`FLAG_NOT_TOUCHABLE`で、挙動を一切変えていない（PO決定B「安易に外さない」を維持）。`blocking==true`のときだけ、ルートを全画面`FrameLayout`にし、`FLAG_NOT_TOUCHABLE`を外し（`FLAG_NOT_FOCUSABLE`のみ）、`OnTouchListener`で常に`true`を返してすべてのタッチを消費する。背景は半透明（`0x66000000`）にして下のLINE画面を目視できるようにした。

検証用の起動口は`RunReceiver`の新しいアクション`jp.salesanchor.lineexport.RUN_ALL_BLOCKING`で、「次の1回だけ帯を遮断モードにする」one-shotフラグ（`SchedulerStore.setBlockingOverlayOnce`/`consumeBlockingOverlayOnce`）を立てたあと、既存の`RUN_ALL`と**まったく同じ経路**（`UnlockAccessibilityService.requestRunAll(context, "RUN_ALL(遮断テスト)")`）で実行する。フラグは`LineExportFlow`が帯を出す直前に必ずconsumeする（読んだらfalseに戻る）ため、プロセスが死んでもフラグが残り続けない。通常実行（`RUN_ALL`等）はこのフラグを一切立てないため、`overlayBlocking`は必ずfalseになる。

### 安全策

右下の「停止」ボタン（非常口）＋フロー独立の60秒強制撤去タイマー。全画面でタッチを止める窓は、フローが死ぬと操作不能になり得るため、この2つは必須。

- 「停止」ボタン: 遮断モードの帯の右下の隅に置く。押されると即座に帯を撤去し（`remove()`）、押されたことを`escapeTapped`フラグに記録する（`wasEscapeTapped()`で読める）。
- 強制撤去タイマー: `show()`の中で`Handler#postDelayed`により`BLOCKING_AUTO_REMOVE_MS`（60秒）後に無条件で`remove()`する。`remove()`が先に呼ばれたら`removeCallbacks`で取り消す。フローが途中で死んでも操作不能が続かないようにするための保険。

### 実行ログへの記録

`export`の`phase:"end"`行に次を追加した（既存の`overlayShown`/`overlayRemoved`はそのまま残す）:
- `overlayBlocking`: 遮断モードで出したときだけ`true`（通常は出さない）
- `overlayEscapeTapped`: 遮断モードで、かつ利用者が「停止」を押したときだけ`true`（押されなければ出さない）

### 通常実行への影響

通常実行には影響しない（one-shotフラグ＋専用アクション`RUN_ALL_BLOCKING`経由のみ）。既存の帯（`RunStatusOverlay`の非遮断モード）はPO決定Bで「安易に外さない」と決まっているので、挙動を変えていない。

## 追補 2026-10-11 EDITをノードクリックにし、配信をダイアログの消滅で確認する

### 実測した事実（2026-10-11 `uiautomator dump`）

Termuxの保存ダイアログは**アクセシビリティに公開されている**ことが実機で確認できた。

```
[TextView] text="Save file in ~/downloads/"   id=alertTitle
[EditText] text="[LINE] …のトーク.txt"         clickable=true
[Button]   text="EDIT"             clickable=true  id=button1  bounds=[777,1155][969,1317]
[Button]   text="キャンセル"        clickable=true  id=button2
[Button]   text="OPEN DIRECTORY"   clickable=true  id=button3
```

EDITは`clickable=true`。boundsの中心 (873,1236) は、既存の比率座標タップ（`EDIT_TAP_X_RATIO=0.8074`→1080幅で872px、`EDIT_TAP_Y_RATIO=0.5287`→2340高で1237px）の座標とほぼ一致していた。

**過去の記録「Termuxの保存ダイアログのEDITボタンはuiautomatorに露出しない（2026-09-17、`/root/line-auto-export/auto-export.sh:13`のコメント・同日のスクリーンショットで確認、本書「追補 2026-10-08」2.参照）」は、今回（2026-10-11）の実測と一致しない。** 一致しない理由は不明（推測は書かない）。

### 「成功と記録されたのに届いていない」事象の実測（2026-10-11 遮断モード検証）

- **06:30**: 9段階すべて完走し、実行ログは`result:"success"`。しかしTermux側（`outbox.sqlite3`）に対応する`received`の記録が無い＝実際には送信が行われていない。
- **06:32**: Termuxの保存ダイアログが開いたまま残っていた（EDITが押された形跡が無い）。

`GestureCompat.tap`の`dispatchGesture`は戻り値が「OSがジェスチャを受理した」ことしか意味せず、実際に指の動きとして再生され、かつTermux側がそれを処理したかは別問題（本書「施錠前に待つ時間」の節と同じ非同期性の問題）。EDITタップでは、受理されたのに実際には押されず、ダイアログが残ったまま後続処理（成功記録・施錠）が進んでしまうケースがあることが実機で確認された。

### 対処

1. **EDITを「ノードのクリック」で優先的に押す**: `NodeOps.findNodeByTextInPackage(service, "EDIT", "com.termux")`でEDITボタンのノードを探す（text完全一致＋パッケージ名が`com.termux`であることを必須条件にした専用の探索メソッド。既存の`findNodeByLabel`/`matchesLabel`はtext/content-descのいずれかの完全一致でパッケージ名を見ないため、LINE側に偶然同じラベルのノードがあった場合の誤爆を避けるために新設した。既存メソッドの挙動は変えていない）。
2. 見つかれば`NodeOps.clickNode`で押す（クリック可能な祖先が無ければノード領域中心への座標タップへフォールバック）。`NodeOps.ClickResult`に`viaAction`を追加し、`ACTION_CLICK`を委譲できたか（true）/bounds中心へのgestureタップにフォールバックしたか（false）を呼び出し側が区別できるようにした（既存の呼び出し元は`accepted`/`traceMessage`のみを見ており、この追加で挙動は変わらない）。
3. 見つからなければ、従来の比率座標タップ（`EDIT_TAP_X_RATIO`/`EDIT_TAP_Y_RATIO`、値は変更していない）をそのまま行う（フォールバック）。
4. どの経路を使ったかを`edit_button`のstepログのextraフィールド`editClickPath`に記録する: `"node-action"`（ACTION_CLICKで押せた）／`"node-bounds-tap"`（ノードは見つかったがbounds中心へ座標タップした）／`"ratio-tap"`（ノードが見つからず従来の比率座標タップをした）。
5. **押した後、ダイアログが閉じたことを確認してから成功と判定する**: `EDIT_CLOSE_POLL_MS`（150ms）間隔・`EDIT_CLOSE_TIMEOUT_MS`（3000ms）を上限に、同じ探索でEDITのノードが消えたかを見る。消えたら成功（`finish(true, null)`）、実行ログに`editDialogClosed:true`・`editCloseWaitMs`を記録する。3,000ms経っても残っていたら、新しい段階名`edit_not_closed`で`finish(false, STAGE_EDIT_NOT_CLOSED)`とし、`editDialogClosed:false`を記録する（これにより`armRetryOnFailure`の経路で`scheduleRetryAfterFailure`が自動で張られ、次回で取り戻せる）。この確認は「EDITを押した後・施錠の待ちに入る前」に挟む。既存の施錠・`lockSkipped`・`drainCallbackSummary()`・`LOCK_DELAY_AFTER_EDIT_MS`の流れは変えていない。

**ノードが見つからない＝消えた＝成功、とする（安全側）**。探索が例外で失敗した場合も成功扱いにする。失敗にするのは「EDITのノードがまだ存在する」という明確な未押下の証拠があるときだけにし、探索自体が不調なだけのケースを誤って失敗扱いにしない（既存の挙動を壊さないため）。

### ノードクリックが使えると分かった意味（遮断モードへの展望）

2026-10-11実機で、ノードクリック（`ACTION_CLICK`）は全画面の遮断モードの帯（`RunStatusOverlay`の`blocking`モード、`FLAG_NOT_TOUCHABLE`を外して全タッチを消費する窓）を素通りすることを確認した（06:30の遮断モード検証）。一方、座標タップ（`dispatchGesture`）は帯に吸われる。EDITをノードクリックで押せるようになったことで、遮断モード自体が実用上機能する可能性が出てきた。

### 守ること

- `EDIT_TAP_X_RATIO`/`EDIT_TAP_Y_RATIO`/`EDIT_TAP_SETTLE_DELAY_MS`の値は変更していない。
- EDITノードの探索（`findNodeByTextInPackage`）で例外が起きた場合は成功扱いにする（上記）。

## 追補 2026-10-11 遮断モードを常時有効にし、再試行を3回にする（PO決定）

### 実機で確定した事実（根拠）

- **EDITはノードクリックで押せる**（2026-10-11 08:25 実測: `editClickPath: "node-action"`, `editDialogClosed: true`, `editCloseWaitMs: 19`）。
- **遮断モードの帯（全画面でタッチを止める）でもフローが完走し、ファイルが届き送信まで成功した**（08:27:00の回: `overlayBlocking: true`, `result: success`, 取り込み`received ok`→送信`accepted 7,234バイト`）。
- **座標タップは遮断中に吸われる**（06:30・06:32の2回: EDITの比率座標タップが効かず、Termuxの保存ダイアログが開いたまま残り、`received`が無かった）。上の「追補2026-10-11 EDITをノードクリックにし…」の「ノードクリックが使えると分かった意味」節で確認済みの事実（ノードクリックは帯を素通りするが座標タップは吸われる）と整合する。
- **座標スワイプについては断定できない**: 遮断中の4回はいずれも`scrollMode:"gesture"`で成功しているが、「スワイプが通った」のか「そのスクロールが実際には不要でノード探索が3回の試行内で目標を見つけた」のかを区別できていない。10-10の内訳は`node`65回・`gesture`12回で、座標スワイプに落ちる回は実在する。
- 端末の管理ポリシーは`maximumFailedPasswordsForWipe=0`（ドコモの管理アプリ含め全て0）＝**誤入力による初期化は設定されていない**（実機確認済み）。
- **帯は`LineExportFlow`（書き出しフェーズ）だけで出している**（`UnlockAccessibilityService`内の`RunStatusOverlay`参照は0件）。PIN入力は座標タップなので、帯を解除フェーズへ広げてはいけない。

### PO決定1: 遮断モードを本番で常時有効にする

`LineExportFlow.start()`が帯を出すとき、`blocking`に`armRetryOnFailure`の値を渡すようにした（`overlayBlocking = armRetryOnFailure;`）。本番実行（RUN_ALL経由、`armRetryOnFailure==true`）は遮断モードで出し、EXPORT単体（手動検証、`armRetryOnFailure==false`）は従来の非遮断の細い帯のまま（診断のため非遮断の経路を残す）。

検証用だった`SchedulerStore.consumeBlockingOverlayOnce`/`setBlockingOverlayOnce`、`RunReceiver`の`ACTION_RUN_ALL_BLOCKING`、`AndroidManifest.xml`の該当`<action>`は削除した（常時有効になり検証用の入口が不要になったため。2つのやり方を残さない）。

**帯は解除フェーズ（`UnlockAccessibilityService`）へは広げていない。** PIN入力は座標タップ（`dispatchGesture`）で行っており、座標タップは遮断モードの帯に吸われることが実機で確認済み（上記「背景」参照）。PIN入力の画面にはクリック可能なノードが無く座標タップしか手段が無いため、帯を広げるとPIN入力そのものが吸われて解除できなくなる。

### PO決定2: 「停止」ボタンを削除する

`RunStatusOverlay.buildBlockingView`から「停止」ボタンと`escapeTapped`/`wasEscapeTapped()`を削除した。`LineExportFlow`側の`overlayEscapeTapped`フィールドとログ項目も削除した。

60秒の強制撤去タイマー（`BLOCKING_AUTO_REMOVE_MS`）は残した。値も60秒のまま変えていない。**「停止」ボタンを削除したため、操作不能から抜ける保証はこのタイマーだけになった。最悪の場合、利用者は最大60秒間タッチできない（フローの実測は約11秒）。PO了承済み（2026-10-11）。**

### PO決定3: 再試行を「初回を含めて3回」にする

`RunScheduler.MAX_CONSECUTIVE_RETRIES`を1→2にした。

数え方: カウンタは「張った再試行の回数」なので、上限2なら「初回の実行→失敗→再試行1回目を張る（count=1）→失敗→再試行2回目を張る（count=2）→失敗→`retry_capped`」＝**初回を含めて合計3回試す**。成功で`clearConsecutiveRetryCount`によりリセットされる（既存のまま）。

失敗の型で分けない（PO決定）: どのパターンも一律3回試す。`maximumFailedPasswordsForWipe=0`を実機で確認済みのため、PIN入力を伴う失敗を3回試しても初期化のリスクは無い。Android標準の一時的な待ち時間（誤入力が連続した場合の猶予）が増える可能性はある。

`RETRY_INTERVAL_MS`（5分）の値は変えていない。

### 未確定事項と検知方法（`blockedCoordinateGesture`）

座標スワイプが遮断中に通るかは未確定（上記「背景」参照）。推測で判断せず、まず実行ログに記録を残す。

`LineExportFlow`に`blockedCoordinateGesture`フラグを追加した。遮断モードが有効（`overlayBlocking==true`）かつ座標ベースのジェスチャ（`GestureCompat.tap`/`GestureCompat.swipe`）を呼んだときにtrueになる。次の3か所で立てる:

1. EDITの比率座標タップ（`editClickPath == "ratio-tap"`の経路、`tapEditButton`）
2. `NodeOps.clickNode`がノード領域の中心を座標タップした経路（`editClickPath == "node-bounds-tap"`、`tapEditButton`内）
3. スクロールの座標スワイプ（`scrollMode == "gesture"`になる経路、`scrollOnce`内の`GestureCompat.swipe`）

`export`の`phase:"end"`行に`blockedCoordinateGesture: true`を（trueのときだけ）追加した。既存の`scrollMode`/`editClickPath`はそのまま残しており、併せて読めばどの座標操作だったか特定できる。

座標ジェスチャを止めたり失敗にしたりはしていない（記録のみ）。先に記録を取り、`blockedCoordinateGesture: true`の回に段階失敗が集まるかを見てから、座標スワイプの扱いを判断する。

## 追補 2026-10-11 EDITの準備完了判定をノード探索に移し、配信確認の条件を正す

### 実機ログ（2026-10-11 09:13、0.18.0-stage3・遮断モード常時有効）

```
edit_button  classDetected=False  classPolls=18  classWaitMs=5107
             editClickPath=ratio-tap
             editDialogClosed=True      ← 誤判定
結果: success                            ← 誤報告
取り込み: 無し（ファイルがTermuxに届かなかった）
再試行: 張られなかった（successだったため）
```

### 原因1: 準備完了の判定がTYPE_WINDOW_STATE_CHANGED依存で、来ない回がある

準備完了（Termuxの保存ダイアログが出た）の判定が、`service.getLastWindowClassName()`に`TermuxFileReceiverActivity`が含まれるか（`TYPE_WINDOW_STATE_CHANGED`イベント由来）に依存していた。このイベントが来ない回があり、`classDetected=false`のときは比率座標タップ（`EDIT_CLICK_PATH_RATIO_TAP`）に落ちていた。

実測の頻度（`classDetected=false`になった回／全export実行回、実行ログから集計）:

- 2026-10-09: 1/46回
- 2026-10-10: 0/38回
- 2026-10-11: 1/19回

合計で約2%。頻度は低いが、**遮断モード（`overlayBlocking==true`）では座標タップが吸われることが06:30・06:32・09:13の実機で確定しているため、この約2%の回は必ずファイルが届かない。**

### 原因2: 配信確認が「押す前の実在確認」を前提にしていなかった

`waitForEditDialogClosed`は「EDITノードが見つからない＝ダイアログが消えた＝配信された」と判定していたが、これは**押す前に一度もノードが見つかっていない場合は意味を持たない**（存在した証拠が無いまま「消えた」と言っているだけ）。09:13の回はまさにこの経路（`editClickPath=ratio-tap`＝ノード未検出でタップ時にも見つからなかった）で、`editDialogClosed=true`（成功）と誤判定された。

### データは失われない

watermark（取り込みの起点）は送信が受理されたときだけ進む（`RunScheduler.recordSuccessfulImport`は`success`のときだけ呼ばれる）。09:13の回はこの意味で「成功」と誤記録されたため本来は前進してはいけなかったが、実際に失われたデータは無い: 09:16の回で正常化（受理・送信成功）を確認済みであり、09:13分も含めて09:16の回がまとめて送った。

### 対処1: 準備完了の判定を「EDITノードが見つかるか」に変える

`LineExportFlow.pollEditClass`を、`NodeOps.findNodeByTextInPackage(service, EDIT_BUTTON_LABEL, TERMUX_PACKAGE_NAME)`が非nullになることを判定本体にするよう変更した。間隔・期限は既存の定数（`NODE_WAIT_POLL_MS`=300ms、`EDIT_CLASS_WAIT_TIMEOUT_MS`=5,000ms）のまま変えていない。見つかったら`EDIT_TAP_SETTLE_DELAY_MS`（1,000ms、値は変えていない）待ってから`tapEditButton`へ進み、見つかった事実を`editNodeWasFound=true`として保持する。

期限までに見つからなかった場合:

- **遮断モードが有効（`overlayBlocking==true`）**: 座標タップは効かないことが実機で確定しているため、比率座標タップへは落とさず失敗にする。新しい段階名`edit_node_not_found`を定義し、`finish(false, STAGE_EDIT_NODE_NOT_FOUND)`とした。既存の`scheduleRetryAfterFailure`が自動で張られ、合計3回まで試される。
- **遮断モードが無効（`overlayBlocking==false`、EXPORT単体の手動検証）**: 従来どおり比率座標タップにフォールバックする（`editClickPath=ratio-tap`）。手動検証の既存挙動は変えていない。

`TYPE_WINDOW_STATE_CHANGED`由来の記録（`classDetected`/`classPolls`/`classWaitMs`）は診断用としてそのまま残した（過去データとの比較のため）。判定には使っていない。

`edit_button`のstepログに新しい項目を追加した: `editNodePolls`（探索した回数）、`editNodeWaitMs`（見つかるまでのms。見つからなければフィールド自体を出さない）。

### 対処2: 配信確認を「押す前にノードが見つかっていた場合だけ」信じる

`waitForEditDialogClosed`とログを次のように変更した。

- `editNodeWasFound==true`（押す前にノードが実在した）: 既存のロジックのまま。消えたら`editDialogClosed:true`＋`editCloseWaitMs`を記録して成功、3,000ms（`EDIT_CLOSE_TIMEOUT_MS`、値は変えていない）経っても残っていたら`edit_not_closed`で失敗。消えたことが確認できた回には`editVerified:true`を記録する。
- `editNodeWasFound==false`（比率座標タップにフォールバックした非遮断の経路のみ）: 配信を確認したと主張しない。`editDialogClosed`フィールドは出さず（null扱い）、代わりに`editVerified:false`を記録する。挙動は従来どおり成功として終える（`finish(true, null)`）: この経路は手動検証のみで、座標タップが歴史的に効いていたため、今まで通っていた回を失敗に変えないという判断（依頼文の指示どおり）。

探索が例外を投げた場合の扱いは現状のまま（消えた＝成功扱い）にした。理由: 探索自体が不調なだけのケースを「押せていない明確な証拠」と区別できず、誤って失敗扱いにしないため（既存のコメントのとおり）。

### 変更していないもの

- 定数の値はすべて変更していない（`NODE_WAIT_POLL_MS`・`EDIT_CLASS_WAIT_TIMEOUT_MS`・`EDIT_TAP_SETTLE_DELAY_MS`・`EDIT_CLOSE_TIMEOUT_MS`・`EDIT_CLOSE_POLL_MS`・`EDIT_TAP_X_RATIO`/`Y_RATIO`・`LOCK_DELAY_AFTER_EDIT_MS`・`BLOCKING_AUTO_REMOVE_MS`・`MAX_CONSECUTIVE_RETRIES`・`RETRY_INTERVAL_MS`）。
- `RunStatusOverlay`の遮断の作り（「停止」ボタンは削除済みのまま、復活させていない）、`overlayBlocking = armRetryOnFailure`の判定、`lockOnFinish`/`armRetryOnFailure`の分岐、`accessibility_service_config.xml`の`accessibilityEventTypes`、`NodeOps`の既存メソッドの挙動、`RunScheduler`の予約・補完・再試行の仕組み・キーガード判定は、いずれも変更していない。

座標スワイプが遮断中に通るかなど、この追補の範囲外の未確定事項については推測を書かない（上の「未確定事項と検知方法」節のまま、別途判断する）。

## 追補 2026-11-26 電池最適化で後回しにされたことを検知・記録・復旧できる仕組み

対象ADR: ADR-1090（本追補の方針の芯と、記録の保持期間・上限の決定はここに記録した）。

### 起きた事象（実機 2026-11-26）

`run-20261126.jsonl` で 18:09:08 の `export/end success` のあと、LINE の新着通知が 18:36:43・18:43:33・18:47:47・18:53:29 の4回届き `scheduler/reserve`（+30秒）も記録されたのに、`unlock`/`export` が1回も走らなかった（48分の空振り）。アプリのログに理由は出ない。

### 実測した事実（根拠・すべて `adb shell dumpsys` の一次情報）

- 保留中の `*walarm*:jp.salesanchor.lineexport.SCHEDULED_RUN` 2件が **同一の `whenElapsed=2074665196`** に束ねられていた。`origWhen` は 18:39:06 と 18:53:59、`nowELAPSED=2073958167`（18:57:11）＝**発火予定は約19:09（遅れ30分/15分）**。
- `am get-standby-bucket jp.salesanchor.lineexport` = **40（RARE）**。
- `dumpsys deviceidle whitelist` に本アプリは**不在**（`com.termux` は在った）。
- AlarmManager の設定値: `app_standby_window=+1h`・`standby_quota_active=720`・`standby_quota_working=10`・`standby_quota_frequent=2`・**`standby_quota_rare=1`**・`standby_quota_restricted=1`・`min_window=+10m`。
- 発火した分の履歴に `policyWhenElapsed: app_standby=-57m12s531ms`＝省電力の方針で約57分ずらされた記録が残っていた。
- アラームは `window=0 exactAllowReason=compat`＝**正確アラームは既に許可されている**。

### 分かったこと（当初案の否定）

- 原因は「正確さ」ではなく **1時間あたりの発火回数の割当**。RARE では1時間に1回しか発火できず、本アプリは1日約90回（約10分おき）動くため、あふれた予約が同一時刻に束ねられる。
- コードは既に `setExactAndAllowWhileIdle` を使い、失敗時だけ不正確へ落ちる（`tools/line-auto-export-app/src/java/jp/salesanchor/lineexport/RunScheduler.java` の `trySetExactAndAllowWhileIdle`）。`targetSdkVersion` は 24 のため `USE_EXACT_ALARM`（API33向け）は効かない。**よって当初検討した `USE_EXACT_ALARM` の宣言は採用しない。**
- 効く対処は電池最適化の除外のみ。2026-11-26 に ADB で `dumpsys deviceidle whitelist +jp.salesanchor.lineexport` ＋ `am set-standby-bucket … active` を適用し、区分が 40→**5（EXEMPTED）**になった直後に `scheduler/fire`（trigger=補完）→ 18:57:51 開始・18:58:02 `export/end success`・18:58:11 送信 `accepted`（HTTP 200・32,119バイト・基準 18:07）で**空振り分を回収**した。書き出しは全文＋60分の重なり、サーバは watermark で差分を取るため**遅れてもデータは失われない**。

### 残る弱点と PO 決定

除外は**ユーザー操作・Samsung のスリープ機能・アプリ再インストールで失われ、失われても誰も気づけない**（アプリは「予約した」としか記録しないため）。2026-11-26 に PO から「3点でgo」を受領し、次の3点を実装する。

### 対処1 除外が外れたことに気づいて記録する

`PowerManager#isIgnoringBatteryOptimizations`（API23追加のためリフレクション不要）で現在値を取り、`notifyIfExactModeChanged` と同じ「前回値と比べ、変わったときだけ記録する」作りにする。実装は `RunScheduler#isIgnoringBatteryOptimizations`・`RunScheduler#checkBatteryOptimizationExemptionChanged`（`scheduleAt` の末尾から呼ぶ）・`SchedulerStore#wasLastIgnoringBatteryOptimizations`。記録は `flow=scheduler` / `phase=battery_exemption_changed`。あわせて実行開始の記録に `batteryOptimizationIgnored` を足す（不明なときは項目を出さない＝既存の nullable 項目と同じ扱い）。

### 対処2 空振り（予約したのに発火しない）を記録する

予約時に引き金ごとの発火予定時刻を `SchedulerStore#setScheduledFireAt` に保存し、発火を受けたら `RunScheduler#onAlarmFired` の冒頭で消す。スケジューラの公開入口を通るたびに `checkStaleScheduledFires` が全引き金を確認し、保存値が **120秒（`STALE_FIRE_THRESHOLD_MS`）以上過去**なら `flow=scheduler` / `phase=missed_fire`（`trigger`・`scheduledAt`・`lateByMs`）を1行記録して消す。`cancelAll` では保存値も消す（意図したキャンセルを空振りと誤判定しないため）。`disable()` は `cancelAll` の前に `checkStaleScheduledFires` を呼び、本物の空振りだけ記録してから消す。

### 対処3 設定画面から自分で復旧できるようにする

`AndroidManifest.xml` に `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` を追加し、設定画面に現在の除外状態の表示と `Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`（`package:` 付き）を開くボタンを置く。`ActivityNotFoundException` は捕まえて落ちない。文字はすべて `res/values/strings.xml`（`battery_*`）に置き、Java に日本語を直接書かない。`onResume`→`refreshStatus`→`refreshBatteryStatus` の経路があるため、設定画面から戻ると表示が更新される。

### 守ること

- 既存のタイミング（`FLOOR_INTERVAL_MS`・各引き金の間隔）とログの既存項目の意味は変えない。足すだけ。
- APK の署名鍵は**既存の `build/debug.keystore`（2026-09-17 作成）を使う**。新しい鍵で署名すると上書き更新ができず、消して入れ直す＝PIN・ユーザー補助・通知の権限を失う。2026-11-26 の版は実機の APK と証明書 SHA-256 が一致することを `apksigner verify --print-certs` で確認済み（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`）。
- `sdk/android-34.jar` は追跡対象外。ビルドする環境ごとに用意する。

### 検証

| 基準 | 検証方法 |
|---|---|
| ビルドが通る | `cd tools/line-auto-export-app && bash build.sh` が終了コード0・`out/app-debug.apk` を出す |
| 上書き更新できる（データ・権限が保たれる） | 新 APK と実機の APK の `apksigner verify --print-certs` の SHA-256 が一致 |
| 版が上がっている | `aapt dump badging out/app-debug.apk` が `versionCode='23' versionName='0.20.0-stage3'` |
| 除外が外れたら気づける | 実機で `adb shell dumpsys deviceidle whitelist -jp.salesanchor.lineexport` → 次の予約で `phase=battery_exemption_changed`・`ignoringBatteryOptimizations=false` が記録される |
| 空振りを記録できる | 同上の状態で予約時刻+120秒以降に入口を通ると `phase=missed_fire` が `lateByMs` 付きで記録される |
| 既存の集計が壊れない | `jq 'select(.flow=="export" and .phase=="end")'` 等の既存条件がそのまま動く（既存項目を変えていない） |

### 外部・過去事例

- Android の App Standby バケットごとのアラーム割当は端末の `dumpsys alarm` の `standby_quota_*` が正本。本件は推測ではなく当該端末（SC-51G）の実値で確認した。
- 同種の「省電力で黙って止まる」事象は 2026-10-13 の記録（ユーザー補助サービス未接続時に合図が黙って捨てられる）と同じ系統＝**黙って止まる経路は記録を足して可視化する**という本リポジトリの既往の対処方針に沿う。

### 変えていないもの

`USE_EXACT_ALARM` の宣言（効かないため）、`targetSdkVersion`（24 のまま）、`minSdkVersion`（23 のまま）、アラームの張り方（`setExactAndAllowWhileIdle` のまま）、送信側 `tools/termux-line-import/client.py`、`termux-job-scheduler` の登録。

## 追補 2026-11-27 保守口（無線デバッグ）が切れたらアプリが開き直す

対象ADR: ADR-1092（方針の芯と実測値はここに記録した）。

### 実測した事実（2026-11-27・SC-51G）

- Wi-Fi が切れている間は `adb_wifi_enabled` に 1 を書いても定着しない（直後・10 秒後ともに 0）。Wi-Fi 接続中なら定着する（直後・10 秒後ともに 1）。
- `adb tcpip 5555` に切り替えると `adb_wifi_enabled` は 0 になる。固定ポートの待ち受けは `[::]:5555`＝全インターフェースで、同一 LAN から到達できる。
- 原因の切り分け: 連続稼働 24 日（再起動は原因でない）／Samsung 自動ブロッカーは OFF・ブロック実績 0（原因でない）／Wi-Fi の切断は多数（ON:97・OFF:268、`WIFI_DISABLED` 2 回、`MAC_CHANGE` 由来あり）。
- proot の中の Ubuntu から Android のコマンドは実行できない（`getprop`・`toybox`・`am`・`settings` の 3 方式すべて `Operation not permitted`）。
- `WRITE_SECURE_SETTINGS` の保護レベルは `development` を含み、`pm grant` で付与できる。

### 対処

アプリに `WRITE_SECURE_SETTINGS` を宣言し、起動時（BOOT_COMPLETED）と毎回の実行時に `adb_wifi_enabled` を確認して 0 なら 1 を書く。Wi-Fi が無い回は定着しないため、次の回に持ち越す（1 日約 70 回動くので Wi-Fi が戻れば数分〜十数分で開き直る）。書き換えるのは `adb_wifi_enabled` の 1 キーだけで、`adb_enabled`（USB デバッグ）には触らない。記録は変化時だけ 1 行。コードの定数で止められるようにする。

### 守ること

- 固定ポート（`adb tcpip`）は常用しない。調査で開いた 5555 は本方式の確認後に閉じ、`adb_enabled` も 0 に戻す。
- `pm grant` はアプリを削除して入れ直すと消える。入れ替え手順に付与を含める。
- 端末を信頼できないネットワークで使うときは定数で止める。

### 検証

| 基準 | 検証方法 |
|---|---|
| ビルドが通る | `cd tools/line-auto-export-app && bash build.sh` が終了コード 0 |
| 自動復旧が働く | `settings put global adb_wifi_enabled 0` の後にアプリを 1 回動かすと 1 に戻り、記録が 1 行残る |
| 他の設定を書かない | 前後で `adb_enabled` の値が変わらない |
| 既存の集計が壊れない | 既存のログ項目・タイミングを変えていないことを差分で確認 |

### 外部・過去事例

`adb tcpip` と `adb_enabled` の変更は、切替の瞬間に adbd を再起動させて自分の足場（ADB 接続）を壊す。2026-10-13 と 2026-11-27 に実際に起きた。復旧はポート走査（30000-55000・約 60 秒）→ `adb connect` で可能（2026-11-27 は 42181 で復帰）。この経験から足場をアプリ側に移した。

### 変えていないもの

既存のタイミング（`FLOOR_INTERVAL_MS` 等）、既存のログ項目の意味、`adb_enabled`、`targetSdkVersion`（24）、送信側 `tools/termux-line-import/client.py`。

## 追補 2026-11-27 保守口（無線デバッグ）の強制開け直し

対象ADR: ADR-1092 追補（本節と同日・同見出しの追補をADR側にも記録した）。

### 実測した事実（2026-11-27・SC-51G・再測不要）

- 端末 SC-51G / Android 16 / adb は `127.0.0.1:46467` でつながっている（`adb devices` で1台）。
- アプリは `jp.salesanchor.lineexport` 0.21.0-stage3（2026-11-27 14:38 導入）。`android.permission.WRITE_SECURE_SETTINGS` は `granted=true`。
- `adb_wifi_enabled`=1、`adb_enabled`=0、`service.adb.tcp.port`=5555（再起動で消える値）。
- アプリは `targetSdkVersion=24`（旧方式のストレージ）。`WRITE_EXTERNAL_STORAGE` は `granted=true`、`READ_EXTERNAL_STORAGE` は `granted=false`。
- この開発環境（proot の中の Ubuntu）から `/sdcard/Download/sa-line-notify/` へのファイル作成・削除は成功する（実証済み）。そこに置いたファイルは uid 10342 / group 1023 / 0660 になる。
- アプリは製品ビルドで `run-as` が使えないため、**アプリ側がそのファイルを読めるか・消せるかは実機検証で確かめる段階**（下記「実機検証手順」参照）。読めない場合に黙らない作りにした（下記「対処」）。
- 既存実績: `/sdcard/Download/sa-line-notify/run-20261127.jsonl` に `phase=maintenance_channel result=opened` が 14:41 に1件ある。

### 解決したい穴

既存の `MaintenanceChannel.ensureOpen` は `adb_wifi_enabled` が 0 のときだけ 1 を書く。ところが実機では**値が 1 のまま adbd（無線デバッグのサーバー本体）が動いていない**状態が起き、アプリは「1 だから正常」と見て何もせず、人が端末画面で OFF→ON するまで復旧しなかった。値を見るだけでは直らないため、強制的な 1→0→1 の開け閉め（cycle）を行う経路を追加した。

### 対処

1. **起動時は必ず cycle する**。`AlarmReceiver` の BOOT_COMPLETED 経路は `ensureOpen` ではなく `MaintenanceChannel.cycle(context, "boot")` を呼ぶ（既存の構造どおり goAsync や別スレッドへの委譲は無く、同期呼び出しのまま。cycle 内部の約2秒の待ちは BroadcastReceiver の実行時間制限（約10秒）に対して十分に短い）。
2. **合図ファイルを見たら cycle する**。`RunScheduler.scheduleAt` が `MaintenanceChannel.ensureOpen` を呼ぶ直前に、合図ファイル（ファイル名 `maintenance-open`。拡張子なし。場所は `LineNotifyListenerService.resolveStorageDir` が返すディレクトリ＝`run-*.jsonl` と同じ場所）を `MaintenanceChannel.checkSignalFile` で確認する。
   **（2026-11-27・検知方式を作り直し。下記「合図検知の作り直し」節参照）** 検知器は `boolean consumed = new File(dir, "maintenance-open").delete();`。`delete()` が `true` を返したときだけ「合図が在って、いま消費した」と確定できるため、**削除してから** `cycle(context, "signal")` を呼ぶ（逆順にすると削除失敗時に同じ合図で毎回 cycle してしまう）。削除が成功した回だけ cycle するため、二重消費が原理的に起きず、旧方式が使っていた識別子（`lastModified`＋`length`）による重複判定は不要になり削除した。
3. **毎回は cycle しない**。通常の実行予約時（`RunScheduler` の予約）は今までどおり `ensureOpen`（0 のときだけ 1 を書く）のまま。cycle は実行中の ADB 接続を切るため、「起動時」と「合図があったとき」だけに限定する。

`cycle` の手順: `adb_wifi_enabled` に 0 を書く → 約2000ms 待つ → 1 を書く → 読み直す。読み直して 1 なら `cycled_opened`、1 にならなければ `cycled_blocked` として、どちらも変化比較せず毎回記録する（既存の `opened` と同じ考え方＝復旧の実績が残らないと ADR-1092「維持の仕組み」が成り立たない）。Wi-Fi が無い回は1を書いても定着しない（実測。上の追補 2026-11-27 参照）ため、その場合は `cycled_blocked` を記録して終わり、復旧は次回以降の `ensureOpen` に持ち越す。Wi-Fi 状態の判定（新しい権限の追加）は行わない。書き換える設定キーは `adb_wifi_enabled` だけ（ADR-1092 What-4）。`adb_enabled` には絶対に触らない。新しい権限はマニフェストに追加していない。

### 黙らせない（2026-11-27の実機事象を受けて作り直し。下記「合図検知の作り直し」節参照）

合図ファイルの検知を `delete()` の戻り値だけに頼ると、`false` が「合図が無い」のか「消せない（経路が壊れている）」のか区別できない。そこで、まだ経路の健全性を確認できていない間だけ自己試験（`.maintenance-probe` の作成→削除の往復）を行う。両方成功したら `signal_channel_ok` を1回記録して以後は試験せず、どちらかが失敗したら専用の重複判定枠で `signal_probe_failed` を1回だけ記録する（旗は立てず次回また試す）。これが実機検証の判定材料になる。旧 `signal_unreadable`（`canRead()` 前提）は撤去した。

### Opus審査で見つけて直した欠陥（2026-11-27・続きの便。当時の実装に対する記録として残す）

1. **記録があふれる**: `signal_unreadable` の重複判定が `ensureOpen`/`cycle` と共用の枠（`SchedulerStore.getLastMaintenanceChannelResult`）を使っていたため、ディレクトリが読めずかつWi-Fiが無い回に枠の往復が起き、記録が毎回2行出ていた。`SchedulerStore` に専用の枠（`last_signal_unreadable`）を追加して分離した。
2. **合図を取りこぼす**: 合図ファイルの削除が成功した場合も識別子（`lastModified`+`length`）を保存していたため、次に置いた合図が偶然同じ識別子だと誤って無視していた。削除に成功したときは識別子を消す（保存するのは削除に失敗したときだけ）ように直した。

**この2点の指摘は、下記「合図検知の作り直し」での `canRead()` 門番の撤去により、両方とも前提（`canRead()` 門番・識別子による重複判定）自体が無くなったため、現在のコードには存在しない。** 記録として残す。

### 版番号の衝突と、版名が中身を保証しない事象への対策（2026-11-27）

実機検証を始める前に重大な事象が見つかり、調査の結果**原因が確定した**（経緯は `docs/handoff/line-auto-export-app/review-opus-adr1092.md` の「続き（2026-11-27・版番号の衝突）」節に詳細を記録。ここでは確定した事実と対策のみ記す）。

**確定した事実**: 端末に 2026-11-27 16:48:51 に入ったAPK（`classes.dex` md5 `216bf5c57db4a42f5e392c1c0de7c8d0`）は `dumpsys` 申告上 `versionName=0.22.0-stage3`／`versionCode=25` で、本PRが当初作っていた版と**同じ値**だった。ハッシュ照合の結果、このAPKは別ブランチ `release/line-export-click-retry`（PR #5808・OPEN）のビルドと1バイト単位で同一であることが確定した。PR #5808 は `versionCode=25`／`versionName=0.22.0-stage3` を本PRより先にコミットしており、**2つの独立したPRが同じ版番号を取り合っていた**。版名が偽りだったわけではなく（PR #5808 のビルド自体は版名と中身が一致した正当なビルド）、**版番号だけでは、端末に入っているのがどちらのPRのコードかを識別できない**状態になっていたことが真因だった。

**対応**: 本PRの `versionCode` を 25→26、`versionName` を 0.22.0-stage3→0.23.0-stage3 に上げ、PR #5808 の値と重複しないようにした。再ビルドし、自己検査（下記）が新しい版番号（`0.23.0-stage3`）で `OK` になることを確認した。

**版名が中身を保証しない状態そのものへの対策（`tools/line-auto-export-app/build.sh` の自己検査。引き続き有効）**:

- `AndroidManifest.xml` の `android:versionName` を**唯一の出所**として、ビルドのたびに `BuildStamp.java`（`final class BuildStamp { static final String VERSION_NAME = "..."; }`）を生成する（手で二重管理しない）。
- ビルドの最後（`classes.dex` 生成直後、`[3b/8]`）に、できあがった `classes.dex` の中にその版名の文字列が実在するかを `grep -a -F` で確認する。**含まれていなければ 0 以外の終了コードでビルドを失敗させる**。
- 検証: 端末の実際の古い `classes.dex`（上記 md5 `216bf5c5...`）に対して同じ `grep -a -F "0.22.0-stage3"` を実行すると**見つからない**（マッチ0件・終了コード1）。一方、本PRのコミットでビルドした `classes.dex` には現在の版名が1件存在し、自己検査は `OK` で通過する。

**自己検査の限界（過信しないこと）**: 今回の真因は「2つのPRが同じ版番号を使っていた」ことであり、PR #5808 のビルドは自己整合（版名と中身が一致）している。**この自己検査は「1つのビルドの中で版名とコードがずれていないか」しか検出できず、「複数のPR・ブランチ間で版番号が重複していないか」は検出できない。** 版番号の衝突は、ブランチを作る時点・統合前に、他にオープン中のPRが使っている値を確認して避ける運用でしか防げない。

**実機で実際に動いているコードの識別方法（版名を信じない）**: 版名（`dumpsys`の申告）は中身を保証しない。実際に動いているコードを識別するには `classes.dex` の内容を直接確認する。

```bash
adb shell pm path jp.salesanchor.lineexport   # 実際のAPKパスを確認
adb pull <上で分かったパス> /tmp/device.apk
unzip -o /tmp/device.apk classes.dex -d /tmp/device_extract
strings -a /tmp/device_extract/classes.dex | grep -x "checkSignalFile\|cycle\|maintenance-open\|cycled_opened"
```

目印の文字列（本PRなら `checkSignalFile`・`cycle`・`maintenance-open`・`cycled_opened`）が出れば、そのPRのコードが実際に動いている証拠になる。

## 追補 2026-11-27 合図検知の作り直し（`canRead()` 門番の撤去）

対象ADR: ADR-1092 追補3（本節と同日・同見出しの追補をADR側にも記録した）。

### 実機で測った事実（一次情報・再測不要）

PR #5811 の成果物（`versionCode=26`／`versionName=0.23.0-stage3`）を2026-11-27 18:24:55に実機へ導入済み。dex照合で `cycle`・`checkSignalFile`・刻印 `0.23.0-stage3` の存在を確認した。

- 導入直後、アプリ自身が `/sdcard/Download/sa-line-notify/run-20261127.jsonl` に次を記録した: `{"at":"2026-11-27T18:24:55+0900","flow":"scheduler","phase":"maintenance_channel","result":"signal_unreadable","adbWifiEnabled":-1,"trigger":"signal"}`。
- つまり旧 `checkSignalFile` の `!dir.canRead()` が **true** になった。**同じディレクトリに書き込みは成功している**（この記録自体がそこに書かれた）。`resolveStorageDir` は `ensureWritableDir` が通った `/sdcard/Download/sa-line-notify` を返している。
- 端末の権限は `WRITE_EXTERNAL_STORAGE: granted=true` / **`READ_EXTERNAL_STORAGE: granted=false`**。アプリは `targetSdkVersion=24`（旧方式のストレージ）。
- `/sdcard/Android/data/jp.salesanchor.lineexport/files` は存在しない（この環境から書けない）ので代替経路にならない。

**結論**: 「書けるのに `canRead()` が false になる」ことが実機で確定した。旧実装は `canRead()`／`isDirectory()` を門番にしていたため、合図ファイルが実際に置かれても常にこの門番で弾かれ、**合図を一度も検知できていなかった**（design.md 上は「未証明」としていたが、実機導入により「機能していない」と確定した）。

### PO の決定

**読み取り権限は増やさない。** 合図の検知に中身の読み取りは不要で、「在るか見て、消す」だけで足りる。削除に必要な書き込み権限は既にある。

### 設計判断（門番の撤去・削除を検知器にする）

- `canRead()`・`isDirectory()` による事前の門番を撤去した。読み取りが拒否される環境ではstat系の戻り値（`isDirectory()`含む）も信頼できないため、門番で弾かずに実際の操作を試す方針に変えた。`dir == null`（`resolveStorageDir` が書き込み先すら解決できない）のときだけ早期returnする。
- 検知器を `boolean consumed = new File(dir, "maintenance-open").delete();` に変えた。`delete()` が `true` を返したときだけ「合図が在って、いま消費した」と確定できる。**必ず削除してから cycle する**（逆順だと削除失敗時に同じ合図で毎回 cycle してしまう。旧審査の指摘と同種の穴）。
- この方式により、`lastModified`＋`length` による識別子の重複判定（旧 `SchedulerStore` の signalId まわり）は不要になったため削除した。削除が成功した回だけ cycle するので、二重消費が原理的に起きない。
- **黙らせない仕組み**: `delete()` が false の「合図が無い」と「消せない（経路が壊れている）」を区別するため、まだ経路の健全性を確認できていない間（`SchedulerStore.isSignalChannelConfirmed` がfalseの間）だけ自己試験を行う。`dir` に試験ファイル（`.maintenance-probe`）を作成→削除の往復を行い、両方成功したら「経路は使える」と記録して旗を立てる（`signal_channel_ok` を1回。以後は試験しない）。どちらかが失敗したら `signal_probe_failed` を専用の重複判定枠（`SchedulerStore.wasSignalProbeFailureRecorded`）で1回だけ記録する（旗は立てず次回また試す）。試験ファイルは後始末する（作成が失敗しても削除を試みる）。
- `signal_unreadable` という結果名は撤去した（`canRead()` 前提の名前であり、意味が変わるため流用しない）。重複判定の枠は `cycle`/`ensureOpen` の結果枠（`last_maintenance_channel_result`）とは別の専用の枠を使う（過去の審査と同じ理由＝記録があふれないため）。

### Opus審査で見つけて直した欠陥（2026-11-27・合図検知の作り直し便）

**試験ファイルの残骸で「経路が壊れている」と誤報する**: `probeSignalChannel` の成功判定に使う `createNewFile()` は、ファイルが既に在るときもfalseを返す（異常ではない）。試験ファイル（`.maintenance-probe`）を作った直後〜削除する前にアプリの処理が落ちる（省電力による停止・プロセス終了等）と残骸が残り、次回の試験で `createNewFile()`=false・`delete()`=trueとなって、経路は正常なのに `signal_probe_failed` を誤記録してしまう（次の回には確認済みで自己回復するが、その1行を見て「経路が使えない」と誤判断する恐れがある）。**直し方**: 試験の最初に残骸の掃除としての `delete()` を1回入れ（結果は判定に使わない）、`createNewFile()` → 後始末の `delete()` の順で行い、成功判定は後ろ2つだけで行う。`exists()`・`canRead()` 等の読み取り系の判定はここでも使わない（この端末では読み取りが拒否されるため）。

詳細コードは `tools/line-auto-export-app/src/java/jp/salesanchor/lineexport/MaintenanceChannel.java` の `checkSignalFile`／`probeSignalChannel`／`recordSignalProbeFailedIfChanged` 参照。版は `versionCode` 26→27、`versionName` 0.23.0-stage3→0.24.0-stage3 に上げた（在庫中の他PRとの衝突がないことを確認済み。`origin/main` は PR #5808 マージ後 25／0.22.0-stage3）。

### 実機検証手順（PO の承認後に実施。本PRの範囲外）

**前提**: 実機に入れ直す前に、上の自己検査（build.sh [3b/8]）が `OK` で通ったビルド（本PRのコミットでビルドした `out/app-debug.apk`）であることを確認すること。さらに、実機に入れた後は版名の `dumpsys` 申告だけで判断せず、`adb pull` → `strings` の手順で実際にそのPRのコードが動いていることを確認すること（版名は複数PR間で衝突しうるため）。

(a) 合図ファイル（`maintenance-open`）を `/sdcard/Download/sa-line-notify/` に置き、10分以内に `run-YYYYMMDD.jsonl` に `trigger=signal` の `cycled_opened`（または `cycled_blocked`）が出て、`maintenance-open` ファイルが消えていることを確認する（＝削除を検知器にした方式が機能している）。
(b) 初回（まだ `signal_channel_ok` を記録していない状態）は、上記(a)の実行の中で `signal_channel_ok` が1行出ることを確認する（自己試験が成功し、以後は試験しなくなる旗が立った証拠）。
(c) `signal_probe_failed` が出た場合は、試験ファイル（`.maintenance-probe`）の作成・削除のいずれかが失敗しており、合図ファイルの削除による検知そのものが使えない可能性があることを意味する。その場合は方式の見直し（別の受け渡し経路への変更等）が必要と判断する。

### 変えていないもの

既存の `ensureOpen` の挙動（0 のときだけ 1 を書く・1 のときは記録もしない・毎回の実行予約時だけに呼ばれる）、既存のタイミング（`FLOOR_INTERVAL_MS` 等）、既存のログ項目の意味、`adb_enabled`、`targetSdkVersion`（24）、送信側 `tools/termux-line-import/client.py`。ビルドは ADR-1090 の7に従い、実機と同じ既存の `build/debug.keystore` で再ビルドした（`apksigner verify --print-certs` の SHA-256 が実機の APK と一致することを確認済み）。

## 追補 2026-11-27 押せなかったら押し直す（一発判定をやめる）

### ①実測した事実

端末の実行ログ `run-*.jsonl` 4,502回を集計した結果、書き出しの失敗123回の内訳は次のとおり:

- `termux_target` **97回**／`menu_button` 9回／`shortcut` 8回 ＝ **待ちも再探索も持たない3段階で114回（93%）**
- `settings_item` 6回／`export_item` 2回／`open_chat` 1回 ＝ 再試行を持つ段階はほぼ失敗しない

`termux_target` は手順9（`share_sheet`、300msおき最大10秒のポーリング）で「Termux」ノードを**見つけている**（share_sheet の失敗は0回）。にもかかわらず手順10が**保存したノードをそのまま押し、押せなければ即 failure**（旧 `LineExportFlow.java:547-553`）していた。失敗時の所要は実測 **6ミリ秒**＝探し直しも待ちもしていなかった。共有一覧は開いた直後に候補が差し替わるためノード参照が古くなるのが原因と判断した。

### ②変える前の作りと行番号

`shortcut`（旧 `step2ClickShortcut`、旧 `LineExportFlow.java:412-425`）・`menu_button`（旧 `step4ClickMenuButton`、旧 `LineExportFlow.java:467-480`）・`termux_target`（旧 `step10ClickTermux`、旧 `LineExportFlow.java:547-561`）の3段階は、いずれも「1回探す→押す→押せなければ即 `finish(false, stage)`」という一発判定だった。`termux_target` は手順9（`step9WaitShareSheet`）が保存した `termuxNode`（インスタンス変数）をそのまま使っていた。

### ③変えた後の作り

3段階を、共通メソッド `clickWithRetry`/`clickWithRetryStep`（`tools/line-auto-export-app/src/java/jp/salesanchor/lineexport/LineExportFlow.java:849-897`）に置き換えた。新しい定数 `CLICK_RETRY_TIMEOUT_MS = 3000L`（期限3秒）を追加し、刻みは既存の `NODE_WAIT_POLL_MS`（300ms）を流用した（新しい刻みの定数は作らない）。

振る舞い（既存の `waitForNode` と同じ再帰＋`schedule()` の形）:

1. ノードを毎回ゼロから探す（前回の参照は使い回さない）。ただし `termux_target` だけは1回目に限り、手順9が保存した `termuxNode` をそのまま使ってよい（成功時の経路を今と同じに保ち、変更の危険を最小にするため）。押せなかった場合は `termuxNode` を捨て、2回目以降は他の2段階と同じくゼロから探し直す。
2. 見つかったら `NodeOps.clickNode` で押す。`result.accepted` なら `recordStep(stage)` して次の手順へ進む。
3. 見つからない・押せなかった場合、期限（3秒）を過ぎていれば `recordStep(stage)` → `finish(false, stage)`。
4. 期限内なら `schedule(..., NODE_WAIT_POLL_MS, ...)` で 1 から繰り返す。

探し方自体は変えていない: `shortcut`=`NodeOps.findByTextPrefix(service, SHORTCUT_TEXT_PREFIX)`、`menu_button`=`NodeOps.findByDescExact(service, MENU_BUTTON_DESC)`、`termux_target`=`NodeOps.findNodeByLabel(service, TERMUX_LABEL)`。手順9（`step9WaitShareSheet`）自体も変更していない。

### ④計測項目

`clickAttempts`（探して押そうとした回数。1なら一発成功＝今と同じ）と `clickWaitMs`（この段階に費やした合計ミリ秒）を、既存の `ScrollStats.toJson()` と同じ作りで各段階の `recordStep` の extraFields に載せる（`buildClickRetryExtraFields`、`LineExportFlow.java:886-897`）。一発成功の回も `clickAttempts: 1` を必ず出す（出ない回があると集計できないため）。

あわせて、失敗したときに「見えていたアプリ名」をすべての段階で記録するよう広げた。`NodeOps.distinctWindowPackageNames(service)`（`NodeOps.java:135-172`）は従来 `open_chat` の失敗時だけ使われていたが（旧 `LineExportFlow.java:778-780`）、`finish(boolean success, String failedStage)` 側（`LineExportFlow.java:1117-`、`seenPackages` 変数）に1箇所にまとめ、失敗した回はすべて `logExportEnd` の extraFields に `seenPackages`（既存と同じカンマ区切りの文字列）として載せるようにした。`open_chat` 専用だった個別記録（`waitForPackage` のタイムアウト分岐）は削除し二重記録を避けた。成功した回には出さない（容量は58日で38MBという実測があるため）。

### ⑤変えていないもの

手順9（`step9WaitShareSheet`）のポーリング間隔・期限、3段階それぞれの探し方（`NodeOps.findByTextPrefix`/`findByDescExact`/`findNodeByLabel`）、`settings_item`/`export_item` のスクロール再試行（`scrollFindAndClick`、`SCROLL_MAX_RETRIES`・`SCROLL_SETTLE_DELAY_MS` など）、遮断モードの帯（`overlayBlocking`・`RunStatusOverlay`）。

## 追補 2026-11-27 署名鍵と成果物の作り直しを仕組みで守る

対象ADR: ADR-1090（「7. 署名鍵」に禁止事項が文章として書かれていたが、仕組みでは守られていなかった）。本追補ではその一文を仕組み（スクリプトとCI）で強制する。ADR本体は編集していない。

### ①実際に起きた2つの事故

1. **2026-11-27、別の鍵で署名された APK ができた。** `tools/line-auto-export-app/build/` は `.gitignore` 対象のため、新しい作業ツリーで `build.sh` を走らせると「鍵が無ければ `keytool` で黙って作る」処理が別の鍵を黙って作っていた。実機に入っている APK の証明書は `c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`（SHA-256）だが、別鍵で署名されたAPKの指紋は `8736637d1db0c7e507ec94a490831fe0509ebfcd72989874c45ee5d1bcbf3b79` だった。別鍵のAPKは実機を上書き更新できず、消して入れ直すとPIN・ユーザー補助・通知の権限を失い自動化が止まる。人が気づいたため実害は出なかった。
2. **同日、APK 成果物だけが古いまま main に残った。** `tools/line-auto-export-app/out/app-debug.apk` は二進ファイルでマージされないため、main 取り込み時に衝突し、片側を選ぶとソースには入っている修正が成果物から消える。実機にそれを入れると修正が無かったことになる現象が実際に起きた。

### ②入れた門番2つ

**門番1（`tools/line-auto-export-app/build.sh`）**:

- 署名鍵（`build/debug.keystore`）が無いときは、既定では作らずエラーで止める（既存の鍵をコピーする候補パスと、`sdk/android-34.jar` も同様に追跡対象外である旨をメッセージに出す）。
- 環境変数 `ALLOW_NEW_KEYSTORE=1` を与えたときだけ、本当に初めての環境向けの逃げ道として従来どおり `keytool` で新しい鍵を作る。そのときは「この APK は実機を上書き更新できない」という警告を目立つ形で出す。**この逃げ道を使った回は、下記の証明書の照合が一致しなくても警告だけで成功させる**（新しい鍵の証明書が定数と一致することは原理上あり得ないため、止めてしまうと逃げ道そのものが使えなくなる）。弱くならないよう、代わりに門番2が成果物の署名を検査する。
- 署名後に `apksigner verify --print-certs` の Signer #1 の SHA-256 を取り出し、スクリプト内の定数 `EXPECTED_SIGNER_SHA256`（値は `c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`）と一致しなければ exit 1 で止める。鍵を正式に入れ替えるときは、この定数と ADR-1090「7. 署名鍵」を同時に直す運用にすることで、仕組み（作業ツリーが鍵を持っていないだけの状態）と意図（鍵を本当に入れ替える決定）を区別する。
- 最後に `tools/line-auto-export-app/out/BUILD-INFO.txt` を4行（`versionCode`・`versionName`・`signerSha256`・`apkSha256`）で書き出し、画面にも1行でまとめて印字する。

**門番2（CI・新規 `scripts/ci/check_line_export_apk.py`）**:

- pure Python（標準ライブラリのみ・`aapt` もAndroid SDKも使わない）。`tools/line-auto-export-app/out/BUILD-INFO.txt` の存在、`versionCode`/`versionName` が `tools/line-auto-export-app/AndroidManifest.xml` と一致すること、`apkSha256` が実ファイル `tools/line-auto-export-app/out/app-debug.apk` の実際のsha256と一致すること、**`signerSha256` が期待値と一致すること**の4つを検査する。4つ目の期待値は検査スクリプトに直書きせず、`tools/line-auto-export-app/build.sh` の `EXPECTED_SIGNER_SHA256` を読み取って使う（正本を1か所にして食い違いを防ぐ）。定数が読めなかった場合も明確なエラーで止める（黙って検査を飛ばさない）。
- 事故1（版だけ上げてビルドし直し忘れ）は `versionCode`/`versionName` の不一致で捕まる。事故2（APK側だけ古いものをマージで選んでしまう）は `apkSha256` の不一致で捕まる。`ALLOW_NEW_KEYSTORE=1` で作った別鍵のAPKをコミットした場合は `signerSha256` の不一致で捕まる。
- ワークフロー `.github/workflows/line-export-apk-guard.yml` から呼ばれる（`tools/line-auto-export-app/` 配下の変更があるPRのみ実行、`.github/workflows/adr-index-check.yml` と同じ変更検出の作り）。単体テストは `scripts/ci/test_check_line_export_apk.py`。

### ②-2 main 側の「ビルド刻印」との関係（二重の仕組みではない）

PR #5811 が `build.sh` に入れた刻印（`BuildStamp.java` を生成して `versionName` をAPKに埋め込み、ビルド直後に自己検査する）とは**見張る時点が違うため役割が重なっていない**。刻印の自己検査は「いま作ったAPKの中身が、いまのマニフェストの版と合っているか」を**ビルド時**に見る。本追補の門番2は「**コミットされている**成果物が、いまのソースと合っているか」を**CI（PR）時**に見る。事故2（マージで片側のAPKを選ぶ）はビルドを伴わないため刻印の自己検査では捕まらず、逆に本追補の門番だけでは作りかけのビルドの食い違いは見えない。両方必要である。

### ③変えていないもの

アプリのコード（Java・リソース・`AndroidManifest.xml` の内容）、`versionCode`/`versionName`の値（この便では上げていない）、署名鍵そのもの（`build/debug.keystore` は既存のものを使い続ける）、ビルドの手順の本体（javac→dalvik-exchange→aapt→zipalign→apksignerの順序・各ステップの内容）はいずれも変更していない。足したのは「鍵が無いときに黙って作らない」「署名後に照合する」「BUILD-INFO.txtを書き出す」「CIで食い違いを検査する」の4点のみ。

## 追補 2026-11-28 合図が黙って捨てられる穴（記録追加＋本番経路の再試行）

### ①実測した事実（一次情報・再測不要）

`RunScheduler.onAlarmFired()` が `RunLogger.logSchedulerEvent(context, "fire", ...)` を書いた直後に `UnlockAccessibilityService.requestRunAll(context, label)` を呼ぶ。この先に「黙って終わる道」が2つあり、どちらも**実行ログに何も残らず、再試行も張らない**:

1. `UnlockAccessibilityService.requestRunAll(Context, String)` の `sInstance == null`（ユーザー補助サービスが未接続）→ `postFailureNotification` のみで return
2. `UnlockAccessibilityService.startUnlockFlow()` の `running.compareAndSet(false, true)` が false（前の回が走っている）→ `Log.i` のみで return

端末ログ51日分を集計した結果、`fire` が記録されたのに実行が始まらなかった回が **4,645回中6回**あり、最大 **59.6分** 取り込みが遅れた（原因は上記1）。補完の予約周期はコア時間帯30分／オフピーク60分のため、取り込み合図が1回捨てられると最悪60分待ちになる。

### ②直し方

- `RunLogger` に `logTriggerDropped(Context, String triggerLabel, String reason)` を追加した。`flow:"scheduler"`／`phase:"trigger_dropped"`／`trigger`（捨てられた合図のラベル）／`reason`（`"service_unbound"` または `"already_running"`）を記録する単発行（`logSchedulerEvent` 等と同じ「runIdに紐づかない」扱い）。メッセージ本文は含めない。
- **本番経路（`requestRunAll(Context, String)` の `sInstance == null` 分岐）だけ**、記録に加えて `RunScheduler.scheduleRetryAfterFailure(context)` を張るようにした。既存の `postFailureNotification` の呼び出しは残したまま。`scheduleRetryAfterFailure` 自体は変更していない（OFF中は何もしない・上限2回・5分後という既存の挙動のまま）。再試行は補完の予約（`SchedulerStore` のpending-next）とは別の要求コードのアラームなので、補完の予約を消さない。
- 手動検証用の入口（`requestRun(Context)`／`requestExport(Context)` の `sInstance == null` 分岐）は**記録のみ**追加し、再試行は張らない。読み取り専用の診断口 `requestDiagWindows` は対象外（無変更）。
- `startUnlockFlow()` の「既に走っている」分岐（前の回が担うのが正しい挙動）も**記録のみ**追加し、再試行は張らない。

### ③変えていないもの

`postFailureNotification` の既存呼び出し、`scheduleRetryAfterFailure`／`requestDiagWindows` の中身、既存の各メソッドのそれ以外の挙動（見送り・床判定・施錠タイミング等）はいずれも変更していない。版は `versionCode` 27→28、`versionName` 0.24.0-stage3→0.25.0-stage3 に上げた（在庫中の他PRとの衝突がないことを確認済み）。

## 追補 2026-11-28 その2 使用中は短く見送る（画面の取り合いを減らす）

### ①実測した事実（一次情報・再測不要）

端末の実行ログ（`/sdcard/Download/sa-line-notify/run-*.jsonl`）直近5日 523回と `dumpsys usagestats`／`dumpsys power` から:

- **1日105回**実行し、1回の画面占有は中央値 **10.5秒**（最長20秒）。合計 **1日18.8分**。
- 契機の内訳は 通知82%／補完15%／再試行2%／手動・外部2%。実行間隔は中央値6分で、**44%が5分未満の連続**。
- 実行開始時の画面状態（`unlock` 終了行の `screenOnAtStart`／`keyguardAtStart`・516回）は **画面ON＋解錠済み 54%／画面OFF 46%／画面ON＋施錠中 2%**。
- 「画面ON＋解錠済み」が**アプリ自身が点けた画面の残り**ではないことを確認した: 直前の実行から2分以内に始まった回は2回（1%）だけ。さらに 14時台の実測で画面を点けていた持ち主は `SCREEN_BRIGHT_WAKE_LOCK ws=WorkSource{com.google.android.youtube}`＝**利用者本人の操作**だった。よって **1日およそ50回は人の操作中の割り込み**。
- 画面がついている一区切りの長さ（`usagestats` の SCREEN_INTERACTIVE/NON_INTERACTIVE 17区間）は **中央値0.3分・75%点0.8分・76%が5分以内**（最長83分）。
- 現状の作りは「施錠されていなければ即実行（PIN入力は飛ばす）」で、遮断モードの覆いは常時ON（全画面・タップを飲み込む）。

### ②PO決定の変更（2026-11-28 GO）

| | 内容 |
|---|---|
| 旧（2026-10-10） | 使用中でも即実行する。中断は受け入れる |
| **新** | **使用中は最大10分まで見送る。10分を超えたら強行するが、そのときは遮断しない** |

根拠: 割り込みが1日およそ50回ある一方、画面がついている一区切りは中央値0.3分・76%が5分以内。**短く待つだけでほとんどの割り込みを避けられ、取り込みの遅れは多くの場合1分未満**で済む。「回数自体を減らす」案（床3分→10分で1日105回→55回）は今回採らない: 減るのは夜間の無害な実行も含むため、同じ遅れの代償に対する見返りが小さい。

### ③変えた後の作り

- **使用中の判定**: `PowerManager.isInteractive()==true` かつ `KeyguardManager.isKeyguardLocked()==false`。場所は `RunScheduler.onAlarmFired()` の床（`FLOOR_INTERVAL_MS`）判定の**直後**・`fire` を書く**直前**。画面ONでも施錠中（ポケット等・実測2%）は従来どおり実行する。
- **見送りの再確認**:
  - 通知・再試行は既存 `defer_floor` と同じ流儀で、**同じ要求コード**で `now + DEFER_RECHECK_MS`（60秒）に再武装する。通知のときは `SchedulerStore.setNotificationReservedAt` も同じ時刻に更新する（床と同じ理由＝古い予約が残ると次の通知が「予約済みでない」と誤判定して割り込む）。
  - **補完は再武装しない**。要求コードを奪うと直前に張った「次回の補完」が消えるため。次回の補完（コア時間帯30分／オフピーク60分）に任せる。補完は通知を取りこぼしたときの保険であり、鮮度の担保は通知側の上限10分が担う。
- **上限（強行）**: 初回の見送り時刻を `SchedulerStore` の `deferInUseStartedAt` に記録する（既に入っていれば更新しない）。`now - deferInUseStartedAt >= DEFER_MAX_MS`（10分）なら見送らずに実行する。実行に進んだ時点でクリアする。この時刻は**引き金をまたいで1つ**を共有する（通知で見送り続けて10分たてば、次に来た補完でも強行になる）。
- **強行した回は遮断しない**: `requestRunAll(Context, String, boolean forcedWhileInUse)` を追加し、`startUnlockFlow`→`LineExportFlow` まで引き渡す。`LineExportFlow` の `overlayBlocking` は `armRetryOnFailure && !forcedWhileInUse` とする。既存の1引数・2引数の入口は `forcedWhileInUse=false` のまま（従来どおり遮断する）。
- **対象外**: 手動（`requestExport`／`requestRun`）と外部（`requestRunAll(Context)`＝RUN_ALL）は見送らない（人が明示的に出した要求のため）。読み取り専用の診断口 `requestDiagWindows` も無変更。
- **無効化スイッチ**: `DEFER_WHILE_IN_USE_ENABLED`（既定 true）。false で判定ごと素通しし旧挙動に戻る（`MaintenanceChannel.SELF_RECOVERY_ENABLED` と同じ作法）。

### ④計測項目

- `defer_in_use`（`flow:"scheduler"`／`phase:"defer_in_use"`）: 見送った回。`trigger`（通知/補完/再試行）・再武装した時刻（補完は null）・`deferredSinceMs`（初回見送りからの経過）。
- `forced_in_use`（同 `phase`）: 上限で強行した回。`deferredMs`（待った合計）。
- 既存の `overlayBlocking`（export 終了行）で「強行時に遮断を外せたか」を確認できる。
- 効果の読み方: `screenOnAtStart==true && keyguardAtStart==false` の回が **1日およそ50回**から何回に減ったか／`defer_in_use` の件数／`forced_in_use` の割合。

### ⑤変えていないもの

床3分（`FLOOR_INTERVAL_MS`）・通知デバウンス30秒・補完の間隔・再試行（5分・最大2回）・施錠の方針（使用中に起動した回は施錠しない）・通常実行の遮断モード（今までどおり遮断する）・覆いの自動解除60秒・PIN入力の手順・押し直し（`clickWithRetry`）。版は `versionCode` 28→29、`versionName` 0.25.0-stage3→0.26.0-stage3。

### ⑥実機で確認すること（投入後）

1. 画面を使っている最中に通知を起こし、`defer_in_use` が出て**画面が奪われない**こと
2. 画面を消すと60秒以内に実行され、成功すること
3. 10分以上使い続けたとき `forced_in_use` が出て、その回の `overlayBlocking` が **false** であること
4. 1日分の記録で「使用中に始まった回」が投入前（約50回/日）から減ったこと
