---
mode: handoff
---
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

- 対象テナント: tenant_004（本番）／ tenant_001（QA）。テナントの用途は docs/ai-agents/design-partner.md 9節が正本。tenant_006 は Meta App Review 専用であり QA に使わない。
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
| 6 | tenant_001 で見本CSVを試す → tenant_004 で44件 | 要 |

便6は、QAで通ってから本番に進む。順序を飛ばさない。前提だった tenant_001 への TCG テーブル作成は migrations/20260906_120000_create_tcg_tables_t001.sql で適用済み（実測: tenant_001 に tcg_products ほか TCG 7 テーブルが存在）。

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

本便の実測の根拠は docs/handoff/tcg-product-import/recon.md にある。

| 基準 | 検証方法 |
|---|---|
| SaaS管理者メニューに商品マスタが出る | 画面を開いて項目の有無を記録する |
| 一覧が登録済み商品を全件見せる | 画面の総件数と tcg_products の実測行数が一致すること |
| ヘッダーのCSVボタンで取り込み画面が開く | 画面を開いて操作し結果を記録する |
| ファイルをドラッグして受け取れる | 画面を開いて操作し結果を記録する |
| 確認を経ずに書き込む経路が無い | backend/app/routers/tcg_product_import.py を走査し preview の指紋照合を経ない INSERT 経路が無いこと |
| 不正な行を止めて名指しで見せる | 止める判定を1行ずつ含む見本CSVで、止めるべき行が全て止まること |
| 取り込みの履歴が残る | 取り込み1回につき tcg_product_import_jobs が1行、tcg_product_import_rows が行数ぶん増えること |
| 新規ファイルに日本語の直書きが無い | Frontend lint が緑であること |
| 調査済みカタログを取り込める | sword-shield-catalog.md の44件が tenant_001 と tenant_004 で44件入ること |

## 9. 維持の仕組み

- 守り手: backend/app/routers/tcg_product_import.py の commit 経路が preview の指紋照合を必須にしている。migrations/20260906_130000_create_tcg_product_import_history_t004.sql の一意索引が同一ファイルの二重取り込みを止める。backend/tests/test_tcg_product_import.py が認証と指紋不一致を検査する。
- 対象: 承認を経ない本番書き込みと、質の悪いキーワードの流入。
- 人手併用: 5-4 の警告は押し切れる。キーワードの質は最終的にPOの目視で担保する。機械は「他の商品にも当たる」ことまでは測れるが、それが正しいかは測れないため。

## 10. 接触面分析（6面走査）

- ①人: PO。CSVを作る作業が増える。代わりにカード発行が不要になる。
- ②エージェント: 実装役。取り込み作業がカードから画面操作に移る。
- ③機械: 新設API2本・新設画面2枚・新設テーブル2本。既存の create_product / check_duplicates は変更しない。
- ④データ: tcg_products / product_search_keywords / product_exclude_keywords に INSERT が増える。analysis_results には触れない。
- ⑤本番: tenant_004 に新テーブル2本を migration で追加する。既存テーブルの構造は変えない。
- ⑥外部: 影響なし（外部APIを呼ばない）。

## 11. 訂正の記録

- 2026-09-06: QA先を tenant_006 から tenant_001 に訂正した。理由は、tenant_006 が Meta アプリ審査専用のテナント（public.tenants で実測・contacts 8件・稼働中）であり、空のQA環境ではなかったため。テナントの用途は docs/ai-agents/design-partner.md 9節が正本であり、tenant_001 が QA・TCG 動作確認用、tenant_006 は Meta App Review 専用で QA 禁止と定められている。
- 同日、tenant_006 に TCG テーブル27本を作る migration（PR #3315）が本番デプロイで失敗し、PR #3318 で取り消された。失敗の直接原因は、migration 末尾に「スキーマ内の全テーブル数が27であること」という検算を入れたこと。tenant_006 には CRM 系のテーブルが既に68本あり、68 + 27 = 95 となって例外が発火した。トランザクション全体が巻き戻ったため、DBへの変更は残っていない。
- 教訓: migration にテーブル全体の件数一致チェックを書かない。自分が作った範囲の名前だけを数える。本テーマの migration にもこの原則を適用する。

## 12. スキーマ修飾テスト拡張（2026-09-10設計案）

対象ADR: ADR-113、ADR-154。証拠正本: docs/handoff/tcg-product-import/recon.md の2026-09-10追補。
本節は商品取り込みサービスが正しいテナントの表を参照するための静的検査の設計。画面の完成や44件取り込みを意味しない。
設計時点の状態: 設計案作成済み・同一AIの自己審査APPROVE（本節の限定範囲）。実装の現在地は tasks/todo.md の依頼6と EV-20260910-TCG-SCHEMA-IMPL を参照。以下の設計時試験と実装後の検証は区別する。

### 目的・変更前後

依頼6の目的は、商品取り込みサービスもテナント指定の抜けを検出すること。
現状の正規表現抽出は隣接文字列の先頭のみを取り出し、後半JOINを見落とす。TARGETSへの1行追加だけでは不十分。
Python標準astでtext(...)の引数を式全体として読む。既存2対象を維持し、商品サービスを3件目として追加する。

### 変更契約と範囲

実装の変更先は backend/tests/test_tcg_schema_qualification.py のみ（必要な台帳・根拠登録を別途更新）。サービス、ルーター、DB、運用スクリプト、CI、frontendは変更しない。
実装用本文候補は同じディレクトリの schema-test-proposal.py.txt。これは設計資料であり、pytestに収集される製品テストではない。

