# recon: 共用商品マスタ登録の必須項目（現在地調査）

> この文書は何か: 共用の商品マスタに商品を登録・更新する経路と画面が、今どの項目を必須としているかを実コードと本番の件数で調べた事実の記録（評価・提案は書かない）。
> 親（設計仕様書）: [docs/specs/product-master/README.md](../../specs/product-master/README.md)
> 実測時の origin/main SHA: b7e3f28d389e1f25b83c1b30b4e6f58735ddc04a（2026-10-16 fetch 後）
> 生出力の保存先: /tmp/CC報告ファイル/master-required-fields/（リポジトリ外）

## 作業メモ
- `bash scripts/new-worktree.sh release/master-register-required-fields --claude` は worktree 作成まで成功し、末尾の claude 起動で `Error: Input must be provided either through stdin or as a prompt argument when using --print` を出して exit 1 で終了した（生出力: worktree.txt）。
- 同スクリプトは「active-work.d に登録しました」と表示したが、worktree 側 .claude-pipeline/active-work.d/ に release-master-register-required-fields.md は無かった。本店側 /Users/tanizawashingo/salesanchor/.claude-pipeline/active-work.d/ には同名ファイルがある（本店側は触っていない）。台帳は worktree 側に新規作成した。
- preflight は rc=0（PREFLIGHT OK）。警告: 本店が origin/main より 2748 コミット遅れ、本店に台帳以外の未保存 26 件（preflight.txt）。
- 作業中にフックで 3 回停止した（いずれも設計者の指示で対応）: (1) 全走査 grep の検索パターンに削除系の語を含めた時（削除経路は対象外にして再走査）、(2) 本番の件数取得で psql に `-A -F` を付けた時（オプションを `-X -At` に揃えて取り直し）、(3) 本文を Bash の heredoc で書いた時（Write ツールで作成）。
- 仕入元の名前は書いていない。

## 4-a 既存 ADR
- コマンド: `git grep -i -l -E 'product_format|細分類|product_formats|商品マスタ|search_keywords|exclude_keywords|name_en|release_date' -- docs/adr/` が 18 ファイル（a_adr_files.txt）。FEATURE-INDEX の該当行は docs/adr/FEATURE-INDEX.md:18（在庫 / 商品マスタ は ADR-099、ADR-093、ADR-014）。
- `git grep -n -i -E 'product_format|細分類' -- docs/adr/ docs/specs/product-master` は 0 件（a_format_grep.txt）。細分類（product_formats）を決めた ADR は grep では見つからなかった。
- docs/adr/ADR-155-product-master-ssot-csv-app.md:23-31（決定）: 商品マスタデータの正規の更新手段は CSV 取り込みとアプリ画面の 2 経路のみ。migration は構造変更のみで、値の操作は禁止。保護対象は public.products・tcg_products・product_search_keywords・product_exclude_keywords。
- docs/adr/ADR-156-product-classification-tree-and-master-separation.md（決定節）: 商品分類を product_kinds（大分類）、type_master（中分類）、product_lines（小分類）、products（商品）の 3 層ツリーで管理。細分類（product_formats）への言及は無い（grep format で 0 件）。
- docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md:44-47: public.products.name_en は tcg_products.english_title から、mark は mark から、release_date は release_date から移す。:73-77 で product_search_keywords と product_exclude_keywords を持つ。
- docs/adr/ADR-093-inventory-table-product-master-redesign.md:35: products の未実装 7 列に search_keywords と exclude_keywords を含む。
- docs/adr/ADR-083-tcg-type-master.md:16: type_master（旧 tcg_type_master）は code・name_ja・name_en・sort_order・is_active を持つ。

## 4-b 共用 products を作る・更新する全経路
全走査: `git grep -n -i -A2 -E 'INSERT INTO|UPDATE ' -- backend/app backend/scripts scripts` を products で絞った結果（b_products_writes.txt）。削除経路は設計対象外のため走査していない。

