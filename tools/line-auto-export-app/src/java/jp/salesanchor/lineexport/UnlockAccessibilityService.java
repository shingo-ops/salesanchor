package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.app.KeyguardManager;
import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.graphics.Point;
import android.os.Handler;
import android.os.PowerManager;
import android.util.Log;
import android.util.SparseArray;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

import org.json.JSONArray;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 段階1の実行主体。「今すぐ実行」の合図（RunReceiver経由）を受けたら:
 *   (a) 画面をウェイクしてロック画面を出す
 *   (b) 保存済みPINの各数字をロック画面上でAccessibilityのノードクリックで入力
 *       （見つからなければ dispatchGesture の座標タップにフォールバック）
 *   (c) Enter/完了を押す
 *   (d) 3秒後にkeyguardが解除されたか判定し、通知で結果を出す
 *
 * LINE操作はまだ実装しない（design.md 段階2以降）。
 *
 * PINは実行中のみメモリ上に保持し、ログ・通知本文・APKリソースには一切出さない。
 */
public class UnlockAccessibilityService extends AccessibilityService {

    private static final String TAG = "SALineExport";
    // LineExportFlow（段階2）も同じ通知チャンネルに乗せる。通知ID(NOTIFICATION_ID_EXPORT)は
    // そちらで別に持つため、このチャンネルIDだけパッケージ内に公開する。
    static final String CHANNEL_ID = "sa_line_export_unlock";
    private static final int NOTIFICATION_ID = 1001;
    private static final int NOTIFICATION_ID_DIAG = 1002;
    private static final String WAKE_LOCK_TAG = "SALineExport:unlock";
    private static final int DIAG_MAX_PACKAGES_PER_DISPLAY = 3;

    // ロック画面は画面消灯までが約5秒（端末の「画面消灯時間」を60秒にしても
    // activityTimeoutWM=5000 が効く。2026-09-18 実機ログで確認）。PIN入力が
    // その窓に確実に収まるよう、待ち時間を詰めてある。
    // 2026-10-06/07 実機計測: 起床+64msのスワイプはBouncerが25秒出ず消失、
    // 起床+1546ms/+3057msのスワイプはいずれも成功（以後9秒以上表示継続）。
    // mWakefulness=Awake は早期に立つが受け付け可能になるのはもっと後なので、
    // 状態判定ではなく実時間での待ちを延ばす。
    private static final long POST_WAKE_DELAY_MS = 1500L;
    private static final long DIGIT_CLICK_INTERVAL_MS = 200L;
    private static final long RESULT_CHECK_DELAY_MS = 1500L;
    // スワイプのやり直しが最大3回入るため、最悪ケースは解除成功まで約9.5秒かかる。
    // 10秒だとこの安全タイムアウトと競合するので余裕を持たせる（2026-10-07）。
    private static final long WAKE_LOCK_SAFETY_TIMEOUT_MS = 15000L;

    // キーパッド（Bouncer）出現確認のポーリング間隔と、1回のスワイプあたりの
    // 確認期限。2026-10-06/07実機計測では出現まで最大約600ms程度だったが、
    // 余裕を持って1500msまで待つ。
    private static final long KEYPAD_CHECK_INTERVAL_MS = 150L;
    private static final long KEYPAD_CHECK_TIMEOUT_MS = 1500L;
    // スワイプは最大3回まで。空振りのタップでPINを誤入力し続けて端末がロック
    // アウトされる事態を避けるため、キーパッドが出ない場合は数字入力に進まず
    // ここで中止する。
    private static final int KEYPAD_MAX_SWIPE_ATTEMPTS = 3;
    // キーパッド出現確認用の固定ラベル。PINの桁を使うと値が挙動に漏れるため、
    // PINとは無関係な数字ラベルで判定する（既存のfindNodeByLabelを再利用）。
    private static final String[] KEYPAD_PROBE_LABELS = {"1", "3", "7"};
    private static final int KEYPAD_PROBE_MIN_MATCHES = 2;

    private static final String[] ENTER_LABELS = {
            "Enter", "enter", "OK", "ok", "確認", "完了", "done", "Done", "→"
    };

    private static volatile UnlockAccessibilityService sInstance;

    /** 動作の記録。ログが端末で抑止されるため、通知に載せる唯一の手がかり（PINは載せない）。 */
    private StringBuilder trace;
    private long flowStartedAt;

    private final Handler handler = new Handler();
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final AtomicBoolean exportRunning = new AtomicBoolean(false);

    // RUN_ALL（ロック解除→LINE操作）かどうか。RUNの挙動は変えず、checkResult()で
    // 解除成功と判定した場合のみこのフラグを見てLineExportFlowへ続ける。
    private volatile boolean runAllRequested;

