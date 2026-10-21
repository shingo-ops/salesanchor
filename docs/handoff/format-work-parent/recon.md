# recon: 細分類を中分類（作品）の子にできるか

- 作成: 2026-10-21 / 担当: Sonnet（Opus 設計の前段・事実集め）
- 範囲: 製品コード・DB・設定は変更していない。本番は ADR-1024 の reader 鍵（ai_ro ビュー＋ pg_catalog）で読むだけ。
- 生出力: 同じフォルダの `raw/`（ファイル名は各節に併記）。SQL 本文は各ファイル1行目。
- 投稿本文・仕入元名・認証情報は載せていない。
- file:line は repo ルートからのフルパス（短縮なし）。

## 0. PO の願い（原文 2026-10-21）と前提

「細分類は中分類と紐づけて中分類を親に親子関係にできる？」

前提: 配線と DB の SSOT を守りデータを分散させない／フロントはデザイントークンと金型を守り、金型登録のないハードコードをしない。

## 1. 先に結論（事実だけ）

【事実】
1. 作品（products.work_id の先）とゲーム（product_format_game_links.type_master_id の先）は **同じ一覧**。どちらも `public.type_master`（18 行）。1 対 1 で、ずれ 0。根拠: §2-1 の FK 定義（raw/q07_constraints.txt）。
2. 細分類（product_formats, 28 行）と作品の「つながり」はすでに `product_format_game_links`（78 行・多対多）にある。画面・API・CSV・往復 CSV の入口は、この表で作品ごとに選択肢を絞り、保存時にも検査している（§4）。
3. 本番の products 1453 行はすべて共用（tenant_id が空）。そのうち細分類が入っている 1283 行で、「細分類が商品の作品につながっていない」行は **0 件**（raw/q12_mismatch_count.txt, raw/q15_unlinked_list.txt）。テナント商品（tenant_id が入っている行）は **0 行**（raw/q13_tenant.txt）。
4. 細分類 28 行のうち **15 行は複数の作品につながっている**（raw/q21_link_stats.txt）。1 作品だけは 13 行。つまり今は「細分類の親は 1 人」ではなく「多対多」。
5. `product_formats.type_master_id`（旧・直接リンク）は 28 行すべてに値が入っているが、products の作品と食い違う商品が 1283 行中 **706 行**（raw/q18_pf_tm_vs_work.txt）。画面の絞り込みには使われていない（§4）。2 つ目のつながりの置き場になっており、データが二重になっている（§5）。

【未確認】
- 上の 2 と 4 を踏まえた「親子にする」設計の良し悪しは、この recon の範囲外（Opus の設計）。
- 在庫一覧 GAS の正本リポジトリ（shingo-ops/tcg-client-viewer）の最新。ローカル控え `~/tcg-viewer-1tb-head/` のみ読んだ（§4-6）。

## 2. DB の形（本番と migrations）

本番は `ssh salesanchor-reader`（ADR-1024）。列は ai_ro ビュー（raw/q01_columns.txt）、制約は `pg_constraint`（raw/q07_constraints.txt）で読んだ。ビューは NOT NULL・FK を持たないので、制約は pg_constraint の値を正とする。

### 2-1. 表ごとの形

