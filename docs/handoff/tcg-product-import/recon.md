# recon — 商品マスタ CSV取り込み

この文書は何か（専門用語なしの1行）:
商品マスタにCSVで商品をまとめて登録する機能を作る前に、いま何がどこにあるかを実測で調べた記録。

親（設計仕様書）へのリンク: ../../specs/product-master/README.md

- 仕事名: tcg-product-import
- 日付: 2026-09-05
- 対象ADR: ADR-154
- 担当: architect
- 状態: 以下は2026-09-05の調査記録。2026-09-10のテスト調査は末尾追補、設計は design.md を参照。

## 既存ADR検索結果

- ADR-154（対象ADR・照合ロジックのGAS移植） — 本テーマの制約。GASの実行順序を100%再現する決定は維持する。
- ADR-027（UI国際化） — 新規画面の文言は t("key") 経由必須。
- FEATURE-INDEX に csv / import 単独の項目は存在しない（実測: git grep -niE 'csv|import|商品' docs/adr/FEATURE-INDEX.md → 該当は在庫/商品マスタ行1件のみ）。
- ADR のファイル名は推測しない。design 便で ls により実名を確認してから引用する。

## 1. 全体像

- 画面の入口定義: frontend/src/App.tsx:78-84（super-admin ページの import）、:269 :274 :279 :284 :289 :294（Route の path）。super-admin のルートは6本。
- サイドメニュー: frontend/src/components/DesktopShell.tsx:190-194。saasAdminItems は3項目（tcg-line-import / tcg-supplier-quality / fx-rate）。
- 商品マスタ登録 API: backend/app/routers/tcg_product_master.py:1-12（5エンドポイント）。認証は require_super_admin、tenant_004 専用。
- 登録の実処理: backend/app/services/tcg_product_master_svc.py（703行）。本 recon では未読。design 前に読む。
- 登録の画面: frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:87-273（RegistrationSection）。呼び出し元は SupplierDetailView.tsx:115。引数は解析レビューの1行（AnalysisReviewItem）。
- データの流れ: 解析レビューの1行 → ドロワー → POST /tcg/products → tcg_products。CSV には解析レビューの行が無いため、この入口は使えない（観点6で対照）。

## 2. 共用部品

本 recon で「部品」とは、frontend/src/components/ 直下の再利用UIを指す。

- 表: frontend/src/components/DataTable.tsx（.css / .stories.tsx あり）
- ヘッダーの操作ボタン: frontend/src/components/HeaderButton.tsx
- ページ枠: frontend/src/components/PageLayout.tsx。使用例は frontend/src/pages/super-admin/FxRatePage.tsx:76（navKey で見出しを引く）
- 見出し下の道具列: frontend/src/components/ContentToolbar.tsx
- 引き出し・モーダル・空表示: Drawer.tsx / Modal.tsx / ConfirmModal.tsx / EmptyState.tsx
- 進捗・通知: frontend/src/components/loading/ProgressBar.tsx / Toast.tsx
- 文言: frontend/src/locales/ja.json:148 と en.json:148 が対になっている。参照元は DesktopShell.tsx:193。

## 3. 非共用部品

- ProductMasterDrawer.tsx:48 の SearchSelect は、このファイル内だけの選択入力。共用の Select.tsx が別に存在する。共用化の候補。
- ProductMasterDrawer.tsx:189-268 の登録フォームは、入力・重複確認・登録の3段階を持つが、解析レビュー専用に閉じている。CSV取り込みでも同じ3段階が要るため、共用化の候補。
- frontend/src/pages/super-admin/ProductMastersTab.tsx:314 は export されているが、import している箇所が0件、App.tsx にルート定義も無い。名称は商品マスタだが、中身は選択肢マスタ（8区分＋TCGシリーズ）の画面。

## 4. ルールの所在

- 文言の直書き禁止: ADR-027。守り手は Frontend lint。
- 本番DBの読み取り: docs/handoff/tcg-product-master-growth/card-templates.md:59-63（psql -f・リダイレクト・不等号の禁止）、:73（ssh + docker exec + default_transaction_read_only=on の定型）。
- 本番DBの書き込み: 同 :85-87。permit は PO が手で発行し、1コマンドで消費、30分で失効する。
- migration: 同 :114。マージ後のデプロイで run_all_migrations.sh が実行する。permit 不要。
- 数える前の除外: 本 recon の数え上げは観点7で仕分けた。

