package jp.salesanchor.lineexport;

import android.app.KeyguardManager;
import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Bundle;
import android.os.Environment;
import android.os.Parcelable;
import android.os.PowerManager;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

import org.json.JSONArray;
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
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/**
 * LINEの会話通知から本文を取り出し端末内に記録するだけのサービス（送信は一切しない）。
 *
 * 本番配線（Termux取り込みへの受け渡し等）は別作業。ここでは (a) 診断用JSONL、
 * (b) 検証用JSONL(raw-*.jsonl)、(c) 既存の android_parser 互換のトーク書式(talk-*.txt)、
 * (d) 削除記録(removed-*.jsonl) の4形式で追記するだけ。
 *
 * extras の android.conversationTitle / android.messages は API24 で追加された
 * Notification.EXTRA_* 定数だがこのビルド環境の android.jar は API23 のため、
 * 定数参照はコンパイルできない（javap で確認済み）。実行時のキー自体は
 * API23の実機でも存在する（Notification.extrasは単なるBundle）ため、
 * リテラル文字列で直読みする。
 *
 * 2026-10-01 追補（診断ログ）: LINEは1つのメッセージに対して2種類の通知を出す
 * （BigTextStyle: id=16880000,tag=null と MessagingStyle: id=1351171955,
 * tag=NOTIFICATION_TAG_MESSAGE を含む）。詳細・実測値は
 * docs/handoff/line-auto-export-app/design.md の「2026-10-01 追補」を参照。
 */
public class LineNotifyListenerService extends NotificationListenerService {

    private static final String TAG = "SALineExport";

    private static final String PACKAGE_LINE = "jp.naver.line.android";

    // API24で追加された Notification.EXTRA_* 定数はAPI23のandroid.jarに無いためリテラルで持つ。
    // EXTRA_SUB_TEXT/EXTRA_SUMMARY_TEXT/EXTRA_TEMPLATE/EXTRA_TITLE/EXTRA_TEXT/EXTRA_BIG_TEXT は
    // API23のandroid.jarに存在するため Notification.EXTRA_* をそのまま使う（javap -p -constants で確認済み）。
    private static final String EXTRA_CONVERSATION_TITLE = "android.conversationTitle";
    private static final String EXTRA_MESSAGES = "android.messages";

    // Notification.MessagingStyle.Message#toBundle() が使うキー（API23のandroid.jarにも
    // 定数は無いためリテラル）。sender_person(android.app.Person、API28)には触れない。
    private static final String MESSAGE_KEY_TEXT = "text";
    private static final String MESSAGE_KEY_SENDER = "sender";
    private static final String MESSAGE_KEY_TIME = "time";

    // MessagingStyle側（本文の採用対象）を示すタグの部分文字列。
    private static final String TAG_MESSAGE = "NOTIFICATION_TAG_MESSAGE";

    private static final String CHANNEL_ID = "sa_line_export_capture";
    private static final int NOTIFICATION_ID = 4204;

    private static final String[] WEEKDAY_KANJI = {"日", "月", "火", "水", "木", "金", "土"};

    private static final Object WRITE_LOCK = new Object();