| 経路 | 入口 | 書き込み箇所 | 呼び出し元 |
|---|---|---|---|
| 画面の新規作成 | POST /tcg/products/create backend/app/routers/tcg_product_import.py:382-412 | create_product（backend/app/services/tcg_product_master_svc.py:331、INSERT は :398） | frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:138 |
| 解析レビューからの登録 | POST /tcg/products backend/app/routers/tcg_product_master.py:210 付近（本文は :112-126 付近） | 同上 create_product | frontend/src/features/tcg-analysis-review/reviewActions.ts:120、ProductMasterDrawer.tsx:147 |
| CSV 取り込み | POST /tcg/products/import/commit tcg_product_import.py:223 | backend/app/services/tcg_product_import_svc.py:524 が create_product を force=True, commit=False で呼ぶ | frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx:52 |
| 詳細の保存（更新） | PUT /tcg/products/detail/{id} tcg_product_import.py:298-321 | backend/app/services/tcg_product_detail_svc.py:177（UPDATE public.products） | TcgProductDetailDrawer.tsx:120、productDetailModel.ts:61（除外語の追加） |
| 往復 CSV の更新 | tcg_product_roundtrip_svc.py の commit_update | backend/app/services/tcg_product_roundtrip_svc.py:378（動的な列の UPDATE public.products） | 取り込み画面（往復 CSV） |
| 検索語・除外語の追加 | POST /tcg/products/{id}/search-keywords、exclude-keywords tcg_product_master.py:250・:279 | tcg_product_master_svc.py:543・:613（キーワード表の INSERT） | ProductMasterDrawer.tsx:295 ほか |

テナント商品用（区別）: backend/app/routers/products.py:379（INSERT）、:408 と :475（UPDATE）。別表の更新として backend/app/routers/purchase_orders.py:265・:301（products の quantity 更新）がある。buyback_shop_products は別表。

各入口の受け取り項目と必須項目:
- CreateProductBody（tcg_product_import.py:369-379）: 必須は japanese_title・product_kind_id・work_id・manufacturer_id・product_category_id（型は str、既定値なし）。任意は mark・english_title・release_date・search_keywords・exclude_keywords（既定は空）。
- CreateProductRequest（tcg_product_master.py:92-）: 必須は extraction_item_id・source_message_id・work_id・manufacturer_id・product_category_id・japanese_title。product_kind_id は既定 ""。任意は mark・english_title・release_date・検索語・除外語・force。入口で japanese_title の空文字だけ 422（PRODUCT_MASTER_V2_JAPANESE_TITLE_REQUIRED、:112-114 付近）。
- ProductDetailUpdate（tcg_product_import.py:275-）: japanese_title は 1〜5000 文字。release_date は `str | None` で既定なし（キー自体は必須）。product_kind_id と work_id は None 可で既定 None。manufacturer_id と product_category_id は None 可で既定なし。revision 必須。extra は forbid。
- CSV（tcg_product_import_svc.py:57-63 の REQUIRED_COLUMNS）: japanese_title・division_code・work_code・manufacturer_code・product_category_code。静的検査（:241-）で release_date の書式不正はブロック、mark 空は警告 MARK_EMPTY、検索語なしは警告 NO_SEARCH_KEYWORD。
- create_product の INSERT 列（tcg_product_master_svc.py:398-410）: product_code, name, release_date, category_class, product_kind_id, work_id, manufacturer_id, product_category_id, mark, name_en, is_active。product_format_id・product_line_id・type_master_id は含まれない。どの入口の入力項目にも product_format_id は無い。
- update_product_detail の UPDATE 列（tcg_product_detail_svc.py:177-184）: name, name_en, mark, release_date, product_kind_id, work_id, manufacturer_id, product_category_id, category_class。product_format_id は含まれない。

## 4-c 画面
frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx（252 行）と productDetailModel.ts（63 行）。部品はすべて components/ の金型（TextField・Textarea・Select・Button・Drawer・ConfirmModal、:3-8）。
- 日本語名: TextField required（:215）。保存時に空なら productDetail.titleRequired（:117 編集、:135 作成）。
- 英語名（:216）、型番（:217）、発売日（:218、type=date）: required 指定なし。
- 分類 4 欄（:219-227）: classificationFields（productDetailModel.ts:4）の product_kind_id・work_id・manufacturer_id・product_category_id を Select で描画。required は field が work_id のとき、または編集モードで元の値が null でないときのみ（:225）。作成モードでは work_id のみ required。
- 検索キーワード（:228）と除外キーワード（:230）: Textarea、required なし。
- 細分類（product_format_id）の入力欄は画面に無い。Detail 型（productDetailModel.ts:6-15）にも product_format_id は無い。
- 作成時の送信（:138-150）: 空の分類は "" のまま送る。API 側は str 必須で、空文字を弾く検査は確認できていない（未確認。実機・テストでは未検証）。
- i18n: frontend/src/locales/ja.json:3935 と en.json:3935 に productDetail（生出力: c_ja_productDetail.txt、c_en_productDetail.txt）。キーは title, code, japanese_title, english_title, mark, release_date, division_id, product_kind_id, work_id, manufacturer_id, product_category_id, search_keywords, exclude_keywords, wordsHint, unset, titleRequired, invalid ほか。product_format_id に対応するキーは無い。