| 表 | 件数（本番） | 列（本番） | 制約・FK（本番 pg_constraint） | migration |
|---|---|---|---|---|
| public.type_master（中分類＝作品。旧 tcg_type_master） | 18 | id, code, name_ja, name_en, sort_order, is_active, created_at, updated_at, kind_id, match_by_code, code_only_match | PK(id) `tcg_type_master_pkey`、UNIQUE(code)、`type_master_kind_id_fkey` kind_id→product_kinds(id) ON DELETE SET NULL | migrations/085_create_tcg_type_master.sql（作成）、migrations/20260921_070000_rename_tcg_type_master_to_type_master.sql:1-20（改名）。互換ビュー public.tcg_type_master が今も本番にある（raw/q19_compat_view.txt: relkind=v） |
| public.product_kinds（種類＝大分類） | 3（TCG / FIGURE / GOODS） | id, code, name, name_en, display_order, is_active, created_at, updated_at | PK(id)、UNIQUE(code) | ADR-156 Phase 1（migrations/20260921_010000 系） |
| public.product_formats（細分類） | 28 | id, code, name, name_en, line_id, display_order, is_active, created_at, updated_at, kind_id, type_master_id | PK(id)、UNIQUE(code)、kind_id→product_kinds(id) SET NULL、line_id→product_lines(id) SET NULL、**type_master_id→type_master(id) SET NULL** | migrations/20260920_130000_create_product_classification.sql:54-70（作成）、migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql:15（kind_id）、migrations/20260923_010000_product_formats_add_type_master_id.sql:16（type_master_id） |
| public.product_format_game_links（細分類×ゲーム） | 78 | format_id, type_master_id, alias | PK(format_id, type_master_id)、format_id→product_formats(id) ON DELETE CASCADE、**type_master_id→type_master(id) ON DELETE CASCADE** | migrations/20260922_030000_product_format_game_links.sql:12-20 |
| public.products（商品） | 1453（active 1427 / inactive 26。raw/q17_active.txt） | work_id（integer, **NOT NULL**）、product_format_id（integer, NULL可）、product_category_id、tenant_id ほか | `fk_products_work_id` work_id→**type_master(id)**、`products_product_format_id_fkey` product_format_id→product_formats(id) ON DELETE SET NULL | work_id: migrations/20260919_030000_master_ssot_fk_work_id.sql:15-35（FK）、migrations/20260916_130000_work_id_not_null.sql（NOT NULL）。product_format_id: migrations/20260920_130000_create_product_classification.sql:98-102 |
| 「種類（kind）」の表 | product_kinds 3 行（上記） | | type_master.kind_id と product_formats.kind_id が両方これを指す | |

DB 側に「細分類が商品の作品につながっていること」を保証する制約は **無い**（products の FK は product_formats だけを指し、links を見ない）。検査はアプリのコードだけ（§4）。【事実】根拠: raw/q07_constraints.txt の products 行は上記 2 本のみ。

### 2-2. 作品（work_id の先）とゲーム（links の先）は同じ一覧か

【事実】同じ一覧。`fk_products_work_id` は `type_master(id)`、`product_format_game_links_type_master_id_fkey` も `type_master(id)`（raw/q07_constraints.txt）。別表は無い。

対応表（作品 id ＝ ゲーム id ＝ type_master.id。2 つの列で同じ番号を使う）。raw/q10_work_map.txt より。

| type_master.id | code | 名前 | 共用商品数（work_id で数えた） | 選べる細分類数（links で数えた） |
|---|---|---|---|---|
| 1 | pokemon_booster_box | ポケモン | 242 | 16 |
| 2 | one_piece | ワンピース | 206 | 13 |
| 3 | dragon_ball | ドラゴンボール | 80 | 5 |
| 4 | union_arena | ユニオンアリーナ | 117 | 3 |
| 5 | yugioh | 遊戯王 | 166 | 9 |
| 6 | other | その他 | 22 | 1 |
| 19 | gundam | ガンダム | 22 | 4 |
| 20 | weiss_schwarz | ヴァイスシュヴァルツ | 465 | 7 |
| 21 | digimon | デジモン | 64 | 6 |
| 22 | hololive | ホロライブ | 29 | 3 |
| 23 | lorcana | ディズニー ロルカナ | 23 | 5 |
| 24 | xross_stars | クロススタァ | 3 | 2 |
| 8981 | duel_masters | デュエル・マスターズ | 4 | 1 |
| 8982 | detective_conan | 名探偵コナン | 4 | 1 |
| 9043 | wuthering_waves | 鳴潮：対決 | 1 | **0** |
| 9044 | magic_the_gathering | マジック：ザ・ギャザリング | 3 | **0** |
| 9045 | harry_potter | ハリー・ポッター | 1 | 1 |
| 9046 | palworld | パルワールド | 1 | 1 |

- 1 対 1 で対応する。ずれ（片方にしか無い id）は 0。links の type_master_id はすべて type_master に存在し有効（raw/q21_link_stats.txt: links_to_inactive_or_missing_game=0）。
- 作品 id の 9043・9044 は、選べる細分類が 0 件。この 2 作品の商品（1 件・3 件）は細分類を入れられない状態（画面の選択肢が空になる。§4-1）。
- 商品の `work_id` が空の行は本番に無い（NOT NULL）。
- type_master の中に「作品」でない行 `6 other（その他）` がある。22 商品がこれ。

### 2-3. product_formats.type_master_id は何を表し、値の分布はどうか

