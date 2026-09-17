package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.graphics.Path;
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
 */
final class GestureCompat {

    private static final String TAG = "SALineExport";

    private GestureCompat() {
    }

    /** Attempts a single tap at (x, y). Returns false if unsupported or it fails. */
    static boolean tap(AccessibilityService service, float x, float y, long durationMs) {
        try {
            Path path = new Path();
            path.moveTo(x, y);

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
            Object accepted = dispatchGesture.invoke(service, gesture, null, null);
            return Boolean.TRUE.equals(accepted);
        } catch (ReflectiveOperationException | RuntimeException e) {
            Log.w(TAG, "dispatchGesture fallback unavailable/failed: " + e);
            return false;
        }
    }
}
