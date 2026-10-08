package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.graphics.Point;
import android.os.Handler;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityNodeInfo;

/**
 * 段階2の実行主体。LINE操作（ホーム→ショートカット→Menu→設定→トーク履歴を送信→Termux→EDIT）を
 * 手順表（docs/handoff/line-auto-export-app/design.md「追補 2026-10-08」）どおりに実行する
 * 状態機械。AccessibilityServiceのコールバックはメインスレッドで動くため、
 * Handler#postDelayedの連鎖のみで実装し、Thread.sleepは一切使わない
 * （UnlockAccessibilityServiceと同じ作法）。
 *
 * LINEのメッセージ本文・ノードのテキストは通知にもログにも一切出さない。
 * 期待グループ名と実際のノードの一致/不一致だけを扱う（値そのものは出さない）。
 */
final class LineExportFlow {

    // ---- ラベル定数。ADB版 /root/line-auto-export/flow.sh の該当行と同一にする -------------

    /** flow.sh:52 `tap_by 'text="WeGo売ります・BOX'`（ホームのショートカット名、前方一致）。 */
    private static final String SHORTCUT_TEXT_PREFIX = "WeGo売ります・BOX";
    /** flow.sh:54 `tap_by 'content-desc="Menu ボタン"'`。 */
    private static final String MENU_BUTTON_DESC = "Menu ボタン";
    /** flow.sh:57 `find_scroll 'text="設定"'`。 */
    private static final String SETTINGS_LABEL = "設定";
    /** flow.sh:60 `find_scroll 'text="トーク履歴を送信"'`。 */
    private static final String EXPORT_ITEM_LABEL = "トーク履歴を送信";
    /** flow.sh:64 `grep -q 'text="Termux"'`。 */
    private static final String TERMUX_LABEL = "Termux";
    /** auto-export.sh:154 `focus | grep -q TermuxFileReceiverActivity`。 */
    private static final String TERMUX_EDIT_CLASS_NAME = "TermuxFileReceiverActivity";
    /**
     * LINEのパッケージ名。LineNotifyListenerService.java:53 の `PACKAGE_LINE` と同じ値
     * （同サービスが対象にしているLINEの会話通知のパッケージ）。手順3の到達判定に使う。
     */
    private static final String LINE_PACKAGE_NAME = "jp.naver.line.android";

    // ---- 段階名。ADB版 flow.sh の step= と同じ語にする（auto-export.logの失敗履歴と比較できるように） ----

    private static final String STAGE_SHORTCUT = "shortcut";
    private static final String STAGE_OPEN_CHAT = "open_chat";
    private static final String STAGE_GROUP_MISMATCH = "group_mismatch";
    private static final String STAGE_MENU_BUTTON = "menu_button";
    /**
     * open_menu/open_settingsは、アプリ経路では到達不能（2026-10-08実機2回目の設計ミス修正。
     * design.md追補参照）: 到達判定（ノード待ち）をスクロール探索と別手順に分けていたため、
     * 画面外（ノードツリーに載らない）にある項目では判定だけが先に10秒でタイムアウトして
     * いた。到達判定は廃止し、スクロール探索（settings_item/export_item）に統合したため、
     * この2段階名は実際には発生しない。ADB版flow.shのstep=語と揃える方針の記録として、
     * 定数自体は残す。
     */
    private static final String STAGE_OPEN_MENU = "open_menu";
    private static final String STAGE_SETTINGS_ITEM = "settings_item";
    private static final String STAGE_OPEN_SETTINGS = "open_settings";
    private static final String STAGE_EXPORT_ITEM = "export_item";
    private static final String STAGE_SHARE_SHEET = "share_sheet";
    private static final String STAGE_TERMUX_TARGET = "termux_target";
    private static final String STAGE_EDIT_BUTTON = "edit_button";

    // ---- 待ち時間（ADB版と同値に揃える。design.md追補の「待ち時間」節） --------------------

