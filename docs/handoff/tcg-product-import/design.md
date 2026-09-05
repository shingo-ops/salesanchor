# design — 商品マスタ CSV取り込み

親（設計仕様書）へのリンク: ../../specs/product-master/README.md

> この文書は何か（専門用語なしの1行）:
> CSVファイルで商品をまとめて商品マスタに登録する機能の、作り方を決めた文書。

## 1. あるべき姿

親テーマの願いに従う。本テーマについてのPO自筆は次の2つ。

- 「インポート機能に集中してほしい、商品マスタページの作成とヘッダーアクションにインポートボタンを配置してそこからインポートが出来るようにしてくれ」
- 「いまのページとは別で独立したページを作る、データ管理も兼ねたページなのでサイドメニューのSaaS管理者メニュー内の商品マスタメニューを作成してページを展開、データテーブル式のマスタ一覧が表示されるページを作成してほしい（中略）そのページ内のヘッダーアクションにCSVボタンを作成してボタンを押すとページが展開されてドラッグ＆ドロップでCSVデータが格納できるページが開く」

## 2. KGI（○×で測る）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| ① | SaaS管理者メニューに商品マスタが出る | 在る=1／無い=0 | 1 |
| ② | 一覧ページが登録済み商品を表で全件見せる | 画面の総件数 ＝ tenant_004.tcg_products の行数 | 一致 |
| ③ | ヘッダーアクションにCSVボタンが在り、押すと取り込み画面が開く | 在って開く=1／欠ける=0 | 1 |
| ④ | 取り込み画面にファイルをドラッグ＆ドロップして受け取れる | 受け取れる=1／できない=0 | 1 |
| ⑤ | 確認画面を通らずに本番DBへ書き込む経路が無い | 確認を経ずに tcg_products が増える操作の数 | 0 |
| ⑥ | 不正な行を取り込み前に止め、止めた行を名指しで見せる | 見本の不正CSVで 止めた行数 ÷ 止めるべき行数 | 満数 |
| ⑦ | 取り込みの履歴が残る | 取り込み1回につき親1行・行ごとに子1行 | 満数 |
| ⑧ | 新規ファイルに日本語の直書きが無い | 新規追加ファイル内の日本語リテラル数 | 0 |
| ⑨ | 調査済みカタログの商品をCSVで取り込める | 取り込めた件数 ÷ 44 | 44/44 |

## 3. 対象範囲

- 対象テナント: tenant_004（本番）／ tenant_006（QA・先に試す）
- 触るテーブル: tcg_products / product_search_keywords / product_exclude_keywords（いずれもINSERTのみ）
- 新設テーブル: tcg_product_import_jobs / tcg_product_import_rows
- 触らないもの: analysis_results（別セッション担当）／既存の create_product・check_duplicates のコード（ADR-154の制約下）／既存 import_jobs（LINE取り込み専用・用途が違う）

## 4. 段階導入

| 便 | 内容 | GO |
|---|---|---|
| 1 | recon | 完了（PR #3308） |
| 2 | design（本書） | 本便 |
| 3 | migration（履歴2テーブル新設） | 要 |
| 4 | backend（取り込みAPI） | 要 |
| 5 | frontend（一覧ページ・取り込み画面・メニュー・翻訳） | 要 |
| 6 | tenant_006 で見本CSVを試す → tenant_004 で44件 | 要 |

便6は、QAで通ってから本番に進む。順序を飛ばさない。

## 5. design（技術How・実装は別便）

### 5-1 画面

