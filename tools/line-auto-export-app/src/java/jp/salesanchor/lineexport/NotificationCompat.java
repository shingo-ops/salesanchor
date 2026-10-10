package jp.salesanchor.lineexport;

import android.app.Notification;
import android.content.Context;
import android.os.Build;
import android.util.Log;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;

/**
 * Small reflection shim so this app can post a working notification on the real target
 * device (Android 16 / API 26+ requires a NotificationChannel) while still compiling
 * against this build environment's android.jar, which is pinned to API23 (see
 * docs/handoff/line-auto-export-app/design.md, recon.md). NotificationChannel and the
 * Notification.Builder(Context, String) / setChannelId(String) APIs were all added in
 * API26, so their classes/members do not exist in the API23 stub jar and cannot be
 * referenced directly — reflection is used instead. On API23 devices these calls are
 * simply skipped (Build.VERSION.SDK_INT < 26 guard).
 */
final class NotificationCompat {

    private static final String TAG = "SALineExport";

    // NotificationManager.IMPORTANCE_DEFAULT (constant only exists in API26+ stubs).
    private static final int IMPORTANCE_DEFAULT = 3;

    private NotificationCompat() {
    }

    static void ensureChannel(Context context, String channelId, CharSequence channelName) {
        if (Build.VERSION.SDK_INT < 26) {
            return;
        }
        try {
            Object notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE);
            Class<?> channelClass = Class.forName("android.app.NotificationChannel");
            Constructor<?> channelCtor = channelClass.getConstructor(String.class, CharSequence.class, int.class);
            Object channel = channelCtor.newInstance(channelId, channelName, IMPORTANCE_DEFAULT);
            Method createChannel = notificationManager.getClass()
                    .getMethod("createNotificationChannel", channelClass);
            createChannel.invoke(notificationManager, channel);
        } catch (ReflectiveOperationException e) {
            Log.w(TAG, "notification channel setup skipped: " + e);
        }
    }

    static Notification.Builder newBuilder(Context context, String channelId) {
        @SuppressWarnings("deprecation")
        Notification.Builder builder = new Notification.Builder(context);
        if (Build.VERSION.SDK_INT >= 26) {
            try {
                Method setChannelId = Notification.Builder.class.getMethod("setChannelId", String.class);
                setChannelId.invoke(builder, channelId);
            } catch (ReflectiveOperationException e) {
                Log.w(TAG, "setChannelId skipped: " + e);
            }
        }
        return builder;
    }
}
