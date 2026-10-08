package jp.salesanchor.lineexport;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * RunScheduler（段階3のアプリ内タイマー）の設定・状態の永続化。PinStore/NotifyStoreと同じ
 * private SharedPreferences方式（別ファイル名）。秘匿値は扱わないため平文保存でよい。
 */
final class SchedulerStore {

    private static final String PREFS_NAME = "sa_line_export_scheduler";

    private static final String KEY_ENABLED = "enabled";
    private static final String KEY_LAST_SCHEDULE_EXACT = "last_schedule_exact";

    /** 既定はOFF（design.md: インストール直後に勝手に動き出さないこと）。 */
    private static final boolean DEFAULT_ENABLED = false;

    private SchedulerStore() {
    }

    /** アプリ内タイマーがONかどうか。設定画面のトグルで変更する。 */
    static boolean isEnabled(Context context) {
        return prefs(context).getBoolean(KEY_ENABLED, DEFAULT_ENABLED);
    }

    static void setEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(KEY_ENABLED, enabled).apply();
    }

    /**
     * 直近のアラーム設定がsetExactAndAllowWhileIdle（正確）で成功したか。
     * 既定はtrue（楽観。実際にフォールバックが起きたときだけfalseに切り替わる）。
     */
    static boolean wasLastScheduleExact(Context context) {
        return prefs(context).getBoolean(KEY_LAST_SCHEDULE_EXACT, true);
    }

    static void setLastScheduleWasExact(Context context, boolean exact) {
        prefs(context).edit().putBoolean(KEY_LAST_SCHEDULE_EXACT, exact).apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }
}
