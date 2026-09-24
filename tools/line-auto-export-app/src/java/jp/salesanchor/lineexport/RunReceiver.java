package jp.salesanchor.lineexport;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * 起動口: Termuxから `am broadcast -a jp.salesanchor.lineexport.RUN` で
 * 「今すぐ実行」を通知するためのBroadcastReceiver。PINはextraに載せない
 * （design.md: 起動口はPINを運ばず、PINはこのアプリの私有領域に保存済みのものを使う）。
 */
public class RunReceiver extends BroadcastReceiver {

    public static final String ACTION_RUN = "jp.salesanchor.lineexport.RUN";

    /**
     * 実験用の診断専用の起動口。RUN（ロック解除）とは独立の経路で、ロック解除や
     * PIN入力は一切行わない読み取り専用の診断（副ディスプレイ上のウィンドウが
     * 見えるか）をUnlockAccessibilityServiceに依頼する。
     */
    public static final String ACTION_DIAG_WINDOWS = "jp.salesanchor.lineexport.DIAG_WINDOWS";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) {
            return;
        }
        String action = intent.getAction();
        if (ACTION_RUN.equals(action)) {
            UnlockAccessibilityService.requestRun(context.getApplicationContext());
        } else if (ACTION_DIAG_WINDOWS.equals(action)) {
            UnlockAccessibilityService.requestDiagWindows(context.getApplicationContext());
        }
    }
}