    /**
     * BigTextStyle側（id=16880000,tag=null）で観測した text/bigText を、後から来る
     * MessagingStyle側（id=1351171955,tag=NOTIFICATION_TAG_MESSAGE）での本文比較の
     * 材料として一時的に持つキャッシュ。(group, sender) で引き当てる。
     *
     * 設計メモ（design.mdには明記がない実装判断）: 2つの通知は別々の
     * StatusBarNotification（id/tagが異なる）として届くため、同一メッセージかどうかを
     * 直接突き合わせる共通IDが無い。実測上は同じ着信メッセージに対して両方の通知が
     * ほぼ同時に飛んでくるため、(group, sender) が一致する直近のBigTextStyle側候補を
     * 使い切り（取り出したら消す）で突き合わせる。取り出し消費にしているのは、
     * 同じ相手との会話が続いた場合に古い候補を別メッセージへ誤って流用するのを防ぐため
     * （古い候補を使い回すと内容が化ける方が、比較材料が見つからず素通りするより害が大きい）。
     * BigTextStyle側がMessagingStyle側より後に届いた場合は突き合わせに失敗し
     * 比較対象なし（messages[i]の本文がそのまま採用）になる＝未対応。
     */
    private static final int BIGTEXT_CACHE_CAPACITY = 20;
    private static final Object BIGTEXT_CACHE_LOCK = new Object();
    private static final Map<String, BigTextCandidate> BIGTEXT_CACHE =
            new LinkedHashMap<String, BigTextCandidate>(16, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<String, BigTextCandidate> eldest) {
                    return size() > BIGTEXT_CACHE_CAPACITY;
                }
            };

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
        // 記録専用。削除そのものへの対応（再送要求等）は行わない。
        // 目的: メッセージが送信取消されたときに通知が消えるかを事実として捉えること。
        // ただしユーザーが既読にした場合も通知は消えるため、removed-*.jsonl の記録だけでは
        // 「取消」と「既読」を区別できない。判定は人間が他の手がかりと合わせて後で行う。
        try {
            handleRemoved(sbn);
        } catch (Throwable t) {
            Log.w(TAG, "onNotificationRemoved failed: " + t);
        }
    }

    private void handle(StatusBarNotification sbn) {
        if (sbn == null || !PACKAGE_LINE.equals(sbn.getPackageName())) {
            return;
        }

        Notification notification = sbn.getNotification();
        if (notification == null) {
            return;
        }

        Bundle extras = notification.extras;
        if (extras == null) {
            return;
        }

        CharSequence conversationTitle = extras.getCharSequence(EXTRA_CONVERSATION_TITLE);
        CharSequence title = extras.getCharSequence(Notification.EXTRA_TITLE);
        CharSequence subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT);
        CharSequence summaryText = extras.getCharSequence(Notification.EXTRA_SUMMARY_TEXT);
        CharSequence bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT);
        CharSequence plainText = extras.getCharSequence(Notification.EXTRA_TEXT);
        String template = extras.getString(Notification.EXTRA_TEMPLATE);
        String titleStr = title == null ? "" : title.toString();

        Parcelable[] messagesArr = extras.getParcelableArray(EXTRA_MESSAGES);
        int messagesCount = messagesArr == null ? 0 : messagesArr.length;

        boolean interactive = isInteractive();
        boolean keyguardLocked = isKeyguardLocked();

        // A: 診断JSONL。対象グループ判定より前に、集約通知も含め全件を記録する。
        try {
            appendDiagRecord(sbn, notification, template, titleStr, subText, summaryText,
                    conversationTitle, bigText, plainText, messagesArr, messagesCount,
                    interactive, keyguardLocked);
        } catch (IOException e) {
            Log.w(TAG, "diag write failed: " + e);
        }

        if ((notification.flags & Notification.FLAG_GROUP_SUMMARY) != 0) {
            return;
        }

        boolean hasMessages = messagesArr != null && messagesArr.length > 0;
        boolean hasBigText = !isEmpty(bigText);

        if (!hasMessages && !hasBigText) {
            // 集約通知（例: summaryText "NNNN件の新規通知" / text "999+件の新規メッセージ"）。
            // messagesもbigTextも無く個別メッセージの本文を持たないため raw/talk にもキャッシュにも使わない。
            return;
        }

        String group = resolveGroup(conversationTitle, subText, titleStr);
        if (!matchesTarget(group)) {
            return;
        }

        // 段階3: 対象グループの通知を引き金にする（design.md追補 2026-10-08「段階3の方式変更」）。
        // conversationTitleが空（＝LINEの「メッセージ内容を表示」がOFFで中身が隠れている）の
        // 場合は、どのグループか判別できないため引き金にしない（保険タイマーに任せる）。
        // resolveGroupはconversationTitleが空でもsubText/titleStrへフォールバックするため、
        // ここでconversationTitle自体を明示的に確認する（フォールバック結果が偶然一致しても
        // 引き金にはしない。判別できないものを引き金にすると他グループの投稿で無駄に起動する）。
        if (!isEmpty(conversationTitle)) {
            RunScheduler.onQualifyingNotification(this);
        }

        if (!hasMessages) {
            // BigTextStyle側（id=16880000,tag=null）。診断JSONLと、MessagingStyle側で使う
            // 長さ比較の材料としてのみ使う。raw/talkへの二重記録を避けるためここでは書かない。
            String sender = titleStr; // templateがBigTextStyleのときは android.title 全体が送信者。
            cacheBigTextCandidate(group, sender, plainText, bigText);
            return;
        }

        String tag = sbn.getTag();
        if (tag == null || !tag.contains(TAG_MESSAGE)) {
            // MessagingStyle相当だが想定タグ(NOTIFICATION_TAG_MESSAGE)でない場合は書かない。
            return;
        }

        int messagesMaxLen = computeMessagesMaxLen(messagesArr);
        String lastWrittenGroup = null;
        long lastWrittenWhen = 0L;

        for (int i = 0; i < messagesArr.length; i++) {
            Object item = messagesArr[i];
            if (!(item instanceof Bundle)) {
                continue;
            }
            Bundle messageBundle = (Bundle) item;
            CharSequence msgText = messageBundle.getCharSequence(MESSAGE_KEY_TEXT);
            if (isEmpty(msgText)) {
                continue;
            }

            String sender = resolveSender(messageBundle, titleStr);
            long whenMs = resolveWhen(messageBundle, notification.when, sbn.getPostTime());

            BigTextCandidate candidate = takeBigTextCandidate(group, sender);
            CharSequence candidateBigText = candidate == null ? null : candidate.bigText;
            CharSequence candidateText = candidate == null ? null : candidate.text;

            LongestPick pick = pickLongest(msgText, candidateBigText, candidateText, i);
            String bodyStr = pick.text;

            int previousLen = NotifyStore.getRecordedLen(sbn.getKey(), whenMs, sender);
            if (bodyStr.length() <= previousLen) {
                // 同じ(key, time, sender)で前回より短いか同じ＝既により良い版を記録済み。
                continue;
            }

            int lenText = candidateText == null ? 0 : candidateText.length();
            int lenBigText = candidateBigText == null ? 0 : candidateBigText.length();

            record(sbn, group, sender, bodyStr, titleStr, messagesCount, pick.source, whenMs,
                    lenText, lenBigText, messagesMaxLen, previousLen);

            NotifyStore.recordLen(sbn.getKey(), whenMs, sender, bodyStr.length());
            lastWrittenGroup = group;
            lastWrittenWhen = whenMs;
        }

        if (lastWrittenGroup != null) {
            updateStatusNotification(lastWrittenGroup, lastWrittenWhen);
        }
    }

    private void handleRemoved(StatusBarNotification sbn) {
        if (sbn == null || !PACKAGE_LINE.equals(sbn.getPackageName())) {
            return;
        }

        File dir = resolveStorageDir();
        if (dir == null) {
            Log.w(TAG, "no writable storage dir for removed record");
            return;
        }

        Notification notification = sbn.getNotification();
        long whenMs = notification == null ? 0L : notification.when;
        boolean interactive = isInteractive();
        boolean keyguardLocked = isKeyguardLocked();

        long postTimeMs = System.currentTimeMillis();
        String fileDateKey = new SimpleDateFormat("yyyyMMdd", Locale.JAPAN).format(new Date(postTimeMs));
        File removedFile = new File(dir, "removed-" + fileDateKey + ".jsonl");

        JSONObject json = new JSONObject();
        try {
            json.put("postTime", formatIso8601(postTimeMs));
            json.put("key", sbn.getKey());
            json.put("id", sbn.getId());
            json.put("tag", sbn.getTag());
            json.put("when", formatIso8601(whenMs));
            json.put("interactive", interactive);
            json.put("keyguardLocked", keyguardLocked);
        } catch (JSONException e) {
            Log.w(TAG, "removed json build failed: " + e);
            return;
        }

        synchronized (WRITE_LOCK) {
            try {
                Writer writer = new OutputStreamWriter(new FileOutputStream(removedFile, true), "UTF-8");
                try {
                    writer.write(json.toString());
                    writer.write("\n");
                    writer.flush();
                } finally {
                    writer.close();
                }
            } catch (IOException e) {
                Log.w(TAG, "removed write failed: " + e);
            }
        }
    }

    private static String resolveGroup(CharSequence conversationTitle, CharSequence subText, String titleStr) {
        if (!isEmpty(conversationTitle)) {
            return conversationTitle.toString();
        }
        if (!isEmpty(subText)) {
            return subText.toString();
        }
        int idx = titleStr.indexOf(": ");
        return idx >= 0 ? titleStr.substring(0, idx) : titleStr;
    }

    private static String resolveSender(Bundle messageBundle, String titleStr) {
        if (messageBundle != null) {
            CharSequence sender = messageBundle.getCharSequence(MESSAGE_KEY_SENDER);
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

    private static long resolveWhen(Bundle messageBundle, long notificationWhen, long postTime) {
        long when = messageBundle != null ? messageBundle.getLong(MESSAGE_KEY_TIME, 0L) : 0L;
        if (when == 0L) {
            when = notificationWhen;
        }
        if (when == 0L) {
            when = postTime;
        }
        return when;
    }

    private static int computeMessagesMaxLen(Parcelable[] messagesArr) {
        int max = 0;
        if (messagesArr == null) {
            return max;
        }
        for (Object item : messagesArr) {
            if (!(item instanceof Bundle)) {
                continue;
            }
            CharSequence text = ((Bundle) item).getCharSequence(MESSAGE_KEY_TEXT);
            if (!isEmpty(text) && text.length() > max) {
                max = text.length();
            }
        }
        return max;
    }

    /** messages[i]/bigText(候補)/text(候補) のうち最も長いものを選ぶ。 */
    private static LongestPick pickLongest(CharSequence messageText, CharSequence bigTextCandidate,
            CharSequence textCandidate, int messageIndex) {
        String best = messageText == null ? "" : messageText.toString();
        String bestSource = "messages[" + messageIndex + "]";
        if (bigTextCandidate != null && bigTextCandidate.length() > best.length()) {
            best = bigTextCandidate.toString();
            bestSource = "bigText";
        }
        if (textCandidate != null && textCandidate.length() > best.length()) {
            best = textCandidate.toString();
            bestSource = "text";
        }
        return new LongestPick(bestSource, best);
    }

    private static void cacheBigTextCandidate(String group, String sender, CharSequence text, CharSequence bigText) {
        String key = cacheKey(group, sender);
        String textStr = isEmpty(text) ? "" : text.toString();
        String bigTextStr = isEmpty(bigText) ? "" : bigText.toString();
        synchronized (BIGTEXT_CACHE_LOCK) {
            BIGTEXT_CACHE.put(key, new BigTextCandidate(textStr, bigTextStr));
        }
    }

    private static BigTextCandidate takeBigTextCandidate(String group, String sender) {
        String key = cacheKey(group, sender);
        synchronized (BIGTEXT_CACHE_LOCK) {
            return BIGTEXT_CACHE.remove(key);
        }
    }

    private static String cacheKey(String group, String sender) {
        return (group == null ? "" : group) + " " + (sender == null ? "" : sender);
    }

    private static final class BigTextCandidate {
        final String text;
        final String bigText;

        BigTextCandidate(String text, String bigText) {
            this.text = text;
            this.bigText = bigText;
        }
    }

    private static final class LongestPick {
        final String source;
        final String text;

        LongestPick(String source, String text) {
            this.source = source;
            this.text = text;
        }
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
            String titleRaw, int messagesCount, String source, long whenMs,
            int lenText, int lenBigText, int messagesMaxLen, int supersedesLen) {
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
                        whenMs, postTimeMs, lenText, lenBigText, messagesMaxLen, supersedesLen);
                appendTalkRecord(talkFile, sender, body, whenMs);
                NotifyStore.recordCapture(this, group, whenMs, storagePath);
            } catch (IOException e) {
                Log.w(TAG, "record write failed (textLen=" + body.length() + "): " + e);
            }
        }
    }

    private void appendRawRecord(File rawFile, StatusBarNotification sbn, String group, String sender,
            String body, String titleRaw, int messagesCount, String source, long whenMs, long postTimeMs,
            int lenText, int lenBigText, int messagesMaxLen, int supersedesLen) throws IOException {
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
            json.put("len_text", lenText);
            json.put("len_bigText", lenBigText);
            json.put("len_messages_max", messagesMaxLen);
            json.put("supersedesLen", supersedesLen);
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

    /**
     * 診断用JSONL(diag-YYYYMMDD.jsonl)に1件追記する。対象グループ判定・集約通知の
     * 除外より前に、jp.naver.line.androidの通知であれば全件を記録する
     * （1024字打ち切りの原因特定のための実測材料であり、絞り込みをかけると
     * 比較対象が欠けてしまうため）。
     */
    private void appendDiagRecord(StatusBarNotification sbn, Notification notification, String template,
            String titleStr, CharSequence subText, CharSequence summaryText, CharSequence conversationTitle,
            CharSequence bigText, CharSequence plainText, Parcelable[] messagesArr, int messagesCount,
            boolean interactive, boolean keyguardLocked) throws IOException {
        File dir = resolveStorageDir();
        if (dir == null) {
            Log.w(TAG, "no writable storage dir for diag record");
            return;
        }
        long postTimeMs = System.currentTimeMillis();
        String fileDateKey = new SimpleDateFormat("yyyyMMdd", Locale.JAPAN).format(new Date(postTimeMs));
        File diagFile = new File(dir, "diag-" + fileDateKey + ".jsonl");

        int lenText = isEmpty(plainText) ? 0 : plainText.length();
        int lenBigText = isEmpty(bigText) ? 0 : bigText.length();

        String longestField = "text";
        int longestLen = lenText;
        String longestText = isEmpty(plainText) ? "" : plainText.toString();
        if (lenBigText > longestLen) {
            longestField = "bigText";
            longestLen = lenBigText;
            longestText = bigText.toString();
        }

        JSONArray messagesJson = new JSONArray();
        if (messagesArr != null) {
            for (int i = 0; i < messagesArr.length; i++) {
                Object item = messagesArr[i];
                if (!(item instanceof Bundle)) {
                    continue;
                }
                Bundle messageBundle = (Bundle) item;
                CharSequence msgText = messageBundle.getCharSequence(MESSAGE_KEY_TEXT);
                CharSequence msgSender = messageBundle.getCharSequence(MESSAGE_KEY_SENDER);
                long msgTime = messageBundle.getLong(MESSAGE_KEY_TIME, 0L);
                int msgLen = isEmpty(msgText) ? 0 : msgText.length();
                try {
                    JSONObject m = new JSONObject();
                    m.put("sender", msgSender == null ? "" : msgSender.toString());
                    m.put("len", msgLen);
                    m.put("time", formatIso8601(msgTime));
                    messagesJson.put(m);
                } catch (JSONException e) {
                    throw new IOException("json build failed", e);
                }
                if (msgLen > longestLen) {
                    longestField = "messages[" + i + "]";
                    longestLen = msgLen;
                    longestText = msgText.toString();
                }
            }
        }

        JSONObject json = new JSONObject();
        try {
            json.put("postTime", formatIso8601(postTimeMs));
            json.put("key", sbn.getKey());
            json.put("id", sbn.getId());
            json.put("tag", sbn.getTag());
            json.put("template", template == null ? "" : template);
            json.put("flags", notification.flags);
            json.put("when", formatIso8601(notification.when));
            json.put("len_text", lenText);
            json.put("len_bigText", lenBigText);
            json.put("len_title", titleStr.length());
            json.put("len_subText", isEmpty(subText) ? 0 : subText.length());
            json.put("len_conversationTitle", isEmpty(conversationTitle) ? 0 : conversationTitle.length());
            json.put("len_summaryText", isEmpty(summaryText) ? 0 : summaryText.length());
            json.put("len_tickerText", isEmpty(notification.tickerText) ? 0 : notification.tickerText.length());
            json.put("messagesCount", messagesCount);
            json.put("messages", messagesJson);
            json.put("longestField", longestField);
            json.put("longestLen", longestLen);
            json.put("longestText", longestText);
            json.put("interactive", interactive);
            json.put("keyguardLocked", keyguardLocked);
            json.put("title", titleStr);
            json.put("subText", isEmpty(subText) ? "" : subText.toString());
            json.put("conversationTitle", isEmpty(conversationTitle) ? "" : conversationTitle.toString());
        } catch (JSONException e) {
            throw new IOException("json build failed", e);
        }

        synchronized (WRITE_LOCK) {
            Writer writer = new OutputStreamWriter(new FileOutputStream(diagFile, true), "UTF-8");
            try {
                writer.write(json.toString());
                writer.write("\n");
                writer.flush();
            } finally {
                writer.close();
            }
        }
    }

    private static String formatIso8601(long millis) {
        return new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssZ", Locale.JAPAN).format(new Date(millis));
    }

    private boolean isInteractive() {
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        return pm != null && pm.isInteractive();
    }

    private boolean isKeyguardLocked() {
        KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
        return km != null && km.isKeyguardLocked();
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