## 4-d 細分類（public.product_formats）
- 列（本番 information_schema、d_formats_columns.txt）: id integer NOT NULL / code varchar NOT NULL / name varchar NOT NULL / name_en varchar NULL / line_id integer NULL / display_order integer NOT NULL 既定100 / is_active boolean NOT NULL 既定true / created_at / updated_at / kind_id integer NULL / type_master_id integer NULL。
- 定義: migrations/20260920_130000_create_product_classification.sql:54-64（line_id は product_lines を参照、ON DELETE SET NULL）、migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql:15（kind_id は product_kinds を参照）、migrations/20260923_010000_product_formats_add_type_master_id.sql:16（type_master_id は type_master を参照）。別表 product_format_game_links（format_id, type_master_id, alias）は migrations/20260922_030000_product_format_game_links.sql:12。
- 親子を表す列: 細分類は line_id（小分類）・kind_id（大分類）・type_master_id（中分類）を持つ。小分類 product_lines は type_id（中分類）を持つ（migrations/20260921_080000_product_lines_add_type_id.sql:27）。中分類 type_master は kind_id（大分類）を持つ（migrations/20260921_070000_rename_tcg_type_master_to_type_master.sql:62）。
- 本番の全行（d_formats_rows.txt、25 行）: 全行 is_active=true。line_id は 25 行すべて null。kind_id は 25 行すべて 1。type_master_id は 1 / 2 / 4 / 5 / 20 / 21 / 23 のいずれか。id と名前（並び順の値）: 1 ブースターパック(10)、2 エクストラブースター(20)、3 スターターデッキ(30)、4 強化拡張パック(40)、5 ハイクラスパック(50)、6 プレミアムブースター(60)、7 テーマブースター(70)、8 コンセプトパック(80)、9 スペシャルパック(90)、10 ストラクチャーデッキ(100)、17 スペシャルBOX、18 デッキビルドBOX、19 プレミアムトレーナーボックス、20 コレクターボックス、21 ハイクラスデッキ、22 ブースターBOX、23 スペシャルセット、24 イラストレーションボックス、25 ストレージボックス（17〜25 は並び値 100）、11 アドバンスデッキ(110)、12 スタートデッキEX(120)、13 メモリアルパック(130)、14 アニバーサリーセット(140)、15 ギフトセット(150)、16 イルミニアーズトローヴ(160)。
- 管理画面: API は backend/app/routers/super_admin_product_formats.py（GET・POST・PATCH・DELETE /super-admin/product-formats、:36・:66・:96・:130）。スキーマは backend/app/schemas/product_format.py。画面は frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx（AnalysisRulesPage.tsx:181 から表示、サイドバーは AnalysisRulesSidebar.tsx:115）。API の列定義 _COLS と Pydantic スキーマに kind_id は含まれない（super_admin_product_formats.py:27）。
- 削除ガード: super_admin_product_formats.py:135-147 が products.product_format_id で参照中なら 409、無ければ is_active を FALSE にする。
- FK: products.product_format_id INTEGER は product_formats(id) を参照、ON DELETE SET NULL（migrations/20260920_130000_create_product_classification.sql:97-99）。
- 本番 products の product_format_id（d_products_format_counts.txt）: 全 1411 件、共用（tenant_id NULL）1411、テナント別 0。product_format_id が入っているのは共用 1247、テナント別 0。
- 未確認: 本番の products.product_format_id がどの経路で入ったか。現行コードの書き込み経路に product_format_id の書き込みは無い。過去の migration や手作業かどうかは未調査。

