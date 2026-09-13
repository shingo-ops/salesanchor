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

### 2026-09-11 実装カード準備の実測

PR #3431マージコミットa66e9382を新しい基点6c55e40dが包含することをgit merge-base --is-ancestorで確認。対象製品7ファイルは両コミット間の差分0。公式new-worktreeでrelease/product-master-date-tabs-implを作成、実在/ブランチ/差分0/preflight成功を確認。Docker CLIは実在するがdocker infoは接続先socket不存在でexit1。Python3.12は/usr/local/bin/python3.12、npm/nodeは実在。製品試験・依存導入は未実行。報告は/tmp/reports/TH-PRODUCT-TABS-IMPL-WORKTREE.txt、TH-PRODUCT-TABS-IMPL-PREFLIGHT.txt、TH-PRODUCT-TABS-DOCKER.txt。

TH-PRODUCT-DATE-TABS-IMPL-01正式検査: card-lint exit0（L24の長行警告8件のみ）、24手順の連続性、19コマンドのcd先実在、入力フルパス実在、未記入目印0、停止/再開/報告経路、承認済み7製品ファイル境界を同一AIで手動照合。独立レビューではない。証拠 /tmp/reports/TH-PRODUCT-TABS-CARD-LINT.txt / TH-PRODUCT-TABS-CARD-REVIEW.json。task-state/diff成功。カード作成・検査済み、実装役への提示待ち、製品コード未変更。

### 2026-09-11 発売日順・作品タブの実装とローカル検証

POが実装役1名への委任を承認し、TH-PRODUCT-DATE-TABS-IMPL-01を実行。開始時preflight成功・指定ブランチ一致・未保存差分0。設計§14の7製品ファイルだけを変更した。APIはwork_idのUUID入力、同一の検索/作品条件によるcountとitems、release_date DESC NULLS LAST/code DESC、検索やページに独立するworksを追加。画面は既存Tabsを使い、query/作品の併用とページリセット、最新応答のみ反映、候補保持/選択消失保持、works不正時エラーを実装。DATEを時刻に変換せず、CSV/認証/全件管理を維持した。

| 条件・検証 | 直接実行した結果 |
|---|---|
| AC1〜5 | PG/HTTP試験を既存隔離スキーマ・rollback・公式作品migrationで追加。逆転するコードと日付、未来日、同日2件、NULL/孤立、作品×検索、候補4種、53件ページ、別スキーマ、UUID/権限を検査する内容。Docker接続不可という準備時実測に従い、本便では未実行 |
| AC6〜7・日英/DATE単体 | TcgProductMasterPage.test.tsxは14 passed。失敗/遅着/不正works/消失した選択作品も検査。APIはモック |
| AC8 | Chromium E2E 5 passed（21.2秒）。日英名称/fallback、2作品切替、狭幅スクロール、Tab/Enter選択、CSV導線、非管理者拒否。API/authモックで実登録なし |
| backend静的 | make lint-ci exit0、対象Python2ファイルruff成功。mypy診断153件が残る（変更ルーターの診断0）。既存Makefileの警告扱いによる終了0であり、全型検査合格とはしない |
| frontend静的・ビルド | check:all exit0（0 errors/221 warnings）。本試験の日本語fixture由来3警告を規約どおり修正後、対象eslint --max-warnings=0成功、14単体再成功。build成功。全体の既存警告0とはしない |
| AC9 | 正式PG skip0、CI、tenant_001の実API/実画面と性能、配備は未実施。ローカル結果だけで完成/マージ可能とはしない |

生報告: /tmp/reports/TH-PRODUCT-DATE-TABS-IMPL-01.txt。画像: /tmp/reports/product-tabs-ja.png、product-tabs-en.png、product-csv-result.png。5173は別worktreeのサーバーが使用中と実測したため、担当間で同じE2Eの専用PORT=5189を確認し、空き確認後に起動した。既存サーバーや設定ファイルは変更していない。待機中のps読み取りはOSに拒否され、再試行せず報告した。依存導入/検査自体の権限拒否はない。

製品7ファイルと本テーマ記録3ファイルをローカル保存する。push/PR本文変更/GO生成/マージ/配備は本カードの対象外。次は実装コミットの差分確認後、準備PR #3433への公開便、正式PG/CI/QAの検証へ進む。


### 2026-09-11 PR #3433 の公開・マージGO受領

PO原文: 「進めてくれ GO#3433」。受領記録時刻 2026-09-11T08:11:21.255931+00:00（記録時の実測であり発話時刻の推定ではない）。対象はPR #3433の商品マスタ発売日順・作品タブ。ローカル実装12e6b13cを確認し、main 7606ca9a041e315b81040373e8f4ddebbc562133へ追従。競合はtasks/todo.mdの2テーマの行で、本テーマの実装行とmain側の金型化行を保持。製品ファイルの競合なし。公開後の実PG/CI、配備結果とtenant_001実接続確認は、GOの受領と分けて記録する。


PR #3433 CI追補: f09d3659の実DB CI（run34578271232）は2566 passed/95 skipped、process-artifacts成功。試験テーブル独自複製をschema gateが拒否したため、cffe3b2eで両隔離schemaを正式migrationから生成する形へ修正。ルール変更・例外追加なし。対象ruff/正式schema gate成功。mainのPR #3434（2ac5e81a）を追従し、別テーマ証跡の追記を保持。最新統合HEADのCIを再検証する。追従前の成功を最新HEADの合格に流用しない。tenant_001実接続・人の確認は未実施。報告 /tmp/reports/TH-PRODUCT-3433-SCHEMA-FIX.txt、TH-PRODUCT-3433-PG-CI-INITIAL.txt。


### 2026-09-11 空のサンプルCSVと登録者情報の再開調査

基点: adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b。git ls-remoteのmainとorigin/main一致。PR #3433はGitHubでMERGED、merge ec173b7e31f079b10993a60abcdae456e516b319、mergedAt 2026-09-11T08:26:02Zを再確認。本番配備の再検証は未実施。
引き継ぎは /Users/tanizawashingo/Documents/SalesAnchor-handoffs/SA-CSV-RESUME-20260911-201030/README.md を読んだ。前便の再現・配備報告と今回直接の検証を分ける。関連runbookはdocs/runbooksのファイル名検索で本CSV専用が見つからず、既存design/reconを継続先とする。

#### 1. 全体像

frontend/src/pages/super-admin/TcgProductImportPage.tsx:14 が管理者だけPanelを表示。frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx:28 にpreview、:37にcommit、:65にファイル選択領域。backend/app/routers/tcg_product_import.py:181が登録入口。ダウンロード操作は現状ない。

#### 2. 共用部品

本調査の部品は画面部品・CSV定数・認証依存。frontend/src/components/Button.tsx:56が標準Button、ContentToolbar.tsxが操作配置。backend/app/services/tcg_product_import_svc.py:40に列定義10個、:54に必須5個、:119にparse_rows。backend/app/auth/dependencies.py:453-481はUserを受け取りUserを返す。backend/app/models.py:22-34にid/email/is_super_admin。

#### 3. 非共用部品

backend/app/routers/tcg_product_import.py:199だけが登録者をuser.getで読む。backend/tests/test_tcg_product_import.py:52,70,84は辞書を認証fixtureにしている。成功commit HTTP試験がない。frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:7のCSV fixtureは2列で、画面試験用の偽物でありCSV仕様根拠にならない。汎用CSV基盤への拡張は不要。

#### 4. ルールの所在

docs/adr/ADR-113-two-mode-dev-flow.md（handoff、How忠実実装）、ADR-027（日英）、ADR-154（解析移植）とfrontend/AGENTS.md、backend/AGENTS.md、docs/STANDARD-WORKFLOW.md:76の既存延長区分を照合。本CSV限定修正は解析移植を変えない。既存designの「ADR-154によりcreate_productを変更しない」という境界も保持する。docs/specs/design-system/component-ssot/page-header-v2/design.md:45以降の本文補助操作に合わせてButton secondaryを採用。

