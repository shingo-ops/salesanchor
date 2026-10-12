package jp.salesanchor.lineexport;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * PIN persistence for this app's private storage.
 *
 * NOTE (design.md 段階1): EncryptedSharedPreferences (androidx.security-crypto) is NOT
 * available in this offline proot build environment — no androidx jars are present and
 * this toolchain has no dependency resolution (javac + android.jar API23 only). Per the
 * design doc's explicit fallback, this uses a plain private-mode SharedPreferences file
 * instead, and that choice must be reported.
 *
 * The PIN value itself must never be logged, displayed, or placed in Intent extras.
 * Callers must only display whether a PIN is saved (see hasPin), never the value.
 */
final class PinStore {

    private static final String PREFS_NAME = "sa_line_export_secure";
    private static final String KEY_PIN = "pin";

    private PinStore() {
    }

    static void savePin(Context context, String pin) {
        SharedPreferences prefs = prefs(context);
        prefs.edit().putString(KEY_PIN, pin).apply();
    }

    static boolean hasPin(Context context) {
        return prefs(context).contains(KEY_PIN);
    }

    /** Returns the saved PIN, or null if none is saved. Never log the result. */
    static String loadPin(Context context) {
        return prefs(context).getString(KEY_PIN, null);
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }
}
