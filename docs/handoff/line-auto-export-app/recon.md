# LINE自動書き出しアプリの現状と検証記録

この文書は、素人にも分かるように、実機で確かめた事実だけを file:line / コマンド出力で残す。
親: [商品マスタ](../../specs/product-master/README.md)
設計: [design.md](design.md)
関連: [Android取り込み](../line-android-import/design.md)（受信後の送信・通知・履歴・原本1件保持は完成済み）

## 背景と目的

個人LINEの通常グループ「WeGo売ります掲示板グループ」に投稿される在庫情報を、人手なしで既存の取り込みへ渡したい。公式アカウント（bot）は使わない方針（PO決定 2026-09-17）。ADBで画面を自動操作する方式は実機で成立を確認済みだが、Wi-Fi必須・ADB接続前提という制約がある。これを解消するため、端末内で動く自作Androidアプリ（ユーザー補助）で同じ操作を行う。

## 確かめた事実（ADB方式の実機結果 2026-09-17）

- 画面消灯＋PINロック状態から、ADBで WAKEUP → `wm dismiss-keyguard` → `input text <PIN>` → ENTER でロック解除でき、LINEの書き出し→Termux→取り込みまで通った（合計約35秒）。ロックはPINのみ（生体認証はユーザーが解除）。`dumpsys window policy` の `secure=true`。
- 1時間ごとの自動実行を termux-job-scheduler job 4203（3600000ms, persisted, network none）で稼働。ランナーは /root/line-auto-export/auto-export.sh（proot内）、Termux起点は ~/bin/line-auto-export。結果は既存 outbox.sqlite3 の events に stage='auto' で記録。
- 同一内容の再共有時に送信結果通知が出ない不具合を発見し、client.py を修正（stage='send' result='duplicate'、通知「取り込み済み」）。PR #3538 に反映済み。

## 自作アプリのために確かめた事実

- ビルド道具は Ubuntu(proot) に導入可能で実在を確認：
  - `java -version` → openjdk 25（javac は `--release 8` 指定で dx 対応の Java8 バイトコードを出す）
  - aapt /usr/bin/aapt、aapt2 /usr/bin/aapt2、apksigner /usr/bin/apksigner、zipalign /usr/bin/zipalign、keytool /usr/bin/keytool
  - dex 変換は `dalvik-exchange`（`dalvik-exchange --version` → dx version 1.16）
  - android.jar: /usr/lib/android-sdk/platforms/android-23/android.jar（API 23）
- 端末: SC-51G、Android 16（`getprop ro.build.version.release`=16）。LINE versionName=26.14.0、package jp.naver.line.android。
- Termux には `am`/`termux-am` あり。termux.properties の allow-external-apps は無効（21行目コメントアウト）。今回は有効化しない方針。
- UID分離の制約：自作アプリ（別UID）は Termux 私有の ~/line-import/state/unlock-pin を読めない。→PINはアプリ自身の私有領域に一度だけ保存する方式（設計A、PO決定 2026-09-17）。
- 自分で入れたアプリ（Google Play 外）のユーザー補助は Android 13+ の「制限付き設定」で保護される。ユーザーが「設定→アプリ→当該→制限付き設定を許可」で解除する必要がある（support.google.com/android/answer/12623953）。

## ADB検索

- `git grep -il -E 'termux|line.?android|accessibility|line-auto' docs/adr/` は該当なし。既存の対象ADRは line-android-import と同じ ADR-072・ADR-154（backend/DB/APIは変更しない）。

## 未確認（設計の検証対象）

- ユーザー補助サービスが、ロック画面（PIN入力画面）上でボタン/数字をクリックできるか。Android公式ドキュメントに明記なし。→最小アプリで実測する。
- このproot環境で APK を最後まで組み立て・署名でき、端末にインストールできるか。→最小アプリで実測する。
- 画面消灯状態からのウェイクをアプリ側で行えるか（WAKE_LOCK / turnScreenOn）。