    // 今回の実行の引き金（診断用。結果通知の本文に「引き金:」として残す。design.md追補
    // 2026-10-08「段階3の方式変更」）。startUnlockFlowからcheckResult()経由でLineExportFlow
    // まで引き継ぐ。
    private volatile String currentTriggerLabel = "";

    // 実行ログ（design.md追補 2026-10-08「実機で動いたが挙動が診断できない」対策）。
    // ロック解除フロー自身のrunId。LINE操作フロー(LineExportFlow)は別のrunIdを自分で持つ
    // （RunLogger.javaのクラスコメント参照: 2つを1本の実行として無理にまとめない判断）。
    private volatile String currentRunId = "";

    private PowerManager.WakeLock wakeLock;
    private String currentPin;
    private StringBuilder failureReasons;

    // onAccessibilityEvent の TYPE_WINDOW_STATE_CHANGED から得たクラス名・パッケージ名。
    // LineExportFlow実行中のみ記録し、終了時に空へ戻す（design.md追補 2026-10-08:
    // 「記録は診断と手順11のTermuxダイアログ待ちにのみ使う。テキスト系の内容は読まない」）。
    private volatile boolean recordingWindowEvents;
    private volatile String lastWindowClassName = "";
    private volatile String lastWindowPackageName = "";

    // 失敗通知の診断用（2026-10-08実機2回目の追補）: 直近に記録したウィンドウの「単純名」
    // （パッケージ部分を落としたクラス名。例: ChatMenuActivity）を最大3件、連続重複を除いて
    // 保持する。lastWindowClassName（手順11のEDITクラス検出に使う、フル値・単発）とは別に
    // 持つ。パッケージ名・ノードのテキスト・メッセージ本文は一切含まない。
    private static final int WINDOW_CLASS_HISTORY_MAX = 3;
    private final Object windowClassHistoryLock = new Object();
    private final ArrayList<String> windowClassHistory = new ArrayList<String>();

    // 診断用: 何回目のスワイプでキーパッドが出たか（0=未出現）と、起床から
    // 出現確認までの経過ms（-1=未確認）。PINの値・桁数は含まない。
    private long wakeStartedAt;
    private int swipeAttempt;
    private int keypadConfirmedAttempt;
    private long keypadConfirmedElapsedMs = -1L;

    /** 外部（RunReceiver）からの実行トリガー。サービス未接続なら失敗通知を出す。 */
    static void requestRun(Context context) {
        UnlockAccessibilityService instance = sInstance;
        if (instance == null) {
            postFailureNotification(context, "ユーザー補助サービスが未接続（無効化されている可能性）");
            return;
        }
        // 実行ログ診断用。RunSchedulerを経由しない入口なので、ここで前回チェーンの残りを消す
        // （onAlarmFiredと同じ理由）。
        SchedulerStore.clearPendingNextTrigger(context);
        instance.startUnlockFlow(false, "RUN(手動)");
    }

    /**
     * 外部（RunReceiver）からの、LINE操作のみの実行トリガー（段階2の単体検証用。
     * design.md追補 2026-10-08の起動口表）。解除済み前提で、ロック解除は一切行わない。
     * 検証中に毎回施錠されると邪魔になるため、終了時の施錠はしない（lockOnFinish=false）。
     */
    static void requestExport(Context context) {
        UnlockAccessibilityService instance = sInstance;
        if (instance == null) {
            postFailureNotification(context, "ユーザー補助サービスが未接続（無効化されている可能性）");
            return;
        }
        SchedulerStore.clearPendingNextTrigger(context);
        instance.startExportFlow(false, "EXPORT(手動)");
    }

    /**
     * 外部（RunReceiver、Termuxの15分ジョブ等）からの、ロック解除→LINE操作（本番の形）の
     * 実行トリガー。段階3のRunScheduler（通知／補完／再試行）はこちらではなく
     * {@link #requestRunAll(Context, String)}を使う（引き金のラベルを結果通知に残すため）。
     */
    static void requestRunAll(Context context) {
        SchedulerStore.clearPendingNextTrigger(context);
        requestRunAll(context, "RUN_ALL(外部)");
    }

    /**
     * ロック解除→LINE操作（本番の形）の実行トリガー。triggerLabelは結果通知の本文に
     * 「何が引き金だったか」として残す（design.md追補 2026-10-08「段階3の方式変更」）。
     * ロック解除の成否はcheckResult()で判定し、成功した場合のみLINE操作へ続ける。
     * RUN単体（requestRun/startUnlockFlow(false, ...)）の挙動はこの経路では一切通らない。
     */
    static void requestRunAll(Context context, String triggerLabel) {
        UnlockAccessibilityService instance = sInstance;
        if (instance == null) {
            postFailureNotification(context, "ユーザー補助サービスが未接続（無効化されている可能性）");
            return;
        }
        instance.startUnlockFlow(true, triggerLabel);
    }