## 4-e 本番の共用商品（tenant_id IS NULL）全件の空欄件数
取得: 2026-10-16、リモート接続 1 本、読み取り専用の件数 SELECT 1 本（FILTER 付き、オプションは -X -At と -c のみ。e_shared_empty_counts.txt）。生出力: `1411|118|868|145|0|1174|164|1260|1024`

| 項目 | 空の件数 | 全件 |
|---|---|---|
| mark（NULL か空白のみ） | 118 | 1411 |
| name_en（NULL か空白のみ） | 868 | 1411 |
| release_date（NULL） | 145 | 1411 |
| 検索語なし（product_search_keywords に行なし） | 0 | 1411 |
| 除外語なし（product_exclude_keywords に行なし） | 1174 | 1411 |
| product_format_id（NULL） | 164 | 1411 |
| manufacturer_id（NULL） | 1260 | 1411 |
| product_category_id（NULL） | 1024 | 1411 |

product_format_id の空 164 は、全件 1411 から値あり 1247（4-d）を引いた数と一致する。
参考（別便の記録の引用）: 10/1 以降に登録した 63 件の数え上げ /tmp/CC報告ファイル/inventory-6checks/box-priority/unreg/fields/recent_counts.txt は total 63、mark_empty 49、name_en_empty 52、release_empty 30、exclude_kw_none 32、format_null 63、line_null 63、type_master_id_null 63、mfr_null 6、pcat_null 0。

## 4-f 関連テスト
- backend/tests/test_tcg_product_master.py: test_create_product_empty_title（:339、タイトル空の登録）、test_create_product_with_mark_english_title（:283）、test_create_product_requires_auth（:126）。
- backend/tests/test_tcg_product_detail_pg.py: test_update_rejects_invalid_payload_before_writing（:332、parametrize は japanese_title 空白・release_date 不正 2 種・work_id 不正・検索語に空文字・除外語 1001 個・code・is_active）、test_empty_mark_and_english_title_are_saved_as_null_and_values_kept（:204）、test_list_finds_english_and_mark_with_both_counts（:77）。
- backend/tests/test_tcg_product_import.py: 23 テスト（f_import_tests.txt）。必須列を確かめる名前のものは test_commit_rejects_invalid_file（:181）のみ。MISSING_ や JAPANESE_TITLE_REQUIRED を参照するテストは backend/tests に無い（git grep で該当なし）。
- backend/tests に product_format を含むテストは無い（git grep -n -i product_format -- backend/tests が 0 件）。
- frontend: frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx（10 ケース、f_frontend_tests.txt）。必須項目の検査を名前に持つケースは無い（衝突警告、除外語追加、409 が中心）。TcgProductImportPanel.test.tsx もある。

## 4-g 解析が name_en・mark・product_format_id を読む箇所
- mark: backend/app/services/gemini_raw_copy_v102_product_first.py:315（p.id, p.product_code, p.mark, p.work_id を読む）、:161 と :209（mark を照合語に使う）。backend/app/services/tcg_analyzer_svc.py:1367（is_active が真で mark が NULL でも空でもない商品の mark と id を読む）。
- release_date: gemini_raw_copy_v102_product_first.py:127（release_date が NULL でない商品のみ読む）。
- 検索語・除外語: tcg_analyzer_svc.py:168-173 付近（product_search_keywords と product_exclude_keywords を配列で読む）。
- name_en（products の列）を読む解析側の箇所: 絞り込み grep では見つからなかった（g_analysis_grep.txt の name_en は type_master、見積・請求明細、別マスタの列）。tcg_product_import.py:106 は管理画面の一覧検索で p.name_en を ILIKE で見る。
- product_format_id: 解析コード（tcg_analyzer_svc.py、gemini_raw_copy_v102_product_first.py、tcg_analysis_review_svc.py）に該当なし（g_analysis_targeted.txt は 0 行）。読むのは super_admin_product_formats.py:137 の削除ガードのみ。
- 未確認: 上記以外のモジュールでの product_format_id の読み取り。d_format_grep.txt（backend/app、frontend/src、migrations、scripts の全走査）でヒットしたのは main.py、super_admin_product_formats.py、super_admin_product_lines.py、schemas/product_format.py、migrations、scripts のみ。
