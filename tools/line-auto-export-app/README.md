# SA LINE Export（最小アプリ・段階1）

正本: [../../docs/handoff/line-auto-export-app/design.md](../../docs/handoff/line-auto-export-app/design.md)、
[recon.md](../../docs/handoff/line-auto-export-app/recon.md)

この段階の機能は3つだけ:

1. 設定Activity（PIN保存、平文非表示、保存済みかどうかのみ表示）
2. AccessibilityService（画面ウェイク→ロック画面上でPIN入力→3秒後にkeyguard解除判定→通知）
3. 起動口 BroadcastReceiver（`jp.salesanchor.lineexport.RUN`）

LINE操作はまだ実装していない（design.md 段階2以降）。

## ビルド

```bash
bash tools/line-auto-export-app/build.sh
```

成功すると `tools/line-auto-export-app/out/app-debug.apk` が生成される（再実行可能）。

## インストール

端末側でADBを使わない運用が最終目標のため、以下のいずれかで配布する。

- 検証時のみ: `adb install -r tools/line-auto-export-app/out/app-debug.apk`
- 通常運用（Termux経由・ADB不使用）: APKをTermuxのホームなどに置き、端末のファイルマネージャ/`termux-open` でタップしてパッケージインストーラを起動する。

## インストール後にユーザーが手動で行う操作

自分で入れたアプリ（Google Play外）のユーザー補助は「制限付き設定」で保護されるため、次の順で手動操作が必要（ADBやスクリプトからは操作できない）。

1. 設定 → アプリ → SA LINE Export → 制限付き設定を許可
   （参考: support.google.com/android/answer/12623953）
2. 設定 → ユーザー補助 → SA LINE Export を有効化
3. アプリを起動し、設定ActivityでPINを一度だけ入力して保存する
   （保存済みなら入力欄は表示されず「PIN: 保存済み」とだけ出る）

## Termuxからの実行合図

```bash
am broadcast -a jp.salesanchor.lineexport.RUN
```

PINはextraに載せない。受信すると `RunReceiver` が `UnlockAccessibilityService` に実行を指示し、
(a) 画面をウェイクしてロック画面を表示 → (b) PINの各桁をロック画面上でクリック（ノード一致、
だめなら座標タップにフォールバック） → (c) Enter/完了を押す → (d) 3秒後にkeyguard状態を判定し、
「ロック解除: 成功/失敗（理由）」の通知を出す、という流れで動く。

## 電池最適化で後回しにされたことを検知・記録・復旧できる仕組み（2026-11-26）

端末の省電力区分が上がる（電池最適化の除外が外れる）と、AlarmManagerの発火が1時間に1回などに
制限され、予約した時刻を過ぎても発火しない「空振り」が起きる（実機2026-11-26で48分・予約4回・
実行0回を確認）。これに気づけるよう3点を追加した。

1. **除外状態の変化を記録**: `PowerManager#isIgnoringBatteryOptimizations` の現在値を、変化した
   ときだけ実行ログ（run-YYYYMMDD.jsonl）に1行記録する（`RunScheduler#checkBatteryOptimizationExemptionChanged`、
   毎回は記録しない）。また実行開始行（`logStart`）には毎回 `batteryOptimizationIgnored` を
   付与する（不明なときは項目自体を出さない）。
2. **空振りの記録**: 引き金（通知／補完／再試行）ごとに「発火予定時刻」を保存し、実際の発火で
   消す。予約・発火などスケジューラの入口を通るたびに、保存値が120秒以上過去のまま残っていたら
   「空振り」として実行ログに1行記録して消す（`RunScheduler#checkStaleScheduledFires`）。
3. **設定画面から除外を戻せる**: 設定Activityに「電池の除外」状態表示と、
   `Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` を開くボタンを追加した。

## 保守口（無線デバッグ）が切れたらアプリが開き直す仕組み（2026-11-27）

