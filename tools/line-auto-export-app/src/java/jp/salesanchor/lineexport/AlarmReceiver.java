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
 * - {@code ACTION_BOOT_COMPLETED}: 再起動後に補完を張り直す（ONのときだけ）。
 * - {@code ACTION_SCHEDULED_RUN}: アラーム発火。{@code EXTRA_TRIGGER}extraで渡された引き金
 *   種別（通知／補完／再試行）とともにRunScheduler.onAlarmFiredへ渡す。
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
            String triggerType = intent.getStringExtra(RunScheduler.EXTRA_TRIGGER);
            RunScheduler.onAlarmFired(appContext, triggerType);
        }
    }
}
