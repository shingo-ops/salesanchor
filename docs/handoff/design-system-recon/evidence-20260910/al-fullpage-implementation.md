# AL専用編集4ボタンの実装・検収

親: [recon](../recon.md)、[設計AL](../../../specs/design-system/design.md)。2026-09-13。

## 承認・範囲

PO原文「進めてくれ」（4件の実装承認質問への返信）を受領。既存button_generatorへCARD-AL-FULLPAGE-01を発行。ContactEditPage/SupplierEditPageのform-actions4件と新規FullPageFormButtonMigration.test.tsxのみ変更。GO #3457は前便のみ、今回PR3461の番号付きGO未受領。

## rootが直接行った検証

- 指定import/tag/class/variant/sizeを逆変換し、2ページが基準9e0406eeと全バイト一致。業務本文・対象外重複確認2ボタン・属性/翻訳変更0。
- TypeScript構文で実運用共通Button100、旧prefix305（button/Link/aを含む既存母数、button単独297）。AKの96/309から4移管。
- 実2ページ、実入力/Select/Button/PageLayout、MemoryRouter/I18nextProviderをmount。lib/apiだけを合成fetchへ差し替え、外部通信は遮断。本番認証/全体App/sidebarはmountしていない。
- 連絡先active/pending_dedup_review、仕入先の3状態×幅390/640/767/768/1279/1280×日英×明暗=72前後組、144表示成功。実Tab/ShiftTab、文字/本体/フォーカス輪郭の4辺欠け0。初期document横overflow/ボタン意味/初期focusが前後同一。
- 3状態×取消Enter/Space、更新Enter/Space、input Enter、textarea Enter、Esc、通常更新pendingの8操作=24前後組48ケース成功。書込回数/URL/ID/PATCH/payload/移動先/入力/disabled/aria-busyの前後一致。
- 390px英語の3画像保存、連絡先重複確認中と仕入先をroot目視。対象4ボタンの文字と輪郭の収まりを確認。
- 最初のChromium起動はOS sandbox権限で失敗。通常の承認経路でOS権限を得て起動し、限定6表示成功後に全行列を実施。ガードの変更なし。検証サーバーは終了済み。

高さ900px、640pxは狭幅で実200%zoomではない。旧ボタンの外観同一ではなく、業務結果を維持して共通外観へ移した。実データ送信・PO目視・本番反映は未実施。

## 実装担当の検証をrootが原ログ・本文で確認

strict eslint警告0、単独12/12成功。全体coverage25files/266tests成功、checkall成功（既存対象外警告218、エラー0）、build/Storybook成功。rootが同じ全品質コマンドを再実行したとは称しない。原ログをarchiveへ収録。

試験は実Router/2ページ/実部品でPATCH全payload・遷移・取消0・失敗入力保持・会社必須・入力Enter・重複確認の別操作成功失敗と既存disabled制御を検証。rootが全本文を読了。通常更新へ保存ロックは追加しない。

## 判定・保存・次の一手

rootの設計照合/操作/表示検収APPROVE。設計は同一AIの自己審査であり独立した第二者設計レビューとは称しない。独立した最終Reviewer/Evaluatorの指名・PO目視完了とも称しない。

製品3hash、19資料のmanifest、al-implementation-checkpoint.tar.gzへ保存。再現原稿はこの作業台の絶対パスを使用、再開時に実在作業台へ合わせる。生成bundle/依存は含めず既存lockから再生成。beforeは9e0406ee、afterはmanifest製品hash。

次は実装をcommit/pushし、既存設計PR3461を実装PRへ更新して最新CI確認。今回番号付きGOなしにマージ/本番反映しない。表/報酬3/カレンダー色保留、新CI最後。