#### 5. 維持の仕組み

backend/tests/test_tcg_product_import.py:28以降は未認証/preview/指紋不一致/拡張子を守るがUserによる成功経路に穴がある。.github/workflows/test.yml:206-241はPG込みpytest、frontend-check.yml:34はcheck:all。既存frontend単体とfrontend/tests-e2e/tcg-product-import.spec.ts:12以降を拡張する。テンプレートと列定義の一致は未実装であり今の守り手はない。

#### 6. 設計図との対照

| 合意した姿/既存契約 | 現状 | 判定 |
|---|---|---|
| 10列空CSV＋入力説明 | Panel:65に選択/書式のみ、保存導線なし | 不足 |
| 認証済み管理者のCSV登録 | User返却に対してrouter:199でget | 不足 |
| 確認したFile/digestで明示登録 | Panel:37-50 | 一致（UI契約） |
| 失敗後の無条件再送を避ける | Panel:49のuncertainロック | 一致 |
| 見本商品0行 | 新設ファイル未実装 | 不足 |

今回の範囲に除去対象の余剰はない。親仕様の全機能再監査ではない。

#### 7. ノイズと境界

backend/app/services/tcg_product_import_svc.py:469の商品登録後、:476のrecord_rowが別commit（:417）。履歴完全追跡・全件rollbackは保証しない。digest一致は人の承認証明ではない。44件・3シート・LINE委任を今回の登録成功や操作権限へ換算しない。台帳には古いIN_PROGRESSが残るが、PR #3433のDONE/mergedは今回直接確認した。migration用worktreeの未保存はmigration2ファイル、product-tabs-table-designのstatusは空で、本設計2文書の新しい予約は確認されなかった。他者の編集は変更しない。

#### 今回直接行った隔離検算

現行ソースをPython ASTで取り出し、decode_csv/parse_rowsのみをcsv/ioとともに実行。BOM＋10列見出し＋CRLFの入力は rows=[]、file_errors=[]。商品行0・エラー0をassertしてPASS。CSV製品ファイルはまだ作成していない。
同じ基点のcommit_import_endpoint本体をASTで取り出し、IOだけAsyncMockへ差替え、属性を持つSimpleNamespace(email,id)で実行。AttributeError（get無し）を再現、commit_importのawait0回をassert。HTTP・本物のUserモデル・認証・DBを実行した証拠ではない。実装後AC5で本物のUser/HTTPを検証する。pytestは実行していない。

#### 仕様参照と限界

Context7 MCPは利用可能ツール一覧に存在しないため起動指示の公式資料代替を適用。2026-09-11に直接確認:
- https://vite.dev/guide/assets#the-public-directory — public資産は開発時ルート配信、build時distへそのままコピー。frontend/vite.config.ts:11以降もpublicDir/baseの変更なし。
- https://html.spec.whatwg.org/multipage/links.html#downloading-resources — 同一オリジンのdownload指定による保存。
- https://developer.mozilla.org/en-US/docs/Web/API/HTMLAnchorElement/download — download値だけでは実際の保存成功を保証しない。E2Eで実ファイルを確認する。
外部導入事例は不要。仕様の可否確認を、実装後の動作成功と取り違えない。

保存結果: 設計文書4ファイルを8a5cb636として専用releaseブランチへコミット・pushし、草案PR https://github.com/shingo-ops/salesanchor/pull/3436 を提出。task-state/diff検査成功、製品ファイル変更0。最初のcommit要求はhookが作業場所指定を本店mainと判断して拒否し、git操作前に停止。明示cdで専用releaseブランチを読取確認後、同じ文書だけを通常経路でコミット成功。ガード変更なし。設計合格と詳細案PO承認/製品実装/マージは区別する。正式実装カードは実装承認後に作成・card-lintと人手照合を経て発行するため本便は未発行。


### 2026-09-12 正式実装カードの検査

PR #3436 d4f5f86fのCIは実行分すべてSUCCESS、製品試験は対象外SKIPPEDと直接確認。mainはgit ls-remoteでadc8bc4dのまま。reaperの事前確認とnew-worktree実行はいずれも削除対象0。公式作成コマンドが終了した後、別操作でrelease/product-import-template-implのディレクトリ・git登録・HEAD/origin/mainの一致・status空を確認した。実装先preflight成功。本店のAGENTS.mdや既存変更は保持。

カード: card-template-impl.md。card-lint exit0、違反0、L24長行警告4件。18手順の連続性、全cd先の実在、既存7製品ファイルと新規1資産、設計/recon入力、未使用報告先、未作成venv、英字を含む未確定目印0、END OF CARDを機械補助で確認。L20/26/27/28/32等の未実装項目は同一AIで本文照合した。設計8ファイルとAC1〜7を保持し、範囲内編集/検査失敗修正、DB未検証、秘密の伏せ方、停止/再開/報告を明記。独立レビューではない。

今回の実装用作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl。製品コードは未変更、実装担当は未起動、実装カードは作成・検査済み。Docker情報照会はソケット不在でexit1。カードでは既知条件としてpytestを実行しない旨を明記し、正式CIでの実DB検査を後続へ残した。


### 2026-09-12 実装カード01の報告保存停止と02への訂正

実装役は01手順6の報告保存で停止。実行役報告では、規則文書をPython文字列に埋めて保存する要求がPreToolUseに拒否された。報告対象は規則本文で実pushは要求していない。親がgit status空と01報告0バイトを直接確認。製品編集・依存導入は未着手。停止をカードの出力保存方式不足として扱った。

設計担当の確認: cat AGENTS.md frontend/AGENTS.md backend/AGENTS.md を未使用報告へ直接リダイレクトする通常の読み取り保存はexit0、19080バイト。規則内容の言換え・ガード変更・権限変更なし。証跡 /tmp/reports/CARD-PRODUCT-CSV-REPORT-PROBE-20260912.txt。

正式カードを02へ更新し、報告ファイルを最初に排他作成、各コマンド出力を直接追記する手順へ訂正。旧01空報告は保持。製品8ファイル/受入基準/権限拒否時停止を変更しない。委任済みの同一実装役へ02を渡す。


### 2026-09-12 カード02の実装結果・設計担当による差分確認

実装役csv_card_executorは専用release/product-import-template-implへ指定8製品ファイルの実装を残した。コミット/公開/マージ/本番操作なし。空CSVの新規1ファイル＋既存7ファイルを親がgit status --short --untracked-files=allで直接確認。

実装役の生報告: /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt。親は該当出力を読み、単体13 passed、E2E7 passed（10.1s）、check:all exit0、build exit0、配布CSV148バイト一致、make lint-ci exit0、diff --check exit0を確認した。これらのコマンドを実行したのは実装役であり、設計担当が再実行した結果ではない。単体初回のfs URL失敗は許可範囲内修正後13件成功。既存frontend警告218件、mypy診断153件が残り、現行Makefileはmypyを警告扱いにする。対象routerの診断は0。

親が直接実施した検査: CSV実バイトがBOM＋CSV_COLUMNSの10列＋CRLFに等しく、商品行0であることをPythonでassert。productCsvの日英キー一致をassert。製品差分を読取確認しUser型/属性アクセス、既存認証条件維持、API未呼出の保存操作、既存確認/再送ロック維持、回帰試験の期待値を照合。E2E画像保存先が未作成のCI環境で失敗する点を見つけ、実装役が同じE2Eファイル内でmkdirと排他保存へ修正した。日英390pxの保存画像を親もview_imageで直接見て欠け/横はみ出しなしを確認した。

