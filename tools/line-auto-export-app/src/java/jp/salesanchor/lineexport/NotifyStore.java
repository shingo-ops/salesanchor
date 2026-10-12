package jp.salesanchor.lineexport;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * LineNotifyListenerService の設定・状態の永続化。PinStore と同じ private
 * SharedPreferences 方式（別ファイル名）を使う。PINのような秘匿値は扱わないため
 * 平文保存でよい。
 */
final class NotifyStore {

    private static final String PREFS_NAME = "sa_line_export_notify";

    private static final String KEY_TARGET_GROUPS = "target_groups";
    private static final String KEY_RECORD_COUNT = "record_count";
    private static final String KEY_LAST_RECORD_TIME = "last_record_time";
    private static final String KEY_LAST_RECORD_GROUP = "last_record_group";
    private static final String KEY_STORAGE_PATH = "storage_path";
    private static final String KEY_LAST_TALK_HEADER_DATE = "last_talk_header_date";

    /** 既定の対象グループ（カンマ区切り）。空文字で保存すると「全グループ」を意味する。 */
    static final String DEFAULT_TARGET_GROUPS = "WeGo売ります掲示板グループ";

    private NotifyStore() {
    }

    static String getTargetGroups(Context context) {
        return prefs(context).getString(KEY_TARGET_GROUPS, DEFAULT_TARGET_GROUPS);
    }

    static void setTargetGroups(Context context, String value) {
        prefs(context).edit().putString(KEY_TARGET_GROUPS, value == null ? "" : value).apply();
    }

    static long getRecordCount(Context context) {
        return prefs(context).getLong(KEY_RECORD_COUNT, 0L);
    }

    static long getLastRecordTime(Context context) {
        return prefs(context).getLong(KEY_LAST_RECORD_TIME, 0L);
    }

    static String getLastRecordGroup(Context context) {
        return prefs(context).getString(KEY_LAST_RECORD_GROUP, "");
    }

    static String getStoragePath(Context context) {
        return prefs(context).getString(KEY_STORAGE_PATH, "");
    }

    static void setStoragePath(Context context, String path) {
        prefs(context).edit().putString(KEY_STORAGE_PATH, path == null ? "" : path).apply();
    }

    static String getLastTalkHeaderDate(Context context) {
        return prefs(context).getString(KEY_LAST_TALK_HEADER_DATE, "");
    }

    static void setLastTalkHeaderDate(Context context, String headerDate) {
        prefs(context).edit().putString(KEY_LAST_TALK_HEADER_DATE, headerDate == null ? "" : headerDate).apply();
    }

    /** 1件記録できたときにカウンタ・最終記録情報をまとめて更新する。 */
    static void recordCapture(Context context, String group, long whenMs, String storagePath) {
        SharedPreferences prefs = prefs(context);
        long count = prefs.getLong(KEY_RECORD_COUNT, 0L) + 1L;
        prefs.edit()
                .putLong(KEY_RECORD_COUNT, count)
                .putLong(KEY_LAST_RECORD_TIME, whenMs)
                .putString(KEY_LAST_RECORD_GROUP, group == null ? "" : group)
                .putString(KEY_STORAGE_PATH, storagePath == null ? "" : storagePath)
                .apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    // --- android.messages の重複排除用リングバッファ -----------------------------------
    //
    // 直近に記録した (key, time, sender) ごとの本文文字数を最大50件のリングで保持する。
    // 同一メッセージ要素が複数回の通知更新で繰り返し現れたとき、前回より短い/同じ版を
    // 再度書き込まないための重複抑止だけが目的。
    //
    // 設計メモ（design.mdには永続化方法の指定が無いための実装判断）: SharedPreferences
    // ではなくプロセス内の静的配列として保持する（永続化しない）。
    // NotificationListenerServiceが生きている間の重複抑止で十分であり、プロセスが
    // 再起動されればリングは空に戻る＝直後の通知は supersedesLen=0 として多少の
    // 重複書き込みを許容する（データが消えるより「稀に二重に残る」方が実害が小さい）。

    private static final int RECENT_RING_CAPACITY = 50;
    private static final Object RECENT_RING_LOCK = new Object();
    private static final String[] RECENT_RING_KEYS = new String[RECENT_RING_CAPACITY];
    private static final long[] RECENT_RING_TIMES = new long[RECENT_RING_CAPACITY];
    private static final String[] RECENT_RING_SENDERS = new String[RECENT_RING_CAPACITY];
    private static final int[] RECENT_RING_LENS = new int[RECENT_RING_CAPACITY];
    private static int recentRingNext = 0;
    private static int recentRingSize = 0;

    /** (key, time, sender) に対して直近に記録した本文の文字数。無ければ0。 */
    static int getRecordedLen(String key, long time, String sender) {
        synchronized (RECENT_RING_LOCK) {
            int idx = findRecentRingIndexLocked(key, time, sender);
            return idx < 0 ? 0 : RECENT_RING_LENS[idx];
        }
    }

    /** (key, time, sender) に対する記録済み文字数を更新（無ければリングへ追加、満杯なら最古を上書き）する。 */
    static void recordLen(String key, long time, String sender, int len) {
        synchronized (RECENT_RING_LOCK) {
            int idx = findRecentRingIndexLocked(key, time, sender);
            if (idx >= 0) {
                RECENT_RING_LENS[idx] = len;
                return;
            }
            idx = recentRingNext;
            RECENT_RING_KEYS[idx] = key;
            RECENT_RING_TIMES[idx] = time;
            RECENT_RING_SENDERS[idx] = sender;
            RECENT_RING_LENS[idx] = len;
            recentRingNext = (recentRingNext + 1) % RECENT_RING_CAPACITY;
            if (recentRingSize < RECENT_RING_CAPACITY) {
                recentRingSize++;
            }
        }
    }

    private static int findRecentRingIndexLocked(String key, long time, String sender) {
        for (int i = 0; i < recentRingSize; i++) {
            if (RECENT_RING_TIMES[i] == time
                    && equalsNullable(RECENT_RING_KEYS[i], key)
                    && equalsNullable(RECENT_RING_SENDERS[i], sender)) {
                return i;
            }
        }
        return -1;
    }

    private static boolean equalsNullable(String a, String b) {
        return a == null ? b == null : a.equals(b);
    }
}
