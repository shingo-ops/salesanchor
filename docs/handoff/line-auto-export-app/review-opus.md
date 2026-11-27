# Opus 審査記録 — 電池最適化で後回しにされたことを検知・記録・復旧できる仕組み

| 項目 | 内容 |
|---|---|
| 対象 | `release/line-export-battery-exempt-guard`（土台 `origin/main` c3834ee5f） |
| 設計 | `docs/handoff/line-auto-export-app/design.md` 追補 2026-11-26 |
| 現在地 | `docs/handoff/line-auto-export-app/recon.md` 追補 2026-11-26 |
| 対象ADR | ADR-1090 |
| 区分 | A（ADR-1015 の危険パス一覧に `tools/` が含まれるため） |
| PO 承認 | 2026-11-26 Shingo（PO）「3点でgo」 |
| 審査日 | 2026-11-26 |
| 結果 | **APPROVE** |

## 確認した点

1. **当初案の否定が実測で裏付けられている**: `USE_EXACT_ALARM` は `targetSdkVersion 24` では効かず、アラームは既に `window=0 exactAllowReason=compat`＝正確。原因は `standby_quota_rare=1`（1時間に1回）であり、実装はこの事実に沿って「割当を外す（除外）」「外れたことに気づく」に絞られている。新機能の追加や仕様の拡大は無い。
2. **API 境界**: `PowerManager#isIgnoringBatteryOptimizations` は API23 追加で、`minSdkVersion 23` の `android.jar` から直接呼べる。リフレクション不要。取得不可・例外時は `null`（不明）を返し、呼び出し元はいずれも `null` を扱っている。
3. **既存の作法を踏襲**: 除外状態の検知は `notifyIfExactModeChanged` + `SchedulerStore#wasLastScheduleWasExact` と同じ「変化時だけ記録」。発火予定時刻の保存は `getNotificationReservedAt` と**別キー**にしており（意味が違うため）、既存の判定を壊していない。
4. **誤検知の経路を確認した**:
   - 個別の `cancel(...)` 呼び出しは `cancelAll` 以外に1か所（`onAlarmFired` 内の通知引き金）だけで、そこは `onAlarmFired` 冒頭の `clearScheduledFireAt` を通った後。保存値が残らない＝誤検知しない。
   - `cancelAll` は保存値も消す。`disable()` は `cancelAll` の前に `checkStaleScheduledFires` を呼ぶので、本物の空振りだけ記録される。
   - `defer_floor` の経路は `scheduleAt` を通るため保存値が延ばした先に更新される。
5. **既存の集計を壊していない**: 追加は新しい `phase`（`battery_exemption_changed`・`missed_fire`）と、実行開始行への `batteryOptimizationIgnored` の追加のみ。既存項目の名前・意味・タイミング（`FLOOR_INTERVAL_MS` 等）は不変。既存の `jq` 条件はそのまま通る。
6. **ビルドと署名**: `bash build.sh` が終了コード0。`out/app-debug.apk` は `versionCode=23` / `0.20.0-stage3`。証明書 SHA-256 が実機の APK と一致（`c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`）＝上書き更新で PIN・ユーザー補助・通知の権限が保たれる。
7. **ハードコード**: 画面文字はすべて `res/values/strings.xml` の `battery_*`。レイアウトの寸法・色は既存の直書き値（24dp/16dp/8dp/20sp/16sp/`#33000000`）の再利用のみで、新しい寸法・色は作っていない。

## 指摘（仕様どおりの振る舞い。直しは不要だが読み手が知っておくこと）

- **再起動後に `missed_fire` が1行出ることがある**: 端末の電源が切れていた間は実際に発火していないため記録は誤りではないが、記録を読むときは再起動を考慮すること。
- **不正確モードに落ちた回は、正当な遅れも `missed_fire` になりうる**: ただし発火した引き金は `onAlarmFired` 冒頭で消えるため、記録されるのは「他の引き金の入口を通ったとき」に限られる。これは検知したい症状そのものなので許容する。

## 未実施（この PR の範囲外）

- 実機へのインストールと、除外を外しての実挙動確認（`battery_exemption_changed`・`missed_fire` の記録確認）。インストールは稼働中の自動化に手を入れるため、PO の指示で別途行う。
- `client.py:679` の `termux-job-scheduler` 呼び出しに残る「孫プロセスを殺さない」書き方（今回の範囲外。別作業）。

# 審査 2026-11-27 押せなかったら押し直す（一発判定をやめる）

対象: ブランチ release/line-export-click-retry（commit 67f6b4edf・b2745d8a1・1499e85d5）。設計の正本は design.md「追補 2026-11-27 押せなかったら押し直す（一発判定をやめる）」。

## 根拠（実測。推測と区別する）

