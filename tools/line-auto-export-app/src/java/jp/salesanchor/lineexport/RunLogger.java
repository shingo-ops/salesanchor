package jp.salesanchor.lineexport;

import android.app.KeyguardManager;
import android.content.Context;
import android.os.PowerManager;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 実行ログ（1行1実行のJSONL）。design.md追補 2026-10-08「実機で46回実行・失敗0で動いたが、
 * アプリ自身の実行履歴が残らず挙動を診断できない」への対策。結果通知は同じ通知IDで上書きされ
 * 直近1件しか残らないため、何が起きていたかを後から追える形で端末に残す。
 *
 * 出力先はLineNotifyListenerServiceが使っているのと同じ共有ストレージの仕組み
 * （{@link LineNotifyListenerService#resolveStorageDir}を再利用）。ファイル名は
 * run-YYYYMMDD.jsonl。
 *
 * 「1実行」は、ロック解除フロー（UnlockAccessibilityService）とLINE操作フロー
 * （LineExportFlow）のそれぞれを指す。RUN_ALLで両方続けて走った場合、それぞれが自分の
 * runId・開始/終了の2行を持つ（合計4行）。既存の設計がロック解除とLINE操作を別々の
 * running系ガード・別々の結果通知に分けているのに合わせ、ログもその単位で分けた
 * （2つを1本の実行として無理にまとめると、単体検証用のRUN/EXPORTとの扱いが揃わなくなるため。
 * 実装判断として報告する）。
 *
 * メッセージ本文・グループ名・PINは絶対に含めない。書き込みに失敗してもフロー本体は
 * 止めない（診断が本体を壊してはいけない。例外はすべてここで吸収する）。
 */
final class RunLogger {

    private static final String TAG = "SALineExport";
    private static final Object WRITE_LOCK = new Object();
    private static final AtomicLong RUN_ID_SEQ = new AtomicLong();

    private RunLogger() {
    }

    /** ログの開始行・終了行を対応付けるためだけのID（epoch ms + 連番）。診断以外の意味は無い。 */
    static String newRunId() {
        return System.currentTimeMillis() + "-" + RUN_ID_SEQ.incrementAndGet();
    }

    /**
     * 実行の開始時に呼ぶ。終了まで到達しなかった実行（プロセスが落ちた等）も、この行だけは
     * 残るようにするため、各flowの一番最初（他のチェックより前）で呼ぶこと。
     */
    static void logStart(Context context, String runId, String flow, String trigger) {
        JSONObject json = new JSONObject();
        try {
            json.put("at", formatIso8601(System.currentTimeMillis()));
            json.put("runId", runId);
            json.put("flow", flow);
            json.put("phase", "start");
            json.put("trigger", trigger == null ? "" : trigger);
            json.put("keyguardLocked", isKeyguardLocked(context));
            json.put("screenOn", isInteractive(context));
        } catch (JSONException e) {
            Log.w(TAG, "run log start build failed: " + e);
            return;
        }
        append(context, json);
    }

    /**
     * 実行の終了時に呼ぶ。
     *
     * @param result "success" / "failure" / "skipped"
     * @param stage 失敗した段階名。成功ならnull
     * @param stepTimings 各段階の所要ms（{stage, ms}の配列）。無ければnull
     * @param locked 施錠を実行したときだけその結果。施錠を実行していないならnull
     * @param nextTrigger このチェーンで新たに張ったアラームの種別。無ければnull
     * @param nextAtMs nextTriggerが発火するまでのms（相対値）。nextTriggerがnullなら無視される
     */
    static void logEnd(Context context, String runId, String flow, String trigger, String result,
            String stage, long elapsedMs, JSONArray stepTimings, Boolean locked,
            String nextTrigger, Long nextAtMs) {
        JSONObject json = new JSONObject();
        try {
            json.put("at", formatIso8601(System.currentTimeMillis()));
            json.put("runId", runId);
            json.put("flow", flow);
            json.put("phase", "end");
            json.put("trigger", trigger == null ? "" : trigger);
            json.put("result", result);
            json.put("stage", stage == null ? JSONObject.NULL : stage);
            json.put("elapsedMs", elapsedMs);
            if (stepTimings != null) {
                json.put("steps", stepTimings);
            }
            if (locked != null) {
                json.put("locked", locked.booleanValue());
            }
            if (nextTrigger != null) {
                json.put("nextTrigger", nextTrigger);
                if (nextAtMs != null) {
                    json.put("nextAtMs", nextAtMs.longValue());
                }
            }
        } catch (JSONException e) {
            Log.w(TAG, "run log end build failed: " + e);
            return;
        }
        append(context, json);
    }

    private static void append(Context context, JSONObject json) {
        try {
            File dir = LineNotifyListenerService.resolveStorageDir(context);
            if (dir == null) {
                Log.w(TAG, "no writable storage dir for run log");
                return;
            }
            String fileDateKey = new SimpleDateFormat("yyyyMMdd", Locale.JAPAN).format(new Date());
            File file = new File(dir, "run-" + fileDateKey + ".jsonl");
            synchronized (WRITE_LOCK) {
                Writer writer = new OutputStreamWriter(new FileOutputStream(file, true), "UTF-8");
                try {
                    writer.write(json.toString());
                    writer.write("\n");
                    writer.flush();
                } finally {
                    writer.close();
                }
            }
        } catch (Exception e) {
            // 診断ログの書き込み失敗でフロー本体を止めない。Log.iはこの端末でlogcatに出ない
            // ことが分かっている（既存コメントのとおり）ため、ここで握るだけで十分。
            Log.w(TAG, "run log write failed: " + e);
        }
    }

    private static String formatIso8601(long millis) {
        // 既存のLineNotifyListenerService#formatIso8601と同じパターン（+0900形式。コロン無し）。
        // 既存の診断JSONL群との一貫性を優先し、ここだけ別形式にはしなかった。
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.JAPAN).format(new Date(millis));
    }

    private static boolean isInteractive(Context context) {
        PowerManager pm = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        return pm != null && pm.isInteractive();
    }

    private static boolean isKeyguardLocked(Context context) {
        KeyguardManager km = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        return km != null && km.isKeyguardLocked();
    }
}
