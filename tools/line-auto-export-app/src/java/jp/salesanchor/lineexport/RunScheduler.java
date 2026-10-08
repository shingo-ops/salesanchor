package jp.salesanchor.lineexport;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/**
 * 段階3: アプリ内タイマー（design.md「追補 2026-10-08 段階3の方式変更：固定間隔から
 * 『投稿の通知で起動』へ（PO決定A）」）。4つの引き金をすべてAlarmManagerで予約する
 * （Handler#postDelayedは使わない。NotificationListenerServiceのプロセスはOSに殺されうる
 * ため、プロセスをまたいで生き残る必要がある）。発火時は{@link AlarmReceiver}を経由して
 * （{@link RunReceiver}は経由しない）{@link UnlockAccessibilityService#requestRunAll}を
 * 直接呼ぶ。
 *
 * <pre>
 * 引き金            動作
 * 対象グループの通知  最初の通知から30秒後に実行。その30秒の間に来た通知で予約を延ばさない
 * 最短間隔（床）      前回の実行開始から3分未満なら、3分経過時点へ予約を延ばす
 * 保険のタイマー      30分ごとに1回実行（コア/オフピークの区別は廃止）
 * 使用中で見送ったとき 5分後に再試行を予約（使用中が続く間は5分ごと）
 * </pre>
 */
final class RunScheduler {

    private static final String TAG = "SALineExport";

    /** 保険のタイマーの間隔（固定30分。コア/オフピークの区別は廃止）。 */
    static final long INSURANCE_INTERVAL_MS = 30L * 60L * 1000L;
    /** 最短間隔（床）。前回の実行開始からこの時間未満なら予約を延ばす。 */
    static final long FLOOR_INTERVAL_MS = 3L * 60L * 1000L;
    /** 対象グループの通知が来てから実行するまでの待ち（バーストをまとめる）。 */
    static final long NOTIFICATION_DEBOUNCE_MS = 30L * 1000L;
    /** 使用中で見送ったときの再試行間隔。 */
    static final long RETRY_INTERVAL_MS = 5L * 60L * 1000L;

    // 引き金の種別。AlarmReceiverが受けたIntentのextraで渡し、結果通知の「引き金」表示と
    // 床判定の対象選別（保険タイマーには床を適用しない。下記onAlarmFired参照）に使う。
    static final String TRIGGER_NOTIFICATION = "notification";
    static final String TRIGGER_INSURANCE = "insurance";
    static final String TRIGGER_RETRY = "retry";

    static final String EXTRA_TRIGGER = "trigger";

    // 3つの引き金は互いに独立のアラームとして共存させるため、requestCodeを別にする
    // （PendingIntentの同一性はaction+component+requestCodeで決まり、extraは含まれない。
    // requestCodeが同じだと互いの予約を上書きしてしまう）。
    private static final int REQUEST_CODE_NOTIFICATION = 2;
    private static final int REQUEST_CODE_INSURANCE = 1;
    private static final int REQUEST_CODE_RETRY = 3;

    private static final int NOTIFICATION_ID_SCHEDULER = 1004;

    private RunScheduler() {
    }

    // ---- ON/OFF・再起動・サービス接続時の入口 ---------------------------------------------

    /**
     * ONなら保険タイマーの次回を張る（無ければ新規、あれば上書き）。OFFなら3つとも解除する。
     * BOOT_COMPLETEDと{@link UnlockAccessibilityService#onServiceConnected()}の両方から呼ぶ
     * （design.md: 再起動・アプリ更新・プロセス再生成を安全に拾うための二重化）。
     * 通知引き金・再試行は発生時に都度予約するものなので、ここでは保険タイマーだけ扱う。
     */
    static void rescheduleIfEnabled(Context context) {
        if (!SchedulerStore.isEnabled(context)) {
            cancelAll(context);
            return;
        }
        scheduleAt(context, REQUEST_CODE_INSURANCE, System.currentTimeMillis() + INSURANCE_INTERVAL_MS,
                TRIGGER_INSURANCE);
    }

