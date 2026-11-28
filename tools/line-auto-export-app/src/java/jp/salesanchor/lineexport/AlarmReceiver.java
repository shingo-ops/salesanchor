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
 * - {@code ACTION_BOOT_COMPLETED}: 再起動後に補完を張り直す（ONのときだけ）。アプリ内タイマーが
 *   OFFでも保守口（無線デバッグ）の確認は行うため、{@link RunScheduler#rescheduleIfEnabled}へ
 *   委譲する前に{@link MaintenanceChannel#cycle}を1回呼ぶ（trigger="boot"。ADR-1092、
 *   design.md追補 2026-11-27「保守口（無線デバッグ）の強制開け直し」①）。{@code ensureOpen}
 *   ではなく{@code cycle}を使う理由: 再起動直後は{@code adb_wifi_enabled}が1のままadbd
 *   （無線デバッグのサーバー本体）が起動していない事象があり得るため、値を見ずに必ず開け直す
 *   必要がある。{@code cycle}は内部で約2秒待つが、BroadcastReceiverの実行時間制限（約10秒）
 *   には遠く届かないため、既存の作り（goAsyncや別スレッドへの委譲は無く、同期呼び出しのまま）
 *   を変えていない。
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
            MaintenanceChannel.cycle(appContext, MaintenanceChannel.TRIGGER_BOOT);
            RunScheduler.rescheduleIfEnabled(appContext);
        } else if (ACTION_SCHEDULED_RUN.equals(action)) {
            String triggerType = intent.getStringExtra(RunScheduler.EXTRA_TRIGGER);
            RunScheduler.onAlarmFired(appContext, triggerType);
        }
    }
}
