#!/usr/bin/env bash
# SA LINE Export - 最小アプリのビルドスクリプト（proot内ツールのみで完結）。
# 正本: docs/handoff/line-auto-export-app/design.md
#
# javac(--release 8) -> dalvik-exchange(classes.dex) -> aapt package(base apk)
#   -> aapt add(dex同梱) -> zipalign -> apksigner(debug鍵で署名)
#
# 再実行可能。失敗したら即停止する(set -e)。
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# javac は API23 でコンパイルする（minSdk 23 に合わせ、新しいAPIを誤って使わないため）。
# aapt のリソース解決だけは API34 を使う。API23 では accessibility-service の
# android:canPerformGestures（API24 で追加）が解決できず、宣言が落ちてしまうため
# （2026-09-18 実測: API23 は "No resource identifier found for attribute
# 'canPerformGestures'"、API34 はエラーなし）。権限が落ちると端末側の
# capabilities が 1 のままになり、タップが一切効かない。
ANDROID_JAR="/usr/lib/android-sdk/platforms/android-23/android.jar"
AAPT_JAR="$APP_DIR/sdk/android-34.jar"
BUILD_DIR="$APP_DIR/build"
OUT_DIR="$APP_DIR/out"
GEN_DIR="$BUILD_DIR/gen"
CLASSES_DIR="$BUILD_DIR/classes"
DEX_FILE="$BUILD_DIR/classes.dex"
KEYSTORE="$BUILD_DIR/debug.keystore"
KEYSTORE_PASS="android"
KEY_ALIAS="sa-line-export-debug"

# 実機(SC-51G)に入っている APK の署名証明書の SHA-256（apksigner verify --print-certsの値）。
# 鍵を正式に入れ替えるときは、この定数と ADR-1090 の「7. 署名鍵」を同時に直す。
# 別の鍵で署名したAPKは実機を上書き更新できない（消して入れ直し＝PIN・ユーザー補助・
# 通知の権限を失い自動化が止まる。2026-11-27に実際に起きた事故）。
EXPECTED_SIGNER_SHA256="c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709"

echo "== SA LINE Export build =="

if [ ! -f "$ANDROID_JAR" ]; then
  echo "ERROR: android.jar not found at $ANDROID_JAR" >&2
  exit 1
fi

if [ ! -f "$AAPT_JAR" ]; then
  echo "ERROR: android-34.jar not found at $AAPT_JAR (aaptのリソース解決に必要)" >&2
  exit 1
fi

rm -rf "$GEN_DIR" "$CLASSES_DIR" "$DEX_FILE" \
  "$OUT_DIR/app-unsigned.apk" "$OUT_DIR/app-aligned.apk" "$OUT_DIR/app-debug.apk"
mkdir -p "$GEN_DIR" "$CLASSES_DIR" "$OUT_DIR"

echo "-- [1/10] aapt package -m -J (R.java生成) --"
aapt package -f -m -J "$GEN_DIR" \
  -M AndroidManifest.xml \
  -S res \
  -I "$AAPT_JAR"
echo "OK: $GEN_DIR"

echo "-- [2/10] javac --release 8 (API23, メインソース) --"
SHIM_SRC="src/java/jp/salesanchor/lineexport/GestureCallbackShim.java"
mapfile -t JAVA_SOURCES < <(find src/java "$GEN_DIR" -name '*.java' ! -name "$(basename "$SHIM_SRC")")
javac --release 8 -encoding UTF-8 -cp "$ANDROID_JAR" -d "$CLASSES_DIR" "${JAVA_SOURCES[@]}"
echo "OK: javac compiled ${#JAVA_SOURCES[@]} file(s) -> $CLASSES_DIR"

# GestureCallbackShimはAccessibilityService.GestureResultCallback(API24で追加)を継承する。
# ビルド環境のandroid.jar(API23)にはそのクラスが無いため、このファイルだけ別途、
# aaptのリソース解決に使っているsdk/android-34.jar(実クラスを含む)をclasspathに加えて
# コンパイルし、同じclassesディレクトリへ合流させる。実機(Android16)には本物の
# フレームワーククラスがあるため実行時はそちらで解決される。GestureCompat.java側は
# このクラスをClass.forName経由のリフレクションでのみ参照する（直接型参照はしない）。
echo "-- [2b/10] javac --release 8 (API34, GestureCallbackShim) --"
javac --release 8 -encoding UTF-8 -cp "$AAPT_JAR:$CLASSES_DIR" -d "$CLASSES_DIR" "$SHIM_SRC"
echo "OK: javac compiled GestureCallbackShim.java -> $CLASSES_DIR"

echo "-- [3/10] dalvik-exchange (classes -> classes.dex) --"
dalvik-exchange --dex --output="$DEX_FILE" "$CLASSES_DIR"
echo "OK: $DEX_FILE"

echo "-- [4/10] aapt package (resources + manifest -> app-unsigned.apk) --"
aapt package -f \
  -M AndroidManifest.xml \
  -S res \
  -I "$AAPT_JAR" \
  -F "$OUT_DIR/app-unsigned.apk"
echo "OK: $OUT_DIR/app-unsigned.apk"

echo "-- [5/10] aapt add (classes.dex を同梱) --"
(cd "$BUILD_DIR" && aapt add "$OUT_DIR/app-unsigned.apk" classes.dex)
echo "OK: classes.dex embedded"

