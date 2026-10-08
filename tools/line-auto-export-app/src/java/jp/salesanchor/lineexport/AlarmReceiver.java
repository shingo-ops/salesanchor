package jp.salesanchor.lineexport;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * 段階3のアプリ内タイマー（{@link RunScheduler}）専用の受信口。Termuxからの起動口
 * （{@link RunReceiver}）とは別にする（design.md: 「発火時はUnlockAccessibilityService.
 * requestRunAllを直接呼ぶ。RunReceiver経由にしない」）。外部アプリからの起動は想定しないため
 * AndroidManifest.xmlでは exported="false"。
 *
 * - {@code ACTION_BOOT_COMPLETED}: 再起動後にアラームを張り直す（ONのときだけ）。
 * - {@code ACTION_SCHEDULED_RUN}: アラーム発火。RunScheduler.onAlarmFiredへ渡す
 *   （次回を張ってからUnlockAccessibilityService.requestRunAllを呼ぶ）。
 */
public class AlarmReceiver extends BroadcastReceiver {

    static final String ACTION_SCHEDULED_RUN = "jp.salesanchor.lineexport.SCHEDULED_RUN";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (context == null || intent == null) {
            return;
        }
        Context appContext = context.getApplicationContext();
        String action = intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(action)) {
            RunScheduler.rescheduleIfEnabled(appContext);
        } else if (ACTION_SCHEDULED_RUN.equals(action)) {
            RunScheduler.onAlarmFired(appContext);
        }
    }
}