- textの位置引数1個をast.Constantまたはast.JoinedStrとして読み、隣接する文字列を連結する。名前参照、任意の式、未知の補間、引数不正、検査対象0件は合格させない。
- 動的補間はTCG_SCHEMAとtableに限定。文字列中に残ったリテラルの置換記号も拒否する。
- 対象テーブル名は識別子単位で比較する。SQLのコメント・通常の文字列値を除き、直前のtenant_004またはTCG_SCHEMAとドットを要求する。遠い位置のスキーマ名で合格させない。
- 商品サービスの直接参照4表（tcg_products、product_search_keywords、tcg_product_import_jobs、tcg_product_import_rows）と動的tableを対象にする。
- LOOKUP_TABLESの4件をソース実物に照合し、動的SQLがそのitems()を回すループ内にあることを確認する。表名4件へ展開した正常例と未修飾例も検査する。
- supplier_channelsのINSERT列とDDLを照合する既存テストは維持する。
- 現在の6呼び出し・7修飾箇所を固定した試験で、SQL追加・削除をレビューの契機にする。数字だけを合わせて検査を削らない。

### 受入基準

| 基準 | 検証方法 |
|---|---|
| 既存2対象と追加1対象が合格する | 15・13・6個のtext呼び出しを抽出し、3対象の実ソースを検査 |
| 商品サービスの修飾抜け7/7件を検出 | 実ソースの各修飾をメモリ上で1か所ずつ削り、全件失敗を確認。実サービスは書き換えない |
| 動的な4表の検査抜け0件 | 各表へ展開した4正常例を通し、各表の修飾を外した4例を拒否 |
| 分割SQL後半のJOINも拒否できる | 正常・異常・文字列値・コメント・引用識別子など10例の期待結果一致 |
| 未解決の式を無視しない | 変数引数・未知の補間・呼び出し0件の3例を拒否 |
| 動的表の前提変更を検知する | マッピング変更・ループ元変更・ループ内再代入の3例を拒否 |
| 既存DDL整合試験を維持 | 既存関数本文の一致と実行成功を確認 |
| 実装後のCIを確認する | test.ymlのpytest-run-internalとlint-backend-internalが実行・成功。集約チェックのみで判定しない |

実装役はDockerと既定開発依存が使える環境で対象pytestを実行し、通常のbackend CIを確認する。DBがない環境でconftestを迂回した結果を正式pytest結果と称さない。
設計時はPython 3.12.8で資料の7関数を直接実行して7/7成功し、ruffも成功した。pytest・DB実行の結果ではない。

### 代替案・弊害・限界

TARGETS追加だけの案は実測した2種類の見落としを残すため不採用。正規表現の継ぎ足しより、Pythonの文字列構造を標準astに任せる案を採用する。
汎用SQL解析ライブラリの追加は今回の6呼び出しに対して依存・保守範囲を広げるため採らない。
この検査はSQL文法全体を理解するものではない。既知の表名と同名の別名、ドル引用文字列、スキーマと表名の間のコメント等は対応契約外で、将来導入時に設計を見直す。
SQLAlchemyの別名import・属性経由呼び出しや別関数で組み立てるSQLを網羅する設計ではない。固定した呼び出し数とソース差分レビューを併用する。
マッピングの実行時のあらゆる破壊を証明するデータフロー解析でもない。SQLのテナント指定を確認する検査であり、TCG_SCHEMAの設定値、DB権限、実取り込み成功は別の検証対象。
固定件数は正常なSQL追加でも検査を止める負担がある。追加箇所の正常・否定試験を増やしてから件数を更新する。
不具合時は本テスト変更をPRで戻し、追加検査が外れた状態を明記する。CIの無効化で対処しない。

### 自己審査と維持