## 5. 維持の仕組み

守り手が在るもの:
- 文言の直書き → Frontend lint
- 本番DBへの直接書き込み → psql-write-guard と permit
- PR の書式・recon/設計の実在 → process-artifacts gate
- 作業前の身元と本店確認 → scripts/dev/executor-preflight.sh

守り手が無いもの（名指し）:
- 検索キーワードの品質。2商品以上に当たるキーワード、3文字以下のキーワードを止める機械が存在しない。
- 商品の必須項目。tcg_products の division_id / work_id / manufacturer_id / product_category_id は DB 上すべて NULL 可（実測）。既存フォームが必須にしているだけで、DBは止めない。
- CSV の中身。取り込み前に検査する機械が、そもそも存在しない。

## 6. 設計図との対照

| あるべき姿の項目 | 現状 | 判定 |
|---|---|---|
| サイドメニューに商品マスタ | saasAdminItems は3項目、商品マスタ無し（DesktopShell.tsx:190-194） | 不足 |
| データテーブル式の一覧ページ | ページ無し。部品 DataTable.tsx は在る | 不足（部品は流用） |
| ヘッダーアクションにCSVボタン | ボタン無し。部品 HeaderButton.tsx は在る | 不足（部品は流用） |
| ドラッグ＆ドロップの取り込み画面 | 無し | 不足 |
| 商品を登録するAPI | 在る（tcg_product_master.py）。ただし extraction_item_id と source_message_id が必須（:88-90）。CSVの行には存在しない | 不足（新しい入口が要る） |
| 重複チェック | 在る。判定は日本語名・作品・メーカー・カテゴリ・マーク・検索KWのみ（:179-188）。解析レビューに依存しない | 一致（流用する） |
| 取り込み前の確認 | ドロワーに3段階が在る（1商品単位・ProductMasterDrawer.tsx:135-172） | 一致（複数行へ拡張する） |
| 取り込み履歴 | tenant_004.import_jobs が在る（6行）。列は filename / raw_sha256 / message_count / provider_count / unresolved_count で、LINE取り込み専用。使用箇所は backend/app/routers/tcg_line_import.py と backend/app/services/tcg_line_import_svc.py | 余剰 → 残す。用途が違うため流用しないが、raw_sha256 の UNIQUE（同一ファイルの二重取り込み防止）を手本として採用する |
| 履歴の作り | analysis_runs（62行・実行1回=1行）と analysis_run_snapshots（1762行・1行ごと）の2階建て | 余剰 → 残す。CSV取り込みの履歴も同じ2階建てを採用する |
| ProductMastersTab.tsx | 未配線の残置物 | 余剰 → 除く。ただし本テーマの範囲外のため、別便で除く |

## 7. ノイズと境界

数え上げから外したもの:
- tenant_004 の退避テーブル（tcg_products_bak_20260901 / 20260903 / 20260904 / 20260904b / 20260905、product_search_keywords_bak 3本、product_exclude_keywords_bak 3本）、および analysis_results_gas_baseline_20260903 / analysis_results_pre_hist01_20260904。掃除は別テーマ。
- .stories.tsx / .test.tsx は共用部品の数え上げから外した（部品本体ではないため）。

今回「見ない」と決めた範囲:
- analysis_results への書き込み（別セッション担当）。
- 解析ロジックそのもの（ADR-154 の制約下にあり、本テーマで変更しない）。
- ワンピース63件のカタログ。main に存在せず、未マージブランチ release/tcg-onepiece-catalog にある。取り込み対象の分母には数えない。

## 実測の根拠（コマンドと生出力）

- git 側: origin/main の SHA を各手順で固定し、git grep / git show / git ls-tree で取得（CI-01 / CI-03 / CI-04 / CI-05b / CI-08）。
- DB 側: ssh -i ~/.ssh/manual-only/id_ed25519 ubuntu@app.salesanchor.jp から docker exec で PGOPTIONS に default_transaction_read_only=on を与えて psql -c で1クエリずつ実行（CI-06 / CI-07）。手順1で SHOW transaction_read_only が on であることを毎回確認した。
- 生出力は /tmp/ci05.txt /tmp/ci06.txt /tmp/ci07.txt /tmp/ci08.txt に保存し、設計パートナーが全文を検算した。

## 未読・未確認（推測で埋めない）