    /** flow.sh:51 `input keyevent KEYCODE_HOME; sleep 1.5` と同値。 */
    private static final long HOME_SETTLE_DELAY_MS = 1500L;
    /** ノード待ちのポーリング間隔。flow.shのwait_focus（20回×0.5秒=10秒）と同じ予算で300ms刻みにする。 */
    private static final long NODE_WAIT_POLL_MS = 300L;
    private static final long NODE_WAIT_TIMEOUT_MS = 10000L;
    /** スクロール再探索は最大4回（flow.sh:26-36のfind_scroll。初回探索+再探索4回=合計5回）。 */
    private static final int SCROLL_MAX_RETRIES = 4;
    /** find_scroll内のsleep 1（flow.sh:29）と同値。スクロール直後の安定待ち。 */
    private static final long SCROLL_SETTLE_DELAY_MS = 1000L;
    /** flow.sh:31 `input swipe 540 1700 540 1100 800` と同じ比率・時間。 */
    private static final float SCROLL_SWIPE_FROM_Y_RATIO = 0.7265f;
    private static final float SCROLL_SWIPE_TO_Y_RATIO = 0.4701f;
    private static final long SCROLL_SWIPE_DURATION_MS = 800L;
    /**
     * 手順11（EDIT）: Termuxの保存画面のクラス名を待つ上限。auto-export.sh:154の
     * `seq 1 10`×`sleep 0.5`＝5秒と同値（design.md追補の修正後の値）。
     */
    private static final long EDIT_CLASS_WAIT_TIMEOUT_MS = 5000L;
    /** auto-export.sh:156 `sleep 1`と同値。クラス名検出後、タップするまでの落ち着き待ち。 */
    private static final long EDIT_TAP_SETTLE_DELAY_MS = 1000L;
    /** auto-export.sh:157 `EDIT_X=872, EDIT_Y=1237`（画面1080x2340）を比率に換算した値。 */
    private static final float EDIT_TAP_X_RATIO = 0.8074f;
    private static final float EDIT_TAP_Y_RATIO = 0.5287f;

    /**
     * AccessibilityService.GLOBAL_ACTION_LOCK_SCREEN の値。API28で追加された定数で、
     * ビルド環境のandroid.jarはAPI23のためコンパイル時に参照できない（実機はAndroid16
     * のため実行時には存在する）。GestureCompatのようなリフレクションは不要: 定数の
     * 「値」が無いだけで、呼び出すメソッド本体のperformGlobalAction(int)自体はAPI16から
     * 存在するため、定数値だけを直書きする（design.md 段階3「アプリ側: 実行後の
     * 再ロック」の先取り。根拠は別worktree docs/handoff/line-auto-export-runtime/
     * design-app-trigger.mdだがこのworktreeからは見えないため、依頼文の指示を正本とする）。
     */
    private static final int GLOBAL_ACTION_LOCK_SCREEN = 8;

    private static final int NOTIFICATION_ID_EXPORT = 1003;

    /** 完了時にUnlockAccessibilityServiceへ戻すためのコールバック（exportRunningフラグの解除用）。 */
    interface Listener {
        void onFinished();
    }

    private final UnlockAccessibilityService service;
    private final boolean lockOnFinish;
    private final Listener listener;
    private final Handler handler = new Handler();

    private long flowStartedAt;
    private long stepStartedAt;
    private StringBuilder stepTimings;
    private String expectedGroup;
    private AccessibilityNodeInfo termuxNode;

    /**
     * lockOnFinishはRUN_ALL（ロック解除→LINE操作）のときだけtrueにする。EXPORT単体
     * （すでに解除して使っている状態での検証用）では施錠しない。成功・失敗どちらの
     * 終了でも、trueなら最後に画面を施錠する（旧ADB方式のKEYCODE_HOME→KEYCODE_SLEEPに
     * 相当。解除したまま放置するのを避けるため、失敗で中止したときも施錠する）。
     */
    LineExportFlow(UnlockAccessibilityService service, boolean lockOnFinish, Listener listener) {
        this.service = service;
        this.lockOnFinish = lockOnFinish;
        this.listener = listener;
    }

