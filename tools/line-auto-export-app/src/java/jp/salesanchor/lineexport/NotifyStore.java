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
}
