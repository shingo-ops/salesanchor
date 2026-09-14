# APリード6ボタン実装・検収

この文書は、リード3フォームの変更内容と、どの条件で検証できたかを追跡する記録です。
親: [design-system](../../../specs/design-system/README.md)。設計: [design.md §AP](../../../specs/design-system/design.md)。調査: [recon](../recon.md)。対象ADR: ADR-113/067/027/073/122/109/119。

## 状態と承認

設計自己審査合格後、既存実装担当1名への6件実装・検証の委任質問へPO原文「進める」を受領。CARD-AP-LEADS-01を既存team_button_generatorへ発行。rootは設計/実物照合/表示操作検収を担当し、新AI起動なし。今回番号付きGO/マージ/本番反映は未承認・未実施。

## 実装範囲・結果

LeadsPage登録/DrawerとLeadEditPageの取消/送信6件のみ既存Buttonへ移管。新規LeadFormButtonMigration.test.tsxを追加。2ページの逆変換は全byte一致、対象外6原文維持、共有21hash不変。共通131→137、旧287→281。raw countの対象と除外は監査JSON参照。入力/送信/失注/権限/SSE/共有CSS/翻訳/依存/DB/CIの製品変更なし。

## rootが直接実行した検収

| 観測 | 結果・証跡 |
|---|---|
| 実表示 | 5構成×6幅×日英×明暗×通常/pendingの240前後組=480観測、最終違反0。browser-result.json |
| 基本操作 | 3フォーム×8操作の24前後組=48観測、URL/全payload/閉鎖/reset/GET/焦点が一致。operations-result.json |
| 閉鎖・再開 | Modal/Drawer×通常X/pendingEsc/pendingXの6前後組=12観測、全一致。closing-result.json |
| 追加操作 | 連投/textarea Enter/国チャネル候補/専用遷移/SSE ping-update/失注3分岐の17前後組=34観測、全一致。extra-result.json |
| 実物照合 | 2ページ逆変換・共有21hash・対象外6原文、最終3ファイルhash。inverse.json、ap-generator-hashes.json |
| 品質原ログの確認 | 担当実行のstrict警告0、70試験、全体31ファイル451試験/coverage19.99%、check:all/build/storybook全exit0を読み取り確認。全体lint既存218警告は保持 |

実ページ/入力/Select/Combobox/Button/Modal/Drawer/Router/翻訳/usePermissions/useSSE/UiPrefsProviderを使用。合成した境界は認証入口/API/SSE transport。外部通信遮断、本番書込0。代表スクリーンショットはrootが画像として確認。全App/sidebar/実認証/本番送信/PO目視/本番配備は未検証。幅640pxを実200%zoomとはしない。

## 初回失敗と切り分け（削除しない）

1. root先行表示20観測中2失敗。390px非lost専用の自然Tabでfocus輪郭欠け。390/1280×前後4ケースで変更前にも同じ欠けを確認。390はscroll486/max518から実wheelで下端518へ進めると輪郭が収まる。設計で指定した実scroll工程の不足を補い、新規自然Tab欠け0も追加比較した。自然Tabの既存制約は残存し、修正済みとはしない。browser-initial-smoke.json/focus-probe.jsonを保存。
2. 担当unit70中45失敗/25成功。登録Modalタイトルの取り違え（newLead/newLeadTitle）と前ケースSSE controller持越し。root実物照合後CARD-AP-TEST-02で新規試験だけ補正。再実行70/70成功、例外握り潰し/skip/期待値削除なし。unit-initial-failure.logを保存。
3. root追加操作で国候補4タイムアウト（drawer/full前後）。6ケースの観測で、既存値があるinputへの直接fillは焦点時の表示切替と重なりJapanUnitedとなることを確認。実click→文字置換→入力文字検算→候補選択に補正して17組成功。製品変更なし。extra-initial-result.json/combo-probe.jsonを保存。

上記はrootの検証前提/新規fixtureの補正。製品仕様・受入範囲を広げず、失敗記録を成功記録と分ける。再現用script/最終結果/初回失敗/スクリーンショット/担当原ログはap-implementation-checkpoint.tar.gz内、全hashはap-implementation-manifest.json。

## 審査と次の一手

実装検収APPROVE。同一設計AIによる自己審査・直接検証であり、独立した第二者レビューとは称しない。3送信契約/原文の維持と最終240表示・47操作前後組の成功を根拠に、保存・PR更新へ進む。設計段階の既存3試験と、今回担当実行70/451の区別を保持。最新mainの影響を再照合してCI確認、今回番号付きGOをPOへ依頼する。新規GOの代筆・マージ・本番操作は行わない。


