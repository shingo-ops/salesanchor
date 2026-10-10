package jp.salesanchor.lineexport;

import android.content.Context;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.Handler;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * 「自動取り込み中」バナーの表示/非表示。design.md追補「実行中の表示」(2026-10-09、PO決定・
 * 案1) に基づく補助表示機能で、書き出しフロー（LineExportFlow）自体の成否には一切影響しない
 * （show/removeが失敗しても例外を投げず、呼び出し側は戻り値のbooleanをログに残すだけでよい）。
 *
 * - TYPE_ACCESSIBILITY_OVERLAY（API22で追加された定数。javapでAPI23ビルドjarに存在する
 *   ことを確認済み）を使う。AccessibilityServiceはこの種別のウィンドウを追加権限なしで
 *   出せるため、SYSTEM_ALERT_WINDOW権限は追加しない（追加禁止、PO決定）。
 * - 通常モード（blocking==false、既定）: FLAG_NOT_TOUCHABLE と FLAG_NOT_FOCUSABLE を必ず
 *   両方立てる。タッチを遮断するとアプリ自身の座標タップ（EDITタップ等）が通らなくなる恐れ
 *   があるため、遮断しない（PO判断）。全画面を覆わない帯として画面上部（Gravity.TOP）、
 *   高さはWRAP_CONTENTのみ。この挙動は1バイトも変えていない。
 * - 表示テキスト「自動取り込み中」は、LINE操作で探索に使う文字列（設定/トーク履歴を送信/
 *   Termux/Menu ボタン/ショートカット名/期待グループ名）と1文字も重複しないことを確認済み。
 *   なお本バナーはLineExportFlowの区間のみ表示し、PIN入力（ロック解除）フェーズの
 *   キーパッドラベル（数字/Enter系）が探索対象になる区間では表示しないため、その面でも
 *   衝突の余地は無い。
 * - このウィンドウ自体はgetWindows()に新しいウィンドウとして現れるため、NodeOps側の
 *   全探索メソッドで自分自身のパッケージのウィンドウを除外する対応を別途行っている
 *   （NodeOps#isOwnWindow）。
 * - 遮断モード（blocking==true、検証用）: design.md追補 2026-10-11「遮断モードの帯
 *   （検証用）」参照。全画面でタッチを消費する帯を出し、dispatchGestureのタップが帯に
 *   吸われるかどうかを確かめるための実験用モード。通常実行では使わない
 *   （SchedulerStoreのone-shotフラグ経由のみ）。
 */
final class RunStatusOverlay {

    private static final String TAG = "SALineExport";
    private static final String MESSAGE = "自動取り込み中";
    private static final String BLOCKING_MESSAGE = "自動取り込み中（操作できません）";
    private static final String ESCAPE_BUTTON_LABEL = "停止";

    /**
     * 遮断モードの強制撤去タイマー。フローが途中で死んでも操作不能が続かないようにするため
     * の保険で、show()の呼び出しチェーンとは独立に60秒後へ無条件でremove()する
     * （design.md追補 2026-10-11参照）。remove()が先に呼ばれたらこのコールバックは
     * removeCallbacksで取り消す。
     */
    private static final long BLOCKING_AUTO_REMOVE_MS = 60_000L;

    private View view;
    private Handler blockingAutoRemoveHandler;
    private Runnable blockingAutoRemoveRunnable;
    private boolean escapeTapped;