端末の保守（ADB接続）の入口である無線デバッグが勝手に切れることがある（ADR-1092）。これに
対して、アプリの起動時（BOOT_COMPLETED）と毎回の実行予約時に `adb_wifi_enabled` を確認し、
0なら1を書く（`MaintenanceChannel#ensureOpen`、`RunScheduler#scheduleAt`と`AlarmReceiver`の
BOOT_COMPLETED経路の2箇所から呼ぶ）。Wi-Fiが無い間は書いても定着しないため、その回は
次回に持ち越す。書き換えるのは `adb_wifi_enabled` だけで、`adb_enabled`（USBデバッグ）には
触らない。結果（`opened`/`blocked`/`no_permission`）が変化したときだけ実行ログに1行記録する。
`MaintenanceChannel.SELF_RECOVERY_ENABLED` をfalseにすると丸ごと止められる。

**権限の付与が別途必要**: このアプリに `android.permission.WRITE_SECURE_SETTINGS`
（development保護レベル）を宣言しているが、インストール時には自動付与されない。
以下をadbから1回実行する必要がある。

```bash
adb shell pm grant jp.salesanchor.lineexport android.permission.WRITE_SECURE_SETTINGS
```

**アプリを削除して入れ直すと付与が消える**ため、入れ替え手順にこの付与をあわせて行うこと。

### 保守口（無線デバッグ）の強制開け直し（2026-11-27）

`ensureOpen`（上記）は `adb_wifi_enabled` が1なら「正常」と見て何もしないため、**値が1のまま
adbd（無線デバッグのサーバー本体）が止まっている**実機事象には効かない。これを塞ぐため、値を
見ずに強制的に0→（約2000ms待ち）→1と開け閉めする `MaintenanceChannel#cycle` を追加した。

- 呼び出し場所は2つに限定する: `AlarmReceiver` のBOOT_COMPLETED経路（`trigger="boot"`。
  `ensureOpen` の代わりに呼ぶ）と、`RunScheduler#scheduleAt` が毎回確認する合図ファイル
  （`RunScheduler` の節参照。`trigger="signal"`）。
- 毎回の実行予約時は今までどおり `ensureOpen` のまま（cycleはADB接続を切るため、起動時と
  合図があったときだけに限定する）。
- 結果（`cycled_opened`/`cycled_blocked`）は変化比較せず毎回記録する。合図ファイルが
  読めない・一覧できない場合は `signal_unreadable` を1回だけ記録する（黙らない）。

#### 合図ファイルで強制開け直しを促す

端末のストレージ（`run-*.jsonl` と同じディレクトリ）に `maintenance-open`（拡張子なし・内容は
空でよい）というファイルを置くと、次回の実行予約時（アプリは1日約70回動く）にアプリがそれを
見つけて強制開け直し（cycle）を行い、ファイルを削除する。削除に失敗した場合は、同じ合図で
毎回cycleしてしまうのを防ぐため、処理済みの識別子（`lastModified`と`length`）を保存し、
次回以降その識別子と同一なら何もしない。

```bash
adb shell "run-as jp.salesanchor.lineexport touch /sdcard/Download/sa-line-notify/maintenance-open" \
  2>/dev/null || adb shell "touch /sdcard/Download/sa-line-notify/maintenance-open"
```

（この開発環境からも `/sdcard/Download/sa-line-notify/` へ直接ファイルを作成できる場合がある。
作成したファイルの権限によってアプリが読めない可能性があり、その場合は実行ログに
`signal_unreadable` が記録される。詳細: `docs/handoff/line-auto-export-app/design.md` 追補
2026-11-27「保守口（無線デバッグ）の強制開け直し」の実機検証手順。）

## 既知の制約（報告書と重複するが実装者向けメモ）

- ビルド環境の android.jar は API23 固定。`android:canPerformGestures` 属性はAPI24追加のため
  `accessibility_service_config.xml` に書けず（aaptがエラーにする）、dispatchGestureの座標タップ
  フォールバックはOSに許可されない可能性がある。主経路はノードのテキスト/description一致クリック。
- PINは EncryptedSharedPreferences ではなく通常の private SharedPreferences に保存している
  （androidx security-crypto がこのオフラインビルド環境に存在しないため）。
- 座標タップのグリッド位置は標準的な3x4キーパッドを仮定した推測値。実機のキーパッドUIに合わせて
  `UnlockAccessibilityService` の `tapDigitByGridGuess` / `tapEnterByGridGuess` の調整が必要になる
  可能性が高い。
