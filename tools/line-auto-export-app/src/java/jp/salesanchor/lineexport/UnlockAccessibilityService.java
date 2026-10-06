package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.app.KeyguardManager;
import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.graphics.Point;
import android.graphics.Rect;
import android.os.Handler;
import android.os.PowerManager;
import android.util.Log;
import android.util.SparseArray;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

import java.lang.reflect.Method;
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
    private static final String CHANNEL_ID = "sa_line_export_unlock";
    private static final int NOTIFICATION_ID = 1001;
    private static final int NOTIFICATION_ID_DIAG = 1002;
    private static final String WAKE_LOCK_TAG = "SALineExport:unlock";
    private static final int DIAG_MAX_PACKAGES_PER_DISPLAY = 3;

    // ロック画面は画面消灯までが約5秒（端末の「画面消灯時間」を60秒にしても
    // activityTimeoutWM=5000 が効く。2026-09-18 実機ログで確認）。PIN入力が
    // その窓に確実に収まるよう、待ち時間を詰めてある。
    private static final long POST_WAKE_DELAY_MS = 600L;
    private static final long DIGIT_CLICK_INTERVAL_MS = 200L;
    private static final long KEYPAD_REVEAL_DELAY_MS = 700L;
    private static final long RESULT_CHECK_DELAY_MS = 1500L;
    private static final long WAKE_LOCK_SAFETY_TIMEOUT_MS = 10000L;

    private static final String[] ENTER_LABELS = {
            "Enter", "enter", "OK", "ok", "確認", "完了", "done", "Done", "→"
    };

    private static volatile UnlockAccessibilityService sInstance;

    /** 動作の記録。ログが端末で抑止されるため、通知に載せる唯一の手がかり（PINは載せない）。 */
    private StringBuilder trace;
    private long flowStartedAt;

    private final Handler handler = new Handler();
    private final AtomicBoolean running = new AtomicBoolean(false);

    private PowerManager.WakeLock wakeLock;
    private String currentPin;
    private StringBuilder failureReasons;

    /** 外部（RunReceiver）からの実行トリガー。サービス未接続なら失敗通知を出す。 */
    static void requestRun(Context context) {
        UnlockAccessibilityService instance = sInstance;
        if (instance == null) {
            postFailureNotification(context, "ユーザー補助サービスが未接続（無効化されている可能性）");
            return;
        }
        instance.startUnlockFlow();
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
        // 段階1ではイベント駆動の処理はしない。実行はrequestRun経由のみ。
    }

    @Override
    public void onInterrupt() {
        // no-op
    }

    private void startUnlockFlow() {
        if (!running.compareAndSet(false, true)) {
            Log.i(TAG, "unlock flow already running, ignoring duplicate trigger");
            return;
        }

        failureReasons = new StringBuilder();
        trace = new StringBuilder();
        flowStartedAt = System.currentTimeMillis();

        // ロックされていないときに数字を打つと、前面のアプリを誤タップする（ADB版の
        // 「使用中は見送り」と同じ判定）。
        KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
        if (km == null || !km.isKeyguardLocked()) {
            running.set(false);
            postNotification(this, "ロック解除: 見送り", "ロックされていない（使用中）");
            return;
        }

        String pin = PinStore.loadPin(this);
        if (pin == null || pin.length() == 0) {
            running.set(false);
            postFailureNotification(this, "PIN未設定");
            return;
        }
        currentPin = pin;

        acquireWakeLock();
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
     */
    private void revealKeypadThenEnterPin() {
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
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                clickDigit(0);
            }
        }, KEYPAD_REVEAL_DELAY_MS);
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

        releaseWakeLock();
        currentPin = null;
        running.set(false);

        long elapsed = System.currentTimeMillis() - flowStartedAt;
        Point screen = getScreenSize();
        String detail = (trace == null ? "" : trace.toString().trim())
                + " / " + elapsed + "ms / 画面" + screen.x + "x" + screen.y;
        if (!locked) {
            postNotification(this, "ロック解除: 成功", detail);
        } else {
            String reason = failureReasons.length() > 0
                    ? failureReasons.toString().trim()
                    : "PIN入力後もロック中";
            postFailureNotification(this, reason + " / " + detail);
        }
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

    private AccessibilityNodeInfo findNodeByLabel(String label) {
        try {
            List<AccessibilityWindowInfo> windows = getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    AccessibilityNodeInfo root = window.getRoot();
                    AccessibilityNodeInfo match = searchNode(root, label);
                    if (match != null) {
                        return match;
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        return searchNode(getRootInActiveWindow(), label);
    }

    private AccessibilityNodeInfo searchNode(AccessibilityNodeInfo node, String label) {
        if (node == null) {
            return null;
        }
        if (matchesLabel(node, label)) {
            return node;
        }
        int count = node.getChildCount();
        for (int i = 0; i < count; i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            AccessibilityNodeInfo match = searchNode(child, label);
            if (match != null) {
                return match;
            }
        }
        return null;
    }

    private boolean matchesLabel(AccessibilityNodeInfo node, String label) {
        CharSequence text = node.getText();
        CharSequence desc = node.getContentDescription();
        return (text != null && label.contentEquals(text))
                || (desc != null && label.contentEquals(desc));
    }

    private boolean clickNode(AccessibilityNodeInfo node) {
        AccessibilityNodeInfo target = node;
        while (target != null && !target.isClickable()) {
            target = target.getParent();
        }
        if (target != null) {
            return target.performAction(AccessibilityNodeInfo.ACTION_CLICK);
        }
        // クリック可能な祖先が無い場合は、そのノード自身の座標へgestureタップ。
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        if (!bounds.isEmpty()) {
            GestureCompat.DispatchReport report = GestureCompat.tap(
                    this, bounds.exactCenterX(), bounds.exactCenterY(), 80L, "node-tap");
            traceAppend(report.describe());
            return report.accepted;
        }
        return false;
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
    private static void postDiagNotification(Context context, String body) {
        NotificationCompat.ensureChannel(context, CHANNEL_ID, "SA LINE Export");
        Notification.Builder builder = NotificationCompat.newBuilder(context, CHANNEL_ID)
                .setContentTitle("画面診断")
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