    /** 設定画面でONにしたときの入口。 */
    static void enable(Context context) {
        SchedulerStore.setEnabled(context, true);
        scheduleAt(context, REQUEST_CODE_INSURANCE, System.currentTimeMillis() + INSURANCE_INTERVAL_MS,
                TRIGGER_INSURANCE);
    }

    /**
     * 設定画面でOFFにしたときの入口。3つとも解除する（design.md: 「ON/OFFトグルは通知起動と
     * 保険タイマーの両方を支配する（OFFなら何も起きない）」。再試行もOFF中は起こしたくないため
     * 同様に解除する）。暴走時に利用者が自分で止められる手段。
     */
    static void disable(Context context) {
        SchedulerStore.setEnabled(context, false);
        cancelAll(context);
    }

    // ---- 対象グループの通知が来たとき（LineNotifyListenerServiceから呼ぶ） -------------------

    /**
     * 対象グループの、かつconversationTitleが空でない通知が来たときに呼ぶ
     * （呼び出し側=LineNotifyListenerService#handleで両条件を確認済みであること）。
     * OFF中は何もしない。既に通知引き金が予約済み（このバーストの最初の通知で既に予約した）
     * なら延ばさない。未予約なら30秒後に予約する。
     */
    static void onQualifyingNotification(Context context) {
        if (!SchedulerStore.isEnabled(context)) {
            return;
        }
        if (isPending(context, REQUEST_CODE_NOTIFICATION, TRIGGER_NOTIFICATION)) {
            // バースト中の2件目以降。予約を延ばさない（長いバーストで遅延が無限に伸びるのを防ぐ）。
            return;
        }
        scheduleAt(context, REQUEST_CODE_NOTIFICATION, System.currentTimeMillis() + NOTIFICATION_DEBOUNCE_MS,
                TRIGGER_NOTIFICATION);
    }

    // ---- 使用中で見送ったとき（UnlockAccessibilityServiceから呼ぶ） --------------------------

    /** 見送り（使用中スキップ）が起きたときに呼ぶ。OFF中は何もしない。 */
    static void scheduleRetryAfterSkip(Context context) {
        if (!SchedulerStore.isEnabled(context)) {
            return;
        }
        long nextAt = System.currentTimeMillis() + RETRY_INTERVAL_MS;
        scheduleAt(context, REQUEST_CODE_RETRY, nextAt, TRIGGER_RETRY);
        // 実行ログ診断用。見送りで再試行を張ったことを今回の実行チェーンに残す
        // （保険タイマー発火が見送りになった場合は、直前にonAlarmFiredが設定した
        // insurance向けのpending-nextをここで再試行向けに上書きする。どちらが先に発火するか
        // という意味では再試行(5分)の方が早いため、診断上はこれで十分という判断）。
        SchedulerStore.setPendingNextTrigger(context, TRIGGER_RETRY, nextAt);
    }

    // ---- アラーム発火の処理（AlarmReceiverから呼ぶ） ----------------------------------------