手順18追加のPython2ファイルruffは、実装役の通常sandboxで.ruff_cacheの一時ファイル作成が拒否されexit2。実装役は停止した。親が同じruff checkを通常のrequire_escalated権限審査に通して実行しAll checks passed/exit0を直接確認。ガード・キャッシュ設定・製品コードの変更なし。失敗出力は02報告にそのまま保持。

差分確認時の8ファイルSHA256と親の検証範囲: /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02-parent-review.json。画像: /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02-template-ja-66adc185-e167-4b5d-9e97-f6b3dc219d84.png、同template-en-c57b8428-c8dd-47c2-93f9-4d3ef104714e.png。

判定: 設計範囲の差分確認で追加指摘なし。製品リリース承認ではない。AC1〜4のローカル検証、AC7のfrontend部分まで完了。AC5〜6の本物User/HTTP試験は追加済み・未実行（修正前に戻した失敗確認も未実行）。Docker不在に従いpytest・実PG・CI・本番QAは未実施。マージGO・実データ投入・再解析・配信は未承認/未実施。次は製品差分の保存・PR公開と正式CI検証を別便で行う。


### 2026-09-12 公開前の改行検査

新規CSVをstageした後の通常git diff --cached --checkがCRLFを末尾空白と判定した。前便は未追跡資産がgit diff --check対象外であった。設計必須のCRLFは維持し、Git公式core.whitespaceのcr-at-eolを当該検査コマンドだけに指定。blank-at-eol/blank-at-eof/space-before-tabは保持。親が同一stage差分へ直接実行しexit0を確認した。永続Git設定/ガード/CI/製品変更なし。Context7未提供のため許可された代替で https://git-scm.com/docs/git-config のcore.whitespaceを直接確認。実資産の148バイト・BOM/CRLF/10列/0行検査は別に成功済み。


### 2026-09-12 製品PR #3438の公開

公開カード01により実装役が製品781257a5、main追従d21b0d26、設計根拠ff008f180e150be2241ad7d6d2d2f292a439f900を保存しpush。PR https://github.com/shingo-ops/salesanchor/pull/3438 を正式作成した。親がgh pr list/viewで番号・HEAD・8製品＋4文書の12ファイルを直接確認。main追従の追加は独立した委任文書4本、製品8ファイルは前便検証時のSHA256と一致することを実装役が再確認。未保存差分0、公開報告は /tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01.txt。

公開中の停止: 通常のstage差分検査のCRLF判定は前節の方法で解消。commit要求の前にログ開始処理を置いたためhookが本店mainと判断して拒否した件は、ログ保存とgit操作を別要求にし、先頭を実在する専用worktreeへのcdとした同じcommitで成功。保護設定の変更なし。

CI process-artifacts gateはFAILURE。詳細ログ取得はghのローカルキャッシュ作成がoperation not permittedで停止。再試行/ガード変更は行わず、親は公開PR本文と実ファイルに既存export検証関数を適用して別途照合した。設計構造・維持の仕組み・引用パスのエラーは各0、GO記録欄欠落を検出。証拠 /tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01-parent-gate.json。これはローカル検査結果でありCI失敗ログではない。POのマージGO未取得につき記録を創作しない。

最終CI確認: 親がgh pr view 3438のstatusCheckRollupを直接取得。HEAD ff008f180e150be2241ad7d6d2d2f292a439f900、OPEN、SUCCESS40/SKIPPED6/FAILURE1。pytest-run-internalとpytest (SQLite + PostgreSQL RLS)はSUCCESS、run34661709205。失敗はprocess-artifacts gateのみ。対象外skipを試験成功と数えない。保存 /tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01-parent-final.json。CIの全suite実行定義は .github/workflows/test.yml:206、pytest -qは同:241。HTTP対象ファイルも全suiteに含まれるが、個別ケースログ・総件数・skip件数は取得していない。DB書込をモックにしたHTTP試験を本番商品登録成功とはしない。

受入上の残件: AC5の修正前user.getへ戻した回帰失敗の実行確認は未実施。通常の全suite成功からこの確認まで完了したとは言わない。設計条件を勝手に削除せず残す。マージ判断前にこの確認とprocess-artifacts詳細確認を行い、その後PO GOを受領する。製品PR提出・CI確認まで実施済み、全受入完了/マージ可能/本番反映済みとは宣言しない。LINE委任も有効化待ち。


### 2026-09-12 残件検証の続行

PO返答原文「次を進める」を、残る回帰確認と失敗ゲート原因確認の続行として受領。マージGOとは扱わない。実装worktree preflight成功、HEAD ff008f18/未保存差分0を直接確認。最新origin/mainは66b41766で独立テーマの文書追加のみ、製品更新なし。本店の未保存変更には手を触れない。正式LINE委任文書もdraft/開始終了未設定で有効化待ち。

前回のログ取得停止はghキャッシュ書込のsandbox制限。親が同じPRの通常ログ取得をrequire_escalatedの正規権限審査へ提出し成功。設定・キャッシュ場所・ガードの変更なし。最新失敗run34661932465/job103466046948の実ログは「PR本文にGO記録セクションがありません」。前便のローカル推定を実ログで裏付けた。保存 /tmp/reports/SA-CSV-REMAINING-GATE-20260912.txt。

同じ正規経路でBackend CI run34661709205/job103465409882の成功ログも取得。2601 passed / 95 skipped / 301 warnings / 110.42s、対象routerのカバレッジ96%。これは既存全suite/PG実行結果であり修正前対照の結果ではない。保存 /tmp/reports/SA-CSV-BACKEND-CI-20260912.txt:1066。個別case名は集約ログに出ない。

AC5対照検算: 既存実装役csv_card_executorが /tmp/reports/CARD-PRODUCT-CSV-AC5-CONTRAST-01.py を実行しexit0。製品ファイルは変更せず、既存test_commit_with_real_userを直接await。元main adc8bc4dのexecuted_by式とASTを照合し、対象関数のメモリ上codeだけを旧user.get式へ交換。emailあり/id代替/両方空の3ケースすべてAttributeError「User object has no attribute get」を再現し、finallyで現行codeへ復元後は同じ3ケースすべて既存HTTP assertion成功。旧式以外の関数本体の一致と変更式1箇所をassertした。

親は検算スクリプト・結果JSONを直接読み、6結果、io_attempts空、8製品SHA256前後一致をassert。HEAD ff008f18と未保存0も実装役が確認。追加mockはAuditMiddleware._record_data_access/_record_auth_eventで両条件共通。認証require_super_admin/対象HTTP assertionは変更せず、全mock・関数code・依存上書きの復帰をassert。実装役がテスト用venvへ既存requirementsを導入し、検算時は環境変数をテスト用に限定、dotenv読み込み・DB接続・外部通信を拒否して試行0を確認。

証拠: /tmp/reports/CARD-PRODUCT-CSV-AC5-CONTRAST-01.json（前後ハッシュと6ケース）、同.txt（実行出力）、同.py（検算手順）。Docker不在につきpytestを実行した結果ではない。これは既存試験関数直接呼出によるASGI内HTTP対照検算であり、CI全suiteの2601成功/95skipとは別の検証。DB書込・監査記録はmock、本番登録成功の証明ではない。AC5の修正前失敗確認の残件を解消。

判定更新: 限定設計§15の検証残件とCI失敗原因確認は完了。設計担当による自己審査・読み取り確認であり独立第三者レビューと称さない。POの番号付きGOは未取得、マージ・本番反映・実データ登録は未実施。main pushで本番配備が起動するため、今後のマージ判断では本番への影響と直前の確認を含める（.github/workflows/deploy.yml:3）。


### 2026-09-13 本番反映前の確認

PO原文「進めてくれ」は直前説明の本番反映前確認への指示として受領し、番号付きGOには読み替えない。実装先preflight成功、PR3438はOPEN/未マージ、開始HEAD ff008f18。mainは5b21b3b8へ更新。追加は独立LINE機能等で今回の8製品ファイルとの重複0。app/main.pyの追加はline_import_devicesのimport/include_router。親がこの変更を読取照合し、既存公開カードのmain追従前提を解消して同じ実装役に統合・SHA照合・CI再確認を委任した。