- backend/app/services/tcg_product_master_svc.py（703行）。tcg_products.category_class と is_active は NOT NULL かつ既定値なし（実測）だが、ルーターにもフォームにも現れない。このサービスが何を入れているかは未確認。design 前に読む。
- tcg_major_categories / tcg_series / tcg_manufacturers / tcg_product_categories の中身（コード体系）。テーブルの存在のみ確認済み。

## 2026-09-10 スキーマ修飾テスト調査（依頼6）

本追補の対象は静的検査だけ。上の古い画面・DB・API状態を現在の完了事実として再利用しない。
設計: docs/handoff/tcg-product-import/design.md §12。対象ADR: ADR-113、ADR-154。
基点: 87e5748b1dab5b062f991a263fa6ac692653877d

| ファイル | 全行数 | Git blob | text呼び出し行 |
|---|---|---|---|
| backend/app/routers/tcg_line_import.py | 666 | 73cf8607889b38c2d2c9e0eafb816e517effcea0 | 213, 261, 305, 347, 411, 445, 459, 475, 484, 497, 511, 531, 572, 604, 627 |
| backend/app/services/tcg_line_import_svc.py | 698 | b69e4562101fcde08cbc6aa71c8a92c739662e74 | 344, 368, 384, 404, 427, 439, 463, 516, 521, 539, 580, 606, 634 |
| backend/app/services/tcg_product_import_svc.py | 486 | cf9c28b5b86de610e79414be5c50bf7f0525a0f6 | 167, 181, 286, 384, 402, 425 |
| backend/tests/test_tcg_schema_qualification.py | 219 | 3df3de6ea6307326a20d5c37bddc16c8b0120dd3 | 検査コード |

商品サービスは全486行を読み、末尾まで確認。167行の動的表はLOOKUP_TABLESの4表。286行のSQLは後続文字列のJOINを含む。修飾は計7か所。
backend/tests/test_tcg_schema_qualification.py:28 の抽出は先頭文字列のみ、:55 の判定は直前14文字内の部分一致。後続JOINの未修飾と動的tableの未修飾を見落とすことを、原本を変更せずにメモリ上の変異で再現した。
.github/workflows/test.yml:114 のpytest-run-internalはbackend変更時に実行し、:241 の全体pytestで本ファイルを収集する。:250 の集約チェックは文書変更時にも成功するため、実行の証拠を区別する。

### 設計資料の検証

- 資料: schema-test-proposal.py.txt。SHA-256: cb7e8f26eca8cd5e1bb630f6e88b249c411f60fbb41a68949fdbda0e0757c7eb
- Python 3.12.8で資料の7テスト関数を直接実行し7/7成功。ruff check --config backend/pyproject.toml --no-cacheで成功。
- 検証はPython標準ライブラリでソースを読むだけ。pytest・conftest・DBは未実行。backendの製品テストには未反映。
- 修飾除去7例、動的表4正常/4異常、抽出回帰10例、未解決3例、動的前提変更3例を含む。詳細の再現手順はdesign.md §12と資料本文。
- 実行記録: /tmp/reports/GUARDS-PMG-DESIGN-20260910/schema-proposal-python312-results.json（初回試験の基点c3eaa3d5）。上記4ファイルの内容は本追補基点まで変更なし。
- 外部事例不要。Context7利用不可のため、PO許可の代替としてPython 3.12公式ast資料を直接確認。

### 既定入口での文書作業

mainとorigin/mainの一致を確認し、new-worktree.shでrelease/tcg-schema-test-designを作成。別手順でディレクトリとgit登録を確認後に移動した。
標準reaperは、未保存なし・origin/mainに統合済みを確認したrelease/worktree-preserve-designを1件回収した。未保存12件は保護された。保持指定の新機能はまだ実装されておらず使っていない。


## 2026-09-10 商品マスタ画面の引継ぎ確認

基点: origin/main a5e5a250aabe2e244ebf64c24bef40b5db40541c。PO「引き継いで良い」を受領した既存 release/tcg-product-import-ui を引き継いだ。実行役preflight成功。9e263fcaから上記基点へfast-forward成功。製品コードの編集、実取り込み、PR作成は未実施。

