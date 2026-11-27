package jp.salesanchor.lineexport;

import android.content.Context;
import android.provider.Settings;
import android.util.Log;

/**
 * 端末の保守口（無線デバッグ）が切れていたら開き直す（ADR-1092、design.md追補 2026-11-27
 * 「保守口（無線デバッグ）が切れたらアプリが開き直す」）。
 *
 * Wi-Fiが切れている間は{@code adb_wifi_enabled}に1を書いても定着しない（実測。design.md
 * 追補参照）。そのため「0なら1を書く」を起動時（{@link AlarmReceiver}のBOOT_COMPLETED経路）
 * と毎回の実行予約時（{@link RunScheduler#scheduleAt}）に繰り返し、Wi-Fiが戻った回に定着させる
 * （アプリは1日約70回動くため、Wi-Fiが戻れば数分〜十数分で開き直る想定）。書き換えるキーは
 * {@link #KEY_ADB_WIFI_ENABLED}の1つだけに限定し、{@code adb_enabled}（USBデバッグ）には
 * 絶対に触らない（ADR-1092 What-4）。
 */
final class MaintenanceChannel {

    private static final String TAG = "SALineExport";

    /**
     * この仕組み全体を止める定数（ADR-1092 What-6）。端末を信頼できないネットワークで使う
     * 場合はfalseにする（無線デバッグが常時ONに保たれることと引き換えに人手の介入を無くす
     * 方式のため、信頼できる家庭内LANであることを前提にしている）。
     */
    private static final boolean SELF_RECOVERY_ENABLED = true;

    /**
     * 書き換え対象はこのキーだけ（ADR-1092 What-4「アプリが書く設定はadb_wifi_enabledだけに
     * 限る」）。{@code adb_enabled}（USBデバッグ）は対象外。
     */
    private static final String KEY_ADB_WIFI_ENABLED = "adb_wifi_enabled";

    private static final String RESULT_OPENED = "opened";
    private static final String RESULT_BLOCKED = "blocked";
    private static final String RESULT_NO_PERMISSION = "no_permission";

    private MaintenanceChannel() {
    }

    /**
     * {@link RunScheduler#scheduleAt}と{@link AlarmReceiver}のBOOT_COMPLETED経路の2箇所から
     * 呼ぶ（design.md追補参照。呼び出し場所をこの2箇所に限定する）。
     *
     * {@code adb_wifi_enabled}が0のときだけ1を書き、書いた後にもう一度読んで実際に1になった
     * か確かめる（Wi-Fiが無い回は0のままになるため。実測。design.md追補参照）。権限未付与
     * （{@link SecurityException}）・その他の予期しない{@link RuntimeException}は必ず捕まえ、
     * アプリ本体の動作を止めない（既存のRunLogger等と同じ「診断・復旧がアプリを壊してはいけない」
     * 作りに揃える）。
     */
    static void ensureOpen(Context context) {
        if (!SELF_RECOVERY_ENABLED) {
            return;
        }
        try {
            int current = Settings.Global.getInt(context.getContentResolver(), KEY_ADB_WIFI_ENABLED, -1);
            if (current == 1) {
                // 既に開いているときは何もしない・記録もしない（design.md追補）。
                return;
            }
            // 0（閉じている）だけでなく、-1（キーが無い・読めない）も「閉じている」として扱い
            // 書きにいく。目的は「閉じていたら開く」であり、未設定のまま放置すると保守口が
            // 永久に開かない（Opus審査 2026-11-27 の指摘1）。1を書くこと自体は無害。
            try {
                Settings.Global.putInt(context.getContentResolver(), KEY_ADB_WIFI_ENABLED, 1);
            } catch (SecurityException e) {
                // WRITE_SECURE_SETTINGSが未付与（pm grant未実施、またはアプリの入れ替えで
                // 消えた。design.md追補「pm grantはアプリを削除して入れ直すと消える」）。
                Log.w(TAG, "write adb_wifi_enabled failed (no permission): " + e);
                recordIfChanged(context, RESULT_NO_PERMISSION, current);
                return;
            }
            int after = Settings.Global.getInt(context.getContentResolver(), KEY_ADB_WIFI_ENABLED, -1);
            if (after == 1) {
                // 実際に開き直せた回は毎回記録する。変化時だけにすると、2回目以降の復旧が
                // 前回値と同じ扱いで消えてしまい、ADR-1092「維持の仕組み」が求める
                // 「復旧の実績が残る」が成り立たない（Opus審査 2026-11-27 の指摘2）。
                // 復旧は本来まれな事象なので毎回記録しても量は増えない。
                SchedulerStore.setLastMaintenanceChannelResult(context, RESULT_OPENED);
                RunLogger.logMaintenanceChannel(context, RESULT_OPENED, after);
            } else {
                // Wi-Fiが無い回は書いても定着しない（実測。design.md追補参照）。次回の
                // ensureOpen呼び出し（起動時・毎回の実行予約時）に持ち越す。
                recordIfChanged(context, RESULT_BLOCKED, after);
            }
        } catch (RuntimeException e) {
            // Settings.Global側が想定外の例外を投げた場合も含め、ここで吸収して落ちない
            // ようにする。結果が確定していないため記録はしない。
            Log.w(TAG, "ensureOpen failed: " + e);
        }
    }

    /**
     * 記録は{@link SchedulerStore}に保存した前回の結果と比較し、変化したときだけ
     * {@link RunLogger#logMaintenanceChannel}へ1行残す
     * （{@link RunScheduler}のwasLastIgnoringBatteryOptimizationsと同じ作り）。
     */
    private static void recordIfChanged(Context context, String result, int valueAfter) {
        String previous = SchedulerStore.getLastMaintenanceChannelResult(context);
        if (result.equals(previous)) {
            return;
        }
        SchedulerStore.setLastMaintenanceChannelResult(context, result);
        RunLogger.logMaintenanceChannel(context, result, valueAfter);
    }
}
