package jp.salesanchor.lineexport;

import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Bundle;
import android.os.Environment;
import android.os.Parcelable;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;

/**
 * LINEの会話通知から本文を取り出し端末内に記録するだけのサービス（送信は一切しない）。
 *
 * 本番配線（Termux取り込みへの受け渡し等）は別作業。ここでは (a) 検証用JSONL と
 * (b) 既存の android_parser 互換のトーク書式(talk-*.txt) の2形式で追記するだけ。
 *
 * extras の android.conversationTitle / android.messages は API24 で追加された
 * Notification.EXTRA_* 定数だがこのビルド環境の android.jar は API23 のため、
 * 定数参照はコンパイルできない（javap で確認済み）。実行時のキー自体は
 * API23の実機でも存在する（Notification.extrasは単なるBundle）ため、
 * リテラル文字列で直読みする。
 */
public class LineNotifyListenerService extends NotificationListenerService {

    private static final String TAG = "SALineExport";

    private static final String PACKAGE_LINE = "jp.naver.line.android";

    // API24で追加された Notification.EXTRA_* 定数はAPI23のandroid.jarに無いためリテラルで持つ。
    private static final String EXTRA_CONVERSATION_TITLE = "android.conversationTitle";
    private static final String EXTRA_MESSAGES = "android.messages";

    // Notification.MessagingStyle.Message#toBundle() が使うキー（API23のandroid.jarにも
    // 定数は無いためリテラル）。sender_person(android.app.Person, API28)には触れない。
    private static final String MESSAGE_KEY_TEXT = "text";
    private static final String MESSAGE_KEY_SENDER = "sender";
    private static final String MESSAGE_KEY_TIME = "time";

    private static final String CHANNEL_ID = "sa_line_export_capture";
    private static final int NOTIFICATION_ID = 4204;

    private static final String[] WEEKDAY_KANJI = {"日", "月", "火", "水", "木", "金", "土"};

    private static final Object WRITE_LOCK = new Object();

    @Override
    public void onListenerConnected() {
        super.onListenerConnected();
        Log.i(TAG, "LineNotifyListenerService connected");
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        try {
            handle(sbn);
        } catch (Throwable t) {
            // 例外でサービスを落とさない。本文は出さず種別だけ記録する。
            Log.w(TAG, "onNotificationPosted failed: " + t);
        }
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification sbn) {
        // 記録専用。削除通知に対する処理は行わない。
    }

    private void handle(StatusBarNotification sbn) {
        if (sbn == null || !PACKAGE_LINE.equals(sbn.getPackageName())) {
            return;
        }

        Notification notification = sbn.getNotification();
        if (notification == null || (notification.flags & Notification.FLAG_GROUP_SUMMARY) != 0) {
            return;
        }

        Bundle extras = notification.extras;
        if (extras == null) {
            return;
        }

        CharSequence conversationTitle = extras.getCharSequence(EXTRA_CONVERSATION_TITLE);
        CharSequence title = extras.getCharSequence(Notification.EXTRA_TITLE);
        CharSequence bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT);
        CharSequence plainText = extras.getCharSequence(Notification.EXTRA_TEXT);
        String titleStr = title == null ? "" : title.toString();

        Parcelable[] messagesArr = extras.getParcelableArray(EXTRA_MESSAGES);
        int messagesCount = messagesArr == null ? 0 : messagesArr.length;
        Bundle lastMessage = null;
        if (messagesArr != null && messagesArr.length > 0) {
            Object last = messagesArr[messagesArr.length - 1];
            if (last instanceof Bundle) {
                lastMessage = (Bundle) last;
            }
        }

        CharSequence body = null;
        String source = null;
        if (lastMessage != null) {
            CharSequence msgText = lastMessage.getCharSequence(MESSAGE_KEY_TEXT);
            if (!isEmpty(msgText)) {
                body = msgText;
                source = "messages";
            }
        }
        if (body == null && !isEmpty(bigText)) {
            body = bigText;
            source = "bigText";
        }
        if (body == null && !isEmpty(plainText)) {
            body = plainText;
            source = "text";
        }
        if (body == null) {
            // android.messages / android.bigText / android.text のいずれからも本文が取れない。
            return;
        }