    /**
     * 外部（RunReceiver）からの診断トリガー。ロック解除（RUN/startUnlockFlow）とは
     * 独立の読み取り専用経路。副ディスプレイ上のウィンドウがアクセシビリティ経由で
     * 読めるかを判定し、結果を通知で返す。ロック解除やPIN入力は一切行わない。
     */
    static void requestDiagWindows(Context context) {
        UnlockAccessibilityService instance = sInstance;
        if (instance == null) {
            postDiagNotification(context, "エラー: ユーザー補助サービスが未接続（無効化されている可能性）");
            return;
        }
        instance.runWindowDiagnostics();
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        sInstance = this;
        NotificationCompat.ensureChannel(this, CHANNEL_ID, "SA LINE Export");
        Log.i(TAG, "UnlockAccessibilityService connected");
        // 段階3: BOOT_COMPLETEDに加え、ここでも張り直す（アプリ更新・プロセス再生成を
        // 安全に拾うための二重化。design.md参照）。ONのときだけ実際に張る。
        RunScheduler.rescheduleIfEnabled(this);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (sInstance == this) {
            sInstance = null;
        }
        releaseWakeLock();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        // 段階1（ロック解除）はイベント駆動の処理をしない。実行はrequestRun経由のみ。
        // 段階2（LINE操作）実行中のみ、画面遷移の診断用にクラス名・パッケージ名を記録する
        // （design.md追補 2026-10-08: テキスト系のイベント内容は読まない。判定の本筋には
        // 置かず、記録と手順11のTermuxダイアログ待ちにのみ使う）。
        if (!recordingWindowEvents || event == null
                || event.getEventType() != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            return;
        }
        CharSequence className = event.getClassName();
        CharSequence packageName = event.getPackageName();
        lastWindowClassName = className == null ? "" : className.toString();
        lastWindowPackageName = packageName == null ? "" : packageName.toString();

        String simpleName = simpleClassName(lastWindowClassName);
        if (simpleName.length() > 0) {
            synchronized (windowClassHistoryLock) {
                int size = windowClassHistory.size();
                if (size == 0 || !simpleName.equals(windowClassHistory.get(size - 1))) {
                    windowClassHistory.add(simpleName);
                    if (windowClassHistory.size() > WINDOW_CLASS_HISTORY_MAX) {
                        windowClassHistory.remove(0);
                    }
                }
            }
        }
    }

    /** パッケージ部分を落とした単純名。例: "jp.naver.line.android...ChatHistoryActivity" -> "ChatHistoryActivity"。 */
    private static String simpleClassName(String className) {
        if (className == null || className.length() == 0) {
            return "";
        }
        int dot = className.lastIndexOf('.');
        return dot >= 0 ? className.substring(dot + 1) : className;
    }

    /** LineExportFlow開始時に呼ぶ。記録バッファをクリアしてから記録を始める。 */
    void startWindowRecording() {
        lastWindowClassName = "";
        lastWindowPackageName = "";
        synchronized (windowClassHistoryLock) {
            windowClassHistory.clear();
        }
        recordingWindowEvents = true;
    }

    /** LineExportFlow終了時に呼ぶ。記録を止め、内容もクリアする（design.mdの要求どおり）。 */
    void stopWindowRecording() {
        recordingWindowEvents = false;
        lastWindowClassName = "";
        lastWindowPackageName = "";
        synchronized (windowClassHistoryLock) {
            windowClassHistory.clear();
        }
    }

    /** 直近に記録したウィンドウのクラス名（フル値）。記録していない/未取得なら空文字。
     * 手順11のTermuxダイアログ検出専用（.contains(TERMUX_EDIT_CLASS_NAME)で使われる）。 */
    String getLastWindowClassName() {
        return lastWindowClassName;
    }

    /**
     * 失敗通知の診断用。記録済みウィンドウの単純クラス名を最新3件まで、カンマ区切りで返す
     * （例: "ChatHistoryActivity,ChatMenuActivity"）。クラス名のみでパッケージ名・ノードの
     * テキスト・メッセージ本文は一切含まない。stopWindowRecording()を呼ぶ前に読むこと
     * （呼んだ後は履歴がクリアされて空文字になる）。
     */
    String recentWindowClassNames() {
        synchronized (windowClassHistoryLock) {
            StringBuilder sb = new StringBuilder();
            for (String name : windowClassHistory) {
                if (sb.length() > 0) {
                    sb.append(',');
                }
                sb.append(name);
            }
            return sb.toString();
        }
    }