    /**
     * {@link AlarmReceiver}が受けた発火の処理。
     * 保険タイマーは次回（+30分）をここで即座に張り直す（design.md: 「次回を張るのは、
     * 実行を始める前」。保険タイマー自身の周期は床の影響を受けない＝常に30分後に戻す）。
     * 通知/再試行は前回の実行開始から3分未満なら、3分経過時点へ同じ予約を延ばして今回は
     * 実行しない（保険タイマーは30分周期で既に床を大きく超えているため対象外。同じ
     * requestCodeに床判定分の予約を重ねると保険タイマー自身の周期が乱れるため）。
     * 実行に進む場合、通知引き金は自分の予約をここでcancelする（次のバーストのために
     * 「予約済みか」の判定をリセットする。保険/再試行は元から一回限りの予約で、発火した
     * 時点でAlarmManager内部では消費済みのため明示cancelは不要）。
     */
    static void onAlarmFired(Context context, String triggerType) {
        if (!SchedulerStore.isEnabled(context)) {
            return;
        }

        // 実行ログ診断用。このチェーンで新たに張るアラームをここから書き込み直すので、
        // 前回のチェーンの残り（古いnextTrigger）が今回のログに混ざらないよう先に消す。
        SchedulerStore.clearPendingNextTrigger(context);

        long now = System.currentTimeMillis();

        if (TRIGGER_INSURANCE.equals(triggerType)) {
            long nextAt = now + INSURANCE_INTERVAL_MS;
            scheduleAt(context, REQUEST_CODE_INSURANCE, nextAt, TRIGGER_INSURANCE);
            SchedulerStore.setPendingNextTrigger(context, TRIGGER_INSURANCE, nextAt);
        } else {
            long lastRunStartedAt = SchedulerStore.getLastRunStartedAt(context);
            if (lastRunStartedAt > 0 && now - lastRunStartedAt < FLOOR_INTERVAL_MS) {
                long deferredAt = lastRunStartedAt + FLOOR_INTERVAL_MS;
                int requestCode = TRIGGER_NOTIFICATION.equals(triggerType)
                        ? REQUEST_CODE_NOTIFICATION : REQUEST_CODE_RETRY;
                scheduleAt(context, requestCode, deferredAt, triggerType);
                return;
            }
        }

        if (TRIGGER_NOTIFICATION.equals(triggerType)) {
            cancel(context, REQUEST_CODE_NOTIFICATION, TRIGGER_NOTIFICATION);
        }

        UnlockAccessibilityService.requestRunAll(context, labelFor(triggerType));
    }

    /** 結果通知の本文に出す引き金の日本語ラベル（診断用）。 */
    static String labelFor(String triggerType) {
        if (TRIGGER_NOTIFICATION.equals(triggerType)) {
            return "通知";
        }
        if (TRIGGER_INSURANCE.equals(triggerType)) {
            return "保険タイマー";
        }
        if (TRIGGER_RETRY.equals(triggerType)) {
            return "再試行";
        }
        return triggerType;
    }

    // ---- AlarmManager操作の共通処理 ---------------------------------------------------------

    private static void scheduleAt(Context context, int requestCode, long triggerAt, String triggerType) {
        AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (am == null) {
            Log.w(TAG, "AlarmManager unavailable, cannot schedule");
            return;
        }
        PendingIntent pendingIntent = buildPendingIntent(context, requestCode, triggerType);
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

    /** 指定のrequestCode/種別の予約が現在残っているか（FLAG_NO_CREATEで既存PendingIntentの有無を見る）。 */
    private static boolean isPending(Context context, int requestCode, String triggerType) {
        Intent intent = new Intent(AlarmReceiver.ACTION_SCHEDULED_RUN);
        intent.setClass(context, AlarmReceiver.class);
        intent.putExtra(EXTRA_TRIGGER, triggerType);
        PendingIntent existing = PendingIntent.getBroadcast(context, requestCode, intent, PendingIntent.FLAG_NO_CREATE);
        return existing != null;
    }

    private static PendingIntent buildPendingIntent(Context context, int requestCode, String triggerType) {
        Intent intent = new Intent(AlarmReceiver.ACTION_SCHEDULED_RUN);
        intent.setClass(context, AlarmReceiver.class);
        intent.putExtra(EXTRA_TRIGGER, triggerType);
        return PendingIntent.getBroadcast(context, requestCode, intent, PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private static void cancel(Context context, int requestCode, String triggerType) {
        AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (am == null) {
            return;
        }
        am.cancel(buildPendingIntent(context, requestCode, triggerType));
    }

    private static void cancelAll(Context context) {
        cancel(context, REQUEST_CODE_INSURANCE, TRIGGER_INSURANCE);
        cancel(context, REQUEST_CODE_NOTIFICATION, TRIGGER_NOTIFICATION);
        cancel(context, REQUEST_CODE_RETRY, TRIGGER_RETRY);
    }

    /**
     * 正確/不正確の状態が切り替わったときだけ通知する（毎回の発火ごとに出すとコアタイムで
     * 積まれてしまうため）。design.md: 「黙って精度が落ちるのを防ぐ」。
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
