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
