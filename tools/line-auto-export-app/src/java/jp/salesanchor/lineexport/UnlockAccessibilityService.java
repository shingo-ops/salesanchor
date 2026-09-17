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
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

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
    private static final String WAKE_LOCK_TAG = "SALineExport:unlock";

    private static final long POST_WAKE_DELAY_MS = 1200L;
    private static final long DIGIT_CLICK_INTERVAL_MS = 350L;
    private static final long RESULT_CHECK_DELAY_MS = 3000L;
    private static final long WAKE_LOCK_SAFETY_TIMEOUT_MS = 10000L;

    private static final String[] ENTER_LABELS = {
            "Enter", "enter", "OK", "ok", "確認", "完了", "done", "Done", "→"
    };

    private static volatile UnlockAccessibilityService sInstance;

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
                clickDigit(0);
            }
        }, POST_WAKE_DELAY_MS);
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
        boolean ok = clickDigitKey(digit);
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

    private boolean clickDigitKey(String digit) {
        AccessibilityNodeInfo node = findNodeByLabel(digit);
        if (node != null && clickNode(node)) {
            return true;
        }
        // フォールバック: ノードが見つからない/クリックできない場合の座標タップ（推測グリッド）。
        return tapDigitByGridGuess(digit);
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
        if (!clicked) {
            failureReasons.append("Enter未検出 ");
            clicked = tapEnterByGridGuess();
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

        if (!locked) {
            postSuccessNotification(this);
        } else {
            String reason = failureReasons.length() > 0
                    ? failureReasons.toString().trim()
                    : "PIN入力後もロック中";
            postFailureNotification(this, reason);
        }
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
            return GestureCompat.tap(this, bounds.exactCenterX(), bounds.exactCenterY(), 80L);
        }
        return false;
    }

    // ---- Coordinate-tap fallback (heuristic, needs on-device calibration) ------------

    /**
     * 最終手段: ノードが全く見つからない場合の推測グリッドタップ。標準的な3列x4行の
     * 数字キーパッド（1 2 3 / 4 5 6 / 7 8 9 / _ 0 _）が画面下側にあると仮定した座標。
     * 実機のOEM/スキンによりレイアウトは異なるため、段階1の実機検証後に要調整
     * （docs/handoff/line-auto-export-app/design.md 段階1）。
     */
    private boolean tapDigitByGridGuess(String digit) {
        Point size = getScreenSize();
        if (size.x == 0 || size.y == 0) {
            return false;
        }

        int row;
        int col;
        if ("0".equals(digit)) {
            row = 3;
            col = 1;
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
            row = d / 3;
            col = d % 3;
        }

        float keypadTop = size.y * 0.42f;
        float keypadBottom = size.y * 0.95f;
        float keypadLeft = size.x * 0.08f;
        float keypadRight = size.x * 0.92f;
        float cellW = (keypadRight - keypadLeft) / 3f;
        float cellH = (keypadBottom - keypadTop) / 4f;
        float x = keypadLeft + cellW * (col + 0.5f);
        float y = keypadTop + cellH * (row + 0.5f);

        return GestureCompat.tap(this, x, y, 80L);
    }

    /** Enterボタンの位置も未確認のため、キーパッド下の中央寄りを推測でタップする。 */
    private boolean tapEnterByGridGuess() {
        Point size = getScreenSize();
        if (size.x == 0 || size.y == 0) {
            return false;
        }
        float x = size.x * 0.5f;
        float y = size.y * 0.95f;
        return GestureCompat.tap(this, x, y, 80L);
    }

    @SuppressWarnings("deprecation")
    private Point getScreenSize() {
        Point size = new Point();
        WindowManager wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
        if (wm != null) {
            wm.getDefaultDisplay().getSize(size);
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

    private static void postNotification(Context context, String title, String reason) {
        NotificationCompat.ensureChannel(context, CHANNEL_ID, "SA LINE Export");
        String text = reason == null ? "" : "理由: " + reason;
        Notification.Builder builder = NotificationCompat.newBuilder(context, CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true);
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID, builder.build());
        }
    }
}
