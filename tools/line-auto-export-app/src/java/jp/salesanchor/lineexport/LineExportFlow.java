package jp.salesanchor.lineexport;

import android.accessibilityservice.AccessibilityService;
import android.app.Notification;
import android.app.NotificationManager;
import android.content.Context;
import android.graphics.Point;
import android.os.Handler;
import android.os.PowerManager;
import android.os.SystemClock;
import android.util.Log;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.Iterator;

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

    private static final String TAG = "SALineExport";

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
     * Termuxの保存ダイアログのEDITボタンのテキスト（design.md追補 2026-10-11、2026-10-11実機
     * uiautomator dumpで確認。`[Button] text="EDIT" clickable=true`）。
     */
    private static final String EDIT_BUTTON_LABEL = "EDIT";
    /**
     * TermuxのパッケージID。EDITボタン探索（NodeOps.findNodeByTextInPackage）でLINE側の
     * 別ノードに誤って一致しないようにするための必須条件（design.md追補 2026-10-11）。
     */
    private static final String TERMUX_PACKAGE_NAME = "com.termux";
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
    /**
     * design.md追補 2026-10-11: EDITを押した後、ダイアログ（EDITノード）がEDIT_CLOSE_TIMEOUT_MS
     * 経っても消えなかった（＝押せていない明確な証拠がある）場合の失敗段階名。
     */
    private static final String STAGE_EDIT_NOT_CLOSED = "edit_not_closed";
    /**
     * design.md追補 2026-10-11「EDITの準備完了判定をノード探索に移し、配信確認の条件を正す」:
     * 遮断モード（{@code overlayBlocking==true}）で、EDIT_CLASS_WAIT_TIMEOUT_MS経っても
     * EDITノードが見つからなかった場合の失敗段階名。遮断中は座標タップが吸われ配信されない
     * ことが実機で確定しているため（06:30・06:32・09:13）、比率座標タップへは落とさず
     * この段階で失敗にする。
     */
    private static final String STAGE_EDIT_NODE_NOT_FOUND = "edit_node_not_found";

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
     * EDITを押した後、ダイアログが閉じた（＝配信された）ことを確認するためのポーリング間隔／
     * 上限（design.md追補 2026-10-11）。dispatchGestureもACTION_CLICKも「押した」ことしか
     * 保証しないため、ダイアログが消えたことで配信を確認する。
     */
    private static final long EDIT_CLOSE_POLL_MS = 150L;
    private static final long EDIT_CLOSE_TIMEOUT_MS = 3000L;

    // ---- edit_buttonのstepログに記録するeditClickPathの値（design.md追補 2026-10-11） -----

    /** NodeOps.findNodeByTextInPackageでノードが見つかり、ACTION_CLICKで押せた。 */
    private static final String EDIT_CLICK_PATH_NODE_ACTION = "node-action";
    /** ノードは見つかったがACTION_CLICKが使えず、ノード領域の中心を座標タップした。 */
    private static final String EDIT_CLICK_PATH_NODE_BOUNDS_TAP = "node-bounds-tap";
    /** ノードが見つからず、従来の比率座標タップをした（フォールバック）。 */
    private static final String EDIT_CLICK_PATH_RATIO_TAP = "ratio-tap";

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

    /**
     * 施錠(performGlobalAction)前に待つ時間。2026-10-08実機（0.3.0-stage2）で発生した
     * 不具合の対策: GestureCompat.tapのdispatchGestureは非同期で、戻り値trueは「OSが
     * 受理した」だけで「指の動きの再生が終わった」ではない（タップ自体は80ms）。EDITタップ
     * 直後に施錠すると、再生が終わる前に画面がロックされてジェスチャが取り消され、Termuxの
     * 保存ダイアログのEDITが押されずに残ったまま施錠される（実機で確認、送信が止まった）。
     * 80msのタップ再生に加え、Termuxの保存ダイアログがタップを処理して次の画面へ進む余裕を
     * 見て2秒。失敗で中止した経路（ジェスチャを出していない場合もある）と区別すると実装が
     * 複雑になるため、安全側に倒してlockOnFinishの全経路で一律この時間だけ待ってから施錠する
     * （成功例の合図からreceived okまでの所要は40秒前後であり、2秒の追加は全体への影響が
     * 無視できる）。
     */
    private static final long LOCK_DELAY_AFTER_EDIT_MS = 2000L;

    /**
     * ウェイクロックのタグ。UnlockAccessibilityServiceの"SALineExport:unlock"と区別する。
     */
    private static final String WAKE_LOCK_TAG = "SALineExport:export";

    /**
     * なぜLineExportFlow自身がウェイクロックを持つ必要があるか（2026-10-08実機、
     * design.md追補「実機で動いたが挙動が診断できない」の調査結果、PO承認済み）:
     * UnlockAccessibilityService#checkResult()はLINE操作が始まる前にロック解除フロー用の
     * ウェイクロックを無条件にreleaseWakeLock()しており、LineExportFlowはそれまで
     * 自前のウェイクロックを一切持っていなかった。ADB版（flow.sh）の`input`コマンドは
     * 画面の消灯タイマーをリセットする効果を持つが、アクセシビリティ経由の操作
     * （performAction(ACTION_CLICK)、特にGestureCompatのdispatchGestureベースのタップ・
     * スワイプ）にはその効果が無く、操作中に画面が暗転しうる。暗転するとノード検索が
     * 失敗し続け、何かの契機（端末側の挙動）で再び点くまで数十秒単位で足止めされる
     * （実機でsettings_item 48秒・edit_button 56秒を観測。設計値どおりならどちらも
     * 5〜6秒で収まるはずで、説明がつかない差分だった）。ADB版でこの症状が一度も
     * 出ていないのは、まさに`input`コマンドが画面を保っていたため。
     * このウェイクロックで画面が消灯しないようにし、ADB版の`input`が代わりに
     * 果たしていた役割をアプリ側でも持たせる。
     */
    private static final long WAKE_LOCK_SAFETY_TIMEOUT_MS = 120000L;

    private static final int NOTIFICATION_ID_EXPORT = 1003;

    /** 完了時にUnlockAccessibilityServiceへ戻すためのコールバック（exportRunningフラグの解除用）。 */
    interface Listener {
        void onFinished();
    }

    private final UnlockAccessibilityService service;
    private final boolean lockOnFinish;
    private final boolean armRetryOnFailure;
    private final String triggerLabel;
    private final Listener listener;
    private final Handler handler = new Handler();

    private PowerManager.WakeLock wakeLock;

    private long flowStartedAt;
    private long flowStartedAtUptime;
    private long stepStartedAt;
    private long stepStartedAtUptime;
    private StringBuilder stepTimings;
    private JSONArray stepTimingsJson;
    private String expectedGroup;
    private AccessibilityNodeInfo termuxNode;
    private String runId;
    private MainThreadStallWatchdog stallWatchdog;

    /**
     * design.md追補「実行中の表示」(2026-10-09, PO決定・案1): 自動操作中であることを画面上部の
     * 帯（バナー）で示す補助表示。show/removeの成否(overlayShown/overlayRemoved)は実行ログに
     * 記録するが、失敗してもフロー自体の成否・制御フローには一切影響させない
     * （NodeOps側の窓除外と合わせてdesign.md追補参照）。
     */
    private final RunStatusOverlay overlay = new RunStatusOverlay();
    private boolean overlayShown;
    private boolean overlayRemoved;

    /**
     * 遮断モードの帯を出すかどうか。design.md追補 2026-10-11「遮断モードの帯（検証用）」で
     * 検証用のone-shotフラグ経由として導入し、同日の追補「遮断モードを常時有効にし、再試行を
     * 3回にする（PO決定）」で本番常時有効化した: {@code armRetryOnFailure}の値をそのまま
     * {@code blocking}として渡す。armRetryOnFailure==true（本番実行、RUN_ALL経由）なら
     * 遮断モード、armRetryOnFailure==false（EXPORT単体・手動検証）なら従来の非遮断の細い帯
     * になる（診断のため非遮断の経路を残す）。
     *
     * armRetryOnFailureを再利用する理由: 「本番実行かどうか」を示す既存のフラグが
     * armRetryOnFailureであり（lockOnFinishは「使用中に起動したら施錠しない」という別の
     * 意味を持つため使えない。コンストラクタのjavadoc参照）、新しいフラグを増やさずに
     * 済ませられる。
     */
    private boolean overlayBlocking;

    /**
     * design.md追補 2026-10-11「遮断モードを常時有効にし、再試行を3回にする（PO決定）」の
     * 検知項目: 遮断モードが有効（{@code overlayBlocking==true}）な間に、座標ベースの
     * ジェスチャ（{@link GestureCompat#tap}/{@link GestureCompat#swipe}）を呼んだら
     * trueにする。少なくとも次の3か所で立てる: EDITの比率座標タップ
     * （{@code editClickPath==}{@link #EDIT_CLICK_PATH_RATIO_TAP}の経路）、
     * {@link NodeOps#clickNode}がノード領域の中心を座標タップした経路
     * （{@code editClickPath==}{@link #EDIT_CLICK_PATH_NODE_BOUNDS_TAP}）、
     * スクロールの座標スワイプ（{@code scrollMode=="gesture"}になる経路）。
     *
     * 座標スワイプが遮断中に通るかは未確定（2026-10-11の遮断4回は{@code scrollMode:"gesture"}
     * で成功したが、スクロールが実際に必要だったか（＝通ったから成功したのか、たまたま
     * ノード探索が試行内で目標を見つけただけなのか）を区別できていない）。先に記録を取り、
     * {@code blockedCoordinateGesture:true}の回に段階失敗が集まるかを見てから判断する
     * （PO決定・この依頼の範囲では座標ジェスチャを止めたり失敗にしたりしない。記録専用）。
     */
    private boolean blockedCoordinateGesture;

    // 計測専用フィールド（design.md追補 2026-10-08「遅い回の原因確定のための計測追加」）。
    // 挙動には一切使わない。診断ログにのみ出す。

    // ウェイクロックの実効性。取得直後にisHeld()を確認(wakeAcquired)し、取得時刻を覚えて
    // おき、フロー終了時に経過(wakeHeldMs)と、その時点でまだ保持できているか
    // (wakeHeldAtEnd、安全タイムアウト120秒で勝手に解放されていないか)を見る。
    private boolean wakeAcquired;
    private long wakeAcquiredAt = -1L;

    // 手順11（EDIT）の内訳。すべて実時間（ms）。
    private long editClassWaitStartedAt;
    private int editClassPolls;
    private boolean editClassDetected;
    private long editClassWaitMs = -1L;
    private long editSettleMs = -1L;
    private long editTapMs = -1L;
    /**
     * design.md追補 2026-10-11「EDITの準備完了判定をノード探索に移し、配信確認の条件を正す」:
     * 準備完了の判定本体。classDetected/classPolls/classWaitMs（TYPE_WINDOW_STATE_CHANGED
     * 由来）は診断用としてそのまま残すが、判定には使わない。2026-10-11 09:13に
     * classDetected=falseで盲目タップ（比率座標タップ）に落ち配信できなかったため、
     * 判定はNodeOps.findNodeByTextInPackageによるEDITノード探索に移した。
     */
    private int editNodePolls;
    /** EDITノードが見つかるまでのms。見つからなければ-1Lのまま（ログには出さない）。 */
    private long editNodeWaitMs = -1L;
    /**
     * EDIT_CLASS_WAIT_TIMEOUT_MSの期限までにEDITノードが見つかったか（＝押す前にノードが
     * 実在したか）。waitForEditDialogClosedで配信確認の前提として使う（この値がfalseの回は
     * 比率座標タップへフォールバックした非遮断の経路のみ）。
     */
    private boolean editNodeWasFound;
    // design.md追補 2026-10-11: どの経路でEDITを押したか（EDIT_CLICK_PATH_*のいずれか）と、
    // 押した後にダイアログが消えたことを確認できたか・消えるまでのms。
    private String editClickPath;
    private boolean editDialogClosed;
    private long editCloseWaitMs = -1L;
    /**
     * design.md追補 2026-10-11「EDITの準備完了判定をノード探索に移し、配信確認の条件を正す」:
     * 配信を確認できたか（null=未確認）。editNodeWasFound==falseの経路では配信を確認した
     * と主張しない（editDialogClosedは出さずfalseを記録する）。
     */
    private Boolean editVerified;
    // 施錠前の待ち（LOCK_DELAY_AFTER_EDIT_MS）の実測。手順11自体の内訳ではないが、
    // 依頼文の分類に合わせてEDIT関連として記録する。
    private long editLockDelayMs = -1L;

    /**
     * lockOnFinishとarmRetryOnFailureは別の意味を持つ（design.md追補 2026-10-10
     * 「使用中に起動した回は施錠しない」で分離。UnlockAccessibilityService#startExportFlow
     * のjavadoc参照）。
     *
     * lockOnFinish: 終了時に画面を施錠するか。trueなら最後に画面を施錠する（旧ADB方式の
     * KEYCODE_HOME→KEYCODE_SLEEPに相当。解除したまま放置するのを避けるため、失敗で中止
     * したときも施錠する）。falseになるのは2つの場合がある: ①EXPORT単体（手動検証用、
     * すでに解除して使っている状態での検証）②開始時に既に解除済みだった（＝利用者が使用中に
     * 起動した）本番実行（使用中に画面が消えて操作を妨げるのを避けるため施錠しない）。
     *
     * armRetryOnFailure: 失敗時にRunScheduler.scheduleRetryAfterFailureを張るか
     * （本番実行＝RUN_ALL経由かどうかの印。①のEXPORT単体ではfalse、②の「使用中に起動」と
     * checkResult()の解除成功後の続行ではtrue）。lockOnFinishだけで本番実行かどうかを
     * 判定していると、①②の両方がlockOnFinish=falseになったときに再試行が退行するため、
     * 分けてある。
     *
     * triggerLabelは結果通知の本文に「引き金:」として残す診断用（design.md追補
     * 2026-10-08「段階3の方式変更」）。
     */
    LineExportFlow(UnlockAccessibilityService service, boolean lockOnFinish, boolean armRetryOnFailure,
            String triggerLabel, Listener listener) {
        this.service = service;
        this.lockOnFinish = lockOnFinish;
        this.armRetryOnFailure = armRetryOnFailure;
        this.triggerLabel = triggerLabel == null ? "" : triggerLabel;
        this.listener = listener;
    }

    void start() {
        flowStartedAt = System.currentTimeMillis();
        flowStartedAtUptime = SystemClock.uptimeMillis();
        stepStartedAt = flowStartedAt;
        stepStartedAtUptime = flowStartedAtUptime;
        stepTimings = new StringBuilder();
        stepTimingsJson = new JSONArray();
        expectedGroup = firstTargetGroup(NotifyStore.getTargetGroups(service));

        // 実行ログの開始行。終了まで到達しなかった実行もこの行だけは残るよう、他のどの処理
        // よりも前に書く（design.md追補「実機で動いたが挙動が診断できない」対策）。
        runId = RunLogger.newRunId();
        RunLogger.logStart(service, runId, "export", triggerLabel);

        // メインスレッドの遅延を別スレッドから見張る診断（design.md追補「原因究明のための
        // 診断追加」。動作は変えない）。フロー内のすべてのhandler.postDelayed待ちをschedule()
        // 経由で登録する。finish()で必ずstop()する（リーク防止）。
        stallWatchdog = new MainThreadStallWatchdog(service, runId, "export", triggerLabel);
        stallWatchdog.start();

        // アクセシビリティ操作は画面の消灯タイマーをリセットしないため、フロー中は画面を
        // 保つ（WAKE_LOCK_TAGの定数コメント参照）。解放はfinish()で、施錠まで終えてから行う。
        acquireWakeLock();

        // 自動取り込み中バナーを表示する（design.md追補「実行中の表示」参照）。表示に失敗しても
        // フローは継続する（補助表示のみ）。design.md追補 2026-10-11「遮断モードを常時有効に
        // し、再試行を3回にする（PO決定）」: armRetryOnFailureの値をそのまま遮断モードの
        // on/offとして使う。本番実行（RUN_ALL経由、armRetryOnFailure==true）は遮断モード、
        // EXPORT単体（手動検証、armRetryOnFailure==false）は従来の非遮断の細い帯になる
        // （診断のため非遮断の経路を残す）。
        //
        // この帯はLineExportFlow（書き出しフェーズ）だけで出す。UnlockAccessibilityService
        // （ロック解除フェーズ、PIN入力）側には広げない: PIN入力は座標タップ（dispatchGesture）
        // で行っており、座標タップは遮断モードの帯に吸われる（design.md追補 2026-10-11
        // 「EDITをノードクリックにし…」の「ノードクリックが使えると分かった意味」節。
        // ノードクリックは帯を素通りするが座標タップは吸われることを実機で確認済み）。
        // PIN入力の画面にはクリック可能なノードが無く座標タップしか手段が無いため、帯を
        // 広げるとPIN入力そのものが吸われて解除できなくなる。
        overlayBlocking = armRetryOnFailure;
        overlayShown = overlay.show(service, overlayBlocking);

        // フロー実行中のみウィンドウ遷移のクラス名・パッケージ名を記録する（終了時にクリア）。
        service.startWindowRecording();

        service.performGlobalAction(AccessibilityService.GLOBAL_ACTION_HOME);
        schedule("homeSettle", HOME_SETTLE_DELAY_MS, new Runnable() {
            @Override
            public void run() {
                step2ClickShortcut();
            }
        });
    }

    /**
     * handler.postDelayedのラッパー。遅延・ラベルをMainThreadStallWatchdogへ登録し、
     * 発火時に解除する（design.md追補「原因究明のための診断追加」）。postDelayed自体の
     * 遅延値・実行されるrunnableの内容は一切変えない。診断専用で挙動には影響しない。
     */
    private void schedule(final String label, final long delayMs, final Runnable runnable) {
        if (stallWatchdog != null) {
            stallWatchdog.registerWait(label, delayMs);
        }
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (stallWatchdog != null) {
                    stallWatchdog.unregisterWait(label);
                }
                runnable.run();
            }
        }, delayMs);
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
        schedule("settle:" + STAGE_SETTINGS_ITEM, SCROLL_SETTLE_DELAY_MS, new Runnable() {
            @Override
            public void run() {
                step6ClickSettings();
            }
        });
    }

    // ---- 手順6: 「設定」をクリック（即時探索＋スクロール再探索、最大4回） ---------------------

    private void step6ClickSettings() {
        scrollFindAndClick(SETTINGS_LABEL, 0, STAGE_SETTINGS_ITEM, new StepCallback() {
            @Override
            public void onSuccess() {
                // 手順7（open_settingsの到達判定）も同じ理由で廃止（上記参照）。
                // 1秒の落ち着き待ちのあと、スクロール探索してクリックへ進む。
                schedule("settle:" + STAGE_EXPORT_ITEM, SCROLL_SETTLE_DELAY_MS, new Runnable() {
                    @Override
                    public void run() {
                        step8ClickExportItem();
                    }
                });
            }

            @Override
            public void onFailure() {
                finish(false, STAGE_SETTINGS_ITEM);
            }
        }, new ScrollStats());
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
        }, new ScrollStats());
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

    // ---- 手順11: EDITを押す（準備完了の判定はEDITノードの探索） -----------------------------
    //
    // design.md追補 2026-10-11「EDITの準備完了判定をノード探索に移し、配信確認の条件を正す」:
    // 準備完了の判定本体はNodeOps.findNodeByTextInPackageによるEDITノード探索にする
    // （NODE_WAIT_POLL_MS間隔・EDIT_CLASS_WAIT_TIMEOUT_MS期限、値は変更していない）。
    // TYPE_WINDOW_STATE_CHANGED由来のクラス名検出（classDetected/classPolls/classWaitMs）は
    // 診断用としてそのまま残すが、判定には使わない。2026-10-11 09:13にclassDetected=falseで
    // 盲目的な比率座標タップに落ち、遮断モードで座標タップが吸われて配信できなかったため。

    private void step11WaitEditClassThenTap() {
        editClassWaitStartedAt = System.currentTimeMillis();
        editClassPolls = 0;
        editNodePolls = 0;
        pollEditClass(editClassWaitStartedAt + EDIT_CLASS_WAIT_TIMEOUT_MS);
    }

    private void pollEditClass(final long deadlineAt) {
        editClassPolls++;
        editNodePolls++;

        // 診断専用（判定には使わない。上記コメント参照）。
        if (!editClassDetected) {
            String className = service.getLastWindowClassName();
            if (className != null && className.contains(TERMUX_EDIT_CLASS_NAME)) {
                editClassDetected = true;
                editClassWaitMs = System.currentTimeMillis() - editClassWaitStartedAt;
            }
        }

        // 判定本体: EDITノードが見つかるか。
        AccessibilityNodeInfo editNode = NodeOps.findNodeByTextInPackage(
                service, EDIT_BUTTON_LABEL, TERMUX_PACKAGE_NAME);
        if (editNode != null) {
            editNodeWasFound = true;
            editNodeWaitMs = System.currentTimeMillis() - editClassWaitStartedAt;
            final long settleStartedAt = System.currentTimeMillis();
            // auto-export.sh:156 の `sleep 1` と同値。見つかってからタップまでの落ち着き待ち。
            schedule("editSettle", EDIT_TAP_SETTLE_DELAY_MS, new Runnable() {
                @Override
                public void run() {
                    editSettleMs = System.currentTimeMillis() - settleStartedAt;
                    tapEditButton();
                }
            });
            return;
        }
        if (System.currentTimeMillis() >= deadlineAt) {
            editNodeWasFound = false;
            if (!editClassDetected) {
                // 最後までクラス名を検出できなかった回の診断値（既存と同じ記録方法）。
                editClassWaitMs = System.currentTimeMillis() - editClassWaitStartedAt;
            }
            if (overlayBlocking) {
                // design.md追補 2026-10-11: 遮断モードでは座標タップが吸われ配信されないことが
                // 実機で確定している（06:30・06:32・09:13）。見つからないまま比率座標タップへ
                // 落とすと09:13の再発になるため、ここで失敗にする。scheduleRetryAfterFailureが
                // 自動で張られ、合計3回まで試される。
                recordStep(STAGE_EDIT_NODE_NOT_FOUND, null, buildEditStageExtraFields());
                finish(false, STAGE_EDIT_NODE_NOT_FOUND);
                return;
            }
            // 非遮断（EXPORT単体の手動検証）は従来どおり比率座標タップへフォールバックする
            // （tapEditButton内でEDITノードが見つからなければEDIT_CLICK_PATH_RATIO_TAPになる）。
            editSettleMs = 0L; // この経路では落ち着き待ちを取っていない。
            tapEditButton();
            return;
        }
        schedule("classPoll", NODE_WAIT_POLL_MS, new Runnable() {
            @Override
            public void run() {
                pollEditClass(deadlineAt);
            }
        });
    }

    /**
     * design.md追補 2026-10-11「EDITをノードクリックにし、配信をダイアログの消滅で確認する」:
     * まずNodeOps.findNodeByTextInPackageでEDITボタンのノード（text完全一致＋パッケージ名が
     * com.termux）を探し、見つかればNodeOps.clickNodeで押す（クリック可能な祖先が無ければ
     * ノード領域の中心への座標タップへフォールバック）。ノードが見つからなければ、従来の
     * 比率座標タップ（EDIT_TAP_X_RATIO/EDIT_TAP_Y_RATIO、値は変更していない）をそのまま行う。
     * どの経路を使ったかはeditClickPathに記録する。
     */
    private void tapEditButton() {
        long tapStartedAt = System.currentTimeMillis();
        AccessibilityNodeInfo editNode = NodeOps.findNodeByTextInPackage(
                service, EDIT_BUTTON_LABEL, TERMUX_PACKAGE_NAME);
        boolean accepted;
        String traceMessage;
        if (editNode != null) {
            NodeOps.ClickResult result = NodeOps.clickNode(service, editNode);
            accepted = result.accepted;
            traceMessage = result.traceMessage;
            editClickPath = result.viaAction ? EDIT_CLICK_PATH_NODE_ACTION : EDIT_CLICK_PATH_NODE_BOUNDS_TAP;
            if (!result.viaAction && overlayBlocking) {
                // design.md追補 2026-10-11「遮断モードを常時有効にし…」の検知項目:
                // NodeOps.clickNodeがノード領域の中心を座標タップ（GestureCompat.tap）に
                // フォールバックした経路。記録のみ、挙動は変えない（blockedCoordinateGesture
                // のjavadoc参照）。
                blockedCoordinateGesture = true;
            }
        } else {
            Point size = getScreenSize();
            GestureCompat.DispatchReport report = GestureCompat.tap(
                    service, size.x * EDIT_TAP_X_RATIO, size.y * EDIT_TAP_Y_RATIO, 80L, "edit");
            accepted = report.accepted;
            traceMessage = report.describe();
            editClickPath = EDIT_CLICK_PATH_RATIO_TAP;
            if (overlayBlocking) {
                // design.md追補 2026-10-11「遮断モードを常時有効にし…」の検知項目:
                // EDITの比率座標タップ（フォールバック経路）。記録のみ、挙動は変えない。
                blockedCoordinateGesture = true;
            }
        }
        editTapMs = System.currentTimeMillis() - tapStartedAt;
        String classNote = editClassDetected ? "" : "editクラス未検出 ";
        String stepExtra = classNote + (traceMessage != null ? traceMessage : "");
        if (!accepted) {
            recordStep(STAGE_EDIT_BUTTON, stepExtra, buildEditStageExtraFields());
            finish(false, STAGE_EDIT_BUTTON);
            return;
        }
        // 押せた（OSが受理した）だけでは配信されたとは言えないため、ダイアログが実際に
        // 消えたことを確認してから成功と判定する（waitForEditDialogClosed参照）。
        // recordStep(STAGE_EDIT_BUTTON, ...)はこの確認結果とあわせて1回だけ呼ぶ。
        waitForEditDialogClosed(System.currentTimeMillis(), stepExtra);
    }

    /**
     * design.md追補 2026-10-11「EDITの準備完了判定をノード探索に移し、配信確認の条件を正す」:
     * EDITを押した直後から、EDIT_CLOSE_POLL_MS間隔・EDIT_CLOSE_TIMEOUT_MSを上限に、EDITの
     * ノード（手順1と同じNodeOps.findNodeByTextInPackage）が消えたかを見る。dispatchGestureも
     * ACTION_CLICKも「押した」ことしか保証しないため、ダイアログが消えたことで配信を確認する。
     *
     * ただし、この判定は押す前に一度もノードが見つかっていない（editNodeWasFound==false、
     * 比率座標タップへフォールバックした非遮断の経路のみ）場合は意味を持たない。2026-10-11
     * 09:13の実機で、ノードが一度も見つかっていないのに「消えた＝配信された」と誤判定し、
     * successとして記録された（実際はファイルが届いていなかった）。そのため editNodeWasFound
     * で前提を分ける: ノードが実在した回だけ消滅確認を信じ、そうでない回は配信を確認したと
     * 主張しない（editVerified:falseを記録する。詳細は下の分岐参照）。
     *
     * editNodeWasFound==trueの経路: ノードが見つからなければ「消えた＝成功」とする（安全側）。
     * 探索が例外で失敗した場合も「押せていない明確な証拠」ではないため成功扱いにする
     * （既存の挙動を壊さないため。失敗にするのは「EDITのノードがまだ存在する」という明確な
     * 未押下の証拠があるときだけ）。3,000ms経ってもノードが残っていたときだけedit_not_closed
     * として失敗にする（これによりarmRetryOnFailureの経路でscheduleRetryAfterFailureが自動で
     * 張られ、次回で取り戻せる）。
     */
    private void waitForEditDialogClosed(final long startedAt, final String stepExtra) {
        if (!editNodeWasFound) {
            // design.md追補 2026-10-11: 押す前にEDITノードが一度も見つかっていない
            // （＝比率座標タップへフォールバックした非遮断の経路）ため、ノードの消滅で配信を
            // 確認したとは主張しない。editDialogClosedは出さずeditVerified:falseを記録する。
            // 挙動は従来どおり成功として終える: この経路は手動検証（EXPORT単体、
            // overlayBlocking==false）専用で、座標タップが歴史的に効いていたため、今まで
            // 通っていた回を失敗に変えない（依頼文の判断どおり）。
            editVerified = Boolean.FALSE;
            recordStep(STAGE_EDIT_BUTTON, stepExtra, buildEditStageExtraFields());
            finish(true, null);
            return;
        }
        boolean stillOpen;
        try {
            stillOpen = NodeOps.findNodeByTextInPackage(service, EDIT_BUTTON_LABEL, TERMUX_PACKAGE_NAME) != null;
        } catch (RuntimeException e) {
            Log.w(TAG, "edit dialog close check failed: " + e);
            stillOpen = false;
        }
        if (!stillOpen) {
            editDialogClosed = true;
            editVerified = Boolean.TRUE;
            editCloseWaitMs = System.currentTimeMillis() - startedAt;
            recordStep(STAGE_EDIT_BUTTON, stepExtra, buildEditStageExtraFields());
            // 手順12（後片付け）は何もしない。ADB版のBACK×3（flow.sh:75-78）は本番では実行されて
            // いない: auto-export.sh:143が`flow.sh 1 keep`と呼び、flow.sh:73の`keep`分岐が
            // 後片付けの手前でexit 0する。本番はEDITタップ後、outbox.sqlite3の送信結果を最大240秒
            // 待ってからHOME+SLEEPする（auto-export.sh:159-170）。EDITタップ直後にBACKを撃つと
            // Termuxの保存ダイアログを取り消し、取り込みが行われない恐れがあるため、段階2では
            // 画面をそのまま残して終了する。HOME・再ロックは段階3の範囲。
            finish(true, null);
            return;
        }
        if (System.currentTimeMillis() - startedAt >= EDIT_CLOSE_TIMEOUT_MS) {
            editDialogClosed = false;
            editVerified = Boolean.FALSE;
            editCloseWaitMs = System.currentTimeMillis() - startedAt;
            recordStep(STAGE_EDIT_NOT_CLOSED, stepExtra, buildEditStageExtraFields());
            finish(false, STAGE_EDIT_NOT_CLOSED);
            return;
        }
        schedule("editCloseWait", EDIT_CLOSE_POLL_MS, new Runnable() {
            @Override
            public void run() {
                waitForEditDialogClosed(startedAt, stepExtra);
            }
        });
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
        schedule("nodeWait:" + stage, NODE_WAIT_POLL_MS, new Runnable() {
            @Override
            public void run() {
                waitForPackage(packageName, stage, deadlineAt, callback);
            }
        });
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
        schedule("nodeWait:" + stage, NODE_WAIT_POLL_MS, new Runnable() {
            @Override
            public void run() {
                waitForNode(label, stage, deadlineAt, callback);
            }
        });
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
        schedule("nodeWait:" + stage, NODE_WAIT_POLL_MS, new Runnable() {
            @Override
            public void run() {
                waitForGroupNode(expectedGroup, stage, deadlineAt, callback);
            }
        });
    }

    // ---- 共通: 見つからなければスクロールして再探索（最大4回） ----------------------------------

    private interface StepCallback {
        void onSuccess();

        void onFailure();
    }

    /**
     * scrollFindAndClickの1呼び出し（settings_item/export_itemそれぞれ1個ずつ、別々に
     * 新規作成して渡す）の内訳。診断ログ専用で挙動には使わない
     * （design.md追補「遅い回の原因確定のための計測追加」）。
     */
    private static final class ScrollStats {
        int attempts;
        int scrolls;
        long searchMsMax;
        long searchMsTotal;
        /** 最後に行ったスクロールの方式。"node"=ACTION_SCROLL_FORWARDが成功、
         * "gesture"=swipeへフォールバック、"none"=一度もスクロールしていない（即時発見）。 */
        String scrollMode = "none";

        JSONObject toJson() {
            JSONObject o = new JSONObject();
            try {
                o.put("attempts", attempts);
                o.put("scrolls", scrolls);
                o.put("searchMsMax", searchMsMax);
                o.put("searchMsTotal", searchMsTotal);
                o.put("scrollMode", scrollMode);
            } catch (JSONException e) {
                Log.w(TAG, "scroll stats json build failed: " + e);
            }
            return o;
        }
    }

    private void scrollFindAndClick(final String label, final int attempt, final String stage,
            final StepCallback callback, final ScrollStats stats) {
        stats.attempts++;
        // ノード探索1回の所要ms（NodeOps.findNodeByLabel呼び出しの前後だけを挟んで測る。
        // findScrollable()はスクロール発生時のみの別の探索なのでここには含めない）。
        long searchStartedAt = System.currentTimeMillis();
        AccessibilityNodeInfo node = NodeOps.findNodeByLabel(service, label);
        long searchMs = System.currentTimeMillis() - searchStartedAt;
        stats.searchMsTotal += searchMs;
        if (searchMs > stats.searchMsMax) {
            stats.searchMsMax = searchMs;
        }

        if (node != null) {
            NodeOps.ClickResult result = NodeOps.clickNode(service, node);
            recordStep(stage, null, stats.toJson());
            if (result.accepted) {
                callback.onSuccess();
            } else {
                callback.onFailure();
            }
            return;
        }
        if (attempt >= SCROLL_MAX_RETRIES) {
            recordStep(stage, null, stats.toJson());
            callback.onFailure();
            return;
        }
        stats.scrolls++;
        stats.scrollMode = scrollOnce();
        schedule("scrollSettle:" + stage, SCROLL_SETTLE_DELAY_MS, new Runnable() {
            @Override
            public void run() {
                scrollFindAndClick(label, attempt + 1, stage, callback, stats);
            }
        });
    }

    /**
     * ACTION_SCROLL_FORWARDを先に試し、スクロール可能なノードが無ければswipeへフォールバック
     * する。戻り値は診断用（"node"/"gesture"）。
     */
    private String scrollOnce() {
        AccessibilityNodeInfo scrollable = NodeOps.findScrollable(service);
        boolean scrolled = scrollable != null
                && scrollable.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD);
        if (!scrolled) {
            Point size = getScreenSize();
            GestureCompat.swipe(service, size.x * 0.5f, size.y * SCROLL_SWIPE_FROM_Y_RATIO,
                    size.x * 0.5f, size.y * SCROLL_SWIPE_TO_Y_RATIO, SCROLL_SWIPE_DURATION_MS, "scroll");
            if (overlayBlocking) {
                // design.md追補 2026-10-11「遮断モードを常時有効にし…」の検知項目:
                // スクロールの座標スワイプ（GestureCompat.swipe）。記録のみ、挙動は変えない
                // （座標スワイプが遮断中に通るかは未確定。blockedCoordinateGestureのjavadoc
                // 参照）。
                blockedCoordinateGesture = true;
            }
            return "gesture";
        }
        return "node";
    }

    /**
     * 手順11（EDIT）の内訳をedit_buttonのstepTimingsJsonエントリに混ぜ込む
     * extraFieldsを組み立てる（design.md追補「遅い回の原因確定のための計測追加」）。
     * lockDelayMsはここでは分からない（施錠前の待ちはfinish()の中、recordStepより後に
     * 起きるため）ので、logExportEndの側で別途トップレベルに載せる。
     */
    private JSONObject buildEditStageExtraFields() {
        JSONObject o = new JSONObject();
        try {
            // 診断用。判定には使わない（classDetectedのjavadoc参照）。
            o.put("classDetected", editClassDetected);
            o.put("classPolls", editClassPolls);
            o.put("classWaitMs", editClassWaitMs);
            // design.md追補 2026-10-11「EDITの準備完了判定をノード探索に移し…」: 判定本体。
            o.put("editNodePolls", editNodePolls);
            // 見つからなければフィールド自体を出さない（editNodeWaitMsは未設定のまま-1L）。
            if (editNodeWaitMs >= 0) {
                o.put("editNodeWaitMs", editNodeWaitMs);
            }
            o.put("settleMs", editSettleMs);
            o.put("tapMs", editTapMs);
            // design.md追補 2026-10-11: どの経路でEDITを押したか。edit_node_not_foundの段階
            // （タップ自体を行っていない）ではnullのまま出さない。
            o.put("editClickPath", editClickPath);
            // ダイアログの消滅確認はaccepted==trueのときだけ行うため、未確認（押下自体が
            // 失敗した回・edit_node_not_foundの回）はeditCloseWaitMsが-1Lのままになり、その
            // 場合は出さない。editNodeWasFound==falseの経路（比率座標タップへフォールバック
            // した非遮断の経路）は配信を確認したと主張しないため、editDialogClosedはここでも
            // 出さず（editCloseWaitMsが-1Lのまま）editVerified:falseだけを出す。
            if (editCloseWaitMs >= 0) {
                o.put("editDialogClosed", editDialogClosed);
                o.put("editCloseWaitMs", editCloseWaitMs);
            }
            if (editVerified != null) {
                o.put("editVerified", editVerified.booleanValue());
            }
        } catch (JSONException e) {
            Log.w(TAG, "edit stage extra fields build failed: " + e);
        }
        return o;
    }

    // ---- 終了処理・通知 ------------------------------------------------------------------

    private void recordStep(String stepName) {
        recordStep(stepName, null, null);
    }

    private void recordStep(String stepName, String extra) {
        recordStep(stepName, extra, null);
    }

    /**
     * extraFieldsは診断ログ(stepTimingsJson)のこの段階のエントリにだけ追加フィールドとして
     * 混ぜ込む（例: scrollFindAndClickの内訳）。通知本文(stepTimings、平文)には一切出さない
     * ＝挙動・既存の通知内容は変えない（design.md追補「遅い回の原因確定のための計測追加」。
     * 計測を足すだけで挙動を変えないこと、という指示どおり）。
     */
    private void recordStep(String stepName, String extra, JSONObject extraFields) {
        long now = System.currentTimeMillis();
        long nowUp = SystemClock.uptimeMillis();
        long ms = now - stepStartedAt;
        long upMs = nowUp - stepStartedAtUptime;
        stepStartedAt = now;
        stepStartedAtUptime = nowUp;
        stepTimings.append(stepName).append(':').append(ms).append("ms");
        if (extra != null && extra.length() > 0) {
            stepTimings.append('(').append(extra).append(')');
        }
        stepTimings.append(' ');

        // 実行ログ用の構造化版（design.md追補「実機で動いたが挙動が診断できない」対策）。
        // 通知本文の平文stepTimingsと内容は同じ（stage名とms）。extraはここには入れない
        // （ノードのテキストやメッセージ本文は無いが、診断ログの対象を絞るため）。
        // upMsはSystemClock.uptimeMillis()の差（端末が起きていた時間、深いスリープ中は
        // 進まない）。ms（実時間）と大きく異なるなら、その段階の間にスリープに入って
        // Handler#postDelayedが引き延ばされたと分かる（design.md追補参照）。
        try {
            JSONObject entry = new JSONObject();
            entry.put("stage", stepName);
            entry.put("ms", ms);
            entry.put("upMs", upMs);
            if (extraFields != null) {
                for (Iterator<String> it = extraFields.keys(); it.hasNext(); ) {
                    String key = it.next();
                    entry.put(key, extraFields.get(key));
                }
            }
            stepTimingsJson.put(entry);
        } catch (JSONException e) {
            Log.w(TAG, "step timing json build failed: " + e);
        }
    }

    private void finish(boolean success, String failedStage) {
        // 自動取り込み中バナーを消す。施錠前の待ち（LOCK_DELAY_AFTER_EDIT_MS・
        // drainCallbackSummary、このあとのlockOnFinish分岐）には一切触れない。自動操作
        // 自体が終わった時点（finish()が呼ばれた時点）で消す、という解釈であり、画面施錠
        // （lockOnFinish==trueの場合は数秒後）より先に消えることがある（design.md追補
        // 「実行中の表示」参照）。
        overlayRemoved = overlay.remove(service);

        // stopWindowRecording()は履歴をクリアするため、読むのはその前に行う（診断用。
        // クラス名のみでパッケージ名・ノードのテキスト・メッセージ本文は含まない）。
        String recentClasses = success ? "" : service.recentWindowClassNames();
        service.stopWindowRecording();
        long elapsed = System.currentTimeMillis() - flowStartedAt;
        // 実時間(elapsed)とuptime(elapsedUptime、深いスリープ中は進まない)の両方を記録する
        // （design.md追補「遅い回の原因確定のための計測追加」）。差が大きければスリープで
        // 引き延ばされたと分かり、ほぼ同じなら本当にその時間処理していたと分かる。
        long elapsedUptime = SystemClock.uptimeMillis() - flowStartedAtUptime;

        // design.md追補「取り込みの時間規則」（PO決定 2026-10-09）: 補完（旧:保険タイマー）の
        // 起点は、書き出しフローが成功したときだけ更新する。失敗時は更新しない（起点が
        // 変わらない＝早めに次の補完が来る、安全側）。トリガー種別を問わず、ここ1箇所で扱う。
        if (success) {
            RunScheduler.recordSuccessfulImport(service);
        }

        final String title = success ? "書き出し: 成功" : "書き出し: 失敗";
        String stagePart = success ? "" : ("段階: " + failedStage + " / ");
        String body = stagePart + elapsed + "ms / " + stepTimings.toString().trim();
        if (!success && recentClasses.length() > 0) {
            // 2026-10-08実機2回目の追補: TYPE_WINDOW_STATE_CHANGEDのクラス名がこの端末で
            // 実際に取れるかの実測も兼ねる。取れることが分かれば、将来ADB版と同じ粒度の
            // 到達判定に戻せる。
            body += " / 最近のクラス名: " + recentClasses;
        }
        // 診断用: 何が引き金だったか（通知／補完／再試行／手動等）。design.md追補
        // 2026-10-08「段階3の方式変更」。
        body += " / 引き金:" + triggerLabel;
        final String bodyBeforeLock = body;

        if (!lockOnFinish) {
            if (armRetryOnFailure) {
                // 施錠を行わないが本番実行の経路（design.md追補 2026-10-10「使用中に起動した
                // 回は施錠しない」: 開始時に既に解除済みだった回）。施錠（performGlobalAction
                // (GLOBAL_ACTION_LOCK_SCREEN)）だけを行わないが、EDITタップ直後に画面状態を
                // 変えるとジェスチャが取り消される2026-10-08の不具合と同じリスクを避けるため、
                // 施錠する経路（lockOnFinish==true、下記）と同じく
                // GestureCompat.drainCallbackSummary()とLOCK_DELAY_AFTER_EDIT_MSの待ちだけは
                // 素通しする。
                final long lockDelayStartedAt = System.currentTimeMillis();
                GestureCompat.drainCallbackSummary();
                schedule("lockDelay", LOCK_DELAY_AFTER_EDIT_MS, new Runnable() {
                    @Override
                    public void run() {
                        editLockDelayMs = System.currentTimeMillis() - lockDelayStartedAt;
                        boolean wakeHeldAtEnd = wakeLock != null && wakeLock.isHeld();
                        long wakeHeldMs = wakeAcquiredAt > 0
                                ? (System.currentTimeMillis() - wakeAcquiredAt) : -1L;
                        releaseWakeLock();
                        postResultNotification(service, title, bodyBeforeLock);
                        logExportEnd(success, failedStage, elapsed, elapsedUptime, null,
                                wakeHeldAtEnd, wakeHeldMs);
                        // design.md追補 2026-10-09「取り込み失敗後に30分空いていた問題」と同じ
                        // 再試行。armRetryOnFailure==true（本番実行）のときだけ張る。
                        if (!success && armRetryOnFailure) {
                            RunScheduler.scheduleRetryAfterFailure(service);
                        }
                        // フローが終わったので見張りスレッドを止める（design.md追補参照。
                        // リーク防止）。
                        if (stallWatchdog != null) {
                            stallWatchdog.stop();
                        }
                        if (listener != null) {
                            listener.onFinished();
                        }
                    }
                });
                return;
            }

            // 施錠を行わず、本番実行でもない経路（EXPORT単体検証）。ここが画面保持の最終
            // 地点になるためここで解放する。解放前にウェイクロックの実効性
            // （design.md追補参照: 安全タイムアウト120秒で勝手に解放されていないか）を記録する。
            boolean wakeHeldAtEnd = wakeLock != null && wakeLock.isHeld();
            long wakeHeldMs = wakeAcquiredAt > 0 ? (System.currentTimeMillis() - wakeAcquiredAt) : -1L;
            releaseWakeLock();
            postResultNotification(service, title, bodyBeforeLock);
            logExportEnd(success, failedStage, elapsed, elapsedUptime, null, wakeHeldAtEnd, wakeHeldMs);
            // armRetryOnFailure==falseのため実際には呼ばれないが、lockOnFinish==trueの経路
            // （下記）と対称に条件を書いておく（design.md追補 2026-10-10の指示どおり）。
            if (!success && armRetryOnFailure) {
                RunScheduler.scheduleRetryAfterFailure(service);
            }
            // フローが終わったので見張りスレッドを止める（design.md追補参照。リーク防止）。
            if (stallWatchdog != null) {
                stallWatchdog.stop();
            }
            if (listener != null) {
                listener.onFinished();
            }
            return;
        }

        // RUN_ALLのときだけ施錠する（EXPORT単体は検証用で解除状態を保つ）。送信結果は
        // 待たない（Termux側は画面と無関係に送信を続けるため）。施錠の成否はflow全体の
        // 成否(success)には影響させない。
        //
        // 2026-10-08実機（0.3.0-stage2）で発生した不具合: GestureCompat.tapの
        // dispatchGestureは非同期で、戻り値trueは「OSが受理した」だけで「指の動きの
        // 再生が終わった」ではない。EDITタップ直後に施錠していたため、再生が終わる前に
        // 画面がロックされてジェスチャが取り消され、Termuxの保存ダイアログのEDITが
        // 押されずに残ったまま施錠されてしまい、送信が止まった。
        // まずGestureCompat.drainCallbackSummary()でOS側のジェスチャ完了/取消を確認し
        // （既存の仕組み、最大300ms待ち合わせ）、そのうえでLOCK_DELAY_AFTER_EDIT_MS
        // （最低2秒）待ってから施錠する。失敗で中止した経路（ジェスチャを出していない
        // 場合もある）と区別すると実装が複雑になるため、安全側に倒して一律この手順を通す。
        final String gestureSummary = GestureCompat.drainCallbackSummary();
        final long lockDelayStartedAt = System.currentTimeMillis();
        schedule("lockDelay", LOCK_DELAY_AFTER_EDIT_MS, new Runnable() {
            @Override
            public void run() {
                // 施錠前の待ち（LOCK_DELAY_AFTER_EDIT_MS）の実測（design.md追補参照）。
                editLockDelayMs = System.currentTimeMillis() - lockDelayStartedAt;
                boolean locked = service.performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN);
                boolean wakeHeldAtEnd = wakeLock != null && wakeLock.isHeld();
                long wakeHeldMs = wakeAcquiredAt > 0 ? (System.currentTimeMillis() - wakeAcquiredAt) : -1L;
                // 施錠まで終えてから解放する（施錠の直前で解放すると、画面が落ちてから
                // GLOBAL_ACTION_LOCK_SCREENを呼ぶことになり、扱いが不安定になりうるため）。
                releaseWakeLock();
                String finalBody = bodyBeforeLock + " / " + gestureSummary + " / 施錠:" + locked;
                postResultNotification(service, title, finalBody);
                logExportEnd(success, failedStage, elapsed, elapsedUptime, Boolean.valueOf(locked),
                        wakeHeldAtEnd, wakeHeldMs);
                // design.md追補 2026-10-09「取り込み失敗後に30分空いていた問題」: 5分後に
                // 再試行を予約する。armRetryOnFailure==true（本番実行）のときだけ対象
                // （design.md追補2026-10-10でlockOnFinishと分離。checkResult()からの
                // 解除成功後の続行はlockOnFinish=true, armRetryOnFailure=trueで渡しており、
                // この経路に来るのは常にarmRetryOnFailure=trueだが、
                // !lockOnFinish側（finish()上部）と条件の書き方を揃えてある）。
                // finish()は!lockOnFinishの分岐で必ずreturnするため、1回のfinish()呼び出しで
                // scheduleRetryAfterFailureが二重に呼ばれることはない。
                // logExportEndの呼び出しより後にすること: logExportEndはSchedulerStoreの
                // pending-nextを読んで終了行に書くため、先に再試行を張ると終了行のnextTriggerが
                // 上書きされ、診断が読みにくくなる。
                if (!success && armRetryOnFailure) {
                    RunScheduler.scheduleRetryAfterFailure(service);
                }
                // フローが終わったので見張りスレッドを止める（design.md追補参照。リーク防止）。
                if (stallWatchdog != null) {
                    stallWatchdog.stop();
                }
                if (listener != null) {
                    listener.onFinished();
                }
            }
        });
    }

    /**
     * LINE操作フローの終了行を書く。nextTrigger/nextAtMsはこのチェーンでRunSchedulerが
     * 新たに張ったアラームをSchedulerStoreのpending-nextから読む（ロック解除フロー側の
     * logUnlockEndと同じ値を指す。チェーンの先頭で1回だけ決まる情報のため）。
     * wakeHeldAtEnd/wakeHeldMs/editLockDelayMsはトップレベルの追加フィールドとして載せる
     * （design.md追補「遅い回の原因確定のための計測追加」）。
     */
    private void logExportEnd(boolean success, String failedStage, long elapsedMs, long elapsedUpMs,
            Boolean locked, boolean wakeHeldAtEnd, long wakeHeldMs) {
        String nextTrigger = SchedulerStore.getPendingNextTrigger(service);
        Long nextAtMs = null;
        if (nextTrigger != null) {
            nextAtMs = Long.valueOf(SchedulerStore.getPendingNextAtMs(service) - System.currentTimeMillis());
        }
        String result = success ? "success" : "failure";

        JSONObject extraFields = new JSONObject();
        try {
            extraFields.put("wakeAcquired", wakeAcquired);
            extraFields.put("overlayShown", overlayShown);
            extraFields.put("overlayRemoved", overlayRemoved);
            // design.md追補 2026-10-11「遮断モードの帯（検証用）」、同日追補「遮断モードを
            // 常時有効にし、再試行を3回にする」: 遮断モードで出したときだけoverlayBlockingを
            // trueで出す（通常=EXPORT単体のときは出さない）。「停止」ボタンは削除済み
            // （overlayEscapeTappedのログ項目も削除）。
            if (overlayBlocking) {
                extraFields.put("overlayBlocking", true);
            }
            // design.md追補 2026-10-11「遮断モードを常時有効にし、再試行を3回にする」:
            // 遮断モード中に座標ベースのジェスチャ（タップ/スワイプ）を使った回だけtrueで出す
            // （検知のための記録。挙動は変えない。blockedCoordinateGestureの定数コメント参照）。
            if (blockedCoordinateGesture) {
                extraFields.put("blockedCoordinateGesture", true);
            }
            extraFields.put("wakeHeldAtEnd", wakeHeldAtEnd);
            if (wakeHeldMs >= 0) {
                extraFields.put("wakeHeldMs", wakeHeldMs);
            }
            if (editLockDelayMs >= 0) {
                extraFields.put("editLockDelayMs", editLockDelayMs);
            }
            // design.md追補 2026-10-10「使用中に起動した回は施錠しない」: 施錠しなかった回
            // （lockOnFinish==false）だけtrueを出す（行った回は出さない）。lockedフィールドは
            // 施錠を試みていないのでnull（既存どおりlogExportEnd呼び出し側でnullを渡す）。
            if (!lockOnFinish) {
                extraFields.put("lockSkipped", true);
            }
        } catch (JSONException e) {
            Log.w(TAG, "export end extra fields build failed: " + e);
        }

        RunLogger.logEnd(service, runId, "export", triggerLabel, result, failedStage, elapsedMs, elapsedUpMs,
                stepTimingsJson, locked, nextTrigger, nextAtMs, extraFields);
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

    // ---- Screen wake ---------------------------------------------------------------------
    //
    // WAKE_LOCK_TAGの定数コメントに理由を書いたとおり、アクセシビリティ経由の操作は画面の
    // 消灯タイマーをリセットしないため、フロー自身でウェイクロックを持つ
    // （UnlockAccessibilityService#acquireWakeLock/releaseWakeLockと同じ作法。フラグも同じ:
    // SCREEN_BRIGHT_WAKE_LOCK|ACQUIRE_CAUSES_WAKEUP|ON_AFTER_RELEASE）。

    @SuppressWarnings("deprecation")
    private void acquireWakeLock() {
        PowerManager pm = (PowerManager) service.getSystemService(Context.POWER_SERVICE);
        if (pm == null) {
            return;
        }
        if (wakeLock == null) {
            wakeLock = pm.newWakeLock(
                    PowerManager.SCREEN_BRIGHT_WAKE_LOCK
                            | PowerManager.ACQUIRE_CAUSES_WAKEUP
                            | PowerManager.ON_AFTER_RELEASE,
                    WAKE_LOCK_TAG);
        }
        if (!wakeLock.isHeld()) {
            // 安全タイムアウト2分（design.md追補参照: 設計値どおりなら全体15〜20秒、
            // 実機の最悪実測でも113秒だったため2分あれば足り、暴走時も必ず解放される）。
            wakeLock.acquire(WAKE_LOCK_SAFETY_TIMEOUT_MS);
            wakeAcquiredAt = System.currentTimeMillis();
        }
        // 取得直後に実際に保持できているかを記録する（診断用。design.md追補
        // 「遅い回の原因確定のための計測追加」）。
        wakeAcquired = wakeLock.isHeld();
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
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
