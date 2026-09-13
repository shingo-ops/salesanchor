# AM スタッフ3フォーム6ボタン実装検収

2026-09-13。PO原文「進める進める」（6ボタン実装承認質問への返信）でCARD-AM-STAFF-01を既存button_generatorへ発行。設計はdesign.md§AM。同一AIのPlanner→Architect自己審査APPROVEは独立第二者レビューではない。

## 実物と検証

製品3ファイルはStaffPage.tsx、StaffEditPage.tsx、StaffFormButtonMigration.test.tsx。6ボタンの取消3=secondary・登録/更新3=primary、size md。root直接検算でimport/tag/variant/sizeを逆変換した2ページは固定af269ae2と全バイト一致。共有Button/CSS/Modal/Drawer/StaffFormFields/UiPrefsContextの7hash一致。認証・権限・Firebase UID・設定・送信の業務本文差分0。

root直接実行:
- 実表示96前後組（192画面）成功。3フォーム×6幅390/640/767/768/1279/1280×日英×明暗72組、登録pending24組。実Tab/ShiftTab到達、文字/本体/輪郭4辺欠け0、初期横overflow増加0、type/disabled/文言/順序同一。pendingのdisabledボタンは通常状態で輪郭とTab到達を検査。
- 操作29前後組（58回）成功。3フォームの取消/送信Enter/Space、入力Enter、Esc、pending、失敗保持、Modal/Drawer閉じる・再開・focus対象比較。専用編集self/other/nullの追加/staff/me=1/0/0、self再取得待機・HTTP失敗後の既存遷移確認。
- 実ページ/入力/Modal/Drawer/UiPrefsProvider/usePermissions/翻訳を使用。認証入口/APIのみ合成して通信をローカルに限定。Provider外no-opは本人refresh証拠にしない。テーマは実CSSのforce-light/dark。
- TypeScript構文再測定: 共通100→106/旧305→299。旧母数button/Link/a、stories/test/spec/design-preview除外。最新main取込み前の固定基準比較。

実装担当の実行を原ログ確認: strict eslint対象3警告/エラー0、新規32試験、全体26files/298tests、check:all/build/Storybook成功。対象外warnings218、coverage statements14.3%（全体高網羅とはしない）。32試験は全payload/required12条件/code省略・trim/6設定boolean/登録連投抑止・再試行/実Provider本人refresh待機・失敗を検証。原ログはcheckpoint内am-generator-*.log。

## 限界・検収器修正

ローカル合成認証/APIによる実フォーム検証。本番認証・実スタッフ更新・アプリsidebar全体・PO目視は未検証。640pxを実200%zoomとしない。
初回操作比較はfocus要素outerHTMLに意図したCSS class差を含め16差異を検出。製品を変更せずfocusのtag/text/typeと操作意味を比較するよう検収器を修正して29組全成功。初回operations-initial-result.jsonも保存。画像4枚は390px英語light代表、全192画面の数値を保存。

## 保存・次の一手

am-implementation-manifest.jsonは製品3hash、archive hash、checkpoint内証跡hashを保持。checkpointは再現スクリプト/JSON/画像/ログで、依存物とbundleを含まない。prepare.cjsの作業パスを復元先へ合わせ、依存導入後に生成しserver.cjs→browser.cjs/operations.cjsで再現する。
root実物照合・ローカル検収APPROVE。維持は32回帰と既存CI、新CIなし。表/報酬3/カレンダー色は別便。本便revertで戻せDB復元不要。
PR3468実装保存、最新main統合後品質/CI確認へ。今回番号付きGO/マージ/本番は未実施。既存GO3461等は転用しない。