echo "-- [6/10] zipalign --"
zipalign -f -p 4 "$OUT_DIR/app-unsigned.apk" "$OUT_DIR/app-aligned.apk"
echo "OK: $OUT_DIR/app-aligned.apk"

echo "-- [7/10] debug keystore --"
if [ ! -f "$KEYSTORE" ]; then
  if [ "${ALLOW_NEW_KEYSTORE:-}" != "1" ]; then
    echo "ERROR: 署名鍵が無い: $KEYSTORE" >&2
    echo "  新しい鍵を黙って作ると、実機と違う鍵で署名したAPKができる" >&2
    echo "  （2026-11-27に実際に発生: 実機の証明書 c64146dc… に対し別鍵のAPKができ、" >&2
    echo "   上書き更新できず消して入れ直し＝PIN・ユーザー補助・通知の権限を失った）。" >&2
    echo "  既存の鍵をコピーしてから再実行する。コピー元の候補（実在確認済み）:" >&2
    echo "    /root/worktrees/salesanchor/release-line-auto-export-app/tools/line-auto-export-app/build/debug.keystore" >&2
    echo "  (build/ はこのリポジトリの .gitignore 対象。sdk/android-34.jar も同様に" >&2
    echo "   追跡対象外なので、無ければ同じ要領で別の作業ツリーからコピーする)" >&2
    echo "  本当に初めての環境で鍵が存在しない場合のみ、ALLOW_NEW_KEYSTORE=1 を付けて" >&2
    echo "  再実行する（下記の警告が出る逃げ道）。" >&2
    exit 1
  fi
  echo "########################################################################"
  echo "# WARNING: ALLOW_NEW_KEYSTORE=1 により新しい署名鍵を作成する。"
  echo "# この APK は実機(既存インストール済みのAPK)を上書き更新できない。"
  echo "# 入れるには一度アンインストールが必要＝PIN・ユーザー補助・通知の権限を失う。"
  echo "########################################################################"
  keytool -genkeypair -v \
    -keystore "$KEYSTORE" \
    -storepass "$KEYSTORE_PASS" \
    -keypass "$KEYSTORE_PASS" \
    -alias "$KEY_ALIAS" \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=SA LINE Export Debug, OU=dev, O=salesanchor, C=JP"
  echo "OK: created $KEYSTORE"
else
  echo "OK: reusing existing $KEYSTORE"
fi

echo "-- [8/10] apksigner sign --"
apksigner sign \
  --ks "$KEYSTORE" \
  --ks-pass "pass:$KEYSTORE_PASS" \
  --key-pass "pass:$KEYSTORE_PASS" \
  --ks-key-alias "$KEY_ALIAS" \
  --out "$OUT_DIR/app-debug.apk" \
  "$OUT_DIR/app-aligned.apk"
echo "OK: $OUT_DIR/app-debug.apk"

echo "-- [9/10] apksigner verify --print-certs (証明書照合) --"
SIGNER_SHA256="$(apksigner verify --print-certs "$OUT_DIR/app-debug.apk" \
  | awk -F': ' '/Signer #1 certificate SHA-256 digest/ {print $2}' \
  | tr '[:upper:]' '[:lower:]')"
if [ -z "$SIGNER_SHA256" ]; then
  echo "ERROR: apksigner verify --print-certs から Signer #1 の SHA-256 を取得できなかった" >&2
  exit 1
fi
if [ "$SIGNER_SHA256" != "$EXPECTED_SIGNER_SHA256" ]; then
  echo "ERROR: 署名証明書が期待値と一致しない" >&2
  echo "  期待値: $EXPECTED_SIGNER_SHA256" >&2
  echo "  実際値: $SIGNER_SHA256" >&2
  echo "  この鍵では実機を上書き更新できない。鍵を正式に入れ替える場合のみ、" >&2
  echo "  build.shのEXPECTED_SIGNER_SHA256とADR-1090「7. 署名鍵」を同時に直す。" >&2
  exit 1
fi
echo "OK: signer sha256 matches: $SIGNER_SHA256"

echo "-- [10/10] BUILD-INFO.txt を書き出す --"
VERSION_CODE="$(grep -o 'android:versionCode="[0-9]*"' AndroidManifest.xml | head -1 | sed -E 's/.*="([0-9]*)"/\1/')"
VERSION_NAME="$(grep -o 'android:versionName="[^"]*"' AndroidManifest.xml | head -1 | sed -E 's/.*="([^"]*)"/\1/')"
if [ -z "$VERSION_CODE" ] || [ -z "$VERSION_NAME" ]; then
  echo "ERROR: AndroidManifest.xml から versionCode/versionName を読み取れなかった" >&2
  exit 1
fi
APK_SHA256="$(sha256sum "$OUT_DIR/app-debug.apk" | awk '{print $1}')"
{
  echo "versionCode=$VERSION_CODE"
  echo "versionName=$VERSION_NAME"
  echo "signerSha256=$SIGNER_SHA256"
  echo "apkSha256=$APK_SHA256"
} > "$OUT_DIR/BUILD-INFO.txt"
echo "OK: $OUT_DIR/BUILD-INFO.txt"

echo "== build complete: $OUT_DIR/app-debug.apk =="
echo "versionCode=$VERSION_CODE versionName=$VERSION_NAME signerSha256=$SIGNER_SHA256"
