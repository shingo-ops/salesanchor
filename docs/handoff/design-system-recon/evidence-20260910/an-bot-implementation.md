# AN Bot3フォーム6ボタン実装検収

2026-09-13。今回6件の実装承認質問へのPO原文「進める」でCARD-AN-BOTS-01を既存button_generatorへ発行。設計はdesign.md§AN。同一AIのPlanner→Architect自己審査であり独立第二者設計レビューではない。

## 実装・直接検収

製品はBotsPage.tsx/BotEditPage.tsxの6ボタンとBotFormButtonMigration.test.tsxの3ファイル。取消3 secondary/送信3 primary/size md。rootがimport/tag/variant/sizeを逆変換して2ページと基準1a8eed69の全バイト一致を確認。共有10hash一致、非対象5ボタン・ConfirmModal2個・APIキー処理・権限・API/DB/CI/共有CSS変更0。構文再測定で共通114→120/旧299→293（旧母数button/Link/a、stories/test/spec/design-preview除外）。

root直接ブラウザー検収:
- 最終96表示前後組（192画面）成功。3フォーム×6幅390/640/767/768/1279/1280×日英×明暗72組＋登録pending24組。実Tab/ShiftTab到達、文字/本体/輪郭4辺欠け0、初期横overflow増加0、文言/type/disabled/順序一致。disabledのTab/輪郭は通常状態で確認。英語の長い登録ラベルも省略しない。
- 操作24前後組48回成功。各3フォームの取消/送信Enter/Space、入力Enter、Esc、保存pending、失敗保持。登録成功後は合成キー表示・確認による消去・再開初期化、簡易は閉鎖/一覧再取得、専用は/bots遷移を比較。
- 閉鎖/再開6前後組12回成功。Modal/Drawerの通常ヘッダX、保存pending時のEsc/ヘッダXとfocus対象・再開状態・通信回数が前後一致。既存の保存中の閉鎖仕様を変更していない。
- 試験前提8観測成功（3フォーム×前後の用途必須負例6＋権限拒否Drawer前後2）。用途のselectedIndex=-1はnative invalid/送信0、DrawerはDOM常設で拒否時openクラスなし。

実ページ/入力/Select/Button/Modal/Drawer/usePermissions/UiPrefsProvider/Router/翻訳を使用。認証入口とAPIのみ合成。実キー・Bot・Discord・外部API操作0。全App/sidebar/本番認証付きフォーム送信/PO目視は対象外。640pxを実200%zoomとはしない。

## 実装担当の品質をrootが原ログと試験本文で確認

strict eslint3ファイル警告/エラー0、単独32試験、全体29files/343tests、check:all/build/Storybookすべてexit0。全体既存警告218、coverage statements16.12%（全体高網羅とはしない）。rootが全品質コマンドを再実行したとは称さない。
回帰は全payload、optional code省略/trim、owner数値化/null化/非空値、必須/不正email、登録連投抑止/再試行、合成キー表示消去/初期化、権限条件/非対象通信0を検証。mockはAuth入口とAPIのみ。新規試験はStaff固有の設定refreshを追加していない。

## 初回失敗と補正

初回単独32中4失敗は、用途に空optionがあるとの仮定3件、閉じたDrawerのDOM不存在という仮定1件。カード停止を守り、rootの実物/実ブラウザー8観測で原因を確定。CARD-AN-TEST-02で試験だけを修正し32件全成功。用途4非空選択肢とrequired属性を維持し、native負例は試験内でselectedIndex=-1とする（通常UIで空を選べるとの主張ではない）。Drawerはopenクラスを検査し権限判定・書込0の条件を保持。製品コードの追加修正・検査条件緩和0。初回ログunit-initial-failure.logとtest-assumptions.jsonを保存。
表示検収は初回96組成功後に文字の縦方向も含む判定へ補強し最終96組全成功。初回browser-initial-result.jsonと最終結果を区別し、条件数を倍加しない。代表390px英語light画像4枚、root3フォーム画像を目視確認済み。

## 保存・判定・次の一手

an-implementation-manifest.jsonに製品3/証跡/archive SHA256。checkpointは再現スクリプト/比較JSON/画像/原ログ（依存物・生成bundleを除外）。復元先に絶対パスを合わせ既存依存でprepare.cjs→server.cjs→browser.cjs/operations.cjs/closing.cjsを実行する。beforeは1a8eed69固定、afterはmanifest製品hash。サーバー停止済み。
root実装照合・表示操作検収APPROVE。維持は新規32回帰と既存CI、新CI追加なし。本便revertで戻せDB復元不要。PR3480へ実装保存、最新main取込み後の差分/製品hashとCI確認へ。今回番号付きGO/マージ/本番は未実施、過去GO3468等は転用しない。表/報酬3/カレンダー色保留、新CI最後。

## 最新main統合確認

2026-09-13、実装08b2fa96をpush後、main 5c0704dfを通常merge（7e179ceb）。evidence-registryの双方追記を保持。基準1a8eed69→mainのfrontend差分0、統合後の製品3/共有10/archive/証跡28 SHA256すべて一致。343試験・96表示・30操作前後組の対象は不変のためローカル全試験を重複実行せず、PR最新HEADのCIを確認する。最新CI結果はPR3480本文と現行active-work.dに記録。GO3480/マージ/本番反映未実施。