【事実】
- 型は `integer`、FK は type_master(id)。28 行すべてに値あり（raw/q05_formats.txt）。
- 値の分布（raw/q05_formats.txt）: id1(ポケモン)＝12 行、id2(ワンピース)＝6、id20(ヴァイス)＝3、id21(デジモン)＝3、id5(遊戯王)＝2、id4(ユニオンアリーナ)＝1、id23(ロルカナ)＝1。（raw/q10_work_map.txt の最終列）
- 意味: コードに書かれた説明は無い。migration は「細分類(product_formats)に中分類(type_master)への直接リンクを追加」とだけ書く（migrations/20260923_010000_product_formats_add_type_master_id.sql:1）。API は任意の整数として受け書くだけ（backend/app/schemas/product_format.py:19,33、backend/app/routers/super_admin_product_formats.py:30-31,93-94）。
- ADR-1026 はこれを「別の情報なので変えない」とした（docs/adr/ADR-1026-drop-products-type-master-id.md「What」3）。
- links との関係（raw/q11_format_map.txt）: 28 行中 27 行は、この値が links の中にも含まれる。**1 行だけ含まれない**（id8 CONCEPT_PACK: type_master_id=1 だが links は 5 のみ）。
- 商品の作品との関係（raw/q18_pf_tm_vs_work.txt）: 細分類が入った商品 1283 行のうち **706 行**で、細分類の type_master_id が商品の work_id と違う。つまりこの列は「商品の作品」を表さない。コード上で絞り込みや検査に使う所は無い（backend/app と frontend/src で type_master_id を読む所は、細分類マスタ画面の表示・編集だけ。前記 grep の結果）。
- 【未確認】この列を入れた人・理由（記録が見つからない）。

## 3. 今のつながりの実態（本番）

### 3-1. 細分類ごとの、つながっているゲームの数（raw/q11_format_map.txt）

| 細分類 id | code | linked_games | 共用商品数 |
|---|---|---|---|
| 1 | BOOSTER | 16 | 989 |
| 2 | EXTRA_BOOSTER | 4 | 11 |
| 3 | STARTER_DECK | 10 | 5 |
| 4 | ENHANCED_BOOSTER | 1 | 0 |
| 5 | HIGH_CLASS | 1 | 0 |
| 6 | PREMIUM_BOOSTER | 2 | 2 |
| 7 | THEME_BOOSTER | 1 | 6 |
| 8 | CONCEPT_PACK | 1 | 0 |
| 9 | SPECIAL_PACK | 2 | 1 |
| 10 | STRUCTURE_DECK | 1 | 23 |
| 11 | ADVANCE_DECK | 1 | 3 |
| 12 | START_DECK_EX | 7 | 141 |
| 13 | MEMORIAL_PACK | 2 | 1 |
| 14 | ANNIVERSARY_SET | 6 | 27 |
| 15 | GIFT_SET | 2 | 1 |
| 16 | ILLUMINEERS_TROVE | 1 | 0 |
| 17 | SPECIAL_BOX | 1 | 6 |
| 18 | DECK_BUILD_BOX | 2 | 18 |
| 19 | PREMIUM_TRAINER_BOX | 1 | 2 |
| 20 | COLLECTOR_BOX | 2 | 2 |
| 21 | HIGH_CLASS_DECK | 1 | 3 |
| 22 | BOOSTER_BOX | 1 | 0 |
| 23 | SPECIAL_SET | 4 | 17 |
| 24 | ILLUSTRATION_BOX | 2 | 11 |
| 25 | STORAGE_BOX | 1 | 1 |
| 28 | PROMO | 2 | 4 |
| 30 | GRADED | 1 | 5 |
| 32 | BULK | 2 | 4 |

- 0 件のつながりの細分類は無い（formats_zero_links=0）。複数ゲームにつながる細分類 15、1 ゲームだけ 13（raw/q21_link_stats.txt）。
- links の `alias` は 78 行中 9 行だけ値あり（raw/q23_alias.txt）。backend/app と frontend/src に、細分類×ゲームの alias を読む・書くコードは見つからなかった（`git grep -w alias` で細分類・ゲームに関わる行 0 件）。
- products.line_id にあたる `product_formats.line_id`（小分類への FK）は 28 行すべて空（raw/q20_lines.txt: formats_with_line_id=0）。product_lines は 10 行ある。ADR-156 の木（product_kinds > type_master > product_lines > products）に、細分類は含まれていない（docs/adr/ADR-156-product-classification-tree-and-master-separation.md「決定」の図）。

