# Button外観・70利用の実装検収（2026-09-11）

[設計§AG](../../../specs/design-system/design.md) / [カード01](../CARD-BUTTON-APPEARANCE-01.txt)。基準main e81dd3ece217c6ea3d43fa9c9943440055e13adf。製品14ファイル。

## 変更と範囲

Button.cssを共通Buttonの色・形・状態の編集元にし、ページのclassName/style入口を閉じ、既存配置2件だけlayoutClassNameへ移管。70利用/18ファイルは維持し、外部class18→0、style0、type明示26/省略44、既存利用欠落0。旧raw352利用は後続へ残し、ソース差分0。CompanyDetailの6タブは既存switchTabとaria-pressed属性なしを保持。Scheduleの作成ボタンは設計どおり共通md・角丸6px・中央揃えへ変わる。検索へ新動作は追加していない。

## 検証と実行者

Generator frontend_definition_auditが実装・コマンド・ブラウザー検査を実行。rootは差分、測定原稿、JSONとログ、14製品hashを照合した。rootによる全テスト再実行やPO画面確認とは称しない。

| 検証 | 結果・根拠 |
|---|---|
| 利用前後 | [対応表](button-appearance-correspondence.json)、[変更前](button-appearance-before-audit.json)、[変更後](button-appearance-after-audit.json) |
| 厳格lint・unit・check:all | lint警告0、22ファイル189試験成功、check:all成功。[先行ログ](button-appearance-checks.txt) |
| 修正後lint・製品/見本build | 3コマンドexit0。[再開ログ](button-appearance-checks-resume.txt) |
| 配色 | 指定5背景×明暗×状態190組、最小コントラスト5.064879620284947、基準4.5以上 |
| 寸法 | app/Storybook CSS順×明暗×幅390/767/768/1279/1280×size/variant/日英ラベル等1080条件 |
| 操作 | disabled/loading/selected13条件、6variantのクリック/Enter/Space、逆Tab、disabled/loadingの操作抑止 |
| 旧raw互換 | 11class組合せ×明暗×5幅×4状態=440組のcomputed値が前後一致。遷移定義も440組一致 |
| ブラウザー根拠 | [全測定](button-appearance-browser-settled-result.json)、[原稿](button-appearance-browser-settled.mjs)、[fixture生成](button-appearance-prepare-browser.cjs)、[CSS順](button-appearance-css-import-order.json) |
| 見本隔離 | 実Docsで独立2iframe・各42Button、明暗別配色・親document class不変。[結果](button-appearance-storybook-browser-result.json) / [原稿](button-appearance-storybook-browser.mjs) |
| 変更範囲 | [14製品manifest](button-appearance-manifest.json)。index.cssの固定hex178→178、全対象hex増加0。backend/CI/依存追加差分0 |

通常文字のコントラスト測定は指定背景のみで、disabledを含む全状態・全画面のWCAG適合宣言ではない。table/modal/adjacentのfocus試験は幅240px・padding8pxの合成境界であり本番ページDOMではない。長文はボタン内の切れを測定し、画面端のはみ出しや200%拡大時の全ページ検査は含まない。完成後のPO目視・全画面移行・理解速度評価は未実施。新CIは全画面移行の最後。

## 失敗と補正の証跡

1. 初回Story cleanupがbooleanを返しbuild TS2345で停止。カード02でvoid cleanupへ修正。旧失敗ログは上記先行ログに保持。さらに同一Docs内で明暗storyがdocumentクラスを競合させる指摘を受け、各storyをinline=falseのiframeへ隔離。修正後のコード限定第二レビューAPPROVE、14hash一致。設計全体の審査は同一AIによる自己審査であり区別する。
2. 初回raw測定はhover直後の150ms遷移中に値を読み、9/440で不一致。[失敗結果](button-appearance-browser-result.json) / [失敗原稿](button-appearance-browser.mjs)を保持。製品は変更せずカード03でgetAnimationsのfinishedを待機。原失敗light390 btn-ghost hoverは両側ともbackground-colorの150ms/ease、currentTime0→150を記録し、終了後全computed一致。transitionを無効化したり期待を緩和していない。
3. 補助原稿のdark focus期待にrgb(226,232,240)という契約にない手転記を検出。rootがindex.css:233のtext-primary=#f1f5f9とButton.css:95-97を確認し、カード04で独立probeのtext-primary色と輪郭の同値比較へ補正。製品色は変更しない。補助の最終結果は次節へ追記する。

Context7 MCPは提供されておらず、POの代替許可で公式資料を直接確認。2026-09-11: [Storybook Story](https://storybook.js.org/docs/api/doc-blocks/doc-block-story)、[Element.getAnimations](https://developer.mozilla.org/en-US/docs/Web/API/Element/getAnimations)、[Animation.finished](https://developer.mozilla.org/en-US/docs/Web/API/Animation/finished)。Storybookはinstalled addon-docs10.4.1のgetStoryPropsとも照合済み。外部企業の事例は不要（有限の既存利用と実部品の比較が直接根拠）。

JSONは空白だけ圧縮して保存し、測定レコードを削除していない。再現原稿は/tmpへ必要ファイルを元名でコピーしてから使用する。原稿中のworktreeと出力先は実測時のもの。正式根拠を直接再実行して上書きしない。

## 状態

設計作成・設計自己審査・限定コード第二レビュー済み。実装済み、補助測定の最終検収とPRは未完。番号付きGO・マージ・本番反映を記録しない。


### 補助検収完了

[修正後測定](button-appearance-browser-extra-corrected-result.json) / [原稿](button-appearance-browser-extra-corrected.mjs) / [ログ](button-appearance-browser-extra-corrected.txt)。4用途×明暗8組同値、loading/Spinner12条件、focus72条件、reduced-motion回転停止とbusy/文言保持、fullWidth、Company向けaria-pressed未出力は成功、console/pageerror0。旧誤転記の[失敗結果](button-appearance-browser-extra-result.json)と原稿/ログは保持。

[14hash再照合](button-appearance-card04-hash-check.json)は全一致。限定第二レビュー担当ci_preflight_readonlyはコードと最終検証証跡をAPPROVE（試験は再実行せず読み取り審査）。rootも保存結果を照合。Company実ページの切替操作は当ブラウザー原稿で再現しておらず、既存イベント差分の読み取りと共通部品aria契約の確認である。loading中のfocusは12件とも外れる観測で、元native disabled契約のまま、復帰を保証する検査ではない。

設計自己審査・限定コード/証跡審査・本便ローカル検証完了、文書保存済み。PR提出と既存CI確認へ進む。PO全画面確認・全体移行・新CI設置は未完。
