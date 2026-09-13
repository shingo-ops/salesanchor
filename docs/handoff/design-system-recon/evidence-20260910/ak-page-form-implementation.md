# AK 12ボタンの実装・検収記録

親: [recon](../recon.md) / [設計AK](../../../specs/design-system/design.md)。2026-09-13。基準739f772d、設計保存ff366628。

## 承認と実装

12件の実装承認質問へのPO原文「進める」を受領し、既存のbutton_generatorへ正式カードCARD-AK-PAGE-FORMS-01を発行。GO #3442は前便のみ。今回のPR番号付きGOは未受領。

CompaniesPage/ContactsPage/SuppliersPageの各4個（取消6、登録/更新6）とPageFormButtonMigration.test.tsxのみを変更。旧btn10・裸取消2を既存Button secondary/primary・mdへ。各type、翻訳、disabled、handlerを保持。

## rootの直接検証

- 原文の逆変換で3ページを739f772dと全バイト一致。指定tag/class/variant/size/import以外の変更0、children/全属性も照合。
- TypeScript構文再監査: 共通84→96、旧prefix319→309、専用20・リンク8不変。母数は本基準のみ。
- 実3ページと実Modal/Drawer/入力/PageLayout/usePermissions/useRecordDrawerをMemoryRouterへmount。lib/apiだけをローカルfetchへ差し替え、通信はlocalhostの合成データに限定。全体Appの認証・サイドバー・本番は検証対象外。
- 通常6フォーム×6幅×日英×明暗=144前後組（288表示）。実Tabで対象12個へ到達、ShiftTab逆順、実focus-visibleの文字/本体/クリップ祖先4辺/輪郭欠け0。初期document横overflowと初期focusの前後差0。入力欄を省略していない。
- 会社/連絡先create pending48前後組（96表示）。保存中文言・2ボタンdisabled・書込1回・画面内表示が前後一致。
- 実キーボード36前後組（72ケース）: 各6フォームの取消/送信をEnter/Space、入力Enter、Escで確認。method/url/payloadと閉じた後のfocusが前後一致。
- 取消後に再び開く6前後組（12ケース）で入力状態一致、書込0。
- 390px英語の6画像を保存。会社登録と連絡先編集の画像をrootが目視し、操作ボタンと輪郭の収まりを確認。
- 初回限定試験は連絡先合成データにcontact_channels配列が欠け、4ケースが描画待ちで失敗。原稿と初回結果を保存し、実型に合わせて配列を補った限定12表示は失敗0、その後に上記全条件を実行。製品変更なし。

高さ900px・640px幅は200%相当の狭幅で実zoomではない。既存のフォーカス仕様を改善したという主張ではない。初期の画面全体横overflow差0と、到達後対象ボタンの欠け0を区別する。

## 実装担当の実行結果をrootが原ログで確認

strict eslint警告0、単独28試験成功。全体coverage 24files/254tests成功、check:all成功（既存の対象外warning218）、build成功、Storybook成功。原ログ4本をarchiveへ収録。rootが同じ全試験を再実行したとは称しない。依存は既存lockのnpm ciのみ、lock/CI/設定の変更0。

ページ試験28件は実3ページを使い、成功12/失敗6/取消6/制御2/入力検証2。API・permissions・翻訳のみmockし、部品を単純buttonに置換していない。rootが試験本文と成功ログを読んで確認。製品diff4ファイル・hashはmanifest参照。

## 検収判定と再開

rootによる設計照合・差分/操作/表示検収: APPROVE（本実装の提出検収）。同一AIによる設計自己審査と区別。独立した最終Reviewer/Evaluatorの指名・PO目視完了とは称しない。

次は保存commit→最新main統合→PR提出→新HEADのCI照合。今回の番号付きPO GO受領前にマージ/本番反映しない。表・報酬3・カレンダー色は別便、新CIは最後。

再現資料: ak-implementation-checkpoint.tar.gzとmanifest。ブラウザー原稿prepare.cjsは前後の実ページをbundleし、初回設定はこの作業台の絶対パスを使う。再開時に実在する作業台へ合わせる。描画のbeforeはff366628の原文、afterはmanifestに固定した実装原文。生成済みbundleはarchiveへ含めず同じlockで再生成する。