### 3-2. 作品ごとに選べる細分類の数

§2-2 の表の最終列（links を作品ごとに数えた値）。作品 9043・9044 は 0 件。

### 3-3. 共用商品で、細分類が入っていて、その細分類が商品の作品につながっていない商品

【事実】0 件。一覧も空（raw/q15_unlinked_list.txt は SQL と列名の行のみ）。
補足の数字（raw/q12_mismatch_count.txt、raw/q16_noformat_by_work.txt）:
- 共用商品 1453 行。細分類あり 1283、細分類なし 170（active のうち 169 が細分類なし）。
- 細分類なしの内訳（work_id 別）: 1(ポケモン)=27、2(ワンピース)=57、3(ドラゴンボール)=37、4=3、5=4、6(その他)=22、19=1、20=5、21=1、24=3、8981=3、8982=3、9043=1、9044=3。
- 使われている（作品, 細分類）の組は 59 通り（raw/q22_pairs.txt）。

### 3-4. テナント商品

【事実】0 行。`public.products` の tenant_id は 1453 行すべて空（raw/q13_tenant.txt）。tenant_001.products と tenant_004.products は別の旧表で、行数 0・work_id/product_format_id 列なし（raw/q13_tenant.txt、raw/q14_t001cols.txt、raw/q09_cols_everywhere.txt）。つまりテナント商品の「つながっていない件数」は 0 件で、そもそも対象行が無い。
なお、`work_id`・`product_format_id` の両方を持つ表は public.products だけ（raw/q09_cols_everywhere.txt。他は analysis_results 系と tenant_004 のバックアップ表に work_id があるのみ）。

## 4. 細分類を選ぶ・書く入口（すべて）

絞り込みの鍵はすべて「作品 id（work_id = type_master.id）」と「links の game_ids」。type_master_id（product_formats の列）では絞っていない。

### 4-0. 共通の部品（バックエンド）
- 選択肢を作る: backend/app/services/tcg_product_master_svc.py:130-145 `fetch_product_format_options`。各細分類に links の type_master_id を配列（game_ids）で付けて返す。
- つながり検査: backend/app/services/tcg_product_master_svc.py:105-112 `format_matches_game`（links に (format_id, type_master_id) があるか）。同:115-127 `_validate_product_format`（work_id を渡されたときだけ照合し、無いと `PRODUCT_FORMAT_GAME_MISMATCH`）。
- 作品の選択肢の出どころ: backend/app/services/tcg_product_master_svc.py:239-245（`public.type_master`）、backend/app/services/tcg_product_detail_svc.py:112-119（同）。

### 4-1. 画面（フロントエンド）

| 入口 | 細分類の欄 | 部品 | 絞り込みの鍵 | file:line |
|---|---|---|---|---|
| 商品詳細ドロワー（TCG 商品マスタ。新規・編集） | 細分類 | 金型 `Select`（components/Select） | `formatOptionsFor(options, draft.work_id)` ＝ game_ids に work_id を含む細分類だけ。作品未選択なら欄ごと無効 | frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:6（import）,255-260,343-346。絞り込み関数: frontend/src/features/tcg-product-import/productDetailModel.ts:87-93。作品を変えたとき新しい作品に無い細分類は空に戻す: TcgProductDetailDrawer.tsx:117、productDetailModel.ts:91-93。親は frontend/src/pages/super-admin/components/ProductMasterPanel.tsx:131-132 |
| 解析レビューの登録（修正ウィザード内） | 細分類 | 金型 `AsyncCombobox` | `formatOptionsFor(lookups.product_format_id, selected.work_id.value)`（work_id） | frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx:9,319,364-368,379-399。呼び出し元: frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx:14,123 |
| 仕入元詳細の商品マスタ登録ドロワー | 細分類（作品も） | **自作の `SearchSelect`**（`TextFieldControl` ＋ ブラウザ標準の `<datalist>`/`<option>`）。細分類・作品・種類・メーカー・区分の 5 欄すべて | `formatOptionsFor(formats, values.work_id)`（work_id）。作品変更時 `formatAfterWorkChange` | frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:54-91（SearchSelect の定義）,118,125,215-219。呼び出し元: frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:6,135 |
| 細分類マスタ（つなぎを編集する所） | 使えるゲーム（行ごとの links） | 金型 `MultiSelect`（`product-format-games`） | 選べるゲーム＝`GET /super-admin/tcg/types` の有効な type_master 全部 | frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:18,113-114,216-218,343-352。保存呼び出し: 同:163-183 |
| 同上（旧・直接リンク） | 「type_master_id」という名前の単独欄 | 金型 `SelectControl` | 全ゲーム（絞り込みなし） | frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:20,328-341,222 |

