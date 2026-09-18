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

echo "-- [1/8] aapt package -m -J (R.java生成) --"
aapt package -f -m -J "$GEN_DIR" \
  -M AndroidManifest.xml \
  -S res \
  -I "$AAPT_JAR"
echo "OK: $GEN_DIR"

echo "-- [2/8] javac --release 8 --"
mapfile -t JAVA_SOURCES < <(find src/java "$GEN_DIR" -name '*.java')
javac --release 8 -encoding UTF-8 -cp "$ANDROID_JAR" -d "$CLASSES_DIR" "${JAVA_SOURCES[@]}"
echo "OK: javac compiled ${#JAVA_SOURCES[@]} file(s) -> $CLASSES_DIR"

echo "-- [3/8] dalvik-exchange (classes -> classes.dex) --"
dalvik-exchange --dex --output="$DEX_FILE" "$CLASSES_DIR"
echo "OK: $DEX_FILE"

echo "-- [4/8] aapt package (resources + manifest -> app-unsigned.apk) --"
aapt package -f \
  -M AndroidManifest.xml \
  -S res \
  -I "$AAPT_JAR" \
  -F "$OUT_DIR/app-unsigned.apk"
echo "OK: $OUT_DIR/app-unsigned.apk"

echo "-- [5/8] aapt add (classes.dex を同梱) --"
(cd "$BUILD_DIR" && aapt add "$OUT_DIR/app-unsigned.apk" classes.dex)
echo "OK: classes.dex embedded"

echo "-- [6/8] zipalign --"
zipalign -f -p 4 "$OUT_DIR/app-unsigned.apk" "$OUT_DIR/app-aligned.apk"
echo "OK: $OUT_DIR/app-aligned.apk"

echo "-- [7/8] debug keystore (keytool, 初回のみ作成) --"
if [ ! -f "$KEYSTORE" ]; then
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

echo "-- [8/8] apksigner sign --"
apksigner sign \
  --ks "$KEYSTORE" \
  --ks-pass "pass:$KEYSTORE_PASS" \
  --key-pass "pass:$KEYSTORE_PASS" \
  --ks-key-alias "$KEY_ALIAS" \
  --out "$OUT_DIR/app-debug.apk" \
  "$OUT_DIR/app-aligned.apk"
echo "OK: $OUT_DIR/app-debug.apk"

echo "== build complete: $OUT_DIR/app-debug.apk =="