    void start() {
        flowStartedAt = System.currentTimeMillis();
        stepStartedAt = flowStartedAt;
        stepTimings = new StringBuilder();
        expectedGroup = firstTargetGroup(NotifyStore.getTargetGroups(service));

        // フロー実行中のみウィンドウ遷移のクラス名・パッケージ名を記録する（終了時にクリア）。
        service.startWindowRecording();

        service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_HOME);
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                step2ClickShortcut();
            }
        }, HOME_SETTLE_DELAY_MS);
    }

    // ---- 手順2: ショートカットをクリック --------------------------------------------------

    private void step2ClickShortcut() {
        AccessibilityNodeInfo node = NodeOps.findByTextPrefix(service, SHORTCUT_TEXT_PREFIX);
        if (node == null) {
            recordStep(STAGE_SHORTCUT);
            finish(false, STAGE_SHORTCUT);
            return;
        }
        NodeOps.ClickResult result = NodeOps.clickNode(service, node);
        recordStep(STAGE_SHORTCUT);
        if (!result.accepted) {
            finish(false, STAGE_SHORTCUT);
            return;
        }
        step3WaitLineOpen();
    }

    // ---- 手順3: トーク画面（LINE）の到達判定 ------------------------------------------------
    //
    // アクティブウィンドウのパッケージ名がLINE_PACKAGE_NAMEになるまで300ms間隔・期限10秒で
    // ポーリングする（design.md修正後）。期限切れ＝ショートカットのタップが空振りして
    // ランチャーのままだったとみなし、open_chatとして中止する。

    private void step3WaitLineOpen() {
        waitForPackage(LINE_PACKAGE_NAME, STAGE_OPEN_CHAT, System.currentTimeMillis() + NODE_WAIT_TIMEOUT_MS,
                new PackageWaitCallback() {
                    @Override
                    public void onFound() {
                        step3bWaitExpectedGroup();
                    }
                });
    }

    // ---- 手順3b: 誤爆防止（期待グループ名確認） ---------------------------------------------
    //
    // LINEは開いたことを手順3で確認済みのうえで、期待グループ名のノードを300ms間隔・
    // 期限10秒で待つ。期限切れ＝LINEは開いたが別のトークだったとみなし、group_mismatch
    // として中止する（Menu以降へは進まない）。
    //
    // NodeOps.findGroupNameNode（完全一致ではなく正規化＋双方向部分一致）を使う。実機の
    // トーク画面タイトルは「WeGo売リ... (480)」のように省略され末尾に人数が付くため
    // （2026-10-08実機1回目の不具合2）、他の手順（設定/トーク履歴を送信など）が使う
    // findNodeByLabel（完全一致、ロック解除側も使っているため変更不可）とは別の探索にする。

    private void step3bWaitExpectedGroup() {
        waitForGroupNode(expectedGroup, STAGE_GROUP_MISMATCH, System.currentTimeMillis() + NODE_WAIT_TIMEOUT_MS,
                new NodeWaitCallback() {
                    @Override
                    public void onFound(AccessibilityNodeInfo node) {
                        step4ClickMenuButton();
                    }
                });
    }

    // ---- 手順4: Menuボタン -----------------------------------------------------------------

    private void step4ClickMenuButton() {
        AccessibilityNodeInfo node = NodeOps.findByDescExact(service, MENU_BUTTON_DESC);
        if (node == null) {
            recordStep(STAGE_MENU_BUTTON);
            finish(false, STAGE_MENU_BUTTON);
            return;
        }
        NodeOps.ClickResult result = NodeOps.clickNode(service, node);
        recordStep(STAGE_MENU_BUTTON);
        if (!result.accepted) {
            finish(false, STAGE_MENU_BUTTON);
            return;
        }
        // 手順5（open_menuの到達判定を別手順として持つ形）は廃止した（design.md追補
        // 2026-10-08「実機2回目」参照）。メニューは縦に長く、「設定」が初期表示より
        // 下にあることがある。アクセシビリティのノードツリーには画面外の項目が
        // 載らないため、判定（ノード待ち）とスクロール探索を別手順に分けると、
        // スクロールする前に判定だけが10秒でタイムアウトする（判定と探索の
        // 二重化という設計ミスだった）。1秒の落ち着き待ちのあと、即時探索＋
        // スクロール再探索（最大4回）をscrollFindAndClickにまとめて行わせる。
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                step6ClickSettings();
            }
        }, SCROLL_SETTLE_DELAY_MS);
    }

    // ---- 手順6: 「設定」をクリック（即時探索＋スクロール再探索、最大4回） ---------------------

    private void step6ClickSettings() {
        scrollFindAndClick(SETTINGS_LABEL, 0, STAGE_SETTINGS_ITEM, new StepCallback() {
            @Override
            public void onSuccess() {
                // 手順7（open_settingsの到達判定）も同じ理由で廃止（上記参照）。
                // 1秒の落ち着き待ちのあと、スクロール探索してクリックへ進む。
                handler.postDelayed(new Runnable() {
                    @Override
                    public void run() {
                        step8ClickExportItem();
                    }
                }, SCROLL_SETTLE_DELAY_MS);
            }

            @Override
            public void onFailure() {
                finish(false, STAGE_SETTINGS_ITEM);
            }
        });
    }

    // ---- 手順8: 「トーク履歴を送信」をクリック（即時探索＋スクロール再探索、最大4回） -----------

    private void step8ClickExportItem() {
        scrollFindAndClick(EXPORT_ITEM_LABEL, 0, STAGE_EXPORT_ITEM, new StepCallback() {
            @Override
            public void onSuccess() {
                step9WaitShareSheet();
            }

            @Override
            public void onFailure() {
                finish(false, STAGE_EXPORT_ITEM);
            }
        });
    }

    // ---- 手順9: 共有シート到達判定（見つかったノードは手順10でそのままクリックする） -----------

    private void step9WaitShareSheet() {
        waitForNode(TERMUX_LABEL, STAGE_SHARE_SHEET, System.currentTimeMillis() + NODE_WAIT_TIMEOUT_MS,
                new NodeWaitCallback() {
                    @Override
                    public void onFound(AccessibilityNodeInfo node) {
                        termuxNode = node;
                        step10ClickTermux();
                    }
                });
    }

    // ---- 手順10: 「Termux」をクリック -------------------------------------------------------

    private void step10ClickTermux() {
        if (termuxNode == null) {
            recordStep(STAGE_TERMUX_TARGET);
            finish(false, STAGE_TERMUX_TARGET);
            return;
        }
        NodeOps.ClickResult result = NodeOps.clickNode(service, termuxNode);
        recordStep(STAGE_TERMUX_TARGET);
        if (!result.accepted) {
            finish(false, STAGE_TERMUX_TARGET);
            return;
        }
        step11WaitEditClassThenTap();
    }

    // ---- 手順11: EDITを座標タップ -----------------------------------------------------------
    //
    // Termuxの保存ダイアログはノードに露出しないため座標タップにする（ADB版auto-export.sh:
    // 157のEDIT_X/EDIT_Yと同じ脆さ）。TermuxFileReceiverActivityのクラス名検出は
    // onAccessibilityEventの記録（診断用）を使うだけで、判定の本筋（タップするか否か）には
    // 使わない＝検出できてもできなくても最終的にはタップする。

    private void step11WaitEditClassThenTap() {
        pollEditClass(System.currentTimeMillis() + EDIT_CLASS_WAIT_TIMEOUT_MS);
    }

    private void pollEditClass(final long deadlineAt) {
        String className = service.getLastWindowClassName();
        boolean detected = className != null && className.contains(TERMUX_EDIT_CLASS_NAME);
        if (detected) {
            // auto-export.sh:156 の `sleep 1` と同値。検出してからタップまでの落ち着き待ち。
            handler.postDelayed(new Runnable() {
                @Override
                public void run() {
                    tapEditButton(true);
                }
            }, EDIT_TAP_SETTLE_DELAY_MS);
            return;
        }
        if (System.currentTimeMillis() >= deadlineAt) {
            // 5秒で検出できなくてもタップは行う（ADB版auto-export.sh:155はここで失敗扱いだが、
            // このダイアログはそもそもノードに露出しないため、アプリ側はクラス名が読めない
            // ことを失敗とみなさない。診断にeditクラス未検出を残すだけ）。
            tapEditButton(false);
            return;
        }
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                pollEditClass(deadlineAt);
            }
        }, NODE_WAIT_POLL_MS);
    }

    private void tapEditButton(boolean classDetected) {
        Point size = getScreenSize();
        GestureCompat.DispatchReport report = GestureCompat.tap(
                service, size.x * EDIT_TAP_X_RATIO, size.y * EDIT_TAP_Y_RATIO, 80L, "edit");
        recordStep(STAGE_EDIT_BUTTON, (classDetected ? "" : "editクラス未検出 ") + report.describe());
        if (!report.accepted) {
            finish(false, STAGE_EDIT_BUTTON);
            return;
        }
        // 手順12（後片付け）は何もしない。ADB版のBACK×3（flow.sh:75-78）は本番では実行されて
        // いない: auto-export.sh:143が`flow.sh 1 keep`と呼び、flow.sh:73の`keep`分岐が
        // 後片付けの手前でexit 0する。本番はEDITタップ後、outbox.sqlite3の送信結果を最大240秒
        // 待ってからHOME+SLEEPする（auto-export.sh:159-170）。EDITタップ直後にBACKを撃つと
        // Termuxの保存ダイアログを取り消し、取り込みが行われない恐れがあるため、段階2では
        // 画面をそのまま残して終了する。HOME・再ロックは段階3の範囲。
        finish(true, null);
    }

    // ---- 共通: 期待パッケージのウィンドウが現れるのを待つ（300ms間隔・期限10秒） -------------------

    private interface PackageWaitCallback {
        void onFound();
    }

    private void waitForPackage(final String packageName, final String stage, final long deadlineAt,
            final PackageWaitCallback callback) {
        if (NodeOps.hasWindowWithPackage(service, packageName)) {
            recordStep(stage);
            callback.onFound();
            return;
        }
        if (System.currentTimeMillis() >= deadlineAt) {
            // open_chat失敗時の診断: 実際に見えていたパッケージ名のみ（重複除去・最大3件）。
            // ノードのテキストやメッセージ本文は含めない（2026-10-08実機1回目の不具合3）。
            String seenPackages = NodeOps.distinctWindowPackageNames(service);
            recordStep(stage, "見えていたパッケージ: " + seenPackages);
            finish(false, stage);
            return;
        }
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                waitForPackage(packageName, stage, deadlineAt, callback);
            }
        }, NODE_WAIT_POLL_MS);
    }

    // ---- 共通: ノード待ち（300ms間隔・期限10秒） ----------------------------------------------

    private interface NodeWaitCallback {
        void onFound(AccessibilityNodeInfo node);
    }

    private void waitForNode(final String label, final String stage, final long deadlineAt,
            final NodeWaitCallback callback) {
        AccessibilityNodeInfo node = NodeOps.findNodeByLabel(service, label);
        if (node != null) {
            recordStep(stage);
            callback.onFound(node);
            return;
        }
        if (System.currentTimeMillis() >= deadlineAt) {
            recordStep(stage);
            finish(false, stage);
            return;
        }
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                waitForNode(label, stage, deadlineAt, callback);
            }
        }, NODE_WAIT_POLL_MS);
    }

    // ---- 共通: グループ名ノード待ち（正規化＋双方向部分一致、300ms間隔・期限10秒） ----------------

    private void waitForGroupNode(final String expectedGroup, final String stage, final long deadlineAt,
            final NodeWaitCallback callback) {
        AccessibilityNodeInfo node = NodeOps.findGroupNameNode(service, expectedGroup);
        if (node != null) {
            recordStep(stage);
            callback.onFound(node);
            return;
        }
        if (System.currentTimeMillis() >= deadlineAt) {
            recordStep(stage);
            finish(false, stage);
            return;
        }
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                waitForGroupNode(expectedGroup, stage, deadlineAt, callback);
            }
        }, NODE_WAIT_POLL_MS);
    }

    // ---- 共通: 見つからなければスクロールして再探索（最大4回） ----------------------------------

    private interface StepCallback {
        void onSuccess();

        void onFailure();
    }

    private void scrollFindAndClick(final String label, final int attempt, final String stage,
            final StepCallback callback) {
        AccessibilityNodeInfo node = NodeOps.findNodeByLabel(service, label);
        if (node != null) {
            NodeOps.ClickResult result = NodeOps.clickNode(service, node);
            recordStep(stage);
            if (result.accepted) {
                callback.onSuccess();
            } else {
                callback.onFailure();
            }
            return;
        }
        if (attempt >= SCROLL_MAX_RETRIES) {
            recordStep(stage);
            callback.onFailure();
            return;
        }
        scrollOnce();
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                scrollFindAndClick(label, attempt + 1, stage, callback);
            }
        }, SCROLL_SETTLE_DELAY_MS);
    }

    /** ACTION_SCROLL_FORWARDを先に試し、スクロール可能なノードが無ければswipeへフォールバックする。 */
    private void scrollOnce() {
        AccessibilityNodeInfo scrollable = NodeOps.findScrollable(service);
        boolean scrolled = scrollable != null
                && scrollable.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD);
        if (!scrolled) {
            Point size = getScreenSize();
            GestureCompat.swipe(service, size.x * 0.5f, size.y * SCROLL_SWIPE_FROM_Y_RATIO,
                    size.x * 0.5f, size.y * SCROLL_SWIPE_TO_Y_RATIO, SCROLL_SWIPE_DURATION_MS, "scroll");
        }
    }

    // ---- 終了処理・通知 ------------------------------------------------------------------

    private void recordStep(String stepName) {
        recordStep(stepName, null);
    }

    private void recordStep(String stepName, String extra) {
        long now = System.currentTimeMillis();
        long ms = now - stepStartedAt;
        stepStartedAt = now;
        stepTimings.append(stepName).append(':').append(ms).append("ms");
        if (extra != null && extra.length() > 0) {
            stepTimings.append('(').append(extra).append(')');
        }
        stepTimings.append(' ');
    }

    private void finish(boolean success, String failedStage) {
        // stopWindowRecording()は履歴をクリアするため、読むのはその前に行う（診断用。
        // クラス名のみでパッケージ名・ノードのテキスト・メッセージ本文は含まない）。
        String recentClasses = success ? "" : service.recentWindowClassNames();
        service.stopWindowRecording();
        long elapsed = System.currentTimeMillis() - flowStartedAt;
        String title = success ? "書き出し: 成功" : "書き出し: 失敗";
        String stagePart = success ? "" : ("段階: " + failedStage + " / ");
        String body = stagePart + elapsed + "ms / " + stepTimings.toString().trim();
        if (!success && recentClasses.length() > 0) {
            // 2026-10-08実機2回目の追補: TYPE_WINDOW_STATE_CHANGEDのクラス名がこの端末で
            // 実際に取れるかの実測も兼ねる。取れることが分かれば、将来ADB版と同じ粒度の
            // 到達判定に戻せる。
            body += " / 最近のクラス名: " + recentClasses;
        }
        if (lockOnFinish) {
            // RUN_ALLのときだけ施錠する（EXPORT単体は検証用で解除状態を保つ）。送信結果は
            // 待たない（Termux側は画面と無関係に送信を続けるため）。成功時はEDITタップ完了
            // 直後にここへ到達し、失敗で中止した場合も（解除したまま放置するのを避けるため）
            // 同じくここで施錠する。施錠の成否はflow全体の成否(success)には影響させない。
            boolean locked = service.performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN);
            body += " / 施錠:" + locked;
        }
        postResultNotification(service, title, body);
        if (listener != null) {
            listener.onFinished();
        }
    }

    /** 対象グループ名設定（カンマ区切り）の先頭要素。空ならNotifyStoreの既定値を使う。 */
    private static String firstTargetGroup(String raw) {
        if (raw != null) {
            String[] parts = raw.split(",");
            for (String part : parts) {
                String trimmed = part.trim();
                if (trimmed.length() > 0) {
                    return trimmed;
                }
            }
        }
        return NotifyStore.DEFAULT_TARGET_GROUPS;
    }

    /** UnlockAccessibilityService#getScreenSizeと同じ考え方（getRealSizeで実画面サイズを取る）。 */
    @SuppressWarnings("deprecation")
    private Point getScreenSize() {
        Point size = new Point();
        WindowManager wm = (WindowManager) service.getSystemService(Context.WINDOW_SERVICE);
        if (wm != null) {
            wm.getDefaultDisplay().getRealSize(size);
        }
        return size;
    }

    /**
     * 既存postNotificationと同じ作法（BigTextStyleで展開時に全文表示）。通知IDは既存
     * （1001/1002）とは別の新しいID（NOTIFICATION_ID_EXPORT）にして取りこぼさないようにする。
     */
    private static void postResultNotification(Context context, String title, String body) {
        NotificationCompat.ensureChannel(context, UnlockAccessibilityService.CHANNEL_ID, "SA LINE Export");
        Notification.Builder builder = NotificationCompat.newBuilder(context, UnlockAccessibilityService.CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new Notification.BigTextStyle().bigText(body))
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true);
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID_EXPORT, builder.build());
        }
    }
}