補足:
- 3 つの登録・編集画面はどれも、作品を先に選ばないと細分類が選べない（ドロワー: TcgProductDetailDrawer.tsx:346 `disabled={saving || !draft.work_id}`、レビュー登録: ReviewRegisterProductForm.tsx:387、`formatOptionsFor` は workId が空だと空配列 productDetailModel.ts:89）。
- 作品 9043・9044 は links が 0 件なので、これらの画面では選択肢が空になる（§2-2。コードの結果としての推論ではなく、`formatOptionsFor` が game_ids.includes を見る実装と links の値からそうなる）。
- 在庫の商品画面（インベントリ）に細分類の欄は無い。`git grep product_format frontend/src` の結果は上の画面だけ（raw/g03_frontend.txt）。

### 4-2. API・サービス（保存時に作品とのつながりを検査しているか）

| 入口 | 検査 | file:line |
|---|---|---|
| `POST /tcg/products/create`（商品詳細ドロワーの新規） | `create_product` → `_validate_product_format(db, product_format_id, work_id)`（つながっていなければ 422 PRODUCT_FORMAT_GAME_MISMATCH）。細分類が空なら ADR-1020 の必須検査で止まる | backend/app/routers/tcg_product_import.py:413-449、backend/app/services/tcg_product_master_svc.py:514-528 |
| `POST /tcg/products`（解析レビューの登録。ReviewRegisterProductForm / ProductMasterDrawer が使う） | 同じ `create_product`（同上の検査） | backend/app/routers/tcg_product_master.py:231-266、フロント側呼び出し: frontend/src/features/tcg-analysis-review/reviewActions.ts:109-125 |
| `PUT /tcg/products/detail/{id}`（商品詳細ドロワーの保存） | 細分類か作品が**変わったときだけ**照合（`PRODUCT_DETAIL_FORMAT_GAME_MISMATCH`）。変わらない古い組は止めない（テスト test_detail_update_keeps_unchanged_old_pair）。細分類の存在確認は `_validate_product_format`（work_id なし） | backend/app/routers/tcg_product_import.py:321（ルート）、backend/app/services/tcg_product_detail_svc.py:269-284 |
| 商品 CSV 取り込み（検証段階） | `product_format_code` を id に直し、`format_matches_game` で照合。不一致は blocking `PRODUCT_FORMAT_GAME_MISMATCH` | backend/app/services/tcg_product_import_svc.py:265-269（コード→id）,318-320,370-373,474-480 |
| 往復 CSV（書き戻し） | 細分類か作品が変わる行は `format_matches_game` で照合し `PRODUCT_FORMAT_GAME_MISMATCH` | backend/app/services/tcg_product_roundtrip_svc.py:288-294,330-336,431 |
| 在庫の商品 API `POST /products` | 作品・細分類を**受け取らない**。共用表へは常に必須検査で 422（`product_format_id: None` を固定で渡す） | backend/app/routers/products.py:366-384 |
| 細分類マスタ API | links の置き換え `PUT /super-admin/product-formats/{id}/games`。外すつながりを使っている商品があれば 409 `PRODUCT_FORMAT_GAME_IN_USE`。作成・更新は旧 type_master_id も受ける | backend/app/routers/super_admin_product_formats.py:30-31,93-94,147-203。スキーマ: backend/app/schemas/product_format.py:19,33 |
| 選択肢 API（フロントが使う game_ids を返す） | `fetch_product_format_options` を詳細 GET・`/tcg/products/lookups`・登録フォームの3か所で呼ぶ | backend/app/services/tcg_product_detail_svc.py:138、backend/app/routers/tcg_product_import.py:351-389、backend/app/services/tcg_product_master_svc.py:273 |

