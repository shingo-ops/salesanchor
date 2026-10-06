package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.KeyguardManager;
import android.content.Context;
import android.graphics.Path;
import android.os.PowerManager;
import android.util.Log;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;

/**
 * Reflection shim for AccessibilityService#dispatchGesture, used as a coordinate-tap
 * fallback when a node cannot be found/clicked by text or content-description.
 *
 * dispatchGesture and the GestureDescription family were added in API24, so their
 * classes/methods do not exist in this build environment's android.jar (pinned to
 * API23 — see docs/handoff/line-auto-export-app/design.md). Reflection is used so this
 * still compiles; on the real target device (Android 16) the real framework classes
 * exist at runtime and the calls work normally.
 *
 * IMPORTANT CAVEAT (report this): granting the CAN_PERFORM_GESTURES capability requires
 * declaring android:canPerformGestures="true" in accessibility_service_config.xml, but
 * that attribute itself was also added in API24 and this build's aapt (linked against
 * the API23 android.jar) fails to compile it ("No resource identifier found for
 * attribute 'canPerformGestures'"). So this fallback may be refused by the OS at
 * runtime even though the code path below is implemented. Untested until stage 1's
 * real-device run (see recon.md 未確認).
 *
 * 診断（原因判別）: dispatchGesture の戻り値（OSが受理したか）だけでは、受理後に本当に
 * ジェスチャが実行されたか（無視されただけか）を区別できない。GestureResultCallback の
 * onCompleted/onCancelledのどちらが呼ばれたか（呼ばれないことも含め）を区別するため、
 * callbackにGestureCallbackShim（GestureOutcome経由で結果を受け取る）を渡している。
 * GestureCallbackShimはAPI34でコンパイルされた別クラス（build.sh参照）で、ここでは
 * Class.forName経由のリフレクションでのみ生成する。
 */
final class GestureCompat {

    private static final String TAG = "SALineExport";

    /** onCompleted/onCancelledのどちらも来ない場合の最大待ち時間。 */
    private static final long CALLBACK_TIMEOUT_MS = 2000L;

    private GestureCompat() {
    }

    /** 1回のdispatchGesture呼び出しの診断結果（通知本文に載せる）。 */
    static final class DispatchReport {
        final String label;
        final boolean accepted;
        final String callbackResult;
        final String deviceState;

        DispatchReport(String label, boolean accepted, String callbackResult, String deviceState) {
            this.label = label;
            this.accepted = accepted;
            this.callbackResult = callbackResult;
            this.deviceState = deviceState;
        }

        /** 通知本文に追記する短い診断文字列。 */
        String describe() {
            return "[" + label + "]dispatch=" + accepted + ",cb=" + callbackResult + "," + deviceState;
        }
    }

    /** Attempts a single tap at (x, y). label は診断用の識別名（例: "pin-key-1"、"enter"）。 */
    static DispatchReport tap(AccessibilityService service, float x, float y, long durationMs, String label) {
        Path path = new Path();
        path.moveTo(x, y);
        return dispatch(service, path, durationMs, label);
    }

    /**
     * Attempts a swipe from (x1, y1) to (x2, y2). ロック画面では上スワイプで数字キー
     * （Bouncer）を出す必要がある（2026-09-18 実機で確認）。
     */
    static DispatchReport swipe(AccessibilityService service, float x1, float y1, float x2, float y2,
            long durationMs, String label) {
        Path path = new Path();
        path.moveTo(x1, y1);
        path.lineTo(x2, y2);
        return dispatch(service, path, durationMs, label);
    }

    private static DispatchReport dispatch(AccessibilityService service, Path path, long durationMs, String label) {
        boolean accepted = false;
        String callbackResult;
        GestureOutcome outcome = new GestureOutcome();
        try {
            Class<?> strokeClass = Class.forName("android.accessibilityservice.GestureDescription$StrokeDescription");
            Constructor<?> strokeCtor = strokeClass.getConstructor(Path.class, long.class, long.class);
            Object stroke = strokeCtor.newInstance(path, 0L, durationMs);

            Class<?> builderClass = Class.forName("android.accessibilityservice.GestureDescription$Builder");
            Object builder = builderClass.getConstructor().newInstance();
            Method addStroke = builderClass.getMethod("addStroke", strokeClass);
            addStroke.invoke(builder, stroke);
            Method build = builderClass.getMethod("build");
            Object gesture = build.invoke(builder);

            Class<?> gestureClass = Class.forName("android.accessibilityservice.GestureDescription");
            Class<?> callbackClass = Class.forName("android.accessibilityservice.AccessibilityService$GestureResultCallback");
            Method dispatchGesture = AccessibilityService.class.getMethod(
                    "dispatchGesture", gestureClass, callbackClass, android.os.Handler.class);

            Object callback = newShimOrNull(outcome);

            Object acceptedObj = dispatchGesture.invoke(service, gesture, callback, null);
            accepted = Boolean.TRUE.equals(acceptedObj);

            if (!accepted) {
                // OSが受理しなかった場合、callbackは呼ばれない。
                callbackResult = GestureOutcome.NO_CALLBACK;
            } else if (callback == null) {
                callbackResult = "shim-unavailable";
            } else {
                callbackResult = outcome.awaitResult(CALLBACK_TIMEOUT_MS);
            }
        } catch (ReflectiveOperationException | RuntimeException e) {
            Log.w(TAG, "dispatchGesture fallback unavailable/failed: " + e);
            callbackResult = "error:" + e.getClass().getSimpleName();
        }

        return new DispatchReport(label, accepted, callbackResult, describeDeviceState(service));
    }

    /** GestureCallbackShim（API34でコンパイル）をリフレクションで生成。失敗したらnull。 */
    private static Object newShimOrNull(GestureOutcome outcome) {
        try {
            Class<?> shimClass = Class.forName("jp.salesanchor.lineexport.GestureCallbackShim");
            Constructor<?> ctor = shimClass.getConstructor(GestureOutcome.class);
            return ctor.newInstance(outcome);
        } catch (ReflectiveOperationException | LinkageError e) {
            Log.w(TAG, "GestureCallbackShim unavailable: " + e);
            return null;
        }
    }

    /** keyguardLocked / 画面ON・OFF / capabilities ビットを1行にまとめる。PIN等の秘密は含まない。 */
    private static String describeDeviceState(AccessibilityService service) {
        boolean locked = false;
        boolean screenOn = false;
        int capabilities = -1;
        try {
            KeyguardManager km = (KeyguardManager) service.getSystemService(Context.KEYGUARD_SERVICE);
            locked = km != null && km.isKeyguardLocked();
        } catch (RuntimeException e) {
            Log.w(TAG, "KeyguardManager read failed: " + e);
        }
        try {
            PowerManager pm = (PowerManager) service.getSystemService(Context.POWER_SERVICE);
            screenOn = pm != null && pm.isInteractive();
        } catch (RuntimeException e) {
            Log.w(TAG, "PowerManager read failed: " + e);
        }
        try {
            AccessibilityServiceInfo info = service.getServiceInfo();
            if (info != null) {
                capabilities = info.getCapabilities();
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "AccessibilityServiceInfo read failed: " + e);
        }
        return "locked=" + locked + ",screenOn=" + screenOn + ",caps=0x" + Integer.toHexString(capabilities);
    }
}
