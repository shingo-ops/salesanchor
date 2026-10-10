package jp.salesanchor.lineexport;

import android.content.Context;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.TextView;

/**
 * 「自動取り込み中」バナーの表示/非表示。design.md追補「実行中の表示」(2026-10-09、PO決定・
 * 案1) に基づく補助表示機能で、書き出しフロー（LineExportFlow）自体の成否には一切影響しない
 * （show/removeが失敗しても例外を投げず、呼び出し側は戻り値のbooleanをログに残すだけでよい）。
 *
 * - TYPE_ACCESSIBILITY_OVERLAY（API22で追加された定数。javapでAPI23ビルドjarに存在する
 *   ことを確認済み）を使う。AccessibilityServiceはこの種別のウィンドウを追加権限なしで
 *   出せるため、SYSTEM_ALERT_WINDOW権限は追加しない（追加禁止、PO決定）。
 * - FLAG_NOT_TOUCHABLE と FLAG_NOT_FOCUSABLE を必ず両方立てる。タッチを遮断すると
 *   アプリ自身の座標タップ（EDITタップ等）が通らなくなる恐れがあるため、遮断しない
 *   （PO判断）。
 * - 全画面を覆わない帯として画面上部（Gravity.TOP）、高さはWRAP_CONTENTのみ。
 * - 表示テキスト「自動取り込み中」は、LINE操作で探索に使う文字列（設定/トーク履歴を送信/
 *   Termux/Menu ボタン/ショートカット名/期待グループ名）と1文字も重複しないことを確認済み。
 *   なお本バナーはLineExportFlowの区間のみ表示し、PIN入力（ロック解除）フェーズの
 *   キーパッドラベル（数字/Enter系）が探索対象になる区間では表示しないため、その面でも
 *   衝突の余地は無い。
 * - このウィンドウ自体はgetWindows()に新しいウィンドウとして現れるため、NodeOps側の
 *   全探索メソッドで自分自身のパッケージのウィンドウを除外する対応を別途行っている
 *   （NodeOps#isOwnWindow）。
 */
final class RunStatusOverlay {

    private static final String TAG = "SALineExport";
    private static final String MESSAGE = "自動取り込み中";

    private TextView view;

    /** @return 表示できたか（失敗してもフローは継続する。呼び出し側がログに残す）。 */
    boolean show(Context context) {
        if (view != null) {
            return true;
        }
        try {
            WindowManager wm = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
            if (wm == null) {
                return false;
            }
            TextView tv = new TextView(context);
            tv.setText(MESSAGE);
            tv.setTextColor(Color.WHITE);
            tv.setBackgroundColor(0xCC1A1A1A);
            tv.setGravity(Gravity.CENTER);
            int paddingPx = (int) TypedValue.applyDimension(
                    TypedValue.COMPLEX_UNIT_DIP, 8f, context.getResources().getDisplayMetrics());
            tv.setPadding(paddingPx, paddingPx, paddingPx, paddingPx);

            WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                    WindowManager.LayoutParams.MATCH_PARENT,
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                    WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                            | WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                    PixelFormat.TRANSLUCENT);
            params.gravity = Gravity.TOP;

            wm.addView(tv, params);
            view = tv;
            return true;
        } catch (RuntimeException e) {
            Log.w(TAG, "overlay show failed: " + e);
            view = null;
            return false;
        }
    }

    /** @return 除去できたか（元々表示していなければtrue）。失敗してもフローは継続する。 */
    boolean remove(Context context) {
        if (view == null) {
            return true;
        }
        try {
            WindowManager wm = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
            if (wm != null) {
                wm.removeView(view);
            }
            view = null;
            return true;
        } catch (RuntimeException e) {
            Log.w(TAG, "overlay remove failed: " + e);
            view = null;
            return false;
        }
    }
}
