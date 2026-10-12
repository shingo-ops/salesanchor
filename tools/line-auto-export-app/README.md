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

## 既知の制約（報告書と重複するが実装者向けメモ）

- ビルド環境の android.jar は API23 固定。`android:canPerformGestures` 属性はAPI24追加のため
  `accessibility_service_config.xml` に書けず（aaptがエラーにする）、dispatchGestureの座標タップ
  フォールバックはOSに許可されない可能性がある。主経路はノードのテキスト/description一致クリック。
- PINは EncryptedSharedPreferences ではなく通常の private SharedPreferences に保存している
  （androidx security-crypto がこのオフラインビルド環境に存在しないため）。
- 座標タップのグリッド位置は標準的な3x4キーパッドを仮定した推測値。実機のキーパッドUIに合わせて
  `UnlockAccessibilityService` の `tapDigitByGridGuess` / `tapEnterByGridGuess` の調整が必要になる
  可能性が高い。