- 未追跡2ファイルを原本のまま保存: /tmp/reports/PRODUCT-UI-TAKEOVER-BACKUP-01/。manifest.jsonにSHA-256・サイズ・記録時刻を保存し、更新前後とも原本一致を確認。TcgProductImportPreview.tsx=7b49f98ad1c24940fff0d6d3678e24e162815d1c69af9a222ce8ae472a42057a、TcgProductMasterPage.tsx=b47367f75804526a90e6bdf0443e9f6206d0d3905dfc96a2d7fe7fe8ab04fa3d。
- frontend/src/pages/super-admin/TcgProductMasterPage.tsx:21 が参照する TcgProductImportPanel は存在しない。未追跡の実装は一覧とpreviewの2ファイルのみ。App.tsxのルートとDesktopShell.tsxのメニューに商品マスタ追加なし。build/test未実施。画面完成と扱わない。
- backend/app/routers/tcg_product_import.py:65 は /tcg/products/list。設計5-2の /tcg/products と異なる。:80と:92はis_active=TRUE条件を持ち、非表示商品を除外する。設計2の全件/DB全行数一致とは対象が異なる。本番の非表示件数は今回未測定。
- backend/app/tcg_config.py:20 の既定はtenant_004。リクエストごとのQA切替ではない。tenant_001試行に本番全体の環境設定を切り替える手順を推測で作らない。
- docs/handoff/tcg-product-master-growth/sword-shield-catalog.md §3に6商品分の未確定項目、§5にキーワード設計・衝突シミュレーション未実施の記載。古い記載だけで現在も未実施と断定しない。実取り込み前に最新証拠を確認する。
- GitHubでrelease/tcg-product-import-uiのPR検索は0件。#3416/#3419はMERGEDだがLINE取込・解析・配信の総合画面とその記録であり、商品マスタCSV画面の完成証拠ではない。

委任: PO「離席するのでcxastragoモードと同じ条件で権限委譲する」、商品マスタ画面・取り込み試行への適用確認に「合っている」を受領。有効化から24時間という条件を変更しない。対応する承認経路は未有効のため開始/終了日時や代理GOを自己発行していない。保護解除、secrets変更、別セッション起動の許可には転用しない。

関連ADR検索: docs/adr/FEATURE-INDEX.mdの在庫/商品マスタ領域とADR-154を確認。今回の値・件数はローカルファイル/Git/PR検索の観測。外部仕様や商品情報を今回検証したとはしない。


## 2026-09-11 画面実装とローカル検証

POが全件表示を承認し、離席中の完遂を依頼。実装は既存release/tcg-product-import-uiで継続。APIのis_active条件2箇所を除去し、商品作成/解析/DB定義は変更していない。frontend/src/pages/super-admin/TcgProductMasterPage.tsxの一覧とTcgProductImportPage.tsxの独立取込画面、features/tcg-product-import配下、App/DesktopShell/ja/enを追加更新。

| 直接実行した検証 | 結果・根拠 |
|---|---|
| 単体テスト | 2ファイル10件成功。PRODUCT-UI-FIX-VERIFY-02.txt。確認前commitなし、同じFile/digest、二重クリック1回、ファイル変更時確認破棄、全行拒否、通信失敗時再送禁止、pending中drop、権限拒否、ページング/検索、古い応答破棄 |
| TypeScript/本番ビルド | 成功。初回はテストのArray.atが既存ターゲット非対応で失敗、sliceへ修正して成功。設定は変更しない |
| frontend check:all | 成功。既存を含むlint警告219件あり、警告0とは称さない。PRODUCT-UI-STATIC-01.txt |
| Playwright Chromium | 2件成功。一覧→CSV確認→登録と非管理者拒否。API/authはモック、実登録ではない。PRODUCT-UI-E2E-01.txt |
| Python ruff | 一覧ルーターと新規PGテストの2ファイル成功。初回はキャッシュ書込権限エラー、許可済みworktree権限で同一コマンド成功 |
| 視覚確認 | /tmp/reports/product-csv-result.pngをAIが閲覧。結果件数・受付番号・一覧への戻りを表示。POの実機確認ではない |

DockerコマンドはこのMacに存在しないためローカルpytestは実行していない。追加PGテストは専用localhost jarvis_test_dbのランダムスキーマをトランザクション内で作り、最後にrollbackする。非表示行を含むtotal・ページ送り・大小文字検索・0件を実SQLで検証する。CIでの実行はこれから確認する。