- 一覧ページ: frontend/src/pages/super-admin/TcgProductMasterPage.tsx を新設。ルートは /super-admin/tcg-product-master。App.tsx の既存6本の並びに追加する。
- 部品は新規に作らず既存を使う: PageLayout.tsx（枠）／DataTable.tsx（表）／HeaderButton.tsx（ヘッダーの操作）／ContentToolbar.tsx（検索）／EmptyState.tsx（0件）。
- 表の列: code / japanese_title / mark / release_date / 検索キーワード数。検索キーワード0件の行は注意色で示す。
- サイドメニュー: DesktopShell.tsx の saasAdminItems に4件目を追加する。
- 取り込み画面: 同ページ配下 /super-admin/tcg-product-master/import。3段階（ファイルを置く → 内容を確認 → 取り込み）。
- 文言は全て t() 経由。ja.json / en.json の同じ位置に対で追加する（既存 nav.superAdminFxRate と同じ形）。

### 5-2 API

backend/app/routers/tcg_product_import.py を新設する。既存 tcg_product_master.py は変更しない。

- GET  /api/v1/tcg/products                 一覧（ページング・検索）
- POST /api/v1/tcg/products/import/preview  検査のみ。書き込みを一切しない
- POST /api/v1/tcg/products/import/commit   実行

認証は require_super_admin。tenant_004 専用。

### 5-3 取り込みの処理

backend/app/services/tcg_product_import_svc.py を新設する。

1. CSVを読み、10列であることを確認する
2. 4つのコード（division_code / work_code / manufacturer_code / product_category_code）を、参照マスタの code から uuid へ変換する
3. 5-4 の検査を行う
4. preview は結果を返すだけで終わる
5. commit は同じ検査をやり直し、止める判定の無い行だけを登録する
6. 登録は既存の create_product をそのまま呼ぶ。使われていない extraction_item_id / source_message_id には空文字を渡す（サービス層 305-306 行で受け取るが本体で未使用であることを実測済み）
7. code / category_class / is_active はサービス側が自動で入れるため、CSVには持たせない

### 5-4 検査の規則

| # | 内容 | 判定 |
|---|---|---|
| 1 | 日本語タイトルが空 | 止める |
| 2 | 4つのコードのいずれかが空、または参照マスタに存在しない | 止める |
| 3 | 発売日が YYYY-MM-DD 形式でない | 止める |
| 4 | 列の数が10でない | 止める（ファイル全体） |
| 5 | 同一ファイル内に同じ商品が2行ある | 止める |
| 6 | 既存マスタとの重複の疑い（既存 check_duplicates の判定） | 警告 |
| 7 | 同じ型番（mark）がマスタに既に在る（本機能の独自チェック・件数制限なし） | 警告 |
| 8 | 検索ワードが1つも無い | 警告 |
| 9 | 3文字以下の検索ワードがある | 警告 |
| 10 | 他の商品にも当たる検索ワードがある | 警告 |
| 11 | 型番が空 | 警告 |

止める判定が1つでもある行は登録しない。警告のみの行は、確認画面でPOが承認すれば登録する。

### 5-5 CSVの形

10列。1行目は見出し。文字コードは UTF-8。

mark, japanese_title, english_title, release_date, search_keywords, exclude_keywords, division_code, work_code, manufacturer_code, product_category_code

- 検索ワード・除外ワードは、1つのセル内でカンマ区切り。表計算ソフトが自動で引用符を付ける
- 4つのコードは uuid ではなくコードで書く（DIV01 / IP001 / MK001 / PC_BOX など）
- 発売日は YYYY-MM-DD

### 5-6 履歴テーブル

migration で新設する。既存 analysis_runs / analysis_run_snapshots と同じ2階建てにする。

tcg_product_import_jobs（親・取り込み1回で1行）
  id uuid PK / filename text NOT NULL / raw_sha256 varchar NOT NULL UNIQUE /
  total_rows int NOT NULL / created_rows int NOT NULL / skipped_rows int NOT NULL /
  executed_by text / status varchar NOT NULL /
  started_at timestamptz NOT NULL DEFAULT now() / completed_at timestamptz

