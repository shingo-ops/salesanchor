# 実機エビデンス 2026-09-18〜19 段階1（アプリ単独でのロック解除）

対象端末: Galaxy（画面 1080x2340、Android 16、ワイヤレスデバッグ 127.0.0.1:40359）。
取得はすべて `adb` の読み取りコマンドによる実測。推測は「帰属」と明記した箇所のみ。

## 結論

- アプリ単独で **画面を点灯させることはできる**（E3）。
- **スワイプ・タップはロック画面に効いていない**（E4）。よって「アプリ単独でのロック解除」は未達。
- 当初はそもそも **ジェスチャ権限が与えられていなかった**（E1）。原因はビルドが参照するSDK（E2）。修正して権限は付与されたが、それでも E4 は変わらなかった。
- 唯一「成功」と記録された 2026-09-18 16:52 の回は、利用者が手で解除したものだった（本人確認済み）。

## E1. ユーザー補助サービスの権限

```
$ adb shell dumpsys accessibility | grep "Bound services" -A4 | tr "," "\n" | grep -E "label=|capabilities="
（修正前 2026-09-18 20:05）Service[label=SA LINE Export  capabilities=1
（修正後 2026-09-19 01:54）Service[label=SA LINE Export  capabilities=33
```

AccessibilityServiceInfo の権限ビット: 1=CAN_RETRIEVE_WINDOW_CONTENT、2=TOUCH_EXPLORATION、
8=FILTER_KEY_EVENTS、16=CONTROL_MAGNIFICATION、32=CAN_PERFORM_GESTURES。
修正前は 32 が立っておらず、`dispatchGesture` は実行されない。アプリの通知に出ていた
「座標」は送出を試みた記録であって、OSによる実行の記録ではない。

## E2. 原因（ビルドが参照するSDK）

`android:canPerformGestures` は API24 で追加された属性。res/xml に同属性を入れた状態で aapt を実行:

```
$ aapt package -f -m -J gen -M AndroidManifest.xml -S res -I android-23/android.jar
終了コード 1
res/xml/accessibility_service_config.xml:9: error: No resource identifier found for attribute 'canPerformGestures' in package 'android'

$ aapt package -f -m -J gen -M AndroidManifest.xml -S res -I sdk/android-34.jar
終了コード 0（出力なし）
```

対策: build.sh の aapt の `-I` を API34 の android.jar に変更（javac は minSdk に合わせ API23 のまま）。
res/xml に `android:canPerformGestures="true"` を宣言。結果は E1 の「修正後」。

## E3. 画面点灯の対照実験（2026-09-19 01:54:50）

```
$ adb shell "dumpsys display | grep -m1 mScreenState= ; dumpsys display | grep -m1 mScreenBrightness= ; dumpsys power | grep -m1 mWakefulness="
消灯時            : mScreenState=OFF  mScreenBrightness=0.0        mWakefulness=Dozing
①ADBで点灯 +1s   : mScreenState=ON   mScreenBrightness=0.16862744 mWakefulness=Awake
再び消灯          : mScreenState=OFF  mScreenBrightness=0.0        mWakefulness=Dozing
②アプリ合図 +1s  : mScreenState=ON   mScreenBrightness=0.23921567 mWakefulness=Awake
②アプリ合図 +3s  : 同上
②アプリ合図 +5s  : 同上
```

②は `am broadcast -a jp.salesanchor.lineexport.RUN` のみ（端末に触れていない）。
ADB経由と同じ状態に到達する。利用者の目視でも点灯を確認済み（2026-09-19 01:50頃）。

補足: 電源ログの `details=EDGELIGHTING:SALineExport:unlock` はウェイクロックの名札であり、
点灯が演出に置き換わったことを意味しない（E3 が反証）。調査中に一度そう誤判定した。

## E4. スワイプ・タップの不達

アプリ単独の実行（合図 01:56:52.887 → 点灯 01:56:53.394）後の観測:

```
前面ウィンドウ              : NotificationShade（ロック画面のまま。Bouncer に遷移せず）
handlePrimaryBouncerVisibilityChanged true : 0 行
暗証番号の照合ログ           : 0 行
アプリの結果通知             : 「ロック解除: 失敗 / 理由: Enter未検出 / スワイプ 座標 座標 座標
                              座標 座標 座標 Enter:座標(540,2223) / 4553ms / 画面1080x2340」
```

同じ計測の直前（01:52:54 の実行）では次の2行が記録されているが、アプリの処理時間（約4.5秒）より
後の時刻であり、利用者が手で解除してメッセージを送信した時刻と一致する。**時刻による帰属であり、
アプリによる解除の記録ではない。**

```
09-19 01:53:00.875 KeyguardUpdateMonitor: handlePrimaryBouncerVisibilityChanged true
09-19 01:53:02.851 LockSettingsService: Verifying lockscreen credential for user 0
```

## 未解決（次に判別すべきこと）

現在のアプリは `dispatchGesture` に GestureResultCallback を渡していないため、次の2つを区別できない。

1. OSがロック画面へのジェスチャ実行を拒否している（＝この方式は成立しない）
2. 実行はされているがロック画面が無視している／座標・手順の問題（＝修正の余地あり）

判別には onCompleted / onCancelled を受け取って結果通知に載せる実装が要る（端末操作は1回）。

## 副次的に判明した端末側の条件

- アプリの通知が無効（`importance=NONE`）かつ「おやすみモード」ONのとき、OSがアプリによる画面点灯を
  拒否する: `Screen on NOT allowed while DnD turned ON` / `Screen__On : Cancel (notifications are
  disabled)`。通知を許可して解消（`importance=DEFAULT`）。ADBの appops 変更では変えられず、
  本体の設定画面での操作が必要だった。
- ロック画面は点灯後およそ5秒で消灯する（端末の「画面消灯時間」を60秒にしても
  `activityTimeoutWM=5000` が効く）。PIN入力はこの窓に収める必要がある。
- ADB注入の `KEYCODE_SLEEP` / `KEYCODE_POWER` では安全ロックにならない（暗証番号なしでスワイプ
  解除できる状態になる）。安全ロックの検証には物理の電源ボタンが要る。