    /**
     * LINE操作を実行する。多重起動は無視する。lockOnFinishはRUN_ALLのときだけtrueにする
     * （requestExportからはfalse固定、checkResult()のRUN_ALL続行からはtrue固定で渡す）。
     * triggerLabelはLineExportFlowの結果通知に「引き金:」として残す。
     */
    private void startExportFlow(final boolean lockOnFinish, String triggerLabel) {
        if (!exportRunning.compareAndSet(false, true)) {
            Log.i(TAG, "export flow already running, ignoring duplicate trigger");
            return;
        }
        new LineExportFlow(this, lockOnFinish, triggerLabel, new LineExportFlow.Listener() {
            @Override
            public void onFinished() {
                exportRunning.set(false);
            }
        }).start();
    }

    @Override
    public void onInterrupt() {
        // no-op
    }

    private void startUnlockFlow(boolean runAll, String triggerLabel) {
        if (!running.compareAndSet(false, true)) {
            Log.i(TAG, "unlock flow already running, ignoring duplicate trigger");
            return;
        }

        runAllRequested = runAll;
        currentTriggerLabel = triggerLabel == null ? "" : triggerLabel;
        currentRunId = RunLogger.newRunId();
        failureReasons = new StringBuilder();
        trace = new StringBuilder();
        flowStartedAt = System.currentTimeMillis();

        // 実行ログの開始行。終了まで到達しなかった実行（プロセスが落ちた等）もこの行だけは
        // 残るよう、他のチェックより前に書く（design.md追補参照）。
        RunLogger.logStart(this, currentRunId, "unlock", currentTriggerLabel);

        // ロックされていないときに数字を打つと、前面のアプリを誤タップする（ADB版の
        // 「使用中は見送り」と同じ判定）。
        KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
        if (km == null || !km.isKeyguardLocked()) {
            if (runAll) {
                // PO決定（実機運用、design.md追補対象）: 使用中でも即実行する。中断は受け入れる。
                // ロック解除（PIN入力）は飛ばし、既存のEXPORT専用経路へ直行する（すでに解除済み
                // のためPIN入力は不要。誤入力リスクを増やさないため一切行わない）。
                // この経路では「ロック解除: 見送り」通知とscheduleRetryAfterSkipは発生しない
                // （RUN単体＝runAll=falseはロック解除機構自体の検証用のため、挙動を変える
                // 必要が無く、下のelse相当の見送り処理をそのまま通る）。
                // 床（SchedulerStore#getLastRunStartedAt）には、実際に画面を使う実行として
                // 通常の経路と同じくここで登録する。
                SchedulerStore.setLastRunStartedAt(this, flowStartedAt);
                running.set(false);
                logUnlockEnd("skipped_to_export", null, System.currentTimeMillis() - flowStartedAt, null);
                // PO決定「終了後は必ず施錠する」: 開始時にロックされていなくても、終了時には
                // 施錠する（lockOnFinish=true）。例外はEXPORT単体（手動検証用、
                // requestExport経由でこのif自体を通らない）だけ。施錠前の待ち
                // （LOCK_DELAY_AFTER_EDIT_MS・drainCallbackSummary）はLineExportFlow#finish
                // 側の既存ロジックのままで、ここでは一切変えない。
                startExportFlow(true, currentTriggerLabel);
                return;
            }
            postNotification(this, "ロック解除: 見送り", "ロックされていない（使用中） / 引き金:" + currentTriggerLabel);
            // 段階3: 使用中で見送ったときは5分後に再試行を予約する（design.md追補
            // 「段階3の方式変更」。RunScheduler側でON/OFFトグルを見るのでここでは無条件に呼ぶ）。
            // runAll=trueの経路（通知/補完/再試行/RUN_ALL）は上のifで即実行に切り替わったため、
            // ここを通るのはRUN単体（手動のロック解除機構検証）だけになった。
            RunScheduler.scheduleRetryAfterSkip(this);
            logUnlockEnd("skipped", "ロックされていない（使用中）",
                    System.currentTimeMillis() - flowStartedAt, null);
            return;
        }

        String pin = PinStore.loadPin(this);
        if (pin == null || pin.length() == 0) {
            running.set(false);
            postFailureNotification(this, "PIN未設定 / 引き金:" + currentTriggerLabel);
            logUnlockEnd("failure", "PIN未設定", System.currentTimeMillis() - flowStartedAt, null);
            return;
        }
        currentPin = pin;

        // 段階3の床（最短間隔）判定に使う「前回の実行開始」。見送りはここに到達しないため
        // 対象外（画面を起こさないため床の対象にする必要が無い。design.md追補参照）。
        SchedulerStore.setLastRunStartedAt(this, flowStartedAt);

        swipeAttempt = 0;
        keypadConfirmedAttempt = 0;
        keypadConfirmedElapsedMs = -1L;

        acquireWakeLock();
        wakeStartedAt = System.currentTimeMillis();
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                revealKeypadThenEnterPin();
            }
        }, POST_WAKE_DELAY_MS);
    }

    /**
     * 画面をつけただけではロック画面（時計）が出るだけで、数字キーは現れない。
     * 上スワイプで数字キー（Bouncer）を出してからPINを打つ（2026-09-18 実機で確認）。
     *
     * 2026-10-06/07実機計測で、早すぎるタイミングのスワイプはBouncerが出ないまま
     * 失われる（遅延して効くわけではない）ことが分かったため、固定時間待って
     * 無条件に数字入力へ進むのではなく、キーパッドの出現を実際に確認してから
     * 数字入力に進む。確認できなければスワイプをやり直す（最大3回）。
     */
    private void revealKeypadThenEnterPin() {
        attemptSwipeAndConfirmKeypad();
    }

    private void attemptSwipeAndConfirmKeypad() {
        swipeAttempt++;
        Point size = getScreenSize();
        boolean swiped = false;
        if (size.y > 0) {
            GestureCompat.DispatchReport report = GestureCompat.swipe(this,
                    size.x * 0.5f, size.y * 0.81f, size.x * 0.5f, size.y * 0.26f, 250L, "swipe");
            swiped = report.accepted;
            traceAppend(report.describe());
        }
        traceAppend(swiped ? "スワイプ" : "スワイプ失敗");
        if (!swiped) {
            failureReasons.append("数字キーを出せない ");
        }

        final long deadlineAt = System.currentTimeMillis() + KEYPAD_CHECK_TIMEOUT_MS;
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                pollKeypadVisibility(deadlineAt);
            }
        }, KEYPAD_CHECK_INTERVAL_MS);
    }

    /**
     * キーパッド出現確認のポーリング。150ms間隔・1回のスワイプにつき期限1500ms。
     * 出現が確認できたらそこで初めて数字入力に進む。期限内に出なければ
     * スワイプをやり直し（最大3回）、3回とも出なければ数字入力・Enterを一切
     * 行わずに中止する（空振りタップでPINを誤入力し続け、端末がロックアウト
     * されるのを避けるため）。
     */
    private void pollKeypadVisibility(final long deadlineAt) {
        if (currentPin == null) {
            return; // 途中で中断された
        }
        if (isKeypadVisible()) {
            keypadConfirmedAttempt = swipeAttempt;
            keypadConfirmedElapsedMs = System.currentTimeMillis() - wakeStartedAt;
            traceAppend("キーパッド確認");
            clickDigit(0);
            return;
        }
        if (System.currentTimeMillis() >= deadlineAt) {
            if (swipeAttempt < KEYPAD_MAX_SWIPE_ATTEMPTS) {
                attemptSwipeAndConfirmKeypad();
            } else {
                failureReasons.append("キーパッド未出現 ");
                checkResult();
            }
            return;
        }
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                pollKeypadVisibility(deadlineAt);
            }
        }, KEYPAD_CHECK_INTERVAL_MS);
    }

    /**
     * キーパッド（数字キー）が出ているかの判定。暗証番号の桁は使わず、PINとは
     * 無関係な固定ラベル（KEYPAD_PROBE_LABELS）を既存のfindNodeByLabelで探し、
     * 2つ以上見つかれば出ていると判定する。
     */
    private boolean isKeypadVisible() {
        int found = 0;
        for (String label : KEYPAD_PROBE_LABELS) {
            if (findNodeByLabel(label) != null) {
                found++;
                if (found >= KEYPAD_PROBE_MIN_MATCHES) {
                    return true;
                }
            }
        }
        return false;
    }

    private void clickDigit(final int index) {
        if (currentPin == null) {
            return; // 途中で中断された
        }
        if (index >= currentPin.length()) {
            handler.postDelayed(new Runnable() {
                @Override
                public void run() {
                    clickEnter();
                }
            }, DIGIT_CLICK_INTERVAL_MS);
            return;
        }

        String digit = String.valueOf(currentPin.charAt(index));
        boolean ok = clickDigitKey(digit, index);
        if (!ok) {
            failureReasons.append("桁").append(index + 1).append(":未検出/失敗 ");
        }

        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                clickDigit(index + 1);
            }
        }, DIGIT_CLICK_INTERVAL_MS);
    }

    private boolean clickDigitKey(String digit, int index) {
        AccessibilityNodeInfo node = findNodeByLabel(digit);
        if (node != null && clickNode(node)) {
            traceAppend("ノード");
            return true;
        }
        // フォールバック: ノードが見つからない/クリックできない場合の座標タップ（実測グリッド）。
        boolean tapped = tapDigitByMeasuredGrid(digit, index);
        traceAppend(tapped ? "座標" : "失敗");
        return tapped;
    }

    /** 記録は手段のみ。どの数字をどこに打ったかは通知に出さない（PIN露出になるため）。 */
    private void traceAppend(String what) {
        if (trace != null) {
            trace.append(what).append(' ');
        }
    }

    private void clickEnter() {
        boolean clicked = false;
        for (String label : ENTER_LABELS) {
            AccessibilityNodeInfo node = findNodeByLabel(label);
            if (node != null && clickNode(node)) {
                clicked = true;
                break;
            }
        }
        if (clicked) {
            traceAppend("Enter:ノード");
        } else {
            failureReasons.append("Enter未検出 ");
            clicked = tapEnterByGridGuess();
            Point size = getScreenSize();
            traceAppend(clicked
                    ? "Enter:座標(" + Math.round(size.x * 0.5f) + "," + Math.round(size.y * 0.95f) + ")"
                    : "Enter:失敗");
            if (!clicked) {
                failureReasons.append("Enterフォールバックも失敗 ");
            }
        }

        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                checkResult();
            }
        }, RESULT_CHECK_DELAY_MS);
    }

    private void checkResult() {
        KeyguardManager keyguardManager = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
        boolean locked = keyguardManager != null && keyguardManager.isKeyguardLocked();

        // 通知を組み立てる直前の1箇所だけで、各ジェスチャのGestureResultCallback結果を
        // まとめて回収する（最大300ms待ち合わせ。各dispatch()自体では待たない）。
        traceAppend(GestureCompat.drainCallbackSummary());

        releaseWakeLock();
        currentPin = null;
        running.set(false);

        long elapsed = System.currentTimeMillis() - flowStartedAt;
        Point screen = getScreenSize();
        String keypadDiag = keypadConfirmedAttempt > 0
                ? "スワイプ" + keypadConfirmedAttempt + "回目で出現/起床→確認" + keypadConfirmedElapsedMs + "ms"
                : "スワイプ" + swipeAttempt + "回とも未出現";
        String detail = (trace == null ? "" : trace.toString().trim())
                + " / " + elapsed + "ms / 画面" + screen.x + "x" + screen.y
                + " / " + keypadDiag + " / 引き金:" + currentTriggerLabel;
        if (!locked) {
            postNotification(this, "ロック解除: 成功", detail);
            logUnlockEnd("success", null, elapsed, null);
            // RUN_ALL（本番の形）のときだけ、解除成功を確認したところでLINE操作へ続ける。
            // RUN単体ではrunAllRequestedがfalseのままなのでここは通らない（挙動不変）。
            // lockOnFinish=trueを渡し、LINE操作の終わりに施錠させる（旧ADB方式の
            // KEYCODE_HOME→KEYCODE_SLEEPに相当）。triggerLabelはLineExportFlowの結果通知へ
            // そのまま引き継ぐ。
            if (runAllRequested) {
                startExportFlow(true, currentTriggerLabel);
            }
        } else {
            String reason = failureReasons.length() > 0
                    ? failureReasons.toString().trim()
                    : "PIN入力後もロック中";
            postFailureNotification(this, reason + " / " + detail);
            logUnlockEnd("failure", reason, elapsed, null);
        }
        runAllRequested = false;
    }

    /**
     * ロック解除フローの終了行を書く。nextTrigger/nextAtMsはこのチェーンでRunSchedulerが
     * 新たに張ったアラーム（SchedulerStoreのpending-next、見送り時のscheduleRetryAfterSkip
     * 等）を読む。RunLogger自体は本体を壊さないため、ここでは失敗を気にせず呼ぶだけでよい。
     */
    private void logUnlockEnd(String result, String stage, long elapsedMs, JSONArray stepTimings) {
        String nextTrigger = SchedulerStore.getPendingNextTrigger(this);
        Long nextAtMs = null;
        if (nextTrigger != null) {
            nextAtMs = Long.valueOf(SchedulerStore.getPendingNextAtMs(this) - System.currentTimeMillis());
        }
        // ロック解除フローはuptimeMillis計測・段階ごとの構造化計測を持たない（2026-10-08
        // 「遅い回の原因確定のための計測追加」の対象はLINE操作フローのみ。unlock側は
        // elapsedUpMs=-1（未測定、ログには出さない）・extraFields=nullで渡す）。
        RunLogger.logEnd(this, currentRunId, "unlock", currentTriggerLabel, result, stage, elapsedMs, -1L,
                stepTimings, null, nextTrigger, nextAtMs, null);
    }

    // ---- Window diagnostics (experimental, read-only) -----------------------------------

    /**
     * 副ディスプレイ（仮想画面）上のアプリのUI要素をアクセシビリティ経由で読めるかを判定する。
     * getWindowsOnAllDisplays()はAPI30で追加されたメソッドで、このビルドがリンクする
     * android.jarはAPI23のためコンパイル時に直接参照できない。GestureCompat.javaと同じく
     * リフレクションで呼ぶ（実機はAndroid16なので実行時にはメソッドが存在する）。
     *
     * ロック解除やPIN入力は一切行わない。読み取りのみ。
     */
    private void runWindowDiagnostics() {
        SparseArray<List<AccessibilityWindowInfo>> allWindows;
        try {
            Method getWindowsOnAllDisplays = AccessibilityService.class.getMethod("getWindowsOnAllDisplays");
            Object result = getWindowsOnAllDisplays.invoke(this);
            @SuppressWarnings("unchecked")
            SparseArray<List<AccessibilityWindowInfo>> casted =
                    (SparseArray<List<AccessibilityWindowInfo>>) result;
            allWindows = casted;
        } catch (ReflectiveOperationException e) {
            postDiagNotification(this,
                    "getWindowsOnAllDisplays()呼び出し失敗: " + e.getClass().getName() + ": " + e.getMessage());
            return;
        } catch (RuntimeException e) {
            postDiagNotification(this,
                    "getWindowsOnAllDisplays()呼び出し失敗: " + e.getClass().getName() + ": " + e.getMessage());
            return;
        }

        StringBuilder allPart = new StringBuilder();
        StringBuilder pkgsPart = new StringBuilder();
        int size = allWindows == null ? 0 : allWindows.size();
        for (int i = 0; i < size; i++) {
            int displayId = allWindows.keyAt(i);
            List<AccessibilityWindowInfo> windows = allWindows.valueAt(i);
            int count = windows == null ? 0 : windows.size();

            if (allPart.length() > 0) {
                allPart.append(", ");
            }
            allPart.append(displayId).append(':').append(count);

            if (pkgsPart.length() > 0) {
                pkgsPart.append(' ');
            }
            pkgsPart.append(displayId).append(':').append(joinDistinctPackageNames(windows));
        }

        int defCount;
        try {
            List<AccessibilityWindowInfo> defaultWindows = getWindows();
            defCount = defaultWindows == null ? 0 : defaultWindows.size();
        } catch (RuntimeException e) {
            defCount = -1;
        }

        String body = "all=[" + allPart + "] / def=" + defCount + " / pkgs=" + pkgsPart;
        postDiagNotification(this, body);
    }

    /** 重複除去した packageName を最大3件、カンマ区切りで返す。PIN等の秘密は含まれない。 */
    private String joinDistinctPackageNames(List<AccessibilityWindowInfo> windows) {
        LinkedHashSet<String> pkgs = new LinkedHashSet<String>();
        if (windows != null) {
            for (AccessibilityWindowInfo window : windows) {
                if (window == null || pkgs.size() >= DIAG_MAX_PACKAGES_PER_DISPLAY) {
                    continue;
                }
                AccessibilityNodeInfo root = window.getRoot();
                CharSequence pkgName = root != null ? root.getPackageName() : null;
                if (pkgName != null) {
                    pkgs.add(pkgName.toString());
                }
            }
        }
        StringBuilder sb = new StringBuilder();
        for (String pkg : pkgs) {
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(pkg);
        }
        return sb.toString();
    }

    // ---- Accessibility node search / click -------------------------------------------
    //
    // 実装はNodeOpsへ移した（段階2 design.md追補 2026-10-08。LineExportFlowからも同じ
    // 探索ロジックを使うための共通化）。ここでは呼び出し先をNodeOpsに差し替えるだけの
    // 薄いラッパーとし、各呼び出し箇所・タイミング・判定順・traceAppendの記録内容は
    // 一切変えていない（純粋な移動）。

    private AccessibilityNodeInfo findNodeByLabel(String label) {
        return NodeOps.findNodeByLabel(this, label);
    }

    private boolean clickNode(AccessibilityNodeInfo node) {
        NodeOps.ClickResult result = NodeOps.clickNode(this, node);
        if (result.traceMessage != null) {
            traceAppend(result.traceMessage);
        }
        return result.accepted;
    }

    // ---- Coordinate-tap fallback (measured on the target device) -----------------------

    /*
     * 数字キーの中心位置（画面サイズに対する比率）。2026-09-18 に対象端末（画面 1080x2340）の
     * ロック画面で実測した値。ロック画面はスクリーンショットが真っ黒になるため、getevent で
     * タップを記録して求めた（1・3・7・9・0 を実測し、2・4・5・6・8 は格子計算による導出）。
     * 測定手順と注意点は docs/handoff/line-auto-export-app/design.md の「追補 2026-09-18」。
     */
    private static final float[] KEY_COL_X_RATIO = {0.2917f, 0.5231f, 0.7556f}; // x = 315 / 565 / 816 px
    private static final float[] KEY_ROW_Y_RATIO = {0.5051f, 0.6013f, 0.6974f}; // y = 1182 / 1407 / 1632 px
    private static final float KEY_ZERO_Y_RATIO = 0.7966f;                      // 0 は中央列、y = 1864 px

    /**
     * ノードが見つからない場合の座標タップ。実測した比率から数字キーの中心を求める。
     * 画面サイズは実行時に取得するため、同じレイアウトであれば解像度が違っても追従する。
     */
    private boolean tapDigitByMeasuredGrid(String digit, int index) {
        Point size = getScreenSize();
        if (size.x == 0 || size.y == 0) {
            return false;
        }

        float x;
        float y;
        if ("0".equals(digit)) {
            x = size.x * KEY_COL_X_RATIO[1];
            y = size.y * KEY_ZERO_Y_RATIO;
        } else {
            int d;
            try {
                d = Integer.parseInt(digit) - 1;
            } catch (NumberFormatException e) {
                return false;
            }
            if (d < 0 || d > 8) {
                return false;
            }
            x = size.x * KEY_COL_X_RATIO[d % 3];
            y = size.y * KEY_ROW_Y_RATIO[d / 3];
        }

        // ラベルは桁の位置のみ（例: "pin-key-1"）。PINの値は通知に出さない。
        GestureCompat.DispatchReport report = GestureCompat.tap(this, x, y, 80L, "pin-key-" + (index + 1));
        traceAppend(report.describe());
        return report.accepted;
    }

    /** Enterボタンの位置も未確認のため、キーパッド下の中央寄りを推測でタップする。 */
    private boolean tapEnterByGridGuess() {
        Point size = getScreenSize();
        if (size.x == 0 || size.y == 0) {
            return false;
        }
        float x = size.x * 0.5f;
        float y = size.y * 0.95f;
        GestureCompat.DispatchReport report = GestureCompat.tap(this, x, y, 80L, "enter");
        traceAppend(report.describe());
        return report.accepted;
    }

    /**
     * 画面全体の大きさ（装飾を除かない実サイズ）。getSize() はナビゲーションバー等を
     * 除いた値を返すことがあり、同じ端末で 2340 と 2184 の2通りが観測された
     * （2026-09-18 実機。高さが6.7%変わると数字キーの位置が約110px＝キー半個分ずれる）。
     * キー座標は実画面サイズに対する比率で測ってあるため、必ず getRealSize() を使う。
     */
    @SuppressWarnings("deprecation")
    private Point getScreenSize() {
        Point size = new Point();
        WindowManager wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
        if (wm != null) {
            wm.getDefaultDisplay().getRealSize(size);
        }
        return size;
    }

    // ---- Screen wake -------------------------------------------------------------------

    @SuppressWarnings("deprecation")
    private void acquireWakeLock() {
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (pm == null) {
            return;
        }
        if (wakeLock == null) {
            wakeLock = pm.newWakeLock(
                    PowerManager.SCREEN_BRIGHT_WAKE_LOCK
                            | PowerManager.ACQUIRE_CAUSES_WAKEUP
                            | PowerManager.ON_AFTER_RELEASE,
                    WAKE_LOCK_TAG);
        }
        if (!wakeLock.isHeld()) {
            wakeLock.acquire(WAKE_LOCK_SAFETY_TIMEOUT_MS);
        }
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }

    // ---- Notifications -------------------------------------------------------------------

    private static void postSuccessNotification(Context context) {
        postNotification(context, "ロック解除: 成功", null);
    }

    private static void postFailureNotification(Context context, String reason) {
        postNotification(context, "ロック解除: 失敗", reason);
    }

    /**
     * DIAG_WINDOWS専用の通知。本文はすでに整形済みの診断結果そのものを出す
     * （postNotificationのように「理由: 」を前置しない）。PIN等の秘密は含まれない。
     * 通常のロック解除結果通知（NOTIFICATION_ID）とは別IDにして、双方を取りこぼさない。
     */
    /**
     * 稼働中のAPKのversionName。ADBが使えない状況では、通知だけが「どの版が入っているか」を
     * 外から確認できる唯一の窓になる（2026-10-08: 新旧APKのversionNameが同じだったため
     * 入れ替わったかを誰も判定できなかった。その反省でタイトルに版を出す）。
     */
    static String versionLabel(Context context) {
        try {
            return context.getPackageManager()
                    .getPackageInfo(context.getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "?";
        }
    }

    private static void postDiagNotification(Context context, String body) {
        NotificationCompat.ensureChannel(context, CHANNEL_ID, "SA LINE Export");
        Notification.Builder builder = NotificationCompat.newBuilder(context, CHANNEL_ID)
                .setContentTitle("画面診断 v" + versionLabel(context))
                .setContentText(body)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true);
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID_DIAG, builder.build());
        }
    }

    private static void postNotification(Context context, String title, String reason) {
        NotificationCompat.ensureChannel(context, CHANNEL_ID, "SA LINE Export");
        String text = reason == null ? "" : "理由: " + reason;
        Notification.Builder builder = NotificationCompat.newBuilder(context, CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(text)
                // ジェスチャ診断(dispatch/cb/locked/screenOn/caps)を含めると長文になるため、
                // 展開時に全文が見えるようにする（本文の出し先・通知IDは変えない）。
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true);
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID, builder.build());
        }
    }
}
