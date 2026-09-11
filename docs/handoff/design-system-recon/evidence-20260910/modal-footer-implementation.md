# 共通Modal footer折返しの検収

これは、狭い画面で操作ボタンが欠けないための先行修正と、その確認結果です。
親: [設計§AI](../../../specs/design-system/design.md)／[調査](../recon.md)。基準main 7606ca9a041e315b81040373e8f4ddebbc562133。

製品差分はModal.cssのflex-wrap:wrap 1宣言と、Modal.stories.tsxのResponsiveFooter見本のみ（2ファイル・22行追加）。実3利用の業務処理・文言・API・他CSSは無変更。保留AH16移管はhash付き7ファイルを/tmpへ保存し、6元ファイルを基準へ戻したため本製品差分へ含まない。

| 確認 | 結果 | 実行担当・証拠 |
|---|---|---|
| 実3footerの前後比較 | 560組成功、縮まず収まる448組は同値、112組は折返し。reference一致/本比較無変更560組 | Generator実行、root結果再集計。modal-browser-v4-cases.csv / modal-browser-v4-summary.json |
| 画面/内容領域内・文字欠け・非重複 | 560組違反0、短高時の本文スクロール確認 | 同上。7幅320/390/640/767/768/1279/1280・高さ360/900・日英・明暗、金額0/123450/999999999999 |
| キーボード・輪郭・form | 輪郭448ボタン、Enter/Space6操作、外部form3確認成功 | Generator実行。modal-focus-result.json / v4-summary.json |
| 次のButton移管前提 | 発送3Button、390pxの日英2組成功 | Generator実行。v4-summary.json future |
| 見本の実表示 | 日英/明暗4組成功 | Generator実行、rootはja/light・en/dark画像を目視。modal-story-result.json / modal-story-ja-false.png / modal-story-en-true.png |
| 品質 | strict eslint、unit coverage 22files189tests、checkall、build、Storybook全exit0 | root実行。modal-footer-quality-results.jsonと各log |
| 限定レビュー | APPROVE、製品hash2/2一致 | 別の既存担当が原稿/結果/実物照合。検査再実行ではない。modal-footer-review.md / modal-manifest.json |

Planner/Architectの設計は同じroot AIの自己審査。上記限定レビューと区別する。比較原稿v1/v2は一行分類を誤り、v3は一時style属性の復元検算に失敗した。root診断でも座標は一致、空属性の原因は未確定。v4は比較対象DOMを変更せず隔離referenceで必要幅だけ測り、本比較無変更を全件確認した。旧失敗は保存し、成功へ書き換えていない。

完全生JSON（7,228,145bytes）は/tmpに保持し、hashをv4-summaryへ記録。正式保存は全560条件のCSVと要約、実行原稿・モック・限定結果。再現方法はmodal-reproduction.md。正式保存のmodal-fixture-sample.tsx / modal-fixture-mock-api.ts / modal-fixture-mock-firebase.tsを再現先modal-fixture内のsample.tsx / mock-api.ts / mock-firebase.tsへ置く。原稿は当日の絶対パス依存のため、別checkoutではrepo/out/import先を置換し、基準SHAと2製品hashを照合する。公開用logは末尾空白を除去、原ログは/tmpに保持。

限界: Chromiumとモックによる局所検査。640pxは200%相当の幅で実zoomではない。任意長文・任意金額・全本番画面の確認ではない。全体coverageは5.91%であり、189件を全アプリ網羅とは称しない。POの画面確認は未実施。新CIは追加せず、画面統一後の設置順を維持する。

状態: 設計・実装・限定検収済み。新PR提出準備中、今回の番号付きGO・マージ・本番反映は未実施。後続AH16移管は先行PRマージ後に最新mainで再検証する。
