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
    private static final String KEY_PENDING_NEXT_TRIGGER = "pending_next_trigger";
    private static final String KEY_PENDING_NEXT_AT_MS = "pending_next_at_ms";
    private static final String KEY_LAST_IMPORT_AT = "last_import_at";
    private static final String KEY_LAST_COMPLEMENT_ATTEMPT_AT = "last_complement_attempt_at";
    private static final String KEY_NOTIFICATION_RESERVED_AT = "notification_reserved_at";
    private static final String KEY_CONSECUTIVE_RETRY_COUNT = "consecutive_retry_count";

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

    /**
     * 実行ログ診断用（design.md追補 2026-10-08「実機で動いたが挙動が診断できない」）:
     * 今回の実行チェーンの中でRunSchedulerが新たに張ったアラームの種別と発火時刻
     * （絶対epoch ms）。チェーンの入口（RunScheduler#onAlarmFired、または
     * UnlockAccessibilityServiceの各request*入口）で{@link #clearPendingNextTrigger}を
     * 呼んでから、各スケジューリング箇所がここに書き込む。補完が再アームされた後に
     * 見送りで再試行が張られた場合は再試行の情報で上書きされる（「次に発火するのはどちらか」
     * という意味では再試行の方が早いため、診断上はこれで十分という判断）。
     * 既定null（このチェーンでは何も新しく張らなかった）。
     */
    static void clearPendingNextTrigger(Context context) {
        prefs(context).edit()
                .remove(KEY_PENDING_NEXT_TRIGGER)
                .remove(KEY_PENDING_NEXT_AT_MS)
                .apply();
    }

    static void setPendingNextTrigger(Context context, String triggerType, long atMs) {
        prefs(context).edit()
                .putString(KEY_PENDING_NEXT_TRIGGER, triggerType)
                .putLong(KEY_PENDING_NEXT_AT_MS, atMs)
                .apply();
    }

    /** nullなら今回のチェーンで新たに張ったアラームは無い。 */
    static String getPendingNextTrigger(Context context) {
        return prefs(context).getString(KEY_PENDING_NEXT_TRIGGER, null);
    }

    /** 絶対epoch ms。getPendingNextTrigger()がnullでないときだけ意味を持つ。 */
    static long getPendingNextAtMs(Context context) {
        return prefs(context).getLong(KEY_PENDING_NEXT_AT_MS, 0L);
    }

    /**
     * 補完（旧:保険タイマー）の起点（epoch ms）。design.md追補「取り込みの時間規則」
     * （PO決定 2026-10-09）: 書き出しフローが成功したときだけ更新する。失敗時は更新しない
     * （起点が変わらない＝早めに次が来る、安全側）。既定0（未設定＝起点が無い）。
     */
    static long getLastImportAt(Context context) {
        return prefs(context).getLong(KEY_LAST_IMPORT_AT, 0L);
    }

    static void setLastImportAt(Context context, long whenMs) {
        prefs(context).edit().putLong(KEY_LAST_IMPORT_AT, whenMs).apply();
    }

    /**
     * 補完が発火して実行を試みた時刻（epoch ms）。design.md追補「取り込みの時間規則」の
     * 欠陥修正（PO確認 2026-10-09）: 補完の再予約はlastImportAtだけを起点にすると、
     * 発火直後は起点がまだ動いていないため「計算結果が過去」になり1分後フォールバックに
     * 落ちる。その回の実行が失敗・見送りで終わるとlastImportAtは更新されないため、
     * 1分ごとに補完が発火し続けてしまう（本物の欠陥、実機で報告・修正）。
     * 補完の発火時に必ずこの値を更新することで、次回の計算が「起点とこの試行時刻の
     * 遅い方」を基準にするようになり、失敗・見送りが続いても次回は正しく30分/60分後になる
     * （1分後フォールバックは、計算結果が実際に過去になる場合だけに限定される）。
     * 既定0（未試行）。
     */
    static long getLastComplementAttemptAt(Context context) {
        return prefs(context).getLong(KEY_LAST_COMPLEMENT_ATTEMPT_AT, 0L);
    }

    static void setLastComplementAttemptAt(Context context, long whenMs) {
        prefs(context).edit().putLong(KEY_LAST_COMPLEMENT_ATTEMPT_AT, whenMs).apply();
    }

    /**
     * 通知引き金アラームの発火予定時刻（絶対epoch ms）。design.md追補 2026-10-09
     * 「通知起動が捨てられていた原因」: 「予約済みか」の判定に{@code PendingIntent}の有無
     * （FLAG_NO_CREATE）を使っていたのが原因で、{@code AlarmManager#cancel}がPendingIntent
     * 自体を消さないため以後の通知がすべて捨てられる不具合があった。代わりにこの予定時刻を
     * 保存し、「未来の予定が残っているか」で判定する（{@link RunScheduler}参照）。
     * 既定0（未予約）。
     */
    static long getNotificationReservedAt(Context context) {
        return prefs(context).getLong(KEY_NOTIFICATION_RESERVED_AT, 0L);
    }

    static void setNotificationReservedAt(Context context, long atMs) {
        prefs(context).edit().putLong(KEY_NOTIFICATION_RESERVED_AT, atMs).apply();
    }

    static void clearNotificationReservedAt(Context context) {
        prefs(context).edit().remove(KEY_NOTIFICATION_RESERVED_AT).apply();
    }

    /**
     * 取り込み失敗後の再試行（{@link RunScheduler#scheduleRetryAfterFailure}）が、連続して
     * 何回張られたか。design.md追補 2026-10-09「取り込み失敗後に30分空いていた問題」:
     * 失敗後の再試行は連続1回までに制限する。失敗の型のひとつが「PIN入力後もロック中」で
     * あり、再試行を増やすほどPIN入力の試行が増え、Android側のロックアウト（誤入力の連続で
     * 待たされる状態）に近づく。30分あたりのPIN入力試行を最大2回（補完1回＋再試行1回）に
     * 抑えるため、意図的に1回に絞っている（上限を増やすのはPO判断）。
     * 取り込み成功で{@link #clearConsecutiveRetryCount}によりリセットされる。既定0。
     */
    static int getConsecutiveRetryCount(Context context) {
        return prefs(context).getInt(KEY_CONSECUTIVE_RETRY_COUNT, 0);
    }

    static void setConsecutiveRetryCount(Context context, int count) {
        prefs(context).edit().putInt(KEY_CONSECUTIVE_RETRY_COUNT, count).apply();
    }

    static void clearConsecutiveRetryCount(Context context) {
        prefs(context).edit().remove(KEY_CONSECUTIVE_RETRY_COUNT).apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }
}