本番の読取確認: API /api/healthとAppトップはcurlでHTTP200。制限付きsalesanchor-claude鍵で要求したHEAD/backup一覧はForceCommandにより監視統計だけ返り、これをHEAD/backup確認済みとは扱わない。無制限鍵への変更なし。統計上はbackend/DB等のコンテナを確認、ディスク45%使用。

最新成功配備run34688991647はmain5b21b3b8。正規権限審査で配備実ログを取得し、2026-09-12 19:39 JSTのsalesanchor_db_20260912_193916.sql.gz（6.7M）生成、HEAD5b21b3b8への更新、19:42 JSTのhealth check成功を直接確認。保存 /tmp/reports/SA-CSV-LATEST-DEPLOY-20260913.txt:583/:1030/:4635。これは過去配備時の生成証拠であり、現在ファイルの存在や復元試験は未確認。

今回のPRはDB migration/サービス/運用スクリプト変更0。既存配備はmain pushで自動起動し、git更新前にbackup.sh実行＋ファイル存在検査があり、失敗時はset -eで停止（.github/workflows/deploy.yml:127）。健康確認失敗時は前HEADへの自動復旧処理がある（同:550）。コード復旧で後日の商品登録データを巻き戻せるとはしない。今回の配備直前バックアップは未来の処理であり未取得。GO後の配備では新しいバックアップ記録と本番HEAD/健康状態/空CSV実資産を確認して完了判定する。

統合確認: 実装役がmain5b21b3b8を取り込み新HEAD2184092c4f7cafcb43188626490c892db5ed82d7をpush。親もPR JSONでHEADと既存12ファイル（8製品＋4文書）を直接確認。8製品SHAは前便の対照検算から一致。公開証跡 /tmp/reports/SA-CSV-PRE-RELEASE-20260913.txt。API health本文はstatus ok/database connected/redis connected/celery connected。本番データへの書込0。

補足: 復旧文書の文字列検索要求は、検索語とパイプの組合せがPreToolUseのDB書込検知に一致して実行前に拒否された。DB操作を要求したものではないが許可解除は行わない。独立したgit diffと保存済みhealth本文の読取は別要求で成功。復旧経路の根拠はすでに読み取った既存deploy.ymlで確認しており、DB復元は行わない。

最終CI: 親がgh pr viewでHEAD2184092c/OPEN/MERGEABLEと38SUCCESS/6SKIPPED/1FAILUREを保存。/tmp/reports/SA-CSV-PRE-RELEASE-FINAL-20260913.json。全pytest/PG成功、最新process-artifacts失敗run34716811945/job103615430624は実装役が正規権限審査で取得した実ログでGO欄欠落と確認。追加製品修正0。POへ提示する判断対象はPR3438マージ＋自動本番配備であり、GOの代筆はしない。

実装役の最終報告: Backend run34716811995/job103615468603の実ログは2674 passed/95 skipped/309 warnings/112.94s。親は実装役の保存ログ該当行を確認。PR本文を最新HEAD/CI件数/失敗runへ更新済み、対照検算は旧HEADで実行・新HEAD8製品SHA一致と区別している。


### 2026-09-13 POの番号付きGO受領

PO原文「GO #3438」を受領。直前に提示した対象はPR3438のマージと自動本番反映、完了確認はbackup/配備HEAD/health/空CSV実資産である。直前の別番号「GO #3458」は本件の承認に用いず停止し、その後の正しい番号だけを採用した。転記用確認時刻2026-09-13 05:36:56 JST（実時刻取得）。これはAI委任GOではなくPO本人の発話の記録。

再確認時のmainはd66923e2へ進んでいた。今回8製品と共通Button自体の変更0、追加は別画面部品のButton統一と設計文書であり、商品CSV機能から当該部品への参照0を確認。既存担当へ最新main統合・CI再確認・GO転記・正式merge・自動配備監視を明記したcard-release.mdを渡す。親は製品操作を担当しない。

反映カードのmain再照合: 実装役はfetch時にmain4d30c0baを検出して統合前に停止。親がd66923e2との差分を確認し、配信サービスの日付列created_at→computed_atの1行と回帰試験/文書だけで、商品CSVの8製品変更0・配信サービス参照0を確認した。許可mainを4d30c0baへ更新。マージコマンドには実CLI helpで確認したmatch-head-commitを加え、CI確認したローカルHEADとの不一致を拒否する。保護設定変更なし、GOは同じ製品変更に有効。

GO転記後に親が本文とparseGORecordを照合し、発行者欄名が「GO発行者:」である必要を確認。カードの汎用的な欄説明を正式な4欄名へ訂正し、同じ担当へ原文/値/日時を維持した欄名修正を指示。承認の創作や検査の迂回ではない。


### 2026-09-13 マージ実行結果

実装役がGO転記、最終HEAD c454957227e6edd6bf039ea78e0633fc2194e233、main4d30c0ba、8SHA/12ファイル/clean、全実行CI成功を確認し、確認済みコメントを残した。最終CIのBackendは2684 passed/95 skipped/309 warnings/98.96s。親もGO検証関数エラー0と全実行CI成功を直接確認した。

正式wrapper --merge --match-head-commitによるPR3438マージ成功。親がgh pr viewでMERGED/2026-09-13 05:46:15 JST/merge739f772d4cf55c1b3972c02c086a7c77b807d293を直接確認。実装worktreeはwrapperの通常cleanupで削除、報告と期待CSVはtmpに保持。自動配備run34718060417は同merge SHA。配備前DB backupステップSUCCESSまで親が直接確認、配備完了は後続記録と区別する。

文書側はmain739f772dを取り込み。evidence-registryの他テーマ追記と本件追記、design/reconの本件追記が競合したため、双方の文字列が保存されることをassertして文書3本だけ解消。mainとの差は証拠台帳/反映カード/design/recon/todoの文書5本のみ。製品差分0、他者変更保持、台帳検査と差分検査成功。


### 2026-09-13 本番反映完了

親と実装役が配備run34718060417 SUCCESSを直接確認。親が実ログを読み、backup salesanchor_db_20260913_054655.sql.gz/6.7Mの生成成功（05:46:58 JST、ログ584行）、本番HEAD739f772d（1031行）、health成功（4677行）を照合した。今回取得されたbackupの生成証拠であり復元試験はしていない。

親も本番API/App/CSVをそれぞれcurlで直接取得してHTTP200を確認。healthはDB/Redis/Celery connected。公開CSVは148バイト、SHA256 08ce5fc2137a86a0f594d0d4272fccbfa8d7b9a26ebdf245020fb742dc936929、レビュー済み期待ファイルと全バイト一致、BOM/CRLF/10列/商品0行。実装役も同じ検査を実行。

正式保存した結果: [release-result.json](release-result.json)。実行主体は実装役、親はPR/CI/配備ログの読み取りと本番HTTP/CSVの直接検証を担当した。設計担当による製品実装切替・独立第三者レビュー・代理GOを行ったとは称さない。設計作成/自己審査/PO承認/文書保存/製品PR/マージ/本番反映/所定完了確認は完了。文書PR3436は保存用OPENのまま、別途マージ承認がないためマージしない。実商品登録・再解析・シート配信・本番の認証付きボタン操作は未実施。


### 2026-09-13 文書PR3436のマージ承認

製品反映完了と文書PR3436未マージの説明後、PO原文「マージしてくれ」を受領。残る文書PR3436のマージ指示として扱う。直前確認はPR3436 OPEN/CLEAN、main739f772d、差分は文書6本のみ、実行CIすべて成功。製品コード変更なし。設計担当がこの明示指示に基づき正式マージ手順を行い、製品実装役への自動切替はしない。最終マージSHA/日時はGitHub PR3436を一次情報とする。以前の未マージ記録は当時の状態であり、この承認後の状態とは区別する。


