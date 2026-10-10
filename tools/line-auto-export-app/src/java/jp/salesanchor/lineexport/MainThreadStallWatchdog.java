package jp.salesanchor.lineexport;

import android.content.Context;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.util.Log;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * メインスレッドの遅延を別スレッドから見張る診断専用クラス（design.md追補「原因究明のための
 * 診断追加」。PO承認済み。動作は一切変えない）。
 *
 * 0.9.0-stage3の計測で、深いスリープ・ウェイクロック解放・ノード探索コスト・CPU不足・
 * プロセス凍結・イベント洪水のいずれでも説明できない遅延（例: 1000ms指定の待ちが
 * 42,379msへ、同じ実行の2秒指定の待ちは2,002msと正確）が確認されたため、
 * 「メインスレッドが実際に何をしているか」を直接見るための最後の手段として追加する。
 *
 * {@link LineExportFlow}が{@code handler.postDelayed}で待ちを仕掛けるたびに
 * {@link #registerWait}で登録し、発火したら{@link #unregisterWait}で解除する
 * （フロー内のすべての待ちが対象）。専用スレッド（{@link HandlerThread}）が500ms間隔で
 * 確認し、期待発火時刻から3,000ms以上遅れている待ちがあれば、メインスレッドの
 * スタックトレース上位フレームと状態（BLOCKED/WAITING/TIMED_WAITING/RUNNABLE等。
 * これが最も重要な判別材料）を{@link RunLogger}へ{@code phase:"stall"}として記録する。
 * 同じ待ちについて最大3回まで（1回目は遅れ3秒時点、以後5秒間隔）。
 *
 * メッセージ本文・グループ名・PINは記録しない。スタックトレースはクラス名・メソッド名・
 * 行番号のみ。ログ書き込みの失敗はフローを壊さない（RunLogger側で吸収）。
 */
final class MainThreadStallWatchdog {

    private static final String TAG = "SALineExport";

    private static final long CHECK_INTERVAL_MS = 500L;
    private static final long STALL_THRESHOLD_MS = 3000L;
    private static final long REPEAT_INTERVAL_MS = 5000L;
    private static final int MAX_RECORDS_PER_WAIT = 3;
    private static final int MAX_STACK_FRAMES = 20;

    /** 1つの待ち（handler.postDelayed呼び出し）の状態。 */
    private static final class WaitEntry {
        final String label;
        final long requestedMs;
        final long expectedAtMs;
        int recordCount;
        long nextRecordAtMs;

        WaitEntry(String label, long scheduledAtMs, long requestedMs) {
            this.label = label;
            this.requestedMs = requestedMs;
            this.expectedAtMs = scheduledAtMs + requestedMs;
            this.nextRecordAtMs = expectedAtMs + STALL_THRESHOLD_MS;
        }
    }

    private final Context context;
    private final String runId;
    private final String flow;
    private final String trigger;

    private final Object lock = new Object();
    private final Map<String, WaitEntry> pendingWaits = new HashMap<String, WaitEntry>();

    private HandlerThread thread;
    private Handler watchdogHandler;
    private volatile boolean running;

    MainThreadStallWatchdog(Context context, String runId, String flow, String trigger) {
        this.context = context;
        this.runId = runId;
        this.flow = flow;
        this.trigger = trigger;
    }

    /** フロー開始時に1回呼ぶ。専用スレッドを起こし、500ms間隔のチェックを始める。 */
    void start() {
        if (thread != null) {
            return;
        }
        running = true;
        thread = new HandlerThread("sa-stall-watchdog");
        thread.start();
        watchdogHandler = new Handler(thread.getLooper());
        scheduleCheck();
    }

    /** フロー終了時に必ず呼ぶ（リーク防止）。専用スレッドを止め、保留中の待ちも捨てる。 */
    void stop() {
        running = false;
        synchronized (lock) {
            pendingWaits.clear();
        }
        if (thread != null) {
            thread.quitSafely();
            thread = null;
        }
        watchdogHandler = null;
    }

    /** labelの待ちをmainスレッドでpostDelayedする直前に呼ぶ。同じlabelは上書きしてよい。 */
    void registerWait(String label, long requestedMs) {
        synchronized (lock) {
            pendingWaits.put(label, new WaitEntry(label, System.currentTimeMillis(), requestedMs));
        }
    }

    /** labelの待ちが（遅延していても）実際に発火したときに呼ぶ。 */
    void unregisterWait(String label) {
        synchronized (lock) {
            pendingWaits.remove(label);
        }
    }

    private void scheduleCheck() {
        if (watchdogHandler == null || !running) {
            return;
        }
        watchdogHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (!running) {
                    return;
                }
                checkOnce();
                scheduleCheck();
            }
        }, CHECK_INTERVAL_MS);
    }

    private void checkOnce() {
        long now = System.currentTimeMillis();
        List<WaitEntry> toRecord = new ArrayList<WaitEntry>();
        synchronized (lock) {
            for (WaitEntry entry : pendingWaits.values()) {
                if (entry.recordCount >= MAX_RECORDS_PER_WAIT) {
                    continue;
                }
                if (now >= entry.nextRecordAtMs) {
                    entry.recordCount++;
                    entry.nextRecordAtMs = now + REPEAT_INTERVAL_MS;
                    toRecord.add(entry);
                }
            }
        }
        if (toRecord.isEmpty()) {
            return;
        }

        // メインスレッドのスタック/状態の取得はここ（遅延検知時のみ）でまとめて1回行う
        // （見張り自体を重くしないため。500ms間隔のポーリング自体は軽い）。
        String mainThreadState;
        StackTraceElement[] stack;
        try {
            Thread mainThread = Looper.getMainLooper().getThread();
            mainThreadState = mainThread.getState() == null ? "" : mainThread.getState().name();
            stack = mainThread.getStackTrace();
        } catch (RuntimeException e) {
            Log.w(TAG, "stall watchdog stack capture failed: " + e);
            return;
        }

        for (WaitEntry entry : toRecord) {
            long delayMs = now - entry.expectedAtMs;
            RunLogger.logStall(context, runId, flow, trigger, entry.label, entry.requestedMs, delayMs,
                    entry.recordCount, mainThreadState, stack, MAX_STACK_FRAMES);
        }
    }
}