- 集計元は端末の `/sdcard/Download/sa-line-notify/run-*.jsonl`（ADB不要で直読み）。`flow=export` / `phase=end` が 4,502件（2026-10-09〜11-27）、うち失敗123件。
- 失敗の内訳: `termux_target` 97／`menu_button` 9／`shortcut` 8／`settings_item` 6／`export_item` 2／`open_chat` 1。**再試行を持たない3段階に114件（93%）が集まっている**。
- 段階ごとの成功時の所要（中央値）: `termux_target` 8ms／`menu_button` 31ms／`shortcut` 1,541ms／`settings_item` 2,063ms／`export_item` 2,038ms。`settings_item`・`export_item` だけが `attempts` を4,470回以上記録している＝再試行を実装済み。
- `termux_target` の失敗時の所要は**6ms**。手順9（`share_sheet`）は300msおき・期限10秒で「Termux」ノードを探し、その失敗は**0件**＝ノードは見つかっていた。したがって落ちているのは探索ではなく `NodeOps.clickNode` の結果が `accepted=false` になった回。
- `NodeOps.clickNode` は押せる祖先を遡って `ACTION_CLICK`、祖先が無ければ bounds 中心へ gesture タップ、bounds が空なら false（NodeOps.java:479-495）。保存したノード参照が古くなるとこの3つすべてが成立せず、一発で false になる。
- 判断: 共有シートは開いた直後に送信先候補が読み込まれて差し替わるため、手順9で保存した参照が手順10までに古くなる。**これは推測であり、`seenPackages` の記録（本便で追加）で次回から裏取りできる形にした。**

## 確認したこと

1. **成功時の経路が変わっていない**: `clickWithRetryStep` は `attempt==1 && firstCandidate!=null` のときだけ保存ノードを使う。手順10は `termuxNode` を渡し、手順2・手順4は null を渡す＝初回から探し直す（従来も初回に探していたので同じ）。一発で押せた回の動作・所要は従来と同一。
2. **期限が既存の見張りに収まる**: 追加は1段階あたり最大3秒、3段階で最大9秒。遮断の帯の強制撤去は60秒（RunStatusOverlay.java:61）、フローの WakeLock 安全弁は120秒（LineExportFlow.java:196）。主スレッドは `schedule()`（postDelayed）で明け渡すため、停滞の見張り（MainThreadStallWatchdog、閾値3秒）にも触れない。
3. **計測が集計できる形になっている**: `clickAttempts` は一発成功でも1を出す（出ない回があると母数が取れない）。`clickWaitMs` はその段階の合計ミリ秒。既存の `ScrollStats.toJson()` と同じ `recordStep` の extraFields 経路で、通知本文（平文）には出さない。
4. **`seenPackages` の二重記録が無い**: `waitForPackage` のタイムアウト分岐から open_chat 専用の個別記録を削除し、`finish(boolean, String)` が失敗時だけ計算して `logExportEnd` のトップレベルに1回出す。`service.stopWindowRecording()` の**前**に読んでいるため値が取れる。成功時は null で項目を出さない（容量は58日38.0MBの実測がある）。
5. **本文・個人情報を増やしていない**: 追加される記録はパッケージ名（最大3件）と回数・ミリ秒のみ。ノードのテキストやメッセージ本文は含まない（2026-10-08 実機1回目の不具合3の方針を維持）。
6. **ビルドと署名**: `bash build.sh` 終了コード0。`aapt dump badging` が `versionCode='24' versionName='0.21.0-stage3'`。dex に `clickWithRetryStep`・`clickAttempts`・`clickWaitMs`・`seenPackages` が入っていることを `unzip -p out/app-debug.apk classes.dex | strings` で確認。証明書 SHA-256 は `c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709`＝実機の base.apk と一致。

## 審査で見つけて直した欠陥（記録）

**別の鍵で署名された APK が一度できていた。** 新しい作業ツリーでは `tools/line-auto-export-app/build/` が .gitignore 対象のため、`build.sh` の「debug keystore（初回のみ作成）」が**別の鍵を黙って作る**。その APK の証明書は `8736637d1db0c7e507ec94a490831fe0509ebfcd72989874c45ee5d1bcbf3b79` で実機と不一致＝上書き更新ができず、消して入れ直し＝暗証番号・ユーザー補助・通知の権限を失う。ADR-1090「7. 署名鍵」に禁止は明文化されているが、**build.sh は警告も照合もしない**ため気づけない。既存鍵を build/ にコピーして再ビルドし、一致を確認した（commit 1499e85d5）。

**改善候補（本便の範囲外）**: build.sh に「鍵を新規作成したら目立つ警告を出す」または「署名後に証明書 SHA-256 を印字する」を足す。仕組みで止めないと作業ツリーを切るたびに踏む。

## 未実施（この PR の時点）

- 実機へのインストールと、`clickAttempts>1` が実際に記録されること・`termux_target` の失敗が減ることの確認。PO の指示（取り込みを止めないこと）に従い、実行の合間を狙って行う。
- 画面の取り合いそのものを減らす設計（実測: 7.1分おきに8.4秒・1日約13分、遮断の帯は全画面でタップを飲み込む）。別便・PO判断待ち。