## 2026-09-13 実商品CSVの登録前調査（未登録・審査REVISE）

本節は、空サンプルとUser型修正の反映完了後にPOが「進める」と依頼した、画面確認・実商品CSV準備の再開記録。商品登録GOではない。親は[商品マスタ仕様](../../specs/product-master/README.md)、対象一覧は[既存44件カタログ](../tcg-product-master-growth/sword-shield-catalog.md)。登録可の判定は未了。

### 作業場所と一次情報

- 専用ブランチ `release/product-csv-registration-preflight`、開始HEAD `ee455fb1ba4c7ad407ed6506ee4fe515fce371a8`。公式new-worktree手順で作成し、executor-preflightはexit 0。開始時の本ブランチ差分0。本店mainの未保存変更を保持した。
- 公式ledger-viewで既存商品CSV設計/実装がDONEであることを確認。旧master-fill-recordはIN_PROGRESS表記が残るが、同ブランチのorigin/mainとの独自差分0、実worktreeの未保存差分0を確認。本便はそのカタログ・growth側文書を更新せず、import側の読み取り調査記録に限定する。旧台帳の表示だけで完了とは断定しない。
- PR3438の反映結果は[release-result.json](release-result.json)が正本。今回のCSV準備は別工程。文書PR3436もマージ済みであるが、商品登録・再解析・配信の承認には用いない。
- `rg`で関連runbookを検索し、tcg-product-import / tcg-product-master-growthの一致0。既存reconとタスク台帳に記録する。

### 公式情報との発売日照合

確認日2026-09-13。商品名の短縮表記・空白差を含む既存44件を対象とし、範囲を拡張していない。以下は発売日の裏付けであり、英語名・マーク・現在のDB未登録を一括して確定する表ではない。43/44件は既存の日付と一致、1/44件は不一致。各リンクは株式会社ポケモンの公式商品情報・当時の告知であり、外部導入成功事例ではない。導入事例は不要（既存機能に渡す商品事実の確認で、採用方式の変更なし）。