        String group = resolveGroup(conversationTitle, titleStr);
        if (!matchesTarget(group)) {
            return;
        }

        String sender = resolveSender(lastMessage, titleStr);
        long whenMs = resolveWhen(lastMessage, notification.when, sbn.getPostTime());
        String bodyStr = body.toString();

        record(sbn, group, sender, bodyStr, titleStr, messagesCount, source, whenMs);
    }

    private static String resolveGroup(CharSequence conversationTitle, String titleStr) {
        if (!isEmpty(conversationTitle)) {
            return conversationTitle.toString();
        }
        int idx = titleStr.indexOf(": ");
        return idx >= 0 ? titleStr.substring(0, idx) : titleStr;
    }

    private static String resolveSender(Bundle lastMessage, String titleStr) {
        if (lastMessage != null) {
            CharSequence sender = lastMessage.getCharSequence(MESSAGE_KEY_SENDER);
            if (!isEmpty(sender)) {
                return sender.toString();
            }
        }
        int idx = titleStr.indexOf(": ");
        if (idx >= 0 && idx + 2 <= titleStr.length()) {
            return titleStr.substring(idx + 2);
        }
        return "";
    }

    private static long resolveWhen(Bundle lastMessage, long notificationWhen, long postTime) {
        long when = lastMessage != null ? lastMessage.getLong(MESSAGE_KEY_TIME, 0L) : 0L;
        if (when == 0L) {
            when = notificationWhen;
        }
        if (when == 0L) {
            when = postTime;
        }
        return when;
    }

    /** 保存済みの対象グループ（カンマ区切り・完全一致）のどれかと一致するか。空欄なら全件一致。 */
    private boolean matchesTarget(String group) {
        String targets = NotifyStore.getTargetGroups(this);
        if (targets == null || targets.trim().length() == 0) {
            return true;
        }
        String[] parts = targets.split(",");
        for (String part : parts) {
            if (part.trim().equals(group)) {
                return true;
            }
        }
        return false;
    }

    private void record(StatusBarNotification sbn, String group, String sender, String body,
            String titleRaw, int messagesCount, String source, long whenMs) {
        File dir = resolveStorageDir();
        if (dir == null) {
            Log.w(TAG, "no writable storage dir for capture (textLen=" + body.length() + ")");
            return;
        }
        String storagePath = dir.getAbsolutePath();
        long postTimeMs = System.currentTimeMillis();
        String fileDateKey = new SimpleDateFormat("yyyyMMdd", Locale.JAPAN).format(new Date(postTimeMs));

        synchronized (WRITE_LOCK) {
            File rawFile = new File(dir, "raw-" + fileDateKey + ".jsonl");
            File talkFile = new File(dir, "talk-" + fileDateKey + ".txt");
            try {
                appendRawRecord(rawFile, sbn, group, sender, body, titleRaw, messagesCount, source,
                        whenMs, postTimeMs);
                appendTalkRecord(talkFile, sender, body, whenMs);
                NotifyStore.recordCapture(this, group, whenMs, storagePath);
            } catch (IOException e) {
                Log.w(TAG, "record write failed (textLen=" + body.length() + "): " + e);
                return;
            }
        }

        updateStatusNotification(group, whenMs);
    }

    private void appendRawRecord(File rawFile, StatusBarNotification sbn, String group, String sender,
            String body, String titleRaw, int messagesCount, String source, long whenMs, long postTimeMs)
            throws IOException {
        JSONObject json = new JSONObject();
        try {
            json.put("postTime", formatIso8601(postTimeMs));
            json.put("when", formatIso8601(whenMs));
            json.put("key", sbn.getKey());
            json.put("group", group);
            json.put("sender", sender);
            json.put("text", body);
            json.put("textLen", body.length());
            json.put("messagesCount", messagesCount);
            json.put("titleRaw", titleRaw);
            json.put("source", source);
        } catch (JSONException e) {
            throw new IOException("json build failed", e);
        }

        Writer writer = new OutputStreamWriter(new FileOutputStream(rawFile, true), "UTF-8");
        try {
            writer.write(json.toString());
            writer.write("\n");
            writer.flush();
        } finally {
            writer.close();
        }
    }

    /**
     * 既存の Android LINE 書き出し形式（tools/termux-line-import/android_parser.py が
     * 読める形）で1件追記する。本文中の改行はエスケープせず、そのまま次の行として
     * 出力する（CharSequenceの"\n"をそのまま書き込むだけで、継続行はタブなしの
     * 生の行になり既存パーサの継続行と同じ扱いになる）。
     */
    private void appendTalkRecord(File talkFile, String sender, String body, long whenMs) throws IOException {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(whenMs);
        String headerDate = cal.get(Calendar.YEAR) + "/" + (cal.get(Calendar.MONTH) + 1) + "/"
                + cal.get(Calendar.DAY_OF_MONTH) + "(" + WEEKDAY_KANJI[cal.get(Calendar.DAY_OF_WEEK) - 1] + ")";
        String timeLabel = cal.get(Calendar.HOUR_OF_DAY) + ":"
                + String.format(Locale.US, "%02d", cal.get(Calendar.MINUTE));
        String line = timeLabel + "\t" + sender + "\t" + body;

        String lastHeader = NotifyStore.getLastTalkHeaderDate(this);
        boolean needHeader = !headerDate.equals(lastHeader);

        Writer writer = new OutputStreamWriter(new FileOutputStream(talkFile, true), "UTF-8");
        try {
            if (needHeader) {
                writer.write(headerDate);
                writer.write("\n");
            }
            writer.write(line);
            writer.write("\n");
            writer.flush();
        } finally {
            writer.close();
        }

        if (needHeader) {
            NotifyStore.setLastTalkHeaderDate(this, headerDate);
        }
    }

    private static String formatIso8601(long millis) {
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.JAPAN).format(new Date(millis));
    }

    /**
     * 記録先ディレクトリを決める。まず外部ストレージのDownload配下を試し、
     * 作成/書き込みできなければアプリ私有領域にフォールバックする。
     */
    private File resolveStorageDir() {
        File primary = new File(Environment.getExternalStorageDirectory(), "Download/sa-line-notify");
        if (ensureWritableDir(primary)) {
            return primary;
        }
        File fallback = new File(getFilesDir(), "sa-line-notify");
        if (ensureWritableDir(fallback)) {
            return fallback;
        }
        return null;
    }

    private static boolean ensureWritableDir(File dir) {
        if (!dir.exists()) {
            dir.mkdirs();
        }
        return dir.isDirectory() && dir.canWrite();
    }

    /** 通知ID 4204 を更新表示する。本文は載せない。 */
    private void updateStatusNotification(String group, long whenMs) {
        try {
            long count = NotifyStore.getRecordCount(this);
            String timeLabel = new SimpleDateFormat("HH:mm", Locale.JAPAN).format(new Date(whenMs));
            String text = "記録: " + count + "件 / 最後: " + timeLabel + " " + group;

            NotificationCompat.ensureChannel(this, CHANNEL_ID, "SA LINE Export 記録");
            Notification.Builder builder = NotificationCompat.newBuilder(this, CHANNEL_ID)
                    .setContentTitle("SA LINE Export")
                    .setContentText(text)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setAutoCancel(false);
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) {
                nm.notify(NOTIFICATION_ID, builder.build());
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "status notification update failed: " + e);
        }
    }

    private static boolean isEmpty(CharSequence cs) {
        return cs == null || cs.length() == 0;
    }
}
