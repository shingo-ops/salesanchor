package jp.salesanchor.lineexport;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * dispatchGesture() が受理した後、GestureResultCallback#onCompleted/onCancelled の
 * どちらが呼ばれたか（呼ばれないことも含む）を観測するための橋渡し。
 *
 * このクラス自体はandroidのジェスチャ関連クラスに一切依存しないため、ビルド環境の
 * android.jar(API23)でも直接コンパイルできる。実体のコールバック（GestureCallbackShim,
 * API34でコンパイル）がonCompleted/onCancelledから setResult() を呼ぶ。
 *
 * setResult()はメインスレッド以外（GestureCompatが用意するsa-gesture-cbスレッド）から
 * 呼ばれる想定。dispatch()側はここでは待たない（GestureCompat.drainCallbackSummary()が
 * 通知組み立て直前に1回だけ、複数ジェスチャ分まとめて待つ）。
 */
final class GestureOutcome {

    static final String COMPLETED = "completed";
    static final String CANCELLED = "cancelled";

    private final CountDownLatch latch = new CountDownLatch(1);
    private volatile String result;

    void setResult(String value) {
        result = value;
        latch.countDown();
    }

    /** 待たずに今わかっている結果を返す。まだ届いていなければnull。 */
    String peekResult() {
        return result;
    }

    /** 最大waitMsだけ待つ。届かなければnullを返す（呼び出し側が"pending"等に読み替える）。 */
    String awaitResult(long waitMs) {
        if (waitMs > 0) {
            try {
                latch.await(waitMs, TimeUnit.MILLISECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        return result;
    }
}
