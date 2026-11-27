package jp.salesanchor.lineexport;

import android.content.Context;
import android.provider.Settings;
import android.util.Log;

import java.io.File;

/**
 * 端末の保守口（無線デバッグ）が切れていたら開き直す（ADR-1092、design.md追補 2026-11-27
 * 「保守口（無線デバッグ）が切れたらアプリが開き直す」／「保守口（無線デバッグ）の強制
 * 開け直し」）。
 *
 * Wi-Fiが切れている間は{@code adb_wifi_enabled}に1を書いても定着しない（実測。design.md
 * 追補参照）。そのため「0なら1を書く」（{@link #ensureOpen}）を毎回の実行予約時
 * （{@link RunScheduler#scheduleAt}）に繰り返し、Wi-Fiが戻った回に定着させる
 * （アプリは1日約70回動くため、Wi-Fiが戻れば数分〜十数分で開き直る想定）。
 *
 * ただし{@code ensureOpen}は値が1なら「正常」と見て何もしないため、**値が1のままadbd
 * （無線デバッグのサーバー本体）が止まっている**実機事象（2026-11-27実測）には効かない。
 * この穴を塞ぐため、値を見ずに強制的に0→1と開け閉めする{@link #cycle}を、起動時
 * （{@link AlarmReceiver}のBOOT_COMPLETED経路、trigger="boot"）と、合図ファイル
 * （{@link #checkSignalFile}、trigger="signal"）を見たときの2か所に限定して呼ぶ。
 * cycleは実行中のADB接続を切るため、毎回の実行予約では呼ばない（そちらは{@code ensureOpen}
 * のまま）。
 *
 * 書き換えるキーは{@link #KEY_ADB_WIFI_ENABLED}の1つだけに限定し、{@code adb_enabled}
 * （USBデバッグ）には絶対に触らない（ADR-1092 What-4）。
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
    /** {@link #cycle}が0→1と書き直した後、読み直して実際に1になった結果（design.md追補参照）。 */
    private static final String RESULT_CYCLED_OPENED = "cycled_opened";
    /** {@link #cycle}が0→1と書き直したが、読み直しても1にならなかった結果（Wi-Fi無し等）。 */
    private static final String RESULT_CYCLED_BLOCKED = "cycled_blocked";
    /**
     * 合図ファイルの確認でディレクトリが読めない・一覧できない（{@code READ_EXTERNAL_STORAGE}
     * 未付与等）ときの結果（design.md追補「黙らせない」）。{@link #checkSignalFile}参照。
     */
    private static final String RESULT_SIGNAL_UNREADABLE = "signal_unreadable";

    /** {@link #ensureOpen}の呼び出し元（毎回の実行予約時）を示すtrigger値。 */
    static final String TRIGGER_RUN = "run";
    /** {@link AlarmReceiver}のBOOT_COMPLETED経路から{@link #cycle}を呼ぶときのtrigger値。 */
    static final String TRIGGER_BOOT = "boot";
    /** {@link #checkSignalFile}が合図ファイルを見て{@link #cycle}を呼ぶときのtrigger値。 */
    static final String TRIGGER_SIGNAL = "signal";

    /**
     * 合図ファイル名（拡張子なし）。場所は{@link LineNotifyListenerService#resolveStorageDir}が
     * 返すディレクトリ（run-*.jsonl等と同じ場所）。design.md追補「保守口（無線デバッグ）の
     * 強制開け直し」②。
     */
    private static final String SIGNAL_FILE_NAME = "maintenance-open";

    /** {@link #cycle}が0を書いた後、1を書くまでに待つ時間（確定仕様）。 */
    private static final long CYCLE_CLOSE_WAIT_MS = 2000L;

    private MaintenanceChannel() {
    }

    /**
     * {@link RunScheduler#scheduleAt}からだけ呼ぶ（design.md追補参照。呼び出し場所をここ1箇所に
     * 限定する）。{@link AlarmReceiver}のBOOT_COMPLETED経路は{@link #cycle}を使う（design.md
     * 追補「保守口（無線デバッグ）の強制開け直し」①。値が1のままadbdが止まっている事象には
     * ensureOpenが効かないため）。
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
                recordIfChanged(context, RESULT_NO_PERMISSION, current, TRIGGER_RUN);
                return;
            }
            int after = Settings.Global.getInt(context.getContentResolver(), KEY_ADB_WIFI_ENABLED, -1);
            if (after == 1) {
                // 実際に開き直せた回は毎回記録する。変化時だけにすると、2回目以降の復旧が
                // 前回値と同じ扱いで消えてしまい、ADR-1092「維持の仕組み」が求める
                // 「復旧の実績が残る」が成り立たない（Opus審査 2026-11-27 の指摘2）。
                // 復旧は本来まれな事象なので毎回記録しても量は増えない。
                SchedulerStore.setLastMaintenanceChannelResult(context, RESULT_OPENED);
                RunLogger.logMaintenanceChannel(context, RESULT_OPENED, after, TRIGGER_RUN);
            } else {
                // Wi-Fiが無い回は書いても定着しない（実測。design.md追補参照）。次回の
                // ensureOpen呼び出し（毎回の実行予約時）に持ち越す。
                recordIfChanged(context, RESULT_BLOCKED, after, TRIGGER_RUN);
            }
        } catch (RuntimeException e) {
            // Settings.Global側が想定外の例外を投げた場合も含め、ここで吸収して落ちない
            // ようにする。結果が確定していないため記録はしない。
            Log.w(TAG, "ensureOpen failed: " + e);
        }
    }

    /**
     * 保守口（無線デバッグ）を値を見ずに強制的に0→（約{@value #CYCLE_CLOSE_WAIT_MS}ms待ち）→1
     * と開け閉めする（design.md追補「保守口（無線デバッグ）の強制開け直し」①②）。
     *
     * {@link #ensureOpen}は「0なら1を書く」だけなので、{@code adb_wifi_enabled}が1のまま
     * adbd（無線デバッグのサーバー本体）が止まっている実機事象（2026-11-27実測。アプリは
     * 「1だから正常」と見て何もしない）には効かない。本メソッドは値を見ずに必ず一度閉じて
     * 開け直すことで、止まっていたadbdを再起動させる。
     *
     * 呼び出し場所は{@link AlarmReceiver}のBOOT_COMPLETED経路（{@code trigger=}
     * {@link #TRIGGER_BOOT}）と{@link #checkSignalFile}（{@code trigger=}
     * {@link #TRIGGER_SIGNAL}）の2か所に限定する。cycleは実行中のADB接続を切るため、毎回の
     * 実行予約（{@link #ensureOpen}が担う）では呼ばない。
     *
     * 読み直して1なら{@code cycled_opened}、1にならなければ{@code cycled_blocked}として、
     * どちらも変化比較せず毎回記録する（既存の{@code RESULT_OPENED}と同じ考え方＝復旧の実績が
     * 残らないとADR-1092「維持の仕組み」が成り立たない）。Wi-Fiが無い回は1を書いても定着しない
     * （実測）ため、その場合は{@code cycled_blocked}を記録して終わり、復旧は次回以降の
     * {@link #ensureOpen}（毎回0→1を書く）に持ち越す。Wi-Fi状態の判定（新しい権限の追加）は
     * 行わない。
     *
     * {@link SecurityException}（権限が消えた場合）は{@link #RESULT_NO_PERMISSION}を
     * {@link #recordIfChanged}で記録してreturnする。その他の{@link RuntimeException}は
     * {@link #ensureOpen}と同じく吸収して落ちない。
     */
    static void cycle(Context context, String trigger) {
        if (!SELF_RECOVERY_ENABLED) {
            return;
        }
        try {
            try {
                Settings.Global.putInt(context.getContentResolver(), KEY_ADB_WIFI_ENABLED, 0);
            } catch (SecurityException e) {
                Log.w(TAG, "cycle(" + trigger + "): write 0 failed (no permission): " + e);
                recordIfChanged(context, RESULT_NO_PERMISSION, -1, trigger);
                return;
            }
            try {
                Thread.sleep(CYCLE_CLOSE_WAIT_MS);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            }
            try {
                Settings.Global.putInt(context.getContentResolver(), KEY_ADB_WIFI_ENABLED, 1);
            } catch (SecurityException e) {
                Log.w(TAG, "cycle(" + trigger + "): write 1 failed (no permission): " + e);
                recordIfChanged(context, RESULT_NO_PERMISSION, 0, trigger);
                return;
            }
            int after = Settings.Global.getInt(context.getContentResolver(), KEY_ADB_WIFI_ENABLED, -1);
            String result = after == 1 ? RESULT_CYCLED_OPENED : RESULT_CYCLED_BLOCKED;
            SchedulerStore.setLastMaintenanceChannelResult(context, result);
            RunLogger.logMaintenanceChannel(context, result, after, trigger);
        } catch (RuntimeException e) {
            Log.w(TAG, "cycle(" + trigger + ") failed: " + e);
        }
    }

    /**
     * 合図ファイル（{@value #SIGNAL_FILE_NAME}）があれば{@link #cycle}する（design.md追補
     * 「保守口（無線デバッグ）の強制開け直し」②）。{@link RunScheduler#scheduleAt}から、
     * {@link #ensureOpen}の直前に毎回呼ぶ。
     *
     * ファイルが無ければ何もしない（記録もしない。通常状態）。あれば{@code cycle(context,
     * TRIGGER_SIGNAL)}を実行し、ファイルを削除する。削除に失敗した場合に同じ合図で毎回
     * cycleしてしまうのを防ぐため、処理した合図の識別子（{@code lastModified}と{@code length}
     * の組）を{@link SchedulerStore}に保存し、次回以降それと同一なら何もしない（cycleもしない・
     * 記録もしない）。削除が成功した場合も同様に識別子を保存する。
     *
     * ディレクトリが読めない・一覧できない（{@code READ_EXTERNAL_STORAGE}が未付与である等）
     * 場合は黙らず{@link #RESULT_SIGNAL_UNREADABLE}を{@link #recordIfChanged}で1回だけ記録する
     * （アプリがこの方式で合図ファイルを読めているかどうかの実機検証の判定材料。design.md
     * 追補「黙らせない」）。
     */
    static void checkSignalFile(Context context) {
        if (!SELF_RECOVERY_ENABLED) {
            return;
        }
        try {
            File dir = LineNotifyListenerService.resolveStorageDir(context);
            if (dir == null || !dir.isDirectory() || !dir.canRead()) {
                recordIfChanged(context, RESULT_SIGNAL_UNREADABLE, -1, TRIGGER_SIGNAL);
                return;
            }
            File signalFile = new File(dir, SIGNAL_FILE_NAME);
            if (!signalFile.isFile()) {
                // 合図なし（通常状態）。記録しない。
                return;
            }
            String signalId = signalFile.lastModified() + ":" + signalFile.length();
            if (signalId.equals(SchedulerStore.getLastMaintenanceSignalId(context))) {
                // 前回、削除に失敗したまま残っている同じ合図。再度cycleしない（design.md追補参照）。
                return;
            }
            cycle(context, TRIGGER_SIGNAL);
            boolean deleted = signalFile.delete();
            // 削除の成否に関わらず識別子を保存する（design.md追補参照）。
            SchedulerStore.setLastMaintenanceSignalId(context, signalId);
            if (!deleted) {
                Log.w(TAG, "maintenance-open signal file delete failed; will not re-cycle on same signal");
            }
        } catch (RuntimeException e) {
            // READ_EXTERNAL_STORAGE未付与等によるSecurityExceptionもここで吸収し、黙らず記録する。
            Log.w(TAG, "checkSignalFile failed: " + e);
            recordIfChanged(context, RESULT_SIGNAL_UNREADABLE, -1, TRIGGER_SIGNAL);
        }
    }

    /**
     * 記録は{@link SchedulerStore}に保存した前回の結果と比較し、変化したときだけ
     * {@link RunLogger#logMaintenanceChannel}へ1行残す
     * （{@link RunScheduler}のwasLastIgnoringBatteryOptimizationsと同じ作り）。
     */
    private static void recordIfChanged(Context context, String result, int valueAfter, String trigger) {
        String previous = SchedulerStore.getLastMaintenanceChannelResult(context);
        if (result.equals(previous)) {
            return;
        }
        SchedulerStore.setLastMaintenanceChannelResult(context, result);
        RunLogger.logMaintenanceChannel(context, result, valueAfter, trigger);
    }
}