- DB 直書き（SQL を直接流す）は上のどの検査も通らない。本番に検査を強制する DB 制約・トリガーは無い（§2-1）。
- products に product_format_id を書くコードは、`git grep "INSERT INTO public.products|UPDATE public.products"` で上の create_product（tcg_product_master_svc.py:566）、詳細保存（tcg_product_detail_svc.py:260,275）、往復 CSV（tcg_product_roundtrip_svc.py:474）の 3 か所に絞られる（raw/g07_product_writers.txt）。ほかに scripts/seed_products_from_master.py:193 の投入台本があるが、細分類の列は書いていない（【未確認】ファイル全体は精読していない。`product_format` を含む行が grep に出ないことだけ確認）。
- 中分類（作品）の変更: 詳細保存 backend/app/services/tcg_product_detail_svc.py:170-187（type_master で存在・有効を確認）。

### 4-3. 在庫一覧 GAS・閲覧ページ

- 配信処理（アプリ → シート）: backend/app/services/tcg_distribution_svc.py:364-365 が `LEFT JOIN public.type_master ser ON ser.id = p.work_id` で作品名を Series 列に書く。**細分類は配信に出していない**（同ファイルに product_format の語が無い）。
- GAS 閲覧ページ（ローカル控え `~/tcg-viewer-1tb-head/コード.js:22` ヘッダーに 'Series'、`index.html:981` で列番号 `series: 11`、`index.html:1197-1211` が Series タブ）。細分類・フォーマットの列は読んでいない（raw/g04_gas_viewer.txt）。
- 【未確認】本番 GAS（1hc）・正本リポジトリ shingo-ops/tcg-client-viewer の最新ソース。メモリ（reference_tcg_client_viewer）に「ローカル src が本番より古かった」記録があるため、この結論はテスト版の控えの範囲。

## 5. データが二重になっている所

| 情報 | 場所 | 正本か | 読む側 |
|---|---|---|---|
| 商品の作品（中分類） | `products.work_id` → type_master | 正本（docs/specs/master-ssot-migration/design.md:13、ADR-1026「Why」） | 全画面・API・配信（tcg_distribution_svc.py:364） |
| 商品の作品（旧・重複） | `products.type_master_id` | ADR-1026 で削除決定（起案 2026-10-17）。【未確認】本番の列が今ある・ないか（ai_ro のビュー列には出していない。raw/q08_products_cols.txt の products 列の抜粋に type_master_id が無い） | 読むコード 0 |
| 商品の作品（旧・重複） | `products.tcg_type` | ADR-1030 で削除（migrations/20261018_110000_drop_products_tcg_type.sql） | - |
| 細分類×ゲームのつながり | `product_format_game_links`（多対多、78 行） | 正（ADR-1020 What 5。docs/adr/ADR-1020-shared-product-required-fields.md） | 画面の絞り込み・全保存入口の検査 |
| 細分類×ゲームのつながり（二重） | `product_formats.type_master_id`（1 対 1、28 行すべて値あり） | **どこからも読まれない**。画面から編集できる（ProductFormatsMasterPanel.tsx:328-341）。links と食い違い 1 行、商品の作品とは 706/1283 行で不一致 | 細分類マスタの一覧表示だけ（ProductFormatsMasterPanel.tsx:222） |
| 細分類×ゲームの別名 | `product_format_game_links.alias`（9 行に値あり） | 読み書きするコード見つからず | なし |
| 細分類の小分類 | `product_formats.line_id`（全部空） | 空のまま | なし |
| 作品の一覧の別名 | 互換ビュー `public.tcg_type_master`（本番に残る） | 廃止予定 2026-12-21 以降（ADR-156） | backend/app で `tcg_type_master` を含む箇所は `git grep -c` で 0 件（出力なし） |
| 作品の名前 → 閲覧ページの Series | type_master.name_ja をシートへ書く | シート側は控え | GAS |

作品と細分類の関係の正本は **1 か所（links）**。もう 1 つ（product_formats.type_master_id）が二重で、これを親にする設計は、2 つの「親」の置き場を持つことになる点が論点になる（Opus の設計へ）。

## 6. 画面の部品と金型（docs/CC_UI_GOVERNANCE.md）