Plannerの設計後、ArchitectとしてADR-113の整合検査を実施。判定: APPROVE（上記の静的検査範囲）。同一AIによる自己審査であり、独立した第二者レビューではない。
根拠: サービス全486行を確認、全6呼び出しを列挙、修飾除去7例の検出、4表展開の正否8例、Python 3.12の直接試験7/7、既存DDL検査の維持、既存CIの収集経路を確認。
設計時に未実施だったもの: 製品側への適用、正式カード検査、実装後pytest/CI、実装PR、実取り込み。実装の現在地は上記の台帳と根拠登録を参照。設計合格だけでこれらを完了としない。
守り手: 実装後は本テストと .github/workflows/test.yml。保守担当は変更PRの実装役とReviewer。POは対象PRの検証証拠から結果を確認する。
外部導入事例は不要。自社の実ソースに対する見落とし再現と否定試験で判断できるため。
Context7は利用不可。起動指示の代替許可に従い [Python 3.12公式ast資料](https://docs.python.org/3.12/library/ast.html)を2026-09-10に直接確認した。


## 13. 画面引継ぎ時の実装前審査（2026-09-10・草案）

根拠: recon.md「2026-09-10 商品マスタ画面の引継ぎ確認」。同一AIがPlannerの整理後にArchitectとして自己審査した。独立した第二者レビューではない。

判定: REVISE。未保存コードは引継ぎ/退避済みだが、一覧対象について既存APIと本書の受入条件が不一致。

- 推奨案: 本書2の全件条件を維持し、管理画面の一覧APIも非表示商品を含める。既存のcreate_product/check_duplicates、解析処理、PR #3385に変更を加えない。影響は管理一覧の表示件数が増えること。表示対象の決定を確認するまでAPIを変更しない。
- 代替案: APIの有効商品のみを維持し、本書の全件/行数一致条件を有効行数へ変更する。非表示商品の管理・確認ができないため、単なる実装都合で採用しない。
- 画面の不足: 取り込み部品、ルート/メニュー、翻訳、検索/総件数、検証結果と確定結果の表示、E2E。確認前のcommit禁止・二重クリック防止・応答不明時に自動再送しないことを試験する必要がある。
- QA/本番取り込み: tenant_001専用の実行経路と44件の最新内容・重複/キーワード衝突を確認するまで実データ投入をしない。画面完成・テスト成功だけで44件登録済みとしない。
- 検証計画: 非表示商品を含むDBの件数照合、検索とページング、非管理者拒否、ドラッグ受取り、不正CSV拒否、preview後のみcommit、ファイル変更時の確認破棄、通信失敗/二重クリック、日英文言を検査する。今回これらの試験は未実施。

維持は既存frontendチェック/追加画面試験と一覧APIの回帰試験を使う。専用のガード制度やGO経路を本テーマで追加しない。外部導入事例は不要で、自社API・実画面・DBの照合を判断根拠とする。


  ### 2026-09-11 PO判断と実装契約の確定

  全件表示についての確認にPO原文「進める、離席するので最後まで完走させて結果を報告してくれ」を受領。非表示商品も含む全件を表示する。APIのcount/一覧のis_active条件だけを除去し、検索とページング・認証は維持する。既存商品作成・重複判定・DB定義は変更しない。

  実装契約: 一覧 /super-admin/tcg-product-master と取込 /super-admin/tcg-product-master/import を独立ルートにする。SaaS管理者メニュー、PageLayoutのCSVアクション、ContentToolbarの検索、DataTable/EmptyState/TextFieldを使う。APIは実在する /tcg/products/list と既存preview/commitへ接続する。確定時は確認したFileそのものとdigestを送る。警告を表示して利用者が登録を押すまでcommitしない。処理中は同期refでも再入を拒否。commit失敗・不正応答は結果不明とし、再送ボタンを出さない。確認と結果の区別、件数、日英翻訳を必須にする。

  同一AIによる実装前自己審査: APPROVE（この画面/API変更契約に限定）。全件のPO判断、既存API/FormDataクライアントと部品props実物を照合。新規ライブラリ/API仕様の推測はしていない。受入検証は画面単体/E2E、PGの有効・非表示行混在/検索/ページング、既存lint/buildとCI。検証前なので製品完成・PO実機確認・44件投入・マージ可能とは判定しない。

  承認の範囲: 実装と検証を進める。現行GO検査を迂回せず、POの番号付きGO原文を生成しない。24時間の代理GO経路が未有効という事実は変わらない。tenant_001試行とtenant_004投入は実行経路・商品内容の確認後に限る。


### 2026-09-11 既存UI規約との対応

- ADR-027（docs/adr/ADR-027-ui-internationalization.md）: UIの見出し・操作・結果・エラーを翻訳キーで表示し、ja/enへ同一キーを追加する。
- ADR-144（docs/adr/ADR-144-ui-component-governance.md）: 一覧と取込は既存PageLayout、検索はTextField、一覧はDataTableを再利用する。新規共通部品やCI例外は追加しない。

PR本文の参照ADRに対応する本書の参照漏れを補正した。実装契約・製品コードの変更はない。GO検査はjob103082848317でpass、同jobの設計参照2件欠落を本追補で修正。Gemini実API試験の失敗は別の未解決事項として維持する。


## 2026-09-11 商品マスタのメニュー配置

PO原文「その前にサイドメニューから開ける状態にしてくれ、saas管理者メニューの解析精度管理の下に配置」。基点e81dd3ecのDesktopShell.tsx:190-195では商品マスタがSaaS管理者配列の先頭に存在し、既存routeも本番配布済み。ja.jsonのnav.superAdminTcgSupplierQualityは「解析精度管理」。

差分設計: DesktopShell.tsxの既存商品マスタ項目1行を解析精度管理の直後へ移動する。順序は取込・解析・配信、解析精度管理、商品マスタ、為替レート管理。既存to=/super-admin/tcg-product-master、labelKey、isSuperAdmin条件、他3項目を維持。API・DB・翻訳キー追加なし。理由はPOが指定した場所から既存画面を見つけられるようにするため。既存先頭維持は希望位置と異なるため不採用。

受入は指定順序・項目4件各1回・既存URL/権限制御の維持を差分で照合し、対象lint/buildと既存CIを確認する。並べ替えをなぞる新規テストは増やさない。守り手はDesktopShellの既存ナビ表示とfrontendのnav/i18n/型チェック。リスクは表示位置が変わることのみで、誤った場合は当該1行を戻すPRで復元できる。外部事例は不要、自社メニュー実物とPOの位置指定で判断可能。ライブラリ/API仕様変更なし。

同一AIのPlanner→Architect自己審査APPROVE（この1行の移動のみ）。独立レビューや番号付きGOではない。新規PRの正式GOは別途必要。新メニューの本番配置は未反映。


## 14. 発売日降順と作品タブ（2026-09-11・設計案）

対象ADR: ADR-113 / ADR-027 / ADR-144 / ADR-154。
recon: docs/handoff/tcg-product-import/recon.md「2026-09-11 発売日順と作品タブの調査」。親: docs/specs/product-master/README.md §8。
この節は既存一覧§13への追加契約案。初期CSV設計の古いAPI名より実在する /tcg/products/list を正とする。

### 14-1 目的・承認の境界・成功条件

PO原文: 「商品マスタの並びはデフォルトは販売日の新しい順に上から並べる、タブを付けてポケモン、ワンピースなど作品別に絞り込みが出来るようにする」。発売日を指すかの質問への返答は「進める」。既存release_dateを使用する。
目的は新しい商品を先に見つけ、選んだ作品だけを確認できること。成功条件は①初期表示の発売日降順、②作品選択後に他作品の混入0件、③絞込み後も日付降順の3項目。依頼として受領済み。以下の詳細ルールはPlannerの提案であり、POが述べた言葉や実装承認として代筆しない。

### 14-2 画面・変更前後

- 前: 商品コード降順、検索とページのみ。後: 「すべて」を初期選択し、検索欄の上に共通Tabs（underline/md）を置く。その下は既存ContentToolbar、件数、DataTable。CSVアクションは維持。
- 全件に対して発売日降順→ページ分割。同日の順はcode DESCで一意に固定。発売日NULLは最後、未来の発売日も日付どおり上に置く。DATEを時刻へ変換せず、そのまま一覧の日付欄に表示する。
- タブは「すべて」の後に14-3のworks順。1つだけ選択し、作品切替でqueryを保ちpage=1。検索変更でもworkIdを保ちpage=1。ページ変更は両方保持。再訪/再読み込みはすべて・空検索・1ページへ戻す（永続設定は追加しない）。
- 一覧の0件は既存EmptyState、件数は作品と検索の両方に一致するtotal。0件検索でもタブ候補は消さず、他作品へ切替できる。作品未設定・参照先不在の商品は「すべて」に残す。今回専用の未設定タブは追加しない。
- Tabsの横スクロールを使い、全作品をキーボード/タッチで選択できる。独自の共通部品や色・サイズ体系は追加しない。固定ラベルはproductCsv.allWorks（日:すべて、英:All）。作品名は業務データであり、コード別の翻訳辞書を作らない。日本語表示では空白除去後のalt_nameがあれば使い、なければdisplay_name、英語はdisplay_name。元データは変更しない。
- 最新成功のworksを一覧itemsとは別に保持し、再取得中もタブを表示する。itemsは既存どおり取得開始時に消しloading表示。最新リクエスト以外の成功/失敗/終了はすべて破棄し、別作品の旧応答で表示を戻さない。取得失敗は既存loadError/retryで同じ条件を再試行。初回失敗時は「すべて」とエラーを表示。
- 再取得で選択中の作品がworksから消えていた場合は、全件へ勝手に戻さず選択名を保持したタブを残す。「すべて」への切替は利用者操作に任せる。次回訪問は現行worksから開始する。

### 14-3 API・DB読み取り契約

既存GET /api/v1/tcg/products/listを拡張する。require_super_admin、TCG_SCHEMA、queryの既存ILIKE意味、limit既定100/上限500、offset非負、既存itemsの項目を維持。

- 任意query parameter work_id: UUIDまたは省略。省略は作品条件なし。空文字・UUID不正は422、正しいUUIDだが該当商品なしならtotal=0/items=[]。画面の「すべて」はパラメータを送らない。
- SQLのcountとitems双方に、検索条件 AND work_id一致を同一条件で適用。work_id未指定時はその条件自体を付けない。値はtextの名前付きbindで渡し、指定ありでは p.work_id = CAST(:work_id AS uuid)。表名は検証済みTCG_SCHEMAのみで組み立てる。作品名部分一致やcategory_classの比較へ置き換えない。
- itemsの並びは ORDER BY p.release_date DESC NULLS LAST, p.code DESC。その後にLIMIT/OFFSET。非表示商品も残す。商品表へのINNER JOINで作品NULL/孤立商品を消さない。
- 応答は既存total/itemsにworksを追加。各要素はid(UUID文字列), code, display_name, alt_name(空文字可)。TCG_SCHEMA.tcg_seriesから、有効な作品 OR 商品が1件以上参照する作品を取得し、code ASCで返す。参照判定は商品is_activeを問わないEXISTSを使う。重複0件、検索・work_id・ページとは独立した候補集合。非表示作品でも商品管理から辿れる。非表示かつ未参照作品は候補に出さない。有効作品は商品0件でも候補に出す。
- 同じAPIで候補を返すためHTTPリクエストは一覧1回につき1回、SQLはcount/items/worksの3回（現行2回から1回追加）。失敗時はレスポンス全体を失敗させ、取得不能を空worksに偽装しない。
- 既存のregistration-formは元明細IDが必要なため流用しない。public.tcg_series_masterも別物のため使わない。新しいDB表/列/索引・ライブラリ・環境変数は追加しない。
- 新frontendはworks欠落/配列不正をloadErrorとして扱う。旧backendへの接続時に、作品絞込みが動くように見せない。旧frontendは追加フィールドを利用しないため共存可能。配備はbackend対応後に新frontendを確認する。

### 14-4 変更範囲・対象外

実装対象は既存7ファイル: backend/app/routers/tcg_product_import.py、backend/tests/test_tcg_product_list_pg.py、frontend/src/pages/super-admin/TcgProductMasterPage.tsx、frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx、frontend/tests-e2e/tcg-product-import.spec.ts、frontend/src/locales/ja.json、frontend/src/locales/en.json。別途この設計/reconと台帳/根拠へ検証結果を記録する。
認証、商品作成、重複照合、CSV preview/commit、解析、配信、DB定義、CI設定、運用スクリプト、共通Tabs/CSSの変更は含まない。商品データの発売日補完・作品付け直しも行わない。既存7ファイルを超える変更が必要なら実装前に範囲を戻して確認する。

### 14-5 受入条件と検証方法

以下は実装後に実行する検証契約。設計時の合格実績ではない。

| 基準 | 検証方法 |
|---|---|
| AC1 初期・検索・作品絞込みの全てで発売日降順、同日code DESC、NULL末尾 | test_tcg_product_list_pg.pyに、コード順と日付順が逆転する行、同日2行、未来日、NULL2行を含め、返却コード列の完全一致を検査 |
| AC2 51件以上でも全体の順序を守りページ間の重複/欠落0 | 同PG試験で同一作品の51件以上を作り、limit50の第1/第2ページの連結が全件期待列と一致。更新がない固定データで比較 |
| AC3 作品×検索はANDで総件数/items一致、他作品混入0 | ポケモン/ワンピースの両方に同じ検索語を置き、作品指定あり/なし・0件・offset超過・非表示商品の検索を実PGで検査 |
| AC4 候補が検索/ページで欠けず重複0、管理対象が消えない | 有効0商品、有効複数商品、非表示参照あり/なしの4種の作品でworks期待配列を比較。商品NULL/孤立work_idがすべてに残ることも検査 |
| AC5 入力・権限・スキーマ境界を維持 | 同backend試験ファイル内のHTTPルータ試験で不正/空UUID=422、非管理者拒否、未認証拒否を既存依存の正規経路で検査。未知の有効UUID=0件はPG試験。全SQLが隔離スキーマのみを参照し、参照不許可スキーマの同名商品を拾わない |
| AC6 切替/検索でpage1へ戻り、片方の条件を保持する | TcgProductMasterPage.test.tsxでpage2→作品切替→検索→すべての各URL/query/offsetと選択タブを検査 |
| AC7 遅着・失敗・欠落worksで誤表示しない | 同frontend試験で作品Aの遅着応答をB完了後に解決してもB表示維持。B失敗時のA成功も無視、retryはB条件。works欠落/不正、0件でも候補保持、選択作品消失時に全件へ自動切替しないことを検査 |
| AC8 日英・狭い画面・既存導線を確認できる | tcg-product-import.spec.tsで日英の作品名fallback、すべて、2作品切替、狭幅横スクロール/キーボード選択、CSV導線と非管理者拒否を確認。既存モックにworksを追加。スクリーンショットを/tmp/reportsに保存 |
| AC9 正式チェックと実接続を区別して完了確認する | backend標準lint/pytest、frontend check:all/build/対象単体/E2E。対象PG試験はskip0を必須としCIのpytest-run-internal成功を確認。tenant_001で日付列・作品別商品・件数を実APIと画面で照合。モック成功のみでは実機確認済みにしない |

PG fixtureは既存の一時スキーマ＋rollback方式を維持し、20260902_110000_tcg_classification_masters.sqlをそのスキーマへ適用して作品表を作る。SQLルーター直接呼出しではwork_id=Noneを明示し、FastAPIのQueryデフォルトオブジェクトをSQLへ渡さない。HTTP試験ではルーターを実際にマウントし入力検証を通す。SQLiteでPGのNULL順/UUID動作を代用しない。Docker不在なら既定のlintだけ実行し、正式PG試験は未実施として残す。

### 14-6 Why・代替案・リスクと対処

- 採用: 既存release_date/work_idと共通Tabsを利用し、サーバーで絞込み・整列する。根拠はreconのAPI2クエリ、1ページ50件、DATE/UUID列、共通部品の実物。新しい保存先や二重の作品定義が不要。ADRのWhyへ転記する場合もこの実物根拠を使い、業務改善率は創作しない。
- 不採用: 取得済み50件だけをfrontendで並べる/絞る案は、別ページの商品を落としてtotalと表示が不一致になる。作品名の固定配列は追加作品のたびに改修が必要。同名の別シリーズAPI流用は参照先が違う。候補専用の新APIは不要な通信/認証/エラー経路を増やす。
- 代償: worksの読取1回追加と毎応答の候補転送、日付ソートによる負荷。seedは11作品だが本番件数/速度は未測定で性能改善を保証しない。実装後に隔離PGとQAで時間/件数を記録し、既存一覧タイムアウト25秒（frontend/src/lib/api.ts:38）未満に完了することを確認。索引追加が必要と判明したら別設計へ戻す。
- 作品タブは有効0商品にも出るため空一覧になり得る。0件表示で説明する。alt_nameは日本語専用列ではないため、値が別名ならそのまま別名が出る。翻訳/作品名修正は本便に混ぜない。
- OFFSET方式は並行の商品追加/発売日変更の間に重複/抜けが起き得る。現行と同じ制約で、固定データ内の安定順序を保証する。更新をまたぐスナップショットやカーソル方式は導入しない。
- 不具合時は実装PRの変更をレビュー付きPRで戻す。DB書込みがないためデータ巻戻しは不要。backendを先に旧版へ戻すと新画面がloadErrorになるためfrontendを先に戻すか両方を揃える。ガード/CIは無効化しない。

### 14-7 計画・維持・公式資料

1. Plannerが調査→本案作成。Architectとして同一AIが整合検査し、その結果を14-8へ記録する。
2. POが詳細案を確認し実装移行を明示承認した後、実装役の専用worktree/正式カードを準備。実在フルパスと読んだ節を記載し、scripts/card-lint.shで正式検査してから発行する。本設計文書を実行カードと扱わない。
3. 実装役が7ファイルを変更しAC1〜9/既存チェックを実行。Reviewerが結果を確認。マージ/配備はその時点の正規GO手順で別途実行し、番号付きGOを推測しない。

守り手は既存backend/tests/test_tcg_product_list_pg.py、frontend/src/pages/super-admin/TcgProductMasterPage.test.tsxとfrontend/tests-e2e/tcg-product-import.spec.tsを拡張する。保守担当は商品一覧を変更する実装役とReviewer。CI設定は既存経路を維持する。POはQAで初期日付順→ポケモン→ワンピース→すべてを操作し、日付列/商品/件数を確認する。

外部導入事例は該当なし。自社一覧のSQL・部品・隔離DBの検証で判定できる小規模変更であり、他社の改善率を成功の証明にする必要がない。
Context7 MCPは利用不可のため、起動指示で許可された公式資料の直接確認を2026-09-11に実施した。
- [PostgreSQL 16のORDER BY](https://www.postgresql.org/docs/16/queries-order.html): DESCの既定はNULL先頭なのでNULLS LASTを明示する。同値は次のソート列で決まる。
- [FastAPIのquery parameter](https://fastapi.tiangolo.com/tutorial/query-params/)と[追加型](https://fastapi.tiangolo.com/tutorial/extra-data-types/): 任意指定はNone、UUID型を境界で検査する契約に使う。
- [SQLAlchemy 2のtext](https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.text): 入力値は名前付きbindにする。

### 14-8 Architect自己審査

判定: APPROVE（14節の詳細案を実装契約として使える設計品質に限定）。Plannerとして作成後、Architectとして同一AIが実物/規約/試験経路との整合を審査した。独立した第二者レビューではない。POの詳細案承認・実装開始・マージ・配備の承認を兼ねない。

| 審査項目 | 根拠・判定 |
|---|---|
| 目的・親仕様との対応 | 3成功条件を14-2/14-3とAC1〜3へ対応。既存全件管理をAC4で維持 |
| API/DBの実在・互換 | DATE/UUID/作品表、既存2クエリ、必須元明細の別APIを照合。追加works契約と旧API混在時のエラーを規定 |
| UI・非同期・翻訳 | Tabs/PageLayout/ContentToolbarのprops実物、cancelled式、日英キーと業務データの区別を照合。独自共通部品0 |
| 検証可能性・CI | 9受入条件にPG/HTTP/画面検証を対応。既存fixtureに不足する作品migrationの追加とskip0条件を明記。25秒は既存クライアント設定を引用 |
| 範囲と維持 | 製品変更7ファイル、共通部品/DB/CI/登録解析は対象外。既存3試験ファイルとReviewerが守る |
| 文書検査 | git diff --check成功、check-task-state成功、validateDesignDoc/validateMaintenanceSectionのエラー0。報告: /tmp/reports/TH-PRODUCT-DATE-TABS-DOC-CHECK.json と TH-PRODUCT-DATE-TABS-TASK-CHECK.txt |

審査中に引用行番号を実ソースへ照合し補正した。外部仕様は14-7の公式資料で確認済み。設計合格を妨げる未確認のAPI仕様は残っていない。
未完了は、POの詳細案確認/実装移行承認、正式カード作成・検査・発行、製品実装、AC1〜9実行、実装後レビュー、PR/CI/配備確認。本番件数・速度・実機表示は未測定のままであり、設計合格を動作保証としない。次の一手はPOが本案を確認すること。

### 2026-09-11 PR #3431へのPO GO受領

PO原文「GO #3431」を本セッションで受領。対象は本節の設計文書PR #3431で、設計案の保存・マージを承認されたものとして扱う。受領確認時刻は2026-09-11 06:29:55 UTC（発話自体の時刻を推定したものではない）。上記のPO詳細案確認待ちという状態を本追記で更新する。製品コード・DB・CI・本番変更は含まない。正式カード未発行・実装未着手。次はレビュー済み設計に基づく実装カードの作成・正式検査であり、この文書PRのGOを製品PRのマージGOとして流用しない。

### 2026-09-11 実装開始承認とカードへの引継ぎ

設計PR #3431はa66e938282ce1c2e3557826a7abb37187110c160でマージ確認済み。実装開始まで承認しカード作成・引継ぎを進めてよいかの質問へのPO原文は「次を進める」。これを本設計の実装開始承認として記録する。設計担当は自動的に実装役へ切り替わらず、別エージェントも起動しない。

実装場所はrelease/product-master-date-tabs-impl、基点6c55e40df3f3762880353e7c9a4f9d768f63f790。#3431反映済み、対象製品7ファイルは#3431マージ時から差分0。正式カードは[TH-PRODUCT-DATE-TABS-IMPL-01.txt](TH-PRODUCT-DATE-TABS-IMPL-01.txt)。本便は実装・ローカル検証・コミットまで。実装コミットの公開、CI/実PG/QA実画面、製品PRのGO・マージ・配備は後続。

準備時のdocker infoはdocker.sock不存在で失敗した。PGの正式実走を飛ばして機能完成とせず、既存CIの実PGを後続の必須条件として保持する。既存依存の導入と変更範囲内の失敗修正だけをカードで許可する。承認済みAC1〜9と7ファイル契約に変更はない。カードの検査結果はreconと根拠登録に記録する。

引継ぎの保存は同じ実装用ブランチの準備PRで行う。実装コミットの確認後はそのPRを更新し、重複する実装PRを新規作成しない。準備PRは実装・検証完了までDraftのまま保持し、文書だけの現在の差分を機能完成としてマージしない。


## 15. 空のサンプルCSVと登録者情報の限定修正（2026-09-11）

状態: 設計前提PO合意済み／詳細案／製品未実装。モードは本書冒頭の handoff。親: [商品マスタ](../../specs/product-master/README.md)。根拠: [調査追補](recon.md#2026-09-11-空のサンプルcsvと登録者情報の再開調査)。既存テーマの延長として本書を更新する。

### 15-1 目的・承認の境界

提示した確認文は「この形式を今回のサンプルとして設計してよいですか？」。対象形式は「10列の見出しだけのCSV＋画面の入力説明」。PO返答原文は「進める」。これは形式を前提に設計を進める承認であり、この詳細案の実装・マージ・本番投入のGOではない。登録不具合は引き継ぎ依頼に従って限定修正案を併記する。

目的は、SaaS管理者が列を手入力せずCSVを作り始められ、既存の認証を通った登録者情報の読み方で登録が落ちないこと。成功条件は下表AC1〜7。44商品登録の完了や安全な本番再送をこの設計の成果に含めない。

### 15-2 変更前後・実装契約案

現状はファイル選択と書式説明だけ。変更後は選択画面のドロップ領域の直前に ContentToolbar を置き、right に既存 Button（secondary、type=button）で「空のサンプルCSVを保存」を配置する。その直下に入力説明を置く。busy中は無効、preview/result/uncertainの段ではこの操作を表示しない。既存PageLayout・確認・結果・再送禁止を維持する。新しいCSSや共通部品変更は不要。

保存対象は新規 `frontend/public/templates/tcg-product-import-template.csv`。UTF-8 BOM付き、見出し1行＋CRLF、商品行0、次の10列を空白を足さずこの順で持つ。

```text
mark,japanese_title,english_title,release_date,search_keywords,exclude_keywords,division_code,work_code,manufacturer_code,product_category_code
```

Buttonのクリック内で一時的なa要素を生成し、hrefを `/templates/tcg-product-import-template.csv`、downloadを `tcg-product-import-template.csv` にする。bodyへ追加してclick、finallyで除去する。商品API、認証情報取得、preview、commitを呼ばず、File/preview/errorの状態も変更しない。保存完了をアプリが推定する通知は出さない。URLは同一オリジンで、CSVは公開静的資産となる。内容は公開可能な見出しだけで、商品・マスタコード・認証情報を含めない。画面自体の管理者制限は既存どおり。

入力説明の翻訳キーと文案（両言語のキーを対に追加、t()経由）:

| productCsv配下のキー | 日本語 | English |
|---|---|---|
| downloadTemplate | 空のサンプルCSVを保存 | Download blank sample CSV |
| templateIntro | 見出しだけのCSVです。2行目から商品を入力し、見出しの順序を変えずにUTF-8のCSVで保存してください。 | This CSV contains only column headings. Enter products from row 2, keep the heading order, and save as UTF-8 CSV. |
| templateRequired | 必須項目は日本語名と4つの分類コードです。分類コードには登録済みのコードを使用してください。 | The Japanese title and all four classification codes are required. Use existing classification codes. |
| templateOptional | 発売日はYYYY-MM-DD形式で入力し、不明なら空欄にします。検索・除外キーワードを複数指定する場合は、1つのセル内でカンマで区切ってください。 | Enter the release date as YYYY-MM-DD, or leave it blank if unknown. Separate multiple search or exclusion keywords with commas within one cell. |

説明では必須5列の機械名を対応づけて表示する（japanese_title、日本語名／division_code、work_code、manufacturer_code、product_category_code、4分類コード）。見出し名は翻訳対象ではないCSV識別子。既存 productCsv.format と重複する説明はまとめて配置し、その既存キーは他画面のために削除しない。

登録側は `backend/app/routers/tcg_product_import.py` で `from app.models import User` を追加し、require_super_adminを受ける3関数の user/_user型をUserへ揃える。実行者の式だけを `str(user.email or user.id or "")` に直す。email優先・id代替・空の場合空文字という既存意図を維持する。require_super_adminの認可条件、get_current_user、サービス、SQL、request/response、digest検査は変更しない。

### 15-3 影響範囲

製品実装時に触るファイルは次の8本に限定する。本設計便では編集しない。

1. frontend/public/templates/tcg-product-import-template.csv（新規）
2. frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx
3. frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx
4. frontend/src/locales/ja.json
5. frontend/src/locales/en.json
6. frontend/tests-e2e/tcg-product-import.spec.ts
7. backend/app/routers/tcg_product_import.py
8. backend/tests/test_tcg_product_import.py

対象外: DB/migration、create_product、履歴の原子性、認証・権限制度、CI/運用スクリプト、44商品のCSV作成・投入・発売日の採択、QA接続先変更、解析/再解析/3シート配信。既存親仕様の2層マスタを今回再設計しない。必要な追加変更が出た場合は契約へ戻す。

### 15-4 受入条件・検証方法

| ID | ○の条件 | 実装後に行う検証 |
|---|---|---|
| AC1 | 保存ファイルの見出しがCSV_COLUMNSと順序まで一致し10列、商品0行、BOM/CRLFあり | Panel.test.tsxでnode:fsを使い実資産を読む。backendサービスのCSV_COLUMNSのリスト区間を限定抽出し、引用された文字列10個を順に比較。リスト抽出不能も失敗にする。固定の期待値複写だけで一致を主張しない |
| AC2 | 日英両方で保存操作が見え、クリック/キーボードでファイルが保存され、画面は取込に留まる | 既存E2Eに日英各ケースを追加。downloadイベント、suggestedFilename、取得ファイルの実バイトを検査。API mockとは別に静的資産は実サーバーから取得する |
| AC3 | 保存操作によるpreview/commit呼出0回、選択済みFile変更0回 | Panelの単体試験でa.clickだけを差し替え、api.postForm未呼出と選択したファイルの維持を確認。busy中とpreview/result/uncertainでは操作不可も確認 |
| AC4 | 空テンプレートを選んで内容確認すると0件で登録できない | E2Eのpreviewを0件応答にして確定ボタン無効・commit0回を検査。このAPI応答はモックであり実DB検査と区別する |
| AC5 | 本物のUserインスタンスでcommit endpointが成功応答し、emailが実行者として1回渡る | backend既存HTTPテストで認証依存をUser(id=1,email="qa@example.com",is_super_admin=True)へ置換、previewとcommit_importをAsyncMock。status200・戻り値・同じraw/file名/emailでawait1回をassert。id代替ケースも追加。修正前のuser.getへ戻すと失敗することを確認 |
| AC6 | 未認証拒否、非管理者403、digest不一致409、不正ファイル422でcommit_import未呼出 | 既存テストの辞書fixtureをUserに置換。非管理者試験はrequire_super_admin自身を残しget_current_userだけ非管理者Userへ置換。各依存上書きはfinallyで復元。認証システムそのものを改造しない |
| AC7 | 日英説明・管理者制限・狭い画面・既存取込操作を維持 | 日英390pxの実ブラウザー画像とキーボード操作、Panel単体/既存E2E、frontend check:all/build、backend lint-ci、既存CIのPGを含むpytestを確認 |

検証で全件rollback・履歴との完全同時確定・実ユーザーログイン・本番登録の成功まで証明したとは言わない。AC5は本物のUser型＋HTTP経路を使うが、DB書き込みはモックである。実DB試験はDocker/CIで実施する。Dockerなしの手元ではpytestを実行せずlint-ciまでとし、CI未確認を合格としない。

### 15-5 選択理由・限界・Why用根拠

見出し10列と必須5列は既存パーサーから確認できる。見本商品を1行入れる方式は、コードの実在・重複・誤登録への対処が増えるため不採用。動的テンプレートAPI新設は固定10列に対して認証/応答/テスト面が増えるため不採用。公開静的1ファイルなら登録サービスを呼ばず配布できる。見本行がなく入力例としては弱い点を画面説明で補うが、実コードの検索UIは追加しない。

認証依存の返却はUser、呼出先はdict.getという実物不一致を直す。現行HTTP試験は成功commit経路を検査していないため、その経路を本物のUser型で1本以上追加する。外部導入事例は該当なし。固定ファイル配布とローカル型不整合の修正であり、他社の成功率は本件の成功根拠にならない。数値のある根拠は列10/必須5/返却型不一致1箇所と検証条件に限る。

残る制約: ダウンロードは利用者のブラウザー設定に左右されるため属性指定だけで成功を判定しない。backendは1商品ごとのcommitであり、途中失敗で部分登録が残る。商品登録と履歴記録の間にも空白区間がある。digestは同一ファイルの証明で、人の承認券ではない。既存§2/§8の「承認を経ない経路0」「追跡できる」という記述を、現実に保証済みと読み替えない。これらの制度/DB変更は別の設計判断を要する。

### 15-6 維持の仕組み

守り手: frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx、frontend/tests-e2e/tcg-product-import.spec.ts、backend/tests/test_tcg_product_import.py。前者に実CSVとbackend列定義の一致検査、後者にUser型の成功経路を追加する契約。既存 .github/workflows/frontend-check.yml と .github/workflows/test.yml の静的/バックエンド検査を維持する。対象E2Eとfrontend単体の実行結果は実装役がPRへ添付し、Reviewerが確認する（本便でCIの新規必須化はしない）。将来列を変更する担当は資産・入力説明・試験を同じ便で更新する。

### 15-7 設計審査

判定: APPROVE（§15の限定設計品質）。同一AIがPlannerとして作成後、Architectとして本物の返却型/既存API/部品/CSV仕様/検証経路と8ファイル境界を照合した自己審査であり、独立した第二者レビューではない。空CSVが既存パーサーで0件・エラー0になる隔離検算と、現行endpointのget不整合再現が根拠。製品試験は未実施で、合格は動作保証ではない。詳細案の未解決技術前提はない。残余リスクは§15-5、実データ投入の認証・復旧経路は別段階の未解決事項として残す。PO詳細案承認、製品実装開始、正式カード発行、製品検証、マージ、本番反映、44商品投入は未実施。LINEのGO委任は有効化待ちのまま。本設計は実行カードではない。


### 2026-09-12 §15のPO承認・正式カード準備

確認文「この設計を承認し、実装役へ渡す正式カードの作成へ進めてよいですか？」へのPO返答原文は「進める」。§15の詳細設計承認および実装役へ渡すカード準備の承認として記録する。設計担当の製品実装への切替、別エージェント起動、PR #3436や後続製品PRのマージ、本番投入を承認されたとは扱わない。前節の詳細案承認待ちは本追記で更新する。

PR #3436のd4f5f86fは実行チェックすべて成功、対象外の製品試験はSKIPPED。2026-09-12のdocker infoはdocker.sock不在でexit1。実装カードはローカルpytestを実行させず、後続の正式CIで実DB試験を確認する境界を保持する。

正式カード: [CARD-PRODUCT-CSV-TEMPLATE-IMPL-01](card-template-impl.md)。origin/main adc8bc4d起点の専用実装worktreeを公式手順で作成し、実在・未保存0・preflight成功を確認。カードはローカル実装/検査/未保存差分の報告までを指定し、公開と本番操作は別便へ分ける。カード発行は実装役の自動起動を意味しない。設計担当は読取・文書作業を継続する。


### 2026-09-12 実装役への委任

直前の説明「カードを実装役へ渡せます。実装役の起動・製品変更・本番変更は行っていません。」へのPO返答原文は「進める」。本カードを実装役1名へ渡す指示として受領し、csv_card_executorへ委任した。担当は専用実装worktreeの8製品ファイル、成果物は差分と指定の生報告。停止条件は正式カードのまま。設計担当は製品編集を行わず、返却差分と試験の読み取り確認を担当する。コミット・公開・マージ・本番変更・孫エージェント起動は委任対象外。

カード運用訂正: 01は報告保存で停止し製品未着手。報告保存方式を直接リダイレクトにした [CARD-PRODUCT-CSV-TEMPLATE-IMPL-02](card-template-impl.md) が現在の正式版。設計§15・8ファイル境界は不変。原因と実測はrecon同日追補。

実装現在地（2026-09-12）: カード02の指定8ファイル実装・ローカル単体13件/E2E7件/ビルド/静的検査まで実施。設計担当の読取差分確認済み。AC5〜6のHTTP試験/実DB/CIと本番QAは未実施。製品コミット・公開・マージ・配備は未実施。詳細と実行主体の区別はreconの同日実装結果を参照する。


### 2026-09-12 製品PR公開・CI確認の承認

提示した次手「実装済みの8ファイルをコミットして製品PRを作り、CIで未実行のHTTP・DB試験を確認する段階」へのPO返答原文は「進める」。これを製品差分のコミット/公開とCI確認の承認として受領。マージ・本番反映は製品PR番号へのGO後とした説明を維持する。[公開カード](card-publish.md)を同じ実装役へ委任した。8製品ファイルに承認設計とreconの2文書を添え、台帳は設計担当が保持する。CIで発見した範囲内の実装修正は実装役が行い、範囲外や契約変更は設計へ戻す。