| カタログ番号 | 照合した発売日 | 一次資料 |
|---|---|---|
| 1–5 | 2019-11-29 | [スターターセットV5種の発売日明記](https://www.pokemon-card.com/info/2019/20191204_002212.html)、[各商品](https://www.pokemon-card.com/ex/sa/) |
| 6 | 2019-11-29 | [V5コンプリート](https://www.pokemon-card.com/info/2019/20191127_002200.html) |
| 7 | 2019-11-29 | [トイザらス限定](https://www.pokemon-card.com/info/2019/20191110_002165.html) |
| 8 | 2019-11-29 | [セブン限定](https://www.pokemon-card.com/info/2019/20191025_002144.html) |
| 9 | 2019-12-06 | [プレミアムトレーナーボックス](https://www.pokemon-card.com/info/2019/20191110_002152.html) |
| 10 | 2019-12-27 | [ザシアン＋ザマゼンタ](https://www.pokemon-card.com/info/2019/20191213_002222.html) |
| 11–12 | 2020-03-27 | [スターターセットVMAX](https://www.pokemon-card.com/products/s/sc.html) |
| 13–21 | 2020-07-10 | [2020年告知](https://www.pokemon-card.com/info/2020/20200703_002473.html)、[9種類の商品](https://www.pokemon-card.com/ex/sd/index.html) |
| 22 | 2020-10-23 | [VMAXスペシャルセット](https://www.pokemon-card.com/products/s/sp2.html) |
| 23–25 | 2020-12-04 | [2種と対戦トリプル](https://www.pokemon-card.com/products/s/SE.html) |
| 26–27 | 2021-01-22 | [ICHIGEKI・RENGEKI](https://www.pokemon-card.com/info/2020/20201215_002714.html) |
| 28 | 2021-04-23 | [ジャンボパック](https://www.pokemon-card.com/info/2021/20210312_002830.html) |
| 29 | 2021-05-28 | [イーブイヒーローズ](https://www.pokemon-card.com/products/s/sp4.html) |
| 30–31 | 2021-07-09 | [ファミリー2商品](https://www.pokemon-card.com/ex/sh/index.html) |
| 32–34 | 2021-08-20 | [V-UNION3商品](https://www.pokemon-card.com/products/s/sp5.html) |
| 35 | 2021-11-05 | [ザシアン・ザマゼンタ vs ムゲンダイナ](https://www.pokemon-card.com/products/s/sj.html) |
| 36 | 2021-12-17 | [通常版と同日発売の明記](https://www.pokemon-card.com/info/003185.html) |
| 37 | 不一致：公式は2022-01-15頃 | [コロコロ版商品情報](https://www.pokemon-card.com/info/003230.html) |
| 38 | 2022-01-14 | [VSTARトレーナーボックス](https://www.pokemon-card.com/products/s/sk.html) |
| 39–40 | 2022-02-25 | [VSTARルカリオ・ダークライ](https://www.pokemon-card.com/products/s/sl.html) |
| 41–42 | 2022-07-15 | [ハイクラスデッキ2商品](https://www.pokemon-card.com/products/s/sp.html) |
| 43 | 2022-08-05 | [VSTARスペシャルセット](https://www.pokemon-card.com/products/s/sp6.html) |
| 44 | 2022-11-04 | [リザードン vs レックウザ](https://www.pokemon-card.com/products/s/so.html) |

### 未確定値と誤判定の前提

- #37：公式は発売日を概日、配送を2022年3月下旬頃/8月下旬頃と分けている。旧一覧の2021-12-17を流用しない。日付空欄案は可能だが、PO承認済みではない。発売日を2022-01-15と断定することも、配送月の任意の日に置き換えることもしない。
- #37：同公式ページがリンクする[ピカチュウV画像](https://www.pokemon-card.com/info/2021/12/images/1448_001a_PIKACHUv.png)を取得しview_imageで目視。左下に `sN` と `001/024` を確認。旧一覧のSIは一致しない。マーク修正案はSN。画像は一時保存のみでリポジトリへ複製しない。
- #25：公式は3デッキ同梱と説明する。SEFだけを商品の専用マークとする根拠は今回も未確認。空欄案を含め要整理。
- 英語名は今回の日本語公式資料で確定していない（#31だけでなく全行の英語表記の採用根拠を区別する）。#37以外のマークも今回の発売日照合だけで確定したとはしない。
- ローカルの既存Markdown表を解析し44行を確認。日本語名＋マークの完全一致重複0。NFKC→空白除去→casefoldによる商品名の包含比較では3組：#2→#8、#22→#29、#36→#37。これは候補名だけの簡易比較で、製品の判定ロジック再現や本番原文1792行の検証ではない。
- 単品側の除外語「種セット」は既存PO方針を維持するが、限定版やイーブイヒーローズ版を区別できる証明にはならない。検索語・除外語の案を作成後、肯定例/否定例と既存商品への影響を照合する必要がある。

### 実コードとの照合と検証の限界

`backend/app/services/tcg_product_import_svc.py:40` のCSV_COLUMNSは10列、同:54の必須項目は日本語名と4分類コード。同:95はUTF-8 BOMを許容、同:100は検索語/除外語をセル内カンマで分割、同:105は発売日空欄を許容する。日付判定は字形のみのため、候補CSV作成時には別途カレンダー上の実在日も検算する。同:230のファイル内重複キーは日本語名＋mark。同:313の既存検索語比較は文字列完全一致であり、上記3組の包含関係の不存在を証明しない。

分類コードDIV01/IP001/MK001/PC_BOXは旧設計の候補値。最新DBに有効な4コードがあること・既存商品との差分・検索語衝突は未検証。今回、本番認証付きpreview/commitは0回、DB/製品コード変更0、再解析0、シート配信0。ローカルの模擬lookupを本番検証として扱わない。

`backend/app/tcg_config.py:19` はTCG_SCHEMAを環境値から読み、既定tenant_004。ログインテナントを切り替えただけではQAのtenant_001へ向く証拠にならない。QA試行前に専用実行先と実スキーマを読み取りで確認する。既存の別便スキーマ検証設計を参照し、本番設定変更で代用しない。

### 実画面とCSV書き出しの停止理由

- 本番ボタンから保存する実画面確認は未実施。Playwright MCPの接続は既存Chromeプロファイル使用中で失敗。その後Browserスキルを確認し、指定の接続用jsツールと発見用ツールが利用できないことを確認した。他プロファイルの終了・設定変更・認証情報取得はしていない。既に確認済みの公開CSV HTTP200/バイト一致を実画面操作成功に読み替えない。
- spreadsheetsスキル指定のload_workspace_dependencies/artifact-toolが利用できない。標準CSV機能で書き出す代替方法についてPOへの確認を提示済み、回答未受領。したがって実商品CSVファイルの作成・静的検証は未了。調査Markdownは保存する。

### Planner整理とArchitect自己審査

目的は44商品の正しい候補を作り、実行前にPOが内容と警告を確認できる状態にすること。正式な取り込みカードは未発行。

判定 **REVISE**（同一AIの自己審査）。公式発売日43件一致・1件不一致と#37マーク不一致を確認できたが、全行の値採用、検索語と除外語、最新DB重複、QA実行先、CSV実ファイル検査、実画面操作が未解決である。設計合格・POによる値承認・登録GOを宣言しない。

次の順序：書き出し方法の回答受領→未確定値を明示したレビュー用CSV作成→10列/BOM/CRLF/件数/実在日/重複/検索語の検査→認証付き読み取り確認と警告一覧化→POの値判断と登録便承認。CSVは登録可能版と区別し、未確定行を黙って除外して44/44としない。実登録・再解析・配信は本便の対象外。

維持する担当は本設計担当（候補値・出典・未決の更新）と後続の実装/検証担当（承認済みカードの実行と結果保存）。判定を更新する時は検証日時・対象ファイルSHA256・件数と不合格行を本節へ追記する。

文書保存の検証：`git diff --check`、`bash scripts/check-task-state.sh`、`bash scripts/check-doc-heading-duplicates.sh` はexit 0。後者の対象はSTANDARD-WORKFLOW/design-partnerの節番号。製品テスト・実CSV検証を実行した結果ではない。本便の文書は専用worktree保存済み、未コミット・PR未提出。


## 2026-09-13 確認用44件CSV作成・静的検証完了

POの「進めてくれ」を、直前に確認したPython標準CSV機能による確認用CSV作成への回答として受領。書き出し方法の回答待ちは解消。商品値の採用・登録GOとは区別する。executor-preflightはexit 0、HEADとローカルorigin/mainの距離0/0。前便の文書3ファイルの差分を保持して作業した。

成果物：[確認用CSV](sword-shield-44-review-draft.csv)／[検証結果](sword-shield-44-review-validation.json)。CSVは44商品すべてを含むレビュー用草案。**登録承認済みファイルではない**。本番preview/commit・商品登録・再解析・配信はすべて未実施。

### CSVへ入れた値と未決事項

| 項目 | 草案での扱い | 登録前の確認 |
|---|---|---|
| 日本語名 | 既存44件の表記を保持 | 正式表記/略称と検索の取りこぼし |
| 英語名 | 既存カタログの44件を保持 | 既存調査由来の表記であり、今回の公式再確認済みではない |
| マーク | #37は公式画像に基づくSN案、#25は空欄、残りは既存値 | #25の採用値と残りの根拠。空欄を承認済み扱いしない |
| 発売日 | 43件は照合値、#37は空欄 | 概日を任意の確定日へ置き換えない。空欄採用は未承認 |
| 検索語 | 日本語名そのまま＋空白除去した日本語名（同一なら1語）。マークだけの検索語なし | 限定版の区別と実際の略称・原文に対する適合 |
| 除外語 | 単独デッキ22件（#1–5/#11–21/#23–24/#39–42）に既存方針の「種セット」。#2に「セブン」、#22に「イーブイヒーローズ」、#36に「コロコロ」を追加案として設定 | 除外語追加3件は設計案で、PO採用済みではない。複数商品を含む原文で必要な単品まで除外しないか検証する |
| 分類4コード | DIV01/IP001/MK001/PC_BOX | 旧設計の値。最新参照マスタとの照合は未実施 |

### 親が直接実行した検証

Python標準csvで生成後、出力バイトを読み直して確認。10列の見出しは現行サービスのCSV_COLUMNSをASTから取得した。現行`decode_csv`/`parse_rows`の2関数だけをASTから取り出して実行し、44行と全セルの一致、file_errors空を確認した。サービス全体を起動した検証やDB照合ではない。

- 44商品、見出し込み45行、10列、UTF-8 BOM付き、改行CRLFのみ、9,798バイト。
- 必須5項目の空欄0、商品名＋mark重複0、日付43件はPython date.fromisoformatで実在日と形式を検査。発売日空欄は#37のみ、mark空欄は#25のみ。
- CSVの書き出し/読み戻しは全セル一致。検索語3文字以下0、数式開始記号のセル0。
- 候補名だけの簡易比較：NFKC→空白除去→casefold後、検索語のいずれかが含まれ、除外語が含まれない場合をhitとした。自己名44/44件hit、他商品名へのhitは1,892比較中0件、単独デッキ名＋「9種セット」の否定例22/22件は非hit。
- 上記簡易比較は、本番の商品照合処理・実原文・既存商品との競合を検証した結果ではない。略称の再現率、備考を含む実際の除外判定、本番DB重複/分類コード、QAスキーマ、認証付き画面確認は未検証。

SHA256: `c4ba5619b293bd222bce0c65d1faab48059d5b3a24ea46c4b12eb5540eaffa1b`。検証結果JSONに作成時刻・入力カタログ/サービスのSHA256も保存した。

### 自己審査と引き継ぎ

判定は **REVISEを維持**。CSV作成と形式検査は完了し、書き出し方法に関する確認は解消した。未確定値・本番データとの比較・実画面確認が残るため、登録可能判定は出していない。新たな実装カード・サブエージェント起動・PR提出・マージはなし。

次は本節の未確定値と検索語案を確定し、承認済みの読み取り経路で最新DB/QA実行先/画面previewの警告を照合する。その結果と同じCSVのSHA256を示して登録便の判断へ進む。今回の確認用CSV作成承認を本番登録承認に読み替えない。


## 2026-09-13 空欄方針のPO回答・既存品質検査・DB照合準備

直前の「発売日1件・マーク1件を空欄のまま扱う方針で確定してよいですか」に対するPO原文「進める」を受領。#37発売日と#25マークを空欄とする方針はPO承認済み。英語名、その他のマーク、検索語採用、本登録の承認を含まない。CSV自体の変更なし、SHA256は前節と同一。

preflight成功。本店の他者変更を保持。origin/mainに後続差分があり、`git diff --name-only HEAD..origin/main`で商品CSVサービス/キーワード品質検査/解析サービスの変更0を確認した。実ブラウザー用のjsツールは引き続き利用不可。

### 既存の品質検査を直接実行した結果

[品質検査の実測JSON](sword-shield-44-keyword-validation.json)。`tcg_analyzer_svc.py:229`のnormalize_en、:247のtoken_and_match、:265のmatch_one_kwと依存定数をASTで抽出し、そのまま実行。`tcg_keyword_lint.py`の既存R1–R7とrun_allを同じ関数へ接続した。DBやサービス全体は起動していない。

- STOP：R2-stop 5件。#1–5の空白付き検索語は草/炎/水/雷/闘の1文字トークンに分かれる。
- WARN：R2-warn 2件。#35/#44の空白付き検索語に2文字のvsが含まれる。
- R1/R3/R4/R5/R6の検出は各0。候補44件の内側だけの検査で、既存本番商品を含まない。
- R7は空白付き検索語の情報表示。詳細はJSON。

前節の形式検査・簡易名称比較の合格を、この既存品質検査の合格としない。CSVは変更せず停止5件を明示して保持。単に空白付き語を削除すると、空白を含む実際の商品名を拾えなくなる可能性がある。検索語修正は肯定例/否定例を揃えてから行い、品質規則を緩めない。設計自己審査はREVISEを維持。

### 本番読み取りの準備（未実行）

CLAUDE.md:28–30はエージェントの鍵を制限付きとし、無制限鍵は「人間の明示許可があるタスクでのみ使用可」「許可は都度・タスク単位」と定める。監視runbookの制限付き経路はdocker stats/free/df/uptimeを返す経路で、DB照合用ではない。新たな認証情報の探索や制限変更で解決しない。

許可を求める具体的範囲：既存 `~/.ssh/manual-only/id_ed25519` を今回の商品CSV照合に限り使用し、`ubuntu@app.salesanchor.jp` の既存postgresコンテナへ読み取り専用のSQLのみを実行する。新規鍵・権限/設定変更・商品/履歴/解析への書き込みなし。商品名/分類コード/検索語等の必要情報だけを取得し、顧客・メッセージ本文・認証情報は取得しない。

手順は既存card-templates.md §2の接続定型を使用。各呼出しでPGOPTIONS `-c default_transaction_read_only=on` を指定する。最初に `SHOW transaction_read_only` がonであることを確認し、不一致・エラー・対象コンテナ不明で停止する。実行SQLを示す（本節は読み取り計画で、実行済みカードではない）。

```sql
SHOW transaction_read_only;
SELECT code, id, display_name, is_active FROM tenant_004.tcg_series ORDER BY code;
SELECT code, id, is_active FROM tenant_004.tcg_major_categories ORDER BY code;
SELECT code, id, is_active FROM tenant_004.tcg_manufacturers ORDER BY code;
SELECT code, id, is_active FROM tenant_004.tcg_product_categories ORDER BY code;
SELECT code, japanese_title, english_title, mark, release_date, work_id, manufacturer_id, product_category_id, is_active FROM tenant_004.tcg_products ORDER BY code;
SELECT p.code, k.keyword FROM tenant_004.product_search_keywords k JOIN tenant_004.tcg_products p ON p.id = k.product_id ORDER BY p.code, k.keyword;
SELECT p.code, k.keyword FROM tenant_004.product_exclude_keywords k JOIN tenant_004.tcg_products p ON p.id = k.product_id ORDER BY p.code, k.keyword;
```

4分類のコード存在・有効状態を確認し、取得商品と候補CSVの日本語名/マーク/分類/検索語をローカル比較する。取得結果の時刻とSHA256を保存し、CSVに対する重複疑いと検索語衝突を一覧化する。本番プレビュー・QA環境への接続・登録実行は本SQL群に含めない。

状態：空欄方針PO承認済み／CSV保存済み／形式検査済み／既存品質検査はSTOP5件／設計REVISE／本番読み取り未実行・鍵使用の許可待ち／本登録未着手。次は許可された読取結果との照合と検索語の修正案を作る。


## 2026-09-13 本番マスタ読み取り・44候補照合完了

PO原文「進めてくれ」を、直前に提示した今回の商品マスタ照合専用の既存manual-only鍵使用への回答として受領。設定/権限変更や書き込みの承認ではない。

executor-preflight成功。既存鍵で指定ホスト・postgresコンテナへ接続し、PGOPTIONS default_transaction_read_only=onを指定したSHOW transaction_read_onlyの出力はon、exit 0。続く前節の7本のSELECTも各接続に同じPGOPTIONSとON_ERROR_STOP=1を付与し、すべてexit 0。JSONで取得するため外側をSELECT json_agg(q) FROM (...) qで包んだ。書き込みSQL0、商品登録/認証付きpreview/再解析/配信0。

保存：[取得マスタと時刻・指紋](sword-shield-44-live-snapshot.json)／[比較結果](sword-shield-44-live-comparison.json)。7問は別接続であり単一トランザクションの同時点スナップショットではない。登録直前には再照合が必要。

### 今回確認できたこと

| 項目 | 実測 |
|---|---|
| 商品 | 全296件、有効293件 |
| マスタ件数 | 作品11・大分類3・メーカー5・商品区分2 |
| キーワード行数 | 検索657・除外156（全商品） |
| CSVが参照する4コード | DIV01/IP001/MK001/PC_BOXすべて存在し有効 |
| 44候補と既存商品名の完全一致 | 0。NFKC/空白除去/casefold後の一致も0 |
| 同じマーク | #13–21のSDがPM0004 Sカードと一致（9行）。既存側の区分はPC_BOXとは異なる。マーク一致を同一商品と断定しない |

名前の一致0は意味上の重複不存在の証明ではない。分類・名称・年違い・検索語をあわせて見る。

### 既存有効293件＋44候補による品質検査

既存純関数を同じ手順で実行し、既存293件のみの結果と337件の結果の差分を取った。既存起因の問題と追加候補に伴う問題を分けた。

| 規則 | 既存のみ | 候補追加で増えた指摘 |
|---|---:|---:|
| R1 検索語なし | 0 | 0 |
| R2 1文字トークン（停止） | 6 | 5 |
| R2 2文字トークン（警告） | 41 | 2 |
| R3 複数商品で同じ検索語（停止） | 1 | 1 |
| R4 自分を除外 | 0 | 0 |
| R5 別商品への相乗り（警告） | 15 | 45 |
| R6 商品内の正規化重複 | 2 | 0 |

R5追加45件はキーワード対の数であり、45商品ではない。候補19商品と既存8商品に関係する。すべて検索語同士の検査であり、実原文で45件誤判定したという意味ではない。

- R3：#36の「スタートデッキ100」がPM0200「MEGA スタートデッキ100 バトルコレクション」（DB発売日2025-12-19）の既存検索語と同一。2021年版を追加する前に世代の区別が必要。
- R5：既存PM0048の「シールド」、PM0060の「白銀」、PM0061の「漆黒」、PM0062の「イーブイヒーローズ」、PM0074の「VMAX」、PM0087の「VSTAR」が新しいセット名にも当たる。
- PM0126は2024年の「いつでもどこでもバトルアカデミー」。既存検索語「いつでもどこでも」が#31の2021年ファミリーポケモンカードゲームへ当たる。完全一致する商品名がないだけでは回避できない。
- 候補側の除外語だけでは、既存商品側の広い検索語による相乗りを止められない。既存DBは変更しない。

終盤にorigin/mainはcacc889e0e44ed647fbd0a7d1c110ab11f86aec5へ進んでいた。解析サービスの差分はプロンプト版定数のimportと実行条件だけで、今回実行したnormalize_en/token_and_match/match_one_kwおよび品質検査サービスの差分0。これはremote refとのソース照合で、本番コンテナの実HEADを観測した結果ではない。

### 次の設計へ渡す修正案と自己審査

1. #1–5の1文字トークン：単純な語削除だけでは元の商品名に含まれる空白表記を拾えなくなる。空白あり/なし・別タイプ・VMAX版を肯定/否定例にし、既存品質規則を満たす候補語を設計する。規則の閾値変更は行わない。
2. #36とPM0200：2021年版/2025年版/コロコロ版を別々の正解として固定し、共通の「スタートデッキ100」だけの投稿を曖昧と扱う案を検討する。既存PM0200側の語と除外条件の変更が必要なら別設計・承認対象にする。候補だけを変更して解消したと称さない。
3. 既存8商品に関する相乗り：拡張パック単品/セット商品を区別する肯定・否定例を用意し、既存側の広い語の見直しと除外条件を設計する。作品・商品区分など後段制約の影響も含めて検証し、R5件数だけで実原文の誤判定件数を推定しない。

Architect自己審査はREVISE。4コードの実在・有効性と最新マスタとの照合は完了。新規R2-stop5件/R3-stop1件を解消する前に登録しない。既存データ修正は本便の読み取り承認外。空欄2項目はPO承認済み、CSV保存済み、登録設計合格/本登録GO/本登録は未了。

文書はローカル専用worktreeに保存。新たなサブエージェント・製品コード/DB変更・PR/マージなし。


## 2026-09-13 検索語修正のオフライン対照設計

POの「進める」に従い[design §16](design.md#16-44候補登録前の検索語修正案2026-09-13草案revise)を草案として追加。[実験JSON](keyword-revision-experiment.json)と[再現コード資料](keyword-revision-experiment.py.txt)を保存。メモリ上だけで既存8商品と候補6商品の語を変更した。CSV/製品コード/DBは変更0。

既存のmatch_pid_with_workまで含む純関数を実行。入力349件（候補名44、既存名293、設計例12）。候補名の正しい確定は25→43、#36の世代不明名は意図して未確定。既存のみで正しく確定していた256名称の劣化0。候補44＋設計例12の期待値不一致0。追加のR3停止1/R5警告45は各0になった。R2停止5/警告2は残る。実原文への適合・略称の取りこぼしの許容は未確認。

自己審査REVISE。新しい略称方針と既存8商品のDB変更はPO承認前。正式実装カード未発行・新規PR未提出。次のPO判断は「商品や世代を識別できない略称は確認待ち」の方針1件とする。


## 2026-09-13 略称方針の承認と空白差の限定設計実験

PO原文「進める」は、直前に提示した曖昧な略称を確認待ちにする方針への回答。正式な実装承認ではない。design §17へ承認範囲を記録した。

データだけで空白付き語を削ると対象7件すべての元の名称が未確定になる。商品名全体の半角/全角スペース差だけを追加一致とするメモリ上の試作を実行。入力389件、期待値付き96件の不一致0、既存正解256名称の劣化0。追加一致へ合わせた品質R5試作を含め、R1–R6の既存からの追加停止/警告0。相乗り対照2表記も検出した。

[結果](keyword-space-design-experiment.json)と[再現資料](keyword-space-design-experiment.py.txt)に保存。元のCSV/製品コード/DBは変更0。既存の実験349件は拡張検算の前提読み込みとして再実行した。無関係な全テストの繰り返しではない。

参照したremote mainとの差分はプロンプト版定数と条件のみで、今回の純関数の差分0。既存pytestの数字境界/作品/フィールド分離を読んで受入条件へ反映した。全体自己審査REVISEを維持。次は正式受入条件と安全な反映順序の設計。文書チェックはdiff --checkとtask-state-checkを実行する。


## 2026-09-13 受入条件・QA・反映順序の確定と限定審査

[design §18](design.md)でA便（判定/品質機械だけ、6製品ファイル）とB便（既存8商品/新規44件のデータ）を分けた。A1–A8と既存CIの隔離PG fixtureを直接照合し、AST読込試験の追加依存も実装範囲へ含めた。B便はQA実行先とデータ部分失敗の前提が未確立のため、引き続き未合格。

[同値検算](keyword-reducer-equivalence.json)は300例、候補0–6の返却tuple不一致0。これは設計用の旧関数対照で、正式pytestではない。共有選択により旧契約が維持できる根拠を追加した。

最新main取得は最初にFETCH_HEADのsandbox書込制限で失敗。同じgit fetchを正規の権限審査へ提出して成功。制限や接続先の変更なし。取得main af269ae20ed2f52e6cd49ba0403ad7799e3a3870。対象純関数の差分0、ADR-154の他者による行番号契約追補5行を確認し、その最新本文を保持した上で本件の未承認追加決定案を末尾へ保存した。

Architect自己審査：A便APPROVE、B便と登録全体REVISE。PO設計承認/実装承認は未受領、正式カード未発行。製品実装/DB書込/本番反映は未着手。次はA便の限定設計をPO承認へ提示し、承認済み文書の保存と正式カード検査を行う。


A便単独検算の追補：既存293名称、従来確定済みのtuple変更0、既存正解256名称の劣化0。PM0191だけNONE→同商品確定。初回試作のPM0152の根拠語変更を、各商品の通常一致を優先する仕様で解消した。design §17-2/18-6と実験資料を修正版へ更新、389入力も再検算。未承認草案の検算上の修正で、製品コード/DBには適用していない。


## 2026-09-13 A便設計承認の保存

POへA便だけの正式設計承認を尋ねた応答「進める」をdesign §18-7へ記録した。ADR-154の追加決定と台帳を同じ範囲で更新。過去の未承認時点の記録は経緯として残す。これは実装開始承認や代理GOではない。B便の商品データ変更と44件登録は引き続きREVISE。

製品コード・DB・CI・運用設定は変更していない。設計検算の96期待例/既存293名称/300同値例は前節の設計実験であり、正式pytestと通常CIの合格を代替しない。


実装カード準備の実測：公式new-worktree.shでrelease/product-name-space-match-implを作成。HEAD/origin/mainはaf269ae20ed2f52e6cd49ba0403ad7799e3a3870、status空、preflight成功。作業場所だけを準備し実装役は起動していない。対象6ファイルの最新差分はWORK_ID_PROMPT_VERSIONS対応とp1/p2統合試験で、これを維持する条件をカードへ記載した。

Docker CLIは存在するがdocker infoは/var/run/docker.sock不在で終了1。ローカルpytest/PGは実施せず既存CIで確認する契約を維持。card-lintは終了0・違反0（L24長行警告2件）、diff --checkとtask-state-checkは終了0。カードの作業場所・基点・入力設計SHA・停止条件・6ファイルとA1–A8を同一AIで照合した。

先約の確認：PR3465はOPENだが対象は比較専用サービス/試験で本便6ファイルと重ならない。旧台帳のPR3400はAPIでMERGED確認（2026-09-10T07:24:27Z）。release/line-box-heading-guardsは同名PRなし、ローカル作業の先約が残るため実装開始直前にも対象の重複を確認する。古い台帳だけで未実施/完了を断定しない。


### 文書PR提出前の停止（2026-09-13）

承認済み設計とカード/証拠17ファイルを0ceb2a16に保存し、0eb20160で最新mainを統合。ADR/evidenceの末尾競合は両側を保持し、mainの全行を順序込みで維持した。PR差分はdocs配下16ファイルとtasks/todo.mdのみ、製品差分0。

PR全差分への通常diff --checkはCSVの規定CRLFを45行のtrailing whitespaceとして検出した（終了2）。CSV以外16ファイルの同検査は成功、CSVはBOM/45 CRLF/44商品と保存SHA c4ba5619b293bd222bce0c65d1faab48059d5b3a24ea46c4b12eb5540eaffa1bの一致を別途確認。通常チェック全体成功とは記録しない。card-lint終了0（長行警告2）、task-state-check終了0、全JSON構文検査成功。

自動承認レビューがgit push -u origin HEADを実行前に拒否。理由は全17ファイルに含むlive snapshot/CSVの送信先・機密性・個別承認が確認できず、未承認データの外部送信となる可能性があるため。拒否後のgh repo viewで送信先shingo-ops/salesanchorがPUBLICであることを確認した。

本番マスタ資料には商品名だけでなく内部商品ID・有効状態・検索語・除外語が含まれる。設計保存の承認と、この内容の一般公開承認を混同せずpushを停止。履歴からの間接送信や別経路での送信は行っていない。文書PR未提出、実装未着手。次はPOへ当該資料を含む公開送信の可否を1件提示する。