- 金型の決まり: 生 `<select>`・生 `<input type=text>` 等は禁止。`ui-allow: <理由> (#<番号>)` コメントで例外（docs/CC_UI_GOVERNANCE.md:9-15,23,35-46）。CI ゲートは scripts/check-ui-governance.js（生 `<select>` は :147-157 の正規表現で検出）。
- components/ にある関連の金型: Select.tsx、AsyncCombobox.tsx（＋ stories/test）、MultiSelect.tsx、CountryCombobox.tsx、ChannelTypeCombobox.tsx（frontend/src/components/）。

| 欄 | 画面 | 部品 | 金型か |
|---|---|---|---|
| 細分類 | 商品詳細ドロワー | `Select`（TcgProductDetailDrawer.tsx:343） | 金型 |
| 中分類（作品） | 商品詳細ドロワー | `Select`（TcgProductDetailDrawer.tsx:333-342。classificationFields の work_id） | 金型 |
| 細分類 | 解析レビュー登録 | `AsyncCombobox`（ReviewRegisterProductForm.tsx:383） | 金型 |
| 中分類（作品） | 解析レビュー登録 | `AsyncCombobox`（ReviewRegisterProductForm.tsx:354。SELECT_FIELDS） | 金型 |
| 細分類・中分類ほか 5 欄 | 仕入元詳細の登録ドロワー | **自作 `SearchSelect`**（`TextFieldControl` ＋ `<datalist>`。ProductMasterDrawer.tsx:54-91） | 金型の一覧（Select / AsyncCombobox / MultiSelect …）に無い、ファイル内の自作部品。`ui-allow` コメントは無い（`git grep ui-allow` の結果 0 件）。生 `<select>`・生 `<input>` ではないのでゲートの検出対象（scripts/check-ui-governance.js:9）には当たっていない【事実：ゲートの対象は生 select・生 input 等】 |
| 使えるゲーム | 細分類マスタ | `MultiSelect`（ProductFormatsMasterPanel.tsx:343） | 金型 |
| type_master_id | 細分類マスタ | `SelectControl`（ProductFormatsMasterPanel.tsx:332） | 金型 |

- ProductFormatsMasterPanel.tsx:290,315,329 に `style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3) var(--space-4)" }}` など、トークン（`var(--…)`）経由のインラインスタイルがある。【未確認】それらがガバナンスの禁止（色直値・生 px）に当たらないことの CI 実行結果は未取得（本 recon では CI を回していない）。

## 7. 関係するテストと CI のチェック

### バックエンド（pytest）
- backend/tests/test_product_format_game_links.py:10,15,20（入力の形：不明な項目の拒否・長さ・game_ids の既定）
- backend/tests/test_product_format_game_links_pg.py:61（つながる細分類は通り、つながらない細分類は拒否）,75（選択肢に game_ids が入る・選択中の無効な細分類を含める）,92（詳細 GET）,107（revision）,122（詳細保存はつながらない細分類への変更を拒否）,142（変えない古い組は止めない）,160（links の置き換え）,176（使用中の組は外せない）
- backend/tests/test_tcg_product_import.py、test_tcg_product_master.py、test_tcg_product_roundtrip.py、test_tcg_product_import_atomicity_pg.py、test_tcg_product_list_pg.py、test_tcg_work_matching_integration.py、test_tcg_completion_safety.py、test_tcg_product_code_collision_wiring.py（`git grep -c` で format_matches_game / GAME_MISMATCH / game_links を含むファイル。raw/g05_tests.txt）
- backend/tests/test_product_required_fields.py、test_products_required_fields_pg.py、test_product_blank_confirmations_pg.py（ADR-1020 の9項目必須）
- backend/tests/test_tcg_schema_qualification.py、backend/tests/rls_bootstrap.py、backend/tests/fixtures/public_products_test.sql（テスト用の表）

### フロントエンド（vitest）
- frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.test.tsx（links の編集）
- frontend/src/features/tcg-product-import/TcgProductDetailDrawer.test.tsx、productDetailModel.test.ts
- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx、ReviewRegisterProductForm.test.tsx、reviewActions.test.ts
- frontend/src/components/Select.test.tsx、AsyncCombobox.test.tsx、MultiSelect.test.tsx（金型）

