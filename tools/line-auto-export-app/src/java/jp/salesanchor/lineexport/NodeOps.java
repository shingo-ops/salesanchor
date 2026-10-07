package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.graphics.Rect;
import android.util.Log;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;

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