未実施: PR/CI、本番反映、tenant_001の実取り込み、44件カタログの最新再照合とtenant_004登録。実装結果自己レビューは、承認済み全件条件・API認証の維持・読み取りSQLの範囲・CSV確認の固定・再送抑止を確認。CI/実DB成功前に完成とはしない。


## 2026-09-11 PR提出・CI初回指摘と44件資料の再照合

PR #3422: https://github.com/shingo-ops/salesanchor/pull/3422 。初回head2352081d。process-artifacts gateはPR番号付きGO記録が無いため拒否（job103075806588）。委任依頼は保存済みだが対応承認経路未有効。迂回やPO原文作成は行わない。

初回test-schema-dup gateは、PG回帰テストが本番表定義を2箇所独自に持つ点を拒否（job103075805890）。a9210be1で既存の20260831_110000_create_tcg_analysis_tables_t004.sqlと20260903_180000_tcg_products_mark_en_t004.sqlを読む方式へ修正。ランダムな専用schemaとrollbackは維持し、正式migration/CIガードを変更していない。修正後CIは確認中。

44件資料の外部確認（2026-09-11、商品情報の一次資料。導入成功事例ではない）:

| 対象 | 観測事実 | 出典・適用限界 |
|---|---|---|
| 候補#7 トイザらス限定セット | 発売日は2019-11-29と公式記載 | https://www.pokemon-card.com/info/2019/20191110_002165.html 。商品情報の発売日欄。キーワード/既登録有無の根拠にはしない |
| 候補#8 セブン限定セット | 発売日は2019-11-29と公式記載 | https://www.pokemon-card.com/info/2019/20191025_002144.html 。商品情報の発売日欄 |
| 候補#37 コロコロ版 | 公式商品情報の発売日は2022年1月15日頃。配送は2022年3月下旬頃/8月下旬頃。候補表の2021-12-17は通常版からの仮置きで、公式の商品情報と一致しない | https://www.pokemon-card.com/info/003230.html 。発売日と配送日を別に扱う。「頃」を確定日へ変換して登録しない |

候補全44件の再確認完了ではない。#6/#25/#31その他の最新照合、現在DBとの重複、キーワード衝突、QA実行経路、バックアップを未確認のまま実登録しない。既存カタログ正本を本便で上書きしない。


## 2026-09-11 CI確定・承認待ち

PR #3422のhead1fd8a4d0244197d6d208e047b3b465d5cdb26e39でCIは40成功・6対象外skip・1失敗。backend job103077025941は2545 passed / 93 skipped / 302 warnings、PostgreSQL用環境変数ありの全体試験を確認。個別試験名は静粛ログに出ないため、新規試験単独の実行ログとは区別する。test-schema-dupの拒否は解消済み。生ログ: /tmp/reports/PRODUCT-UI-CI-PYTEST-FINAL.log。

唯一の失敗はprocess-artifacts gate job103077053336。実際の番号付きGOを受領してからPR本文へ転記する規則による拒否。PO原文GO #3422は未受領。代理承認の経路も有効化されていないため代筆・迂回はしない。生ログ: /tmp/reports/PRODUCT-UI-CI-APPROVAL-FINAL.log。

実装・ローカル検証・上記headの技術CI・PR提出は完了。マージ、本番反映、tenant_001試行、tenant_004の44件登録は未実施。次は番号付きGO受領後、最終headのCI再確認、公式マージ・配備確認。実データ投入は候補情報/重複/キーワード/QA経路の確認が別途必要。


2026-09-11 最終再検査追補: PR #3422 head e2f1063d（前headから文書3件のみ変更）のCIは38成功/6skip/3失敗。backend job103078793511は2544 passed/93 skipped/1 failed。失敗は既存test_inventory_parser_llm_real_api.py::test_real_gemini_call_returns_structured_itemsで、Gemini APIがHTTP429とYour prepayment credits are depletedを返した。集約pytestも失敗。GO記録欠落も継続。前headの2545成功を最終headの成功と混同しない。ログ/tmp/reports/PRODUCT-UI-CI-PYTEST-REPEAT.log。課金・secrets・CI変更、無意味な再試行、マージ/配備は実行しない。外部サービス復旧と番号付きGOが必要。この追補はローカル文書commitに保存し、再CIを無用に起動しないためpushは保留。PR本文には同じ停止理由を反映する。