### CI・ゲート（.github/workflows/ と scripts/）
- migration-guard.yml（`scripts/migration-guard/protected-tables.txt:36` に product_formats。migration での値書き込みを禁止。scripts/tests/test_migration_value_writes.py）
- adr-index-check.yml（ADR 追加時に docs/adr/README.md 再生成）
- frontend-check.yml、design-token-guard.yml、design-token-audit.yml、process-artifacts-gate.yml
- scripts/check-ui-governance.js（金型ゲート）、scripts/tests/test-ui-governance.js
- frontend/scripts/check-i18n-missing-keys.js（ja/en の同一キー。ADR-027）
- backend/app/tasks/master_required_fields_monitor.py:24,41（products の9項目の空欄件数を数える定期作業。細分類の空欄 `product_format_id IS NULL` も集計）
- 【未確認】作品と細分類の不一致を数える定期点検は見つからない（上記 monitor は空欄の数だけ。`git grep` の範囲）。

## 8. 守るべき既存の決め（Opus が設計に引くもの）

- docs/adr/ADR-1020-shared-product-required-fields.md「What」5: 細分類の選択肢は product_format_game_links で選んだゲームに紐づくものだけ。紐づけは細分類マスタ画面で編集。
- docs/adr/ADR-1026-drop-products-type-master-id.md「What」3: `product_formats.type_master_id` と `product_format_game_links.type_master_id` は別の情報なので変えない（Proposed。起案時点の判断）。
- docs/adr/ADR-156-product-classification-tree-and-master-separation.md: 木は 種類 > 中分類 > 小分類 > 商品。細分類は木の外。
- docs/specs/product-master/registration-rules.md:§2「細分類」行: 選んだゲームで使える細分類から選ぶ。
- docs/adr/ADR-1007: migration で値を書かない（protected-tables）。値の入れ替えは別手順。
- docs/adr/FEATURE-INDEX.md:19: 「細分類」の項目は ADR-1020 / ADR-155 / ADR-156。
- 既存 ADR の見落とし防止検索（git grep -i -l docs/adr/）の結果: 細分類→ADR-1020/1026/1028/1035/FEATURE-INDEX、product_format→ADR-1020/1026、中分類→ADR-1020/1026/1030/156、work_id→ADR-1001/1020/1026/1030/154、type_master→ADR-083/090/1007/1026/1030/156、分類の木→ADR-1026。

## 9. 親子にするときに効く事実（設計は Opus。ここは事実のみ）

1. 今の細分類は多対多。複数作品に付く細分類 15 個（BOOSTER は 16 作品）。1 作品 1 親にするなら、現状のままでは 15 個を作品ごとに分ける必要がある（使われている（作品, 細分類）の組は 59 通り。raw/q22_pairs.txt）。
2. 作品ごとに別の細分類 id になると、ADR-1020 の 9 項目・往復 CSV の `product_format_code`（UNIQUE な code で細分類を指定。raw/q07 の product_formats_code_key）・解析の既存データ（products の product_format_id）が影響を受ける。影響範囲の走査対象は §4 の表と §5。
3. links の `alias`（9 行）は作品ごとの呼び名。親子にする案では置き場が必要か要判断。
4. `product_formats.type_master_id` は既に「1 つの親」の形をしているが、値は商品の作品と 706/1283 行で合わず、1 行は links にも無い（§2-3）。このまま親にはできない（値の正しさの保証が無い）。
5. 作品 9043・9044 は選べる細分類が 0 件（商品 1 件・3 件）。
6. DB 制約が無いので、親子の保証を DB で持たせる案（複合 FK 等）は新しい設計になる。列追加の場合、products は列番号 1600 の上限に到達済み（docs/adr/ADR-1026-drop-products-type-master-id.md「守ること・危ないこと」）なので products への列追加は不可。product_formats / links は別表で影響なし。

## 付録: 実行記録
- preflight: raw/preflight.txt（PREFLIGHT OK、identity=shingo-cc）
- worktree: ~/worktrees/salesanchor/release-format-work-parent（branch release/format-work-parent）
- 読んだ文書: AGENTS.md は読んでいない（行数のみ確認）【未確認】、docs/STANDARD-WORKFLOW.md（§1・§1.5 読了）、docs/ai-agents/executor-checklist.md（行数のみ確認）【未確認】、docs/specs/README.md（読了せず）【未確認】、docs/specs/product-master/registration-rules.md（全文）、ADR-156・1020（What/Why）・1026・1024（全文）、docs/specs/master-ssot-migration/design.md（1-80 行）