tcg_product_import_rows（子・CSVの1行で1行）
  id uuid PK / job_id uuid NOT NULL FK / row_no int NOT NULL /
  japanese_title text NOT NULL / mark varchar /
  result varchar NOT NULL / product_code varchar / messages text /
  created_at timestamptz NOT NULL DEFAULT now()

raw_sha256 の UNIQUE は既存 import_jobs から採る。同じファイルを二度取り込むと弾かれる。

## 6. 弊害・トレードオフ

- 既存 create_product は1商品ごとに commit する（サービス層 426 行）。途中で落ちると、そこまでの行が入った状態で止まる。全件のやり直しはできない。取り消しではなく、tcg_product_import_rows に1行ずつ結果を残すことで追跡する。
- commit では force=True で登録する。警告は確認画面でPOが承認済みのため。承認を経ない登録経路は作らない。
- 既存の重複チェックは候補取得を20件で打ち切る（サービス層 247 行）。同一分類の商品が20件を超えると漏れる。ADR-154 により既存ロジックは変更しないため、この穴は残る。5-4 の7番（型番チェック）で部分的に補う。GASに同じ打ち切りがあるかは未確認。
- 型番は作品をまたいで重複し得るため、5-4 の7番は別商品にも警告を出す。確認画面が煩雑になる。
- 使われない引数に空文字を渡す形になる。既存関数を変えないための代償。
- 本機能はアプリから本番DBへ書き込む。「書き込みは migration 経由のみ」という運用前提は、「スキーマ変更は migration 経由のみ／データ投入は承認を経たアプリ経由を許す」に更新が要る。

## 7. 外部・過去事例

- 該当あり。tenant_004.import_jobs（LINE取り込み用）の raw_sha256 UNIQUE による二重取り込み防止を踏襲する。
- analysis_runs（実行1回=1行）と analysis_run_snapshots（1行ごと）の2階建てを踏襲する。
- 既存 ProductMasterDrawer.tsx:135-172 の3段階（入力 → 重複確認 → 登録）を、複数行へ拡張する形で踏襲する。

## 8. 受入基準

- ①③④: 画面を開いて実際に操作し、結果を記録する。
- ②: 画面の総件数と、tenant_004.tcg_products の実測行数が一致すること。
- ⑤: 取り込み系のコードを走査し、preview を経ずに INSERT へ到達する経路が無いこと。
- ⑥: 止める判定11種それぞれを1行ずつ含む見本CSVを作り、止めるべき行が全て止まること。tenant_006 で実測する。
- ⑦: 取り込み1回につき tcg_product_import_jobs が1行、tcg_product_import_rows がCSVの行数ぶん増えること。
- ⑧: Frontend lint が緑であること。
- ⑨: sword-shield-catalog.md の44件をCSVにして、tenant_006 で44件、tenant_004 で44件が入ること。

## 9. 維持の仕組み

- 守り手: preview を経ない commit を作らないこと（コードレビューとKGI⑤の走査）。Frontend lint（文言の直書き）。tcg_product_import_jobs.raw_sha256 の UNIQUE（同一ファイルの二重取り込み）。
- 対象: 承認を経ない本番書き込みと、質の悪いキーワードの流入。
- 人手併用: 5-4 の警告は押し切れる。キーワードの質は最終的にPOの目視で担保する。機械は「他の商品にも当たる」ことまでは測れるが、それが正しいかは測れないため。

## 10. 接触面分析（6面走査）

- ①人: PO。CSVを作る作業が増える。代わりにカード発行が不要になる。
- ②エージェント: 実装役。取り込み作業がカードから画面操作に移る。
- ③機械: 新設API2本・新設画面2枚・新設テーブル2本。既存の create_product / check_duplicates は変更しない。
- ④データ: tcg_products / product_search_keywords / product_exclude_keywords に INSERT が増える。analysis_results には触れない。
- ⑤本番: tenant_004 に新テーブル2本を migration で追加する。既存テーブルの構造は変えない。
- ⑥外部: 影響なし（外部APIを呼ばない）。
