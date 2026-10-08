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
    private static final String KEY_LAST_RUN_STARTED_AT = "last_run_started_at";

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

    /**
     * 前回「実際に実行を開始した」時刻（epoch ms）。見送り（使用中スキップ）は含めない
     * （画面を起こさないため、最短間隔の床の対象にする必要が無い）。床の判定に使う。
     * 既定0（未実行）。
     */
    static long getLastRunStartedAt(Context context) {
        return prefs(context).getLong(KEY_LAST_RUN_STARTED_AT, 0L);
    }

    static void setLastRunStartedAt(Context context, long whenMs) {
        prefs(context).edit().putLong(KEY_LAST_RUN_STARTED_AT, whenMs).apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }
}
