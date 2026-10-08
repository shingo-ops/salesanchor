package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.graphics.Rect;
import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

import java.util.LinkedHashSet;
import java.util.List;

/**
 * ノード検索・クリックの共通処理。元はUnlockAccessibilityService（段階1・ロック解除）に
 * あった findNodeByLabel/searchNode/matchesLabel/clickNode をそのまま移し、
 * AccessibilityServiceを引数で受ける形にしただけ（挙動は変えていない純粋な移動。
 * design.md「追補 2026-10-08」参照）。LineExportFlow（段階2・LINE操作）からも
 * 同じ探索ロジックを使うための共通化。
 */
final class NodeOps {

    private static final String TAG = "SALineExport";

    private NodeOps() {
    }

    /** clickNodeの結果。traceMessageはbounds中心へのgestureタップにフォールバックした場合のみ
     * 非null（元のUnlockAccessibilityService#clickNodeがtraceAppendしていた内容と同じ）。
     * 呼び出し側でtraceAppend等に渡して既存の記録内容を保つ。 */
    static final class ClickResult {
        final boolean accepted;
        final String traceMessage;

        ClickResult(boolean accepted, String traceMessage) {
            this.accepted = accepted;
            this.traceMessage = traceMessage;
        }
    }

    /** text または content-desc の完全一致でノードを探す（全ウィンドウ横断、無ければアクティブウィンドウ）。 */
    static AccessibilityNodeInfo findNodeByLabel(AccessibilityService service, String label) {
        try {
            List<AccessibilityWindowInfo> windows = service.getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    AccessibilityNodeInfo root = window.getRoot();
                    AccessibilityNodeInfo match = searchNode(root, label);
                    if (match != null) {
                        return match;
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        return searchNode(service.getRootInActiveWindow(), label);
    }

    /** joinDistinctPackageNames等と同じ上限（UnlockAccessibilityService#DIAG_MAX_PACKAGES_PER_DISPLAYと同値）。 */
    private static final int MAX_DISTINCT_PACKAGES = 3;

    /**
     * 期待パッケージのウィンドウが1つでもあるか。LineExportFlowの手順3（トーク画面=LINEの
     * 到達判定）が、ショートカットのタップが空振りしてランチャーに留まった場合（open_chat）と、
     * LINEは開いたが別グループだった場合（group_mismatch）を区別するために使う。
     *
     * 2026-10-08実機1回目の不具合1（design.md追補参照）: 以前はgetWindows()の「先頭」の
     * ウィンドウのrootのパッケージ名だけを見ていたため、ステータスバー等(com.android.systemui)
     * を拾って誤判定し、画面上はLINEが開いているのにopen_chatでタイムアウトした。
     * 「先頭だけ見る」のをやめ、全ウィンドウのいずれかが期待パッケージかを判定する形にする
     * （見つからなければgetRootInActiveWindow()のパッケージ名でもフォールバック判定）。
     * 後段（findGroupNameNode）でグループ名を照合するため、ここを緩めても誤爆防止は損なわれない。
     */
    static boolean hasWindowWithPackage(AccessibilityService service, String packageName) {
        try {
            List<AccessibilityWindowInfo> windows = service.getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    AccessibilityNodeInfo root = window.getRoot();
                    CharSequence pkg = root != null ? root.getPackageName() : null;
                    if (pkg != null && packageName.contentEquals(pkg)) {
                        return true;
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        AccessibilityNodeInfo root = service.getRootInActiveWindow();
        CharSequence pkg = root != null ? root.getPackageName() : null;
        return pkg != null && packageName.contentEquals(pkg);
    }

    /**
     * 実際に見えていたウィンドウのパッケージ名（重複除去・最大3件、カンマ区切り）。
     * open_chat失敗時の診断用。UnlockAccessibilityService#joinDistinctPackageNamesと同じ
     * ロジック（重複除去＋上限3件）をgetWindows()横断で行う。パッケージ名のみを返し、
     * ノードのテキストやメッセージ本文は一切含まない。
     */
    static String distinctWindowPackageNames(AccessibilityService service) {
        LinkedHashSet<String> pkgs = new LinkedHashSet<String>();
        try {
            List<AccessibilityWindowInfo> windows = service.getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    if (pkgs.size() >= MAX_DISTINCT_PACKAGES) {
                        break;
                    }
                    AccessibilityNodeInfo root = window.getRoot();
                    CharSequence pkg = root != null ? root.getPackageName() : null;
                    if (pkg != null) {
                        pkgs.add(pkg.toString());
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        if (pkgs.isEmpty()) {
            AccessibilityNodeInfo root = service.getRootInActiveWindow();
            CharSequence pkg = root != null ? root.getPackageName() : null;
            if (pkg != null) {
                pkgs.add(pkg.toString());
            }
        }
        StringBuilder sb = new StringBuilder();
        for (String pkg : pkgs) {
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(pkg);
        }
        return sb.toString();
    }

    static AccessibilityNodeInfo searchNode(AccessibilityNodeInfo node, String label) {
        if (node == null) {
            return null;
        }
        if (matchesLabel(node, label)) {
            return node;
        }
        int count = node.getChildCount();
        for (int i = 0; i < count; i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            AccessibilityNodeInfo match = searchNode(child, label);
            if (match != null) {
                return match;
            }
        }
        return null;
    }

    static boolean matchesLabel(AccessibilityNodeInfo node, String label) {
        CharSequence text = node.getText();
        CharSequence desc = node.getContentDescription();
        return (text != null && label.contentEquals(text))
                || (desc != null && label.contentEquals(desc));
    }

    /**
     * テキストがprefixで始まるノードを探す（前方一致）。ホームのショートカット名の判定に使う
     * （ADB版 /root/line-auto-export/flow.sh:52 の tap_by 'text="WeGo売ります・BOX' が前方一致のため）。
     * findAccessibilityNodeInfosByText は部分一致・大文字小文字無視で挙動が広すぎるため使わず、
     * 既存の再帰探索と同じ形で実装する。
     */
    static AccessibilityNodeInfo findByTextPrefix(AccessibilityService service, String prefix) {
        try {
            List<AccessibilityWindowInfo> windows = service.getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    AccessibilityNodeInfo match = searchNodeByTextPrefix(window.getRoot(), prefix);
                    if (match != null) {
                        return match;
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        return searchNodeByTextPrefix(service.getRootInActiveWindow(), prefix);
    }

    private static AccessibilityNodeInfo searchNodeByTextPrefix(AccessibilityNodeInfo node, String prefix) {
        if (node == null) {
            return null;
        }
        CharSequence text = node.getText();
        if (text != null && text.toString().startsWith(prefix)) {
            return node;
        }
        int count = node.getChildCount();
        for (int i = 0; i < count; i++) {
            AccessibilityNodeInfo match = searchNodeByTextPrefix(node.getChild(i), prefix);
            if (match != null) {
                return match;
            }
        }
        return null;
    }

    /**
     * content-desc の完全一致でノードを探す（Menuボタンの判定に使う。ADB版flow.sh:54の
     * tap_by 'content-desc="Menu ボタン"' と同じ条件）。
     */
    static AccessibilityNodeInfo findByDescExact(AccessibilityService service, String desc) {
        try {
            List<AccessibilityWindowInfo> windows = service.getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    AccessibilityNodeInfo match = searchNodeByDescExact(window.getRoot(), desc);
                    if (match != null) {
                        return match;
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        return searchNodeByDescExact(service.getRootInActiveWindow(), desc);
    }

    private static AccessibilityNodeInfo searchNodeByDescExact(AccessibilityNodeInfo node, String desc) {
        if (node == null) {
            return null;
        }
        CharSequence nodeDesc = node.getContentDescription();
        if (nodeDesc != null && desc.contentEquals(nodeDesc)) {
            return node;
        }
        int count = node.getChildCount();
        for (int i = 0; i < count; i++) {
            AccessibilityNodeInfo match = searchNodeByDescExact(node.getChild(i), desc);
            if (match != null) {
                return match;
            }
        }
        return null;
    }

    /**
     * isScrollable() なノードを探す（祖先・子孫を区別せず木全体を探索。スクロール操作用）。
     * ADB版flow.sh:31の `input swipe` の代わりに、まずACTION_SCROLL_FORWARDを試すために使う。
     */
    static AccessibilityNodeInfo findScrollable(AccessibilityService service) {
        try {
            List<AccessibilityWindowInfo> windows = service.getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    AccessibilityNodeInfo match = searchScrollable(window.getRoot());
                    if (match != null) {
                        return match;
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        return searchScrollable(service.getRootInActiveWindow());
    }

    private static AccessibilityNodeInfo searchScrollable(AccessibilityNodeInfo node) {
        if (node == null) {
            return null;
        }
        if (node.isScrollable()) {
            return node;
        }
        int count = node.getChildCount();
        for (int i = 0; i < count; i++) {
            AccessibilityNodeInfo match = searchScrollable(node.getChild(i));
            if (match != null) {
                return match;
            }
        }
        return null;
    }

    /** グループ名の比較に使う文字列として短すぎる場合は一致とみなさない（誤爆防止）。 */
    private static final int MIN_GROUP_LABEL_LENGTH = 6;

    /**
     * 期待グループ名のノードを探す（LineExportFlowの手順3bの誤爆防止用）。既存の完全一致探索
     * （findNodeByLabel/searchNode/matchesLabel、ロック解除側が使っている）は変えず、グループ
     * 名照合専用にこのメソッドを別途用意する。
     *
     * 2026-10-08実機1回目の不具合2（design.md追補参照）: 実機のトーク画面タイトルは
     * 「WeGo売リ... (480)」のように途中で省略され末尾に人数が付くため、完全一致では
     * 期待値「WeGo売ります掲示板グループ」と一致しない。正規化（末尾の(数字)・省略記号
     * （…/...）・前後の空白を落とす）してから双方向の部分一致で判定する。
     * 比較に使う文字列（正規化後のノード側・期待値側のどちらも）が6文字未満なら一致と
     * みなさない（短い文字列どうしの部分一致は誤爆防止が骨抜きになるため）。
     */
    static AccessibilityNodeInfo findGroupNameNode(AccessibilityService service, String expectedGroup) {
        String normalizedExpected = normalizeGroupLabel(expectedGroup);
        try {
            List<AccessibilityWindowInfo> windows = service.getWindows();
            if (windows != null) {
                for (AccessibilityWindowInfo window : windows) {
                    AccessibilityNodeInfo match = searchGroupLabel(window.getRoot(), normalizedExpected);
                    if (match != null) {
                        return match;
                    }
                }
            }
        } catch (RuntimeException e) {
            Log.w(TAG, "getWindows() failed: " + e);
        }
        return searchGroupLabel(service.getRootInActiveWindow(), normalizedExpected);
    }

    private static AccessibilityNodeInfo searchGroupLabel(AccessibilityNodeInfo node, String normalizedExpected) {
        if (node == null) {
            return null;
        }
        if (matchesGroupLabel(node, normalizedExpected)) {
            return node;
        }
        int count = node.getChildCount();
        for (int i = 0; i < count; i++) {
            AccessibilityNodeInfo match = searchGroupLabel(node.getChild(i), normalizedExpected);
            if (match != null) {
                return match;
            }
        }
        return null;
    }

    private static boolean matchesGroupLabel(AccessibilityNodeInfo node, String normalizedExpected) {
        return matchesGroupText(node.getText(), normalizedExpected)
                || matchesGroupText(node.getContentDescription(), normalizedExpected);
    }

    private static boolean matchesGroupText(CharSequence raw, String normalizedExpected) {
        if (raw == null || normalizedExpected.length() < MIN_GROUP_LABEL_LENGTH) {
            return false;
        }
        String normalizedNode = normalizeGroupLabel(raw.toString());
        if (normalizedNode.length() < MIN_GROUP_LABEL_LENGTH) {
            return false;
        }
        return normalizedNode.contains(normalizedExpected) || normalizedExpected.contains(normalizedNode);
    }

    /**
     * グループ名の末尾の `(数字)`・省略記号（`…`/`...`）・前後の空白を落として正規化する。
     * 例: "WeGo売リ... (480)" -> "WeGo売リ"。
     */
    static String normalizeGroupLabel(String raw) {
        if (raw == null) {
            return "";
        }
        String s = raw.trim();
        s = s.replaceAll("\\s*\\(\\d+\\)\\s*$", "");
        s = s.trim();
        while (s.endsWith("...") || s.endsWith("…")) {
            s = s.endsWith("...") ? s.substring(0, s.length() - 3) : s.substring(0, s.length() - 1);
            s = s.trim();
        }
        return s;
    }

    /**
     * ノードをクリックする。クリック可能な祖先を遡って見つかればACTION_CLICKを委譲し、
     * 見つからなければそのノード自身のbounds中心へGestureCompat.tapでフォールバックする
     * （元のUnlockAccessibilityService#clickNodeと同じフォールバック順）。
     */
    static ClickResult clickNode(AccessibilityService service, AccessibilityNodeInfo node) {
        AccessibilityNodeInfo target = node;
        while (target != null && !target.isClickable()) {
            target = target.getParent();
        }
        if (target != null) {
            return new ClickResult(target.performAction(AccessibilityNodeInfo.ACTION_CLICK), null);
        }
        // クリック可能な祖先が無い場合は、そのノード自身の座標へgestureタップ。
        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        if (!bounds.isEmpty()) {
            GestureCompat.DispatchReport report = GestureCompat.tap(
                    service, bounds.exactCenterX(), bounds.exactCenterY(), 80L, "node-tap");
            return new ClickResult(report.accepted, report.describe());
        }
        return new ClickResult(false, null);
    }
}
