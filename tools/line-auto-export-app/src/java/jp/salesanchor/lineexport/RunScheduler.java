package jp.salesanchor.lineexport;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import java.util.Calendar;

/**
 * 段階3: アプリ内タイマー（design.md「追補 2026-10-08 段階3の設計」）。
 * コアタイム(9〜21時)は5分間隔、それ以外は30分間隔で
 * {@link UnlockAccessibilityService#requestRunAll(Context)} を直接呼ぶ（{@link RunReceiver}
 * 経由にしない。発火口は{@link AlarmReceiver}）。
 *
 * AlarmManager#setExactAndAllowWhileIdle で次回を1回だけ張り、発火のたびに次を張り直す
 * （固定周期API（setRepeating等）は使わない。時間帯で間隔を変えるため）。
 * 次回を張るのは実行を始める前（実行中に落ちても連鎖が切れないように）。
 */
final class RunScheduler {

    private static final String TAG = "SALineExport";

    // 時間帯の境界と間隔。1か所にまとめる（design.md: 実測2026-10-08・端末履歴3,306件/42日分の
    // 時刻別集計に基づく。9-21時が全体の84%、3-7時はほぼ皆無）。
    static final int CORE_START_HOUR = 9;
    static final int CORE_END_HOUR = 21;
    static final long CORE_INTERVAL_MS = 5L * 60L * 1000L;
    static final long OFF_PEAK_INTERVAL_MS = 30L * 60L * 1000L;

    private static final int REQUEST_CODE = 1;
    private static final int NOTIFICATION_ID_SCHEDULER = 1004;

    private RunScheduler() {
    }

    /**
     * ONなら次回アラームを張る（無ければ新規、あれば上書き）。OFFなら解除する。
     * BOOT_COMPLETEDと{@link UnlockAccessibilityService#onServiceConnected()}の両方から呼ぶ
     * （design.md: 再起動・アプリ更新・プロセス再生成を安全に拾うための二重化）。
     */
    static void rescheduleIfEnabled(Context context) {
        if (!SchedulerStore.isEnabled(context)) {
            cancel(context);
            return;
        }
        scheduleNext(context, System.currentTimeMillis());
    }

    /** 設定画面でONにしたときの入口。 */
    static void enable(Context context) {
        SchedulerStore.setEnabled(context, true);
        scheduleNext(context, System.currentTimeMillis());
    }

    /** 設定画面でOFFにしたときの入口。暴走時に利用者が自分で止められる手段（design.md）。 */
    static void disable(Context context) {
        SchedulerStore.setEnabled(context, false);
        cancel(context);
    }

    /**
     * {@link AlarmReceiver}が受けた発火の処理。次回を張ってから
     * {@link UnlockAccessibilityService#requestRunAll(Context)}を呼ぶ（この順序が重要。
     * design.md: 「次回を張るのは、実行を始める前」）。
     *
     * 多重起動の防止はUnlockAccessibilityService側の既存のrunningガードに委ねる
     * （アプリ内タイマーとTermuxの15分ジョブの両方から合図が来るため）。
     */
    static void onAlarmFired(Context context) {
        if (!SchedulerStore.isEnabled(context)) {
            // OFFにした直後にcancel()が間に合わず届いた発火は無視する（念のための二重防御）。
            return;
        }
        scheduleNext(context, System.currentTimeMillis());
        UnlockAccessibilityService.requestRunAll(context);
    }

    private static void scheduleNext(Context context, long now) {
        AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (am == null) {
            Log.w(TAG, "AlarmManager unavailable, cannot schedule");
            return;
        }
        long intervalMs = isCoreTime(now) ? CORE_INTERVAL_MS : OFF_PEAK_INTERVAL_MS;
        long triggerAt = now + intervalMs;
        PendingIntent pendingIntent = buildPendingIntent(context);

        boolean exact = trySetExactAndAllowWhileIdle(am, triggerAt, pendingIntent);
        if (!exact) {
            // Android 12+ の正確アラーム制限などでsetExactAndAllowWhileIdleが使えない場合の
            // フォールバック（不正確。setAndAllowWhileIdle自体はAPI23から存在し直接呼べる）。
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent);
        }
        notifyIfExactModeChanged(context, exact);
        SchedulerStore.setLastScheduleWasExact(context, exact);
    }

    /**
     * setExactAndAllowWhileIdleを試す。成功したらtrue。SecurityException等で使えない場合は
     * falseを返し、呼び出し側でsetAndAllowWhileIdleへ落とす。
     *
     * 判定にAlarmManager#canScheduleExactAlarms()（API31で追加）を使う案もあったが、
     * android.jarはAPI23のため参照にはリフレクションが必要になる。setExactAndAllowWhileIdle
     * 自体はAPI23から存在し直接呼べるため、ここでは「実際に呼んで失敗を検知する」方式にして
     * リフレクションを避けた（結果は同じ: 使えなければ不正確な代替へ落とす）。
     */
    private static boolean trySetExactAndAllowWhileIdle(AlarmManager am, long triggerAt, PendingIntent pendingIntent) {
        try {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pendingIntent);
            return true;
        } catch (RuntimeException e) {
            Log.w(TAG, "setExactAndAllowWhileIdle failed, falling back to inexact: " + e);
            return false;
        }
    }

    /** ローカル時刻でコアタイム(9-21時)かどうかを判定する。 */
    private static boolean isCoreTime(long epochMs) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(epochMs);
        int hour = cal.get(Calendar.HOUR_OF_DAY);
        return hour >= CORE_START_HOUR && hour < CORE_END_HOUR;
    }

    private static PendingIntent buildPendingIntent(Context context) {
        Intent intent = new Intent(AlarmReceiver.ACTION_SCHEDULED_RUN);
        intent.setClass(context, AlarmReceiver.class);
        return PendingIntent.getBroadcast(context, REQUEST_CODE, intent, PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private static void cancel(Context context) {
        AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (am == null) {
            return;
        }
        am.cancel(buildPendingIntent(context));
    }

    /**
     * 正確/不正確の状態が切り替わったときだけ通知する（毎回の発火ごとに出すとコアタイムで
     * 5分おきに通知が積まれてしまうため）。design.md: 「黙って精度が落ちるのを防ぐ」。
     */
    private static void notifyIfExactModeChanged(Context context, boolean nowExact) {
        boolean previouslyExact = SchedulerStore.wasLastScheduleExact(context);
        if (nowExact == previouslyExact) {
            return;
        }
        String title = nowExact
                ? "アプリ内タイマー: 正確なアラームに復帰"
                : "アプリ内タイマー: 不正確なアラームに切替";
        String body = nowExact
                ? "setExactAndAllowWhileIdleが使えるようになりました。"
                : "setExactAndAllowWhileIdleが使えないため、setAndAllowWhileIdle（不正確）に"
                        + "切り替えました。発火の間隔がずれる場合があります。";
        NotificationCompat.ensureChannel(context, UnlockAccessibilityService.CHANNEL_ID, "SA LINE Export");
        Notification.Builder builder = NotificationCompat.newBuilder(context, UnlockAccessibilityService.CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(body)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true);
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID_SCHEDULER, builder.build());
        }
    }
}
