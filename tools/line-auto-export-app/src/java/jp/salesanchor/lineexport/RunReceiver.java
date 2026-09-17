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

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !ACTION_RUN.equals(intent.getAction())) {
            return;
        }
        UnlockAccessibilityService.requestRun(context.getApplicationContext());
    }
}
