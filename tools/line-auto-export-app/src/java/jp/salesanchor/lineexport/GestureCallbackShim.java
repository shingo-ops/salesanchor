package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.GestureDescription;

/**
 * AccessibilityService.GestureResultCallback の実体。onCompleted/onCancelledのどちらが
 * 呼ばれたか（GestureOutcome経由で観測するため）を区別するのに必要だが、このクラスの
 * 直接のスーパークラス（GestureResultCallback）はAPI24で追加されたため、ビルド環境の
 * android.jar(API23, build.shのANDROID_JAR)には存在せず直接コンパイルできない。
 *
 * そのため、このファイルだけ build.sh の別javacパスで sdk/android-34.jar を
 * classpathにしてコンパイルし、同じ classes ディレクトリへ合流させている
 * （aaptのリソース解決に使っているのと同じjar。GestureDescription/StrokeDescription等の
 * 実クラスを含むことは確認済み）。他のファイル（GestureCompat.java）からはこのクラスを
 * 直接型参照せず、Class.forName経由のリフレクションでのみ生成する。実機（Android16）には
 * 本物のフレームワーククラスが存在するため、実行時はそちらで解決される。
 */
final class GestureCallbackShim extends AccessibilityService.GestureResultCallback {

    private final GestureOutcome outcome;

    public GestureCallbackShim(GestureOutcome outcome) {
        this.outcome = outcome;
    }

    @Override
    public void onCompleted(GestureDescription gestureDescription) {
        outcome.setResult(GestureOutcome.COMPLETED);
    }

    @Override
    public void onCancelled(GestureDescription gestureDescription) {
        outcome.setResult(GestureOutcome.CANCELLED);
    }
}