### 2026-09-14 配備前提の停止

AP実装は1c0791c1で保存し、最新main e69da6edをf3598fb2へ通常統合。evidence-registryの追記競合は双方保持、main全行の包含と製品3hash一致を確認。製品HEAD f3598fb2のCIは38成功/8対象外、process-artifactsだけ今回GO未受領のため停止している。

別件の最新main deploy34797490804/job103833308323が既存migration 20260913_210000_tcg_cardset_bundle_registration.sqlの「identity mismatch PM0264」で失敗したことをrootが原ログで直接確認。バックアップsalesanchor_db_20260914_105621.sql.gz/7.2M、後続Finalize health成功。公開App/APIはTLS検証有効のcurlでHTTP200、DB/Redis/Celery connected。Pythonの初回確認はローカルCA証明書取得失敗であり稼働不良には数えない。

同件はPR3496にも既に記録され、修正範囲判断待ち。APのButton変更と別の問題だが、配備前提が未解決のため今回GO依頼/マージ/本番反映を保留する。既存migrationの変更・商品名巻戻し・ガード迂回・同じ配備の無条件再実行は行っていない。根拠ap-release-prerequisite.json。AP実装・検収・保存済みと本番反映未実施を区別する。次は既存移行処理の復旧担当/範囲を確認し、復旧事実の確認後にAP番号付きGOへ進む。


### 2026-09-14 PM0264配備障害の復旧確認

修正PR3500のmain 70d145f090e122dd36e4a39b4928e13cc0dae613について、deploy34804164057/job103852603870がsuccess、03:57:47 UTC完了とGitHub APIで直接確認。原ログでは従前失敗の231番がDO/COMMIT成功、233/233まで完走しMigrations done、SA-19 smoke全成功、Verify deployment成功。事前バックアップsalesanchor_db_20260914_125456.sql.gz/6.7M。確認時点の公開App/APIはTLS検証有効のcurlで200、DB/Redis/Celery connected。

修正差分は既存商品の固定日本語名照合を外し、構造属性の照合を維持。対象の既存seedは非NULL値の保持等に変更。全CSV更新の保全や本番の商品名そのものは直接SELECT/往復試験していないため未検証。AP対象2ページ・共有21ファイルの基準から最新mainへの変化は0。PM0264による配備保留は解消。AP3497の最新main統合・確認と番号付きGOは別途必要で、今回マージ/本番反映は行っていない。根拠: ap-release-prerequisite.json recoveryVerification。前節は復旧前の履歴として保持する。


### 2026-09-14 本番反映指示後の統合確認

POから根拠確立後の本番反映指示を受領（逐語はap-release-prerequisite.json）。main95daf966を37193080へ通常統合、mainのdeploy34808959394成功を直接確認。基準2ページ/共有21のmain変化0、製品3hash不変。evidence-registryの追記競合は両親コミット全文を保持。初回の可変origin/main参照検算は並行更新により不一致となったため、固定した両親SHAで再確認して成功した。製品への独自変更なし。統合後の正式CIを確認中。scripts/check-process-artifacts.js:291–322は番号付きGO原文を要求しており、今回の指示を「GO #3497」へ改作しない。マージ/本番反映は未実施。


### 2026-09-14 GO3497受領・別件DB移行による再停止

GO原文「GO #3497」をPOから受領しPR本文へ逐語転記（記録時刻15:52 JST、対象af3734c9）。代理GOではない。直前確認で最新main180c0f38（PR3503）のdeploy34810423329/job103870490025が失敗と判明。234/234の20260914_140000_unify_tcg_products_to_public.sqlが、tenant_001.product_search_keywordsからpublic.products(tcg_uuid)への外部キー追加で「there is no unique constraint matching given keys for referenced table products」と停止。従前PM0264の231番は成功。バックアップ14:40/7.9M、Finalize health成功、root curlでApp/API200・DB/Redis/Celery connected。処理途中の297 upsertログをコミット済みとは断定せず、直接DB検査は未実施。

GO受領済みと配備可能性を区別し、APマージ/配備を停止。今回製品変更・新main統合・本番操作なし。別件修復を本GOの対象へ拡張しない。次はPR3503復旧担当を確認し、復旧成功後に最新main統合/製品照合/CIを再確認する。GO #3497は保持し再承認を要求しない。根拠ap-release-prerequisite.json newDeploymentBlocker。
