package jp.salesanchor.lineexport;

import android.content.Context;
import android.provider.Settings;
import android.util.Log;

import java.io.File;
import java.io.IOException;

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
     * {@link #checkSignalFile}の自己試験（{@link #PROBE_FILE_NAME}の作成→削除の往復）が
     * 両方成功し、合図ファイルの経路（削除による検知）が使えると確認できた結果
     * （design.md追補「保守口（無線デバッグ）の強制開け直し・合図検知の作り直し」2026-11-27）。
     * 記録後は{@link SchedulerStore#setSignalChannelConfirmed}で旗を立て、以後は自己試験を
     * 行わない。
     */
    private static final String RESULT_SIGNAL_CHANNEL_OK = "signal_channel_ok";
    /**
     * 自己試験のどちらか（作成・削除）が失敗した結果。合図ファイルの検知そのもの
     * （{@code delete()}）が機能しない可能性があることを黙らず示す（design.md追補参照）。
     * 旗は立てないため次回また試験する。重複判定は{@link SchedulerStore
     * #wasSignalProbeFailureRecorded}専用の枠で行い、一度記録したら試験が成功するまで
     * 再記録しない（アプリは1日約70回動くため、毎回記録すると溢れる）。
     */
    private static final String RESULT_SIGNAL_PROBE_FAILED = "signal_probe_failed";

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

    /**
     * {@link #checkSignalFile}の自己試験が作成・削除する試験ファイル名（design.md追補
     * 「合図検知の作り直し」2026-11-27）。{@value #SIGNAL_FILE_NAME}とは別の名前にし、
     * 合図ファイル本体とは絶対に衝突しないようにする。
     */
    private static final String PROBE_FILE_NAME = ".maintenance-probe";

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
     * 「保守口（無線デバッグ）の強制開け直し・合図検知の作り直し」2026-11-27）。
     * {@link RunScheduler#scheduleAt}から、{@link #ensureOpen}の直前に毎回呼ぶ。
     *
     * <p><b>実機で分かった前提（2026-11-27実測。design.md追補参照）</b>: 端末は
     * {@code WRITE_EXTERNAL_STORAGE: granted=true} / {@code READ_EXTERNAL_STORAGE:
     * granted=false}（targetSdk 24の旧方式ストレージ）。{@code dir.canRead()}は常にfalseを
     * 返すが、同じディレクトリへの書き込み・削除は実際に成功する。PO方針は「読み取り権限は
     * 増やさない」（合図の検知に中身の読み取りは不要で、「在るか見て、消す」だけで足りる）。
     * そのため、{@code canRead()}・{@code isDirectory()}による門番は置かない（読み取りが
     * 拒否される環境ではstat系の戻り値も信頼できないため、門番で弾かずに実際の削除操作を
     * 試す方針。{@code dir == null}だけは{@link LineNotifyListenerService#resolveStorageDir}が
     * 書き込み先すら解決できなかった場合であり、これだけは早期returnする）。
     *
     * <p><b>削除を検知器にする</b>: {@code new File(dir, SIGNAL_FILE_NAME).delete()}が
     * {@code true}を返したら「合図が在って、いま消費した」と確定できる。{@code false}は
     * 「合図が無い」のか「消せない（経路が壊れている）」のか区別できないため、cycleも記録も
     * しない（通常は前者。後者は下記の自己試験で別途検知する）。**必ず削除してからcycleする**
     * （逆にすると、削除が失敗する環境では同じ合図ファイルで毎回cycleしてしまう。Opus審査
     * 2026-11-27の指摘と同じ穴）。この方式では、削除が成功した回だけcycleするため、
     * {@code lastModified}・{@code length}による識別子の重複判定（旧{@code
     * SchedulerStore.getLastMaintenanceSignalId}系）は不要になり、削除した
     * （二重消費が原理的に起きない）。
     *
     * <p><b>黙らせない（自己試験）</b>: {@code delete()}の{@code false}だけでは経路の健全性を
     * 確認できないため、まだ確認できていない間（{@link SchedulerStore
     * #isSignalChannelConfirmed}がfalseの間）だけ{@link #probeSignalChannel}を実行する。
     * 確認できたら旗を立て、以後は試験しない（毎回のファイル操作を増やさないため）。
     */
    static void checkSignalFile(Context context) {
        if (!SELF_RECOVERY_ENABLED) {
            return;
        }
        try {
            File dir = LineNotifyListenerService.resolveStorageDir(context);
            if (dir == null) {
                // 書き込み先すら解決できない（経路が丸ごと壊れている）。黙らず1回だけ記録する。
                recordSignalProbeFailedIfChanged(context);
                return;
            }
            if (!SchedulerStore.isSignalChannelConfirmed(context)) {
                probeSignalChannel(context, dir);
            }
            // 削除を検知器として使う。trueなら「合図が在って、いま消費した」と確定できる。
            boolean consumed = new File(dir, SIGNAL_FILE_NAME).delete();
            if (consumed) {
                cycle(context, TRIGGER_SIGNAL);
            }
        } catch (RuntimeException e) {
            // SecurityException等もここで吸収し、黙らず記録する。
            Log.w(TAG, "checkSignalFile failed: " + e);
            recordSignalProbeFailedIfChanged(context);
        }
    }

    /**
     * 経路の健全性を確認する自己試験（design.md追補「合図検知の作り直し」2026-11-27）。
     * {@code dir}に試験ファイル（{@value #PROBE_FILE_NAME}）を作成→削除の往復を行う。
     * 両方成功したら「経路は使える」と確定し、{@link SchedulerStore
     * #setSignalChannelConfirmed}で旗を立てて{@value #RESULT_SIGNAL_CHANNEL_OK}を1回
     * 記録する（旗が立った以後は{@link #checkSignalFile}が本メソッドを呼ばなくなるため、
     * 自然に1回だけになる）。どちらかが失敗したら旗は立てず（次回また試す）、
     * {@value #RESULT_SIGNAL_PROBE_FAILED}を{@link #recordSignalProbeFailedIfChanged}
     * 経由で記録する（専用の枠で重複判定し、失敗が続く間は1行だけになる）。
     *
     * <p><b>先頭の掃除deleteが要る理由（Opus審査 2026-11-27の指摘）</b>:
     * {@code createNewFile()}はファイルが既に在るときもfalseを返す（異常ではない）。試験
     * ファイルを作った直後〜削除する前にアプリの処理が落ちる（省電力による停止・プロセス
     * 終了等）と{@value #PROBE_FILE_NAME}が残ることがあり、次回の試験で
     * {@code createNewFile()}=false・{@code delete()}=trueとなって、経路は正常なのに
     * {@value #RESULT_SIGNAL_PROBE_FAILED}を誤記録してしまう（記録に騙されると方式の見直し
     * を誤判断する）。そこで試験の最初に残骸の掃除としてのdeleteを1回入れ、
     * {@code createNewFile()}を残骸の無い状態から行う。成功判定は後ろ2つ（作成・後始末の
     * delete）だけで行い、掃除deleteの結果は使わない。{@code exists()}・{@code canRead()}
     * 等の読み取り系の判定はここでも使わない（この端末では読み取りが拒否されるため）。
     */
    private static void probeSignalChannel(Context context, File dir) {
        File probeFile = new File(dir, PROBE_FILE_NAME);
        // 掃除delete: 前回の試験が落ちて残った残骸を消す。結果は判定に使わない
        // （無い状態からfalseが返るのは正常であり、これ自体は成否の材料にならない）。
        try {
            probeFile.delete();
        } catch (SecurityException e) {
            Log.w(TAG, "signal channel probe pre-cleanup failed: " + e);
        }
        boolean created;
        try {
            created = probeFile.createNewFile();
        } catch (IOException | SecurityException e) {
            Log.w(TAG, "signal channel probe create failed: " + e);
            created = false;
        }
        boolean deleted;
        try {
            // 作成に失敗しても、残っているかもしれない試験ファイルの後始末を必ず試みる。
            deleted = probeFile.delete();
        } catch (SecurityException e) {
            Log.w(TAG, "signal channel probe cleanup failed: " + e);
            deleted = false;
        }
        if (created && deleted) {
            SchedulerStore.setSignalChannelConfirmed(context, true);
            RunLogger.logMaintenanceChannel(context, RESULT_SIGNAL_CHANNEL_OK, -1, TRIGGER_SIGNAL);
        } else {
            recordSignalProbeFailedIfChanged(context);
        }
    }

    /**
     * {@value #RESULT_SIGNAL_PROBE_FAILED}を、{@link SchedulerStore
     * #wasSignalProbeFailureRecorded}専用の枠で重複判定して記録する（{@link #checkSignalFile}・
     * {@link #probeSignalChannel}参照）。{@link #recordIfChanged}が使う
     * {@code last_maintenance_channel_result}枠を共用すると、同じ実行の中で記録が往復して
     * 「変化したときだけ記録する」作法が崩れる（Opus審査 2026-11-27 の指摘と同種の穴。
     * design.md追補参照）ため、別の専用の枠を使う。
     */
    private static void recordSignalProbeFailedIfChanged(Context context) {
        if (SchedulerStore.wasSignalProbeFailureRecorded(context)) {
            return;
        }
        SchedulerStore.setSignalProbeFailureRecorded(context, true);
        RunLogger.logMaintenanceChannel(context, RESULT_SIGNAL_PROBE_FAILED, -1, TRIGGER_SIGNAL);
    }

    /**
     * 記録は{@link SchedulerStore}に保存した前回の結果と比較し、変化したときだけ
     * {@link RunLogger#logMaintenanceChannel}へ1行残す
     * （{@link RunScheduler}のwasLastIgnoringBatteryOptimizationsと同じ作り）。
     * {@value #RESULT_SIGNAL_CHANNEL_OK}・{@value #RESULT_SIGNAL_PROBE_FAILED}はここを使わず
     * {@link #recordSignalProbeFailedIfChanged}専用の枠（または旗立てによる自然な1回化）を
     * 使う（理由は{@link #probeSignalChannel}のjavadoc参照）。
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