2026-09-11 08:06 JST（受領後記録時刻）: PO原文「GO #3422」を受領。PR本文へ本人の承認を転記する。Gemini残高の復旧は未確認で、既存実API試験の失敗は未解消。番号付きGOと全検査成功を区別し、マージ/配備/実登録はまだ行わない。課金やCI設定は変更しない。


2026-09-11 本番反映再開: PO原文「商品マスタの本番反映を実行、離席するので最後まで進めてくれデプロイ反映を完了条件とする」。GO #3422は受領済み。外部API停止は別PR #3425の3.1/キー変更とdeploy成功で対応済み。main4774d774を2a85d3d2へ統合。台帳2件はmain全文と自分の追記を保持、商品画面/APIの承認blob不変、日英両側の変更保持を照合。今回の完了条件はマージ・自動deploy成功・本番応答と配布資産確認。CSV実登録・tenant_001試行・44件本登録は本便対象外。最新CI確認中。


## 2026-09-11 商品マスタのメニュー配置

PO原文「その前にサイドメニューから開ける状態にしてくれ、saas管理者メニューの解析精度管理の下に配置」。基点e81dd3ecのDesktopShell.tsx:190-195では商品マスタがSaaS管理者配列の先頭に存在し、既存routeも本番配布済み。ja.jsonのnav.superAdminTcgSupplierQualityは「解析精度管理」。

差分設計: DesktopShell.tsxの既存商品マスタ項目1行を解析精度管理の直後へ移動する。順序は取込・解析・配信、解析精度管理、商品マスタ、為替レート管理。既存to=/super-admin/tcg-product-master、labelKey、isSuperAdmin条件、他3項目を維持。API・DB・翻訳キー追加なし。理由はPOが指定した場所から既存画面を見つけられるようにするため。既存先頭維持は希望位置と異なるため不採用。

受入は指定順序・項目4件各1回・既存URL/権限制御の維持を差分で照合し、対象lint/buildと既存CIを確認する。並べ替えをなぞる新規テストは増やさない。守り手はDesktopShellの既存ナビ表示とfrontendのnav/i18n/型チェック。リスクは表示位置が変わることのみで、誤った場合は当該1行を戻すPRで復元できる。外部事例は不要、自社メニュー実物とPOの位置指定で判断可能。ライブラリ/API仕様変更なし。

同一AIのPlanner→Architect自己審査APPROVE（この1行の移動のみ）。独立レビューや番号付きGOではない。新規PRの正式GOは別途必要。新メニューの本番配置は未反映。


商品マスタ配置PR #3429提出済み: https://github.com/shingo-ops/salesanchor/pull/3429 。commit6e289bd9、製品変更はDesktopShell既存1行移動。対象eslint/build/台帳/diff成功、既存4項目と移動先/権限維持を自己レビュー。CI確認中、番号付きGO未受領、本番配置は未反映。生報告/tmp/reports/PRODUCT-MENU-PR-01.txt。


## 2026-09-11 発売日順と作品タブの調査

対象: 商品マスタ一覧の追加設計。基点 b6644187c55a3dc58df0bc7e7a4dbba870c186a9、専用ブランチ release/product-master-date-tabs-design。preflight成功、開始時差分0、HEAD対origin/mainは0/0。報告は /tmp/reports/TH-PRODUCT-DATE-TABS-DESIGN-PREFLIGHT.txt と TH-PRODUCT-DATE-TABS-ENTRY.json。既存台帳は古い状態を含むため完了の証明に使わない。公式ledger-viewで本テーマの作業登録を確認する。

### 観点1 全体像

- backend/app/routers/tcg_product_import.py:65: GET /tcg/products/list。:70 のquery/limit/offset、:76 のrequire_super_adminを使い、:93 は商品コード降順。countとitemsは同じ検索条件で、商品is_activeの除外なし。
- frontend/src/pages/super-admin/TcgProductMasterPage.tsx:20: 1ページ50件、:26 の状態はquery/pageのみ、:35 のURLでサーバーへページ指定。:45 はrelease_date列、:50 は検索欄。作品絞込み・タブはない。
- migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:82: 商品表の定義。release_dateはDATEかつNULL可、work_idはUUIDかつNULL可、codeは一意。商品一覧で取引の売却日時は使っていない。

### 観点2 共用部品

