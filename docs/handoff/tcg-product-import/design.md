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
状態: 設計案作成済み・同一AIの自己審査APPROVE（本節の限定範囲）・製品側テスト未変更。個別の実装カードは未発行。

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
未実施: 製品側への適用、正式カード検査、実装後pytest/CI、実装PR、実取り込み。設計合格をこれらの完了に読み替えない。
守り手: 実装後は本テストと .github/workflows/test.yml。保守担当は変更PRの実装役とReviewer。POは対象PRの検証証拠から結果を確認する。
外部導入事例は不要。自社の実ソースに対する見落とし再現と否定試験で判断できるため。
Context7は利用不可。起動指示の代替許可に従い [Python 3.12公式ast資料](https://docs.python.org/3.12/library/ast.html)を2026-09-10に直接確認した。
