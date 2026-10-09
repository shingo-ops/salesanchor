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
 * 段階3: アプリ内タイマー（design.md「追補 2026-10-08 段階3の方式変更：固定間隔から
 * 『投稿の通知で起動』へ（PO決定A）」、および追補「取り込みの時間規則」PO決定
 * 2026-10-09）。4つの引き金をすべてAlarmManagerで予約する（Handler#postDelayedは
 * 使わない。NotificationListenerServiceのプロセスはOSに殺されうるため、プロセスを
 * またいで生き残る必要がある）。発火時は{@link AlarmReceiver}を経由して
 * （{@link RunReceiver}は経由しない）{@link UnlockAccessibilityService#requestRunAll}を
 * 直接呼ぶ。
 *
 * <pre>
 * 引き金            動作
 * 対象グループの通知  最初の通知から30秒後に実行。その30秒の間に来た通知で予約を延ばさない
 * 最短間隔（床）      前回の実行開始から3分未満なら、3分経過時点へ予約を延ばす
 * 補完（旧:保険タイマー）最後の取り込み（起点）から、起点の時刻帯で決まる間隔が空いたら実行。
 *                   コアタイム(7:00以上)は30分、コア外(0:00〜6:59)は60分。通知等で取り込みが
 *                   起きるたびに起点が更新され、補完の予約はその時刻から数え直して張り替わる
 *                   （＝通知が頻繁な時間帯は補完が一度も発動しない）
 * 使用中で見送ったとき 5分後に再試行を予約（使用中が続く間は5分ごと）
 * </pre>
 */
final class RunScheduler {

    private static final String TAG = "SALineExport";

    /**
     * コアタイムの境目（この時刻以上24:00未満がコア、0:00〜6:59がコア外）。
     * 実測根拠（design.md追補「取り込みの時間規則」）: 投稿3,306件のうちコアタイム内が
     * 96.9%、0:00〜6:59は3.1%（1日あたり約2.5件）。
     */
    static final int CORE_START_HOUR = 7;
    /** 補完の間隔（起点がコアタイムのとき）。 */
    static final long CORE_COMPLEMENT_INTERVAL_MS = 30L * 60L * 1000L;
    /** 補完の間隔（起点がコア外のとき）。 */
    static final long OFF_PEAK_COMPLEMENT_INTERVAL_MS = 60L * 60L * 1000L;
    /**
     * 計算した次回がすでに過去だった場合に代わりに使う間隔（タイトループ防止）。
     * design.md追補「取り込みの時間規則」規則5。
     */
    static final long COMPLEMENT_PAST_DUE_RETRY_MS = 60L * 1000L;
    /** 最短間隔（床）。前回の実行開始からこの時間未満なら予約を延ばす。 */
    static final long FLOOR_INTERVAL_MS = 3L * 60L * 1000L;
    /** 対象グループの通知が来てから実行するまでの待ち（バーストをまとめる）。 */
    static final long NOTIFICATION_DEBOUNCE_MS = 30L * 1000L;
    /** 使用中で見送ったときの再試行間隔。 */
    static final long RETRY_INTERVAL_MS = 5L * 60L * 1000L;

    // 引き金の種別。AlarmReceiverが受けたIntentのextraで渡し、結果通知の「引き金」表示と
    // 床判定の対象選別（補完には床を適用しない。下記onAlarmFired参照）に使う。
    // "insurance"から"complement"へ改名（design.md追補「取り込みの時間規則」:
    // 固定間隔の保険から、最後の取り込みを起点に数え直す補完へ意味が変わったため）。
    static final String TRIGGER_NOTIFICATION = "notification";
    static final String TRIGGER_COMPLEMENT = "complement";
    static final String TRIGGER_RETRY = "retry";

    static final String EXTRA_TRIGGER = "trigger";

    // 3つの引き金は互いに独立のアラームとして共存させるため、requestCodeを別にする
    // （PendingIntentの同一性はaction+component+requestCodeで決まり、extraは含まれない。
    // requestCodeが同じだと互いの予約を上書きしてしまう）。
    private static final int REQUEST_CODE_NOTIFICATION = 2;
    private static final int REQUEST_CODE_COMPLEMENT = 1;
    private static final int REQUEST_CODE_RETRY = 3;

    private static final int NOTIFICATION_ID_SCHEDULER = 1004;

    private RunScheduler() {
    }

    // ---- ON/OFF・再起動・サービス接続時の入口 ---------------------------------------------

    /**
     * ONなら補完の次回を、保存された起点（{@link SchedulerStore#getLastImportAt}。無ければ
     * "今"）から計算して張る（無ければ新規、あれば上書き）。OFFなら3つとも解除する。
     * BOOT_COMPLETEDと{@link UnlockAccessibilityService#onServiceConnected()}の両方から呼ぶ
     * （design.md: 再起動・アプリ更新・プロセス再生成を安全に拾うための二重化）。
     * 通知引き金・再試行は発生時に都度予約するものなので、ここでは補完だけ扱う。
     */
    static void rescheduleIfEnabled(Context context) {
        if (!SchedulerStore.isEnabled(context)) {
            cancelAll(context);
            return;
        }
        long nextAt = computeNextComplementAt(context);
        scheduleAt(context, REQUEST_CODE_COMPLEMENT, nextAt, TRIGGER_COMPLEMENT);
        SchedulerStore.setPendingNextTrigger(context, TRIGGER_COMPLEMENT, nextAt);
    }

    /** 設定画面でONにしたときの入口。 */
    static void enable(Context context) {
        SchedulerStore.setEnabled(context, true);
        long nextAt = computeNextComplementAt(context);
        scheduleAt(context, REQUEST_CODE_COMPLEMENT, nextAt, TRIGGER_COMPLEMENT);
        SchedulerStore.setPendingNextTrigger(context, TRIGGER_COMPLEMENT, nextAt);
    }

    /**
     * 設定画面でOFFにしたときの入口。3つとも解除する（design.md: 「ON/OFFトグルは通知起動と
     * 補完の両方を支配する（OFFなら何も起きない）」。再試行もOFF中は起こしたくないため
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
        // （補完発火が見送りになった場合は、直前にonAlarmFiredが設定した
        // complement向けのpending-nextをここで再試行向けに上書きする。どちらが先に発火するか
        // という意味では再試行(5分)の方が早いため、診断上はこれで十分という判断）。
        SchedulerStore.setPendingNextTrigger(context, TRIGGER_RETRY, nextAt);
    }

    // ---- アラーム発火の処理（AlarmReceiverから呼ぶ） ----------------------------------------

    /**
     * {@link AlarmReceiver}が受けた発火の処理。
     * 補完は次回をここで即座に張り直す（design.md: 「次回を張るのは、実行を始める前」）。
     * 張り直す前に、今回の発火自体を試行時刻として{@link SchedulerStore#setLastComplementAttemptAt}
     * へ記録する（design.md追補「取り込みの時間規則」の欠陥修正、PO確認 2026-10-09）:
     * これを記録せずに起点（最後の取り込み）だけを基準にすると、発火直後は起点がまだ
     * 動いていないため計算結果が「すでに過去」になり、その回の実行が失敗・見送りで終わると
     * 起点も動かないままなので、1分後フォールバック→失敗→1分後フォールバック…と1分ごとに
     * 発火し続ける不具合になる（実機で確認）。試行時刻を記録しておけば、{@link
     * #computeNextComplementAt}が「起点とこの試行時刻の遅い方」を基準に計算するため、
     * 失敗・見送りが続いても次回は正しく30分/60分後になる。今回の発火が成功すれば
     * {@link #recordSuccessfulImport}が起点（lastImportAt）を更新し、そちらが新しくなる
     * ためさらに前に進む。補完自身はこの仕組みで自己再アームするため、床の対象外（同じ
     * requestCodeに床判定分の予約を重ねると補完自身の張り直しが乱れるため）。
     * 通知/再試行は前回の実行開始から3分未満なら、3分経過時点へ同じ予約を延ばして今回は
     * 実行しない。
     * 実行に進む場合、通知引き金は自分の予約をここでcancelする（次のバーストのために
     * 「予約済みか」の判定をリセットする。補完/再試行は元から一回限りの予約で、発火した
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

        if (TRIGGER_COMPLEMENT.equals(triggerType)) {
            // 必ず試行時刻を記録してから次回を計算する（上記javadocの欠陥修正の要）。
            SchedulerStore.setLastComplementAttemptAt(context, now);
            long nextAt = computeNextComplementAt(context);
            scheduleAt(context, REQUEST_CODE_COMPLEMENT, nextAt, TRIGGER_COMPLEMENT);
            SchedulerStore.setPendingNextTrigger(context, TRIGGER_COMPLEMENT, nextAt);
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
        if (TRIGGER_COMPLEMENT.equals(triggerType)) {
            return "補完";
        }
        if (TRIGGER_RETRY.equals(triggerType)) {
            return "再試行";
        }
        return triggerType;
    }

    // ---- 補完（design.md追補「取り込みの時間規則」PO決定 2026-10-09） ------------------------

    /**
     * 書き出しフローが成功したときだけ呼ぶ（{@link LineExportFlow#finish}から。失敗時は
     * 呼ばない＝起点が変わらない＝早めに次の補完が来る、安全側）。起点を今の時刻に更新し、
     * 補完の次回を新しい起点から計算して張り直す（＝通知等で取り込みが起きるたびに、補完の
     * 予約はその時刻から数え直して張り替わる）。
     *
     * OFF中でも起点自体は更新する（将来ONにしたときに正しい起点を使えるようにするため）。
     * 補完アラームの張り直しはON中だけ行う。
     */
    static void recordSuccessfulImport(Context context) {
        SchedulerStore.setLastImportAt(context, System.currentTimeMillis());
        if (!SchedulerStore.isEnabled(context)) {
            return;
        }
        long nextAt = computeNextComplementAt(context);
        scheduleAt(context, REQUEST_CODE_COMPLEMENT, nextAt, TRIGGER_COMPLEMENT);
        SchedulerStore.setPendingNextTrigger(context, TRIGGER_COMPLEMENT, nextAt);
    }

    /**
     * 補完の次回発火時刻を計算する。基準時刻は「{@link SchedulerStore#getLastImportAt}
     * （最後に取り込みが成功した時刻）」と「{@link SchedulerStore#getLastComplementAttemptAt}
     * （補完が最後に発火を試みた時刻）」の遅い方（どちらも無ければ"今"）。この遅い方を
     * 基準時刻の時刻帯で間隔を決める（PO決定・案A: 発火時刻ではなく基準時刻で決める。
     * 例: 基準時刻が23:50（コア内）→+30分→0:20に発火、発火時刻がコア外でも60分にしない。
     * 計算を1回で済ませ挙動を読みやすくするため）。
     *
     * 「遅い方」を使う理由（design.md追補「取り込みの時間規則」の欠陥修正、PO確認
     * 2026-10-09）: lastImportAtだけを基準にすると、補完が発火した直後はまだlastImportAtが
     * 動いていないため計算結果が常に過去になり、その発火が失敗・見送りで終わると
     * lastImportAtも動かないため、1分後フォールバック→失敗→1分後フォールバック…と
     * 1分ごとに発火し続けてしまう（実機で確認した本物の欠陥）。lastComplementAttemptAtを
     * 合わせて基準にすることで、失敗・見送りが続いても次回は正しく30分/60分後になる。
     *
     * 1分後フォールバック（規則5、タイトループ防止）は、この「遅い方」を使ってもなお
     * 結果が過去になる場合（基準時刻が古すぎる・端末時計が進んだ等）だけに限定される。
     * 通常経路では使われない。
     */
    private static long computeNextComplementAt(Context context) {
        long lastImportAt = SchedulerStore.getLastImportAt(context);
        long lastAttemptAt = SchedulerStore.getLastComplementAttemptAt(context);
        long anchor = Math.max(lastImportAt, lastAttemptAt);
        if (anchor <= 0) {
            anchor = System.currentTimeMillis();
        }
        long intervalMs = isCoreTime(anchor) ? CORE_COMPLEMENT_INTERVAL_MS : OFF_PEAK_COMPLEMENT_INTERVAL_MS;
        long nextAt = anchor + intervalMs;
        long now = System.currentTimeMillis();
        if (nextAt <= now) {
            nextAt = now + COMPLEMENT_PAST_DUE_RETRY_MS;
        }
        return nextAt;
    }

    /** ローカル時刻でCORE_START_HOUR（7時）以上24時未満かどうかを判定する。 */
    private static boolean isCoreTime(long epochMs) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(epochMs);
        int hour = cal.get(Calendar.HOUR_OF_DAY);
        return hour >= CORE_START_HOUR;
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
        cancel(context, REQUEST_CODE_COMPLEMENT, TRIGGER_COMPLEMENT);
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