- frontend/src/components/Tabs.tsx:37: items/activeKey/onChange等の契約。:61 のtablist、:76 のtab、aria-selected、buttonを備える。frontend/src/components/Tabs.css:24 の既存横スクロールと色変数を再利用できる。
- backend/app/services/tcg_product_master_svc.py:85: work_idの参照先はTCG_SCHEMA.tcg_series。migrations/20260902_110000_tcg_classification_masters.sql:39 にid/code/display_name/alt_name/is_active、:94 に11作品のseed定義。IP001/Pokemon/ポケモンとIP002/One Piece/ワンピースがある。これはリポジトリ内定義の11件であり、本番の現行件数を実測したものではない。

### 観点3 非共用部品・使えない入口

- backend/app/routers/tcg_product_master.py:141: registration-formはextraction_item_idとsource_message_idが必須。backend/app/services/tcg_product_master_svc.py:67 で元明細の存在・未解決を検査する。無関係なIDや空文字で作品候補だけを取得する用途には使えない。
- backend/app/routers/super_admin_tcg.py:63: 同名に近い別のシリーズAPIはpublic.tcg_series_masterを読む。work_idの参照先と異なるため本設計では利用しない。

### 観点4 ルールの所在

- docs/adr/ADR-113-two-mode-dev-flow.md:80: 実物確認→設計→整合検査→実装の順序。本書の調査後、design.md §14を作成して自己審査する。
- docs/adr/ADR-027-ui-internationalization.md:50: 業務データの翻訳は対象外。固定UI文言は日英キー、作品名は既存DBデータとして扱う。ADR-144の共通部品再利用に従う。ADR-154の登録・重複照合・解析ロジックは本変更の対象外。
- backend/app/tcg_config.py:23: TCG_SCHEMAの形式検査。入力からスキーマを選ばせず既存設定を使う。QAはtenant_001、本番はtenant_004という現行境界を維持する。

### 観点5 維持の仕組み

- backend/tests/test_tcg_product_list_pg.py:18: 専用DB/localhost確認、:26 から一時スキーマをrollbackする実PGテスト。現在は全件3件・検索・コード順ページングを検査する。発売日/作品の検査はまだない。作品表のmigrationは現在のfixtureに含まれない。
- frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx:14: 非管理者、:19 ページ/検索、:28 遅着応答を検査。frontend/tests-e2e/tcg-product-import.spec.ts:6: 一覧からCSVへの既存導線と非管理者拒否。新契約ではモックのworks追加が必要。
- .github/workflows/test.yml:222: RLS_TEST_DATABASE_URL/:224 RLS_ADMIN_DATABASE_URLを用意し、:241 でpytest全体を実行。skip0確認が必要で、集約チェック成功だけでは追加PG試験成功としない。

### 観点6 設計図との対照

| 依頼・既存条件 | 現状 | 分類 |
|---|---|---|
| 発売日の新しい順 | 商品コード降順 | 不足 |
| 作品タブで絞る | 作品情報はDB定義にあるが一覧UI/APIに指定なし | 不足 |
| 絞込み後も新しい順 | 作品絞込み未実装 | 不足 |
| 管理者限定・全件管理・検索・50件ページ・CSV導線 | ページ/API/既存§13契約に実在 | 一致・維持 |

今回新たに削除を検討する余剰はない。根拠: frontend/src/pages/super-admin/TcgProductMasterPage.tsx:48 の既存管理操作と本設計の境界。

### 観点7 ノイズと境界・未確認

- backend/app/routers/super_admin_tcg.py:2 のpublicのシリーズとtenantの作品を区別。migrationsのseedを本番の現在値と断定しない。非公開移植リポジトリのコード・文書は参照/転送していない。
- 本番DBの実件数、NULL日付件数、work_id未設定/孤立件数、性能、実画面は本調査では未測定。設計はこれらの件数に依存せず扱いを定義し、実装後の隔離PG試験とtenant_001画面確認を完了条件とする。本番データの修正・migration・取込実行は対象外。
- Context7 MCPは公開ツール一覧に存在せず利用不可。起動指示の代替許可により2026-09-11にPostgreSQL 16 ORDER BY、FastAPI query/extra data types、SQLAlchemy 2 textの公式資料を直接確認。出典と適用はdesign.md §14に記す。製品のテストは今回未実行。

次: docs/handoff/tcg-product-import/design.md §14の詳細案をPO確認へ渡す。独立したレビューや実装完了とは扱わない。
