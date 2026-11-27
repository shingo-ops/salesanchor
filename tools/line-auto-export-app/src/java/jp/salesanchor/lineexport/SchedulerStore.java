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
    private static final String KEY_LAST_IGNORING_BATTERY_OPTIMIZATIONS = "last_ignoring_battery_optimizations";
    private static final String KEY_SCHEDULED_FIRE_AT_PREFIX = "scheduled_fire_at_";
    private static final String KEY_LAST_MAINTENANCE_CHANNEL_RESULT = "last_maintenance_channel_result";

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
     * 何回張られたか。design.md追補 2026-10-09「取り込み失敗後に30分空いていた問題」で
     * 連続再試行の回数に上限（{@link RunScheduler#MAX_CONSECUTIVE_RETRIES}）を設けた。
     * 上限の値・根拠（2026-10-11更新: 1→2、初回を含めて合計3回試す）は同定数のjavadoc参照。
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

    /**
     * 直近に確認した「電池最適化の除外」（{@code PowerManager#isIgnoringBatteryOptimizations}）の
     * 状態。design.md追補「電池最適化で後回しにされたことを検知・記録・復旧できる仕組み」
     * (2026-11-26)。{@link #wasLastScheduleExact}と同じ作り（既定値は楽観的にtrue。実際に
     * 除外が外れたときだけfalseに切り替わる）。{@link RunScheduler}が変化時だけ更新する。
     */
    static boolean wasLastIgnoringBatteryOptimizations(Context context) {
        return prefs(context).getBoolean(KEY_LAST_IGNORING_BATTERY_OPTIMIZATIONS, true);
    }

    static void setLastIgnoringBatteryOptimizations(Context context, boolean ignoring) {
        prefs(context).edit().putBoolean(KEY_LAST_IGNORING_BATTERY_OPTIMIZATIONS, ignoring).apply();
    }

    /**
     * 引き金（{@link RunScheduler}のTRIGGER_*定数）ごとの「発火予定時刻」（絶対epoch ms）。
     * design.md追補「電池最適化で後回しにされたことを検知・記録・復旧できる仕組み」(2026-11-26):
     * 省電力区分が上がるとAlarmManagerの発火が1時間に1回などに制限され、予約したのに発火
     * しない「空振り」が起きる（実機2026-11-26で48分・予約4回・実行0回を確認）。予約時に
     * ここへ保存し、発火を受けたら消す（{@link RunScheduler#onAlarmFired}）。スケジューラの
     * 入口を通るたびに、残っている値が十分古ければ「空振り」として検知できる
     * （{@link RunScheduler}参照）。{@link #getNotificationReservedAt}とは別の仕組み
     * （そちらは通知引き金のバースト抑制専用の判定に使っており、意味が違うため共用しない）。
     * 既定0（未予約）。
     */
    static long getScheduledFireAt(Context context, String triggerType) {
        return prefs(context).getLong(KEY_SCHEDULED_FIRE_AT_PREFIX + triggerType, 0L);
    }

    static void setScheduledFireAt(Context context, String triggerType, long atMs) {
        prefs(context).edit().putLong(KEY_SCHEDULED_FIRE_AT_PREFIX + triggerType, atMs).apply();
    }

    static void clearScheduledFireAt(Context context, String triggerType) {
        prefs(context).edit().remove(KEY_SCHEDULED_FIRE_AT_PREFIX + triggerType).apply();
    }

    /**
     * 直近に記録した保守口（無線デバッグ）の復旧結果（"opened"/"blocked"/"no_permission"）。
     * ADR-1092、design.md追補 2026-11-27「保守口（無線デバッグ）が切れたらアプリが開き直す」。
     * {@link #wasLastIgnoringBatteryOptimizations}と同じ作り（{@link MaintenanceChannel}が
     * 前回値と比較し、変化したときだけ更新・記録する）。既定null（まだ一度も記録していない）。
     */
    static String getLastMaintenanceChannelResult(Context context) {
        return prefs(context).getString(KEY_LAST_MAINTENANCE_CHANNEL_RESULT, null);
    }

    static void setLastMaintenanceChannelResult(Context context, String result) {
        prefs(context).edit().putString(KEY_LAST_MAINTENANCE_CHANNEL_RESULT, result).apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }
}
