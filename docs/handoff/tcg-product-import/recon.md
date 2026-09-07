# recon — 商品マスタ CSV取り込み

この文書は何か（専門用語なしの1行）:
商品マスタにCSVで商品をまとめて登録する機能を作る前に、いま何がどこにあるかを実測で調べた記録。

親（設計仕様書）へのリンク: ../../specs/product-master/README.md

- 仕事名: tcg-product-import
- 日付: 2026-09-05
- 対象ADR: ADR-154
- 担当: architect
- 状態: 実測完了・design 未着手

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