    /** @return 表示できたか（失敗してもフローは継続する。呼び出し側がログに残す）。 */
    boolean show(Context context, boolean blocking) {
        if (view != null) {
            return true;
        }
        try {
            WindowManager wm = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
            if (wm == null) {
                return false;
            }
            View root = blocking ? buildBlockingView(context) : buildPlainView(context);

            WindowManager.LayoutParams params;
            if (blocking) {
                params = new WindowManager.LayoutParams(
                        WindowManager.LayoutParams.MATCH_PARENT,
                        WindowManager.LayoutParams.MATCH_PARENT,
                        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                        PixelFormat.TRANSLUCENT);
                params.gravity = Gravity.TOP;
            } else {
                params = new WindowManager.LayoutParams(
                        WindowManager.LayoutParams.MATCH_PARENT,
                        WindowManager.LayoutParams.WRAP_CONTENT,
                        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                        WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                                | WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                        PixelFormat.TRANSLUCENT);
                params.gravity = Gravity.TOP;
            }

            wm.addView(root, params);
            view = root;
            escapeTapped = false;

            if (blocking) {
                // フローとは独立の強制撤去タイマー（保険）。フローが途中で死んでも
                // 操作不能が続かないようにする。
                blockingAutoRemoveHandler = new Handler(context.getMainLooper());
                blockingAutoRemoveRunnable = new Runnable() {
                    @Override
                    public void run() {
                        Log.w(TAG, "blocking overlay auto-removed after " + BLOCKING_AUTO_REMOVE_MS + "ms");
                        remove(context);
                    }
                };
                blockingAutoRemoveHandler.postDelayed(blockingAutoRemoveRunnable, BLOCKING_AUTO_REMOVE_MS);
            }
            return true;
        } catch (RuntimeException e) {
            Log.w(TAG, "overlay show failed: " + e);
            view = null;
            return false;
        }
    }

    private View buildPlainView(Context context) {
        TextView tv = new TextView(context);
        tv.setText(MESSAGE);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC1A1A1A);
        tv.setGravity(Gravity.CENTER);
        int paddingPx = (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, 8f, context.getResources().getDisplayMetrics());
        tv.setPadding(paddingPx, paddingPx, paddingPx, paddingPx);
        return tv;
    }

    /**
     * 遮断モードのルート。全画面FrameLayoutで、常にtrueを返すOnTouchListenerにより
     * すべてのタッチを消費する（下のアプリへ渡さない）。半透明背景で下のLINE画面が
     * 目視できるようにし、上端に案内文、右下に非常口（停止ボタン）を置く。
     */
    private View buildBlockingView(final Context context) {
        FrameLayout root = new FrameLayout(context);
        root.setBackgroundColor(0x66000000);
        root.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, android.view.MotionEvent event) {
                return true;
            }
        });

        TextView label = new TextView(context);
        label.setText(BLOCKING_MESSAGE);
        label.setTextColor(Color.WHITE);
        label.setBackgroundColor(0xCC1A1A1A);
        label.setGravity(Gravity.CENTER);
        int paddingPx = (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, 8f, context.getResources().getDisplayMetrics());
        label.setPadding(paddingPx, paddingPx, paddingPx, paddingPx);
        FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT);
        labelParams.gravity = Gravity.TOP;
        root.addView(label, labelParams);

        // 非常口: 利用者が操作不能から必ず抜け出せる「停止」ボタン。右下の隅、
        // 誤って押しにくい位置に、十分な大きさ（最低48dp）で置く。
        android.widget.Button escapeButton = new android.widget.Button(context);
        escapeButton.setText(ESCAPE_BUTTON_LABEL);
        int minSizePx = (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, 48f, context.getResources().getDisplayMetrics());
        escapeButton.setMinWidth(minSizePx);
        escapeButton.setMinHeight(minSizePx);
        escapeButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                escapeTapped = true;
                remove(context);
            }
        });
        FrameLayout.LayoutParams escapeParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
        escapeParams.gravity = Gravity.BOTTOM | Gravity.END;
        int marginPx = (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, 16f, context.getResources().getDisplayMetrics());
        escapeParams.setMargins(marginPx, marginPx, marginPx, marginPx);
        root.addView(escapeButton, escapeParams);

        return root;
    }

    /** @return 除去できたか（元々表示していなければtrue）。失敗してもフローは継続する。 */
    boolean remove(Context context) {
        if (blockingAutoRemoveHandler != null && blockingAutoRemoveRunnable != null) {
            blockingAutoRemoveHandler.removeCallbacks(blockingAutoRemoveRunnable);
            blockingAutoRemoveHandler = null;
            blockingAutoRemoveRunnable = null;
        }
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

    /** @return 遮断モードで「停止」(非常口)が押されたか。押されなければfalse。 */
    boolean wasEscapeTapped() {
        return escapeTapped;
    }
}
