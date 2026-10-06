package jp.salesanchor.lineexport;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * dispatchGesture() が受理した後、GestureResultCallback#onCompleted/onCancelled の
 * どちらが呼ばれたか（呼ばれないことも含む）を観測するための橋渡し。
 *
 * このクラス自体はandroidのジェスチャ関連クラスに一切依存しないため、ビルド環境の
 * android.jar(API23)でも直接コンパイルできる。実体のコールバック（GestureCallbackShim,
 * API34でコンパイル）がonCompleted/onCancelledから setResult() を呼び、GestureCompat側は
 * awaitResult() で一定時間待って結果を読む。
 */
final class GestureOutcome {

    static final String COMPLETED = "completed";
    static final String CANCELLED = "cancelled";
    static final String NO_CALLBACK = "no-callback";

    private final CountDownLatch latch = new CountDownLatch(1);
    private volatile String result;

    void setResult(String value) {
        result = value;
        latch.countDown();
    }

    /** 最大waitMsだけ待つ。呼ばれなければ NO_CALLBACK を返す。 */
    String awaitResult(long waitMs) {
        try {
            latch.await(waitMs, TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        String r = result;
        return r != null ? r : NO_CALLBACK;
    }
}
