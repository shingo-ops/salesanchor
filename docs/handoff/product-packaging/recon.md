# recon: 商品の荷姿（入数・重さ）の現在地

- 基準: origin/main 869b29869。読み取りのみ（2026-10-17、Sonnet 調査・Opus 確認）
- 本番の値は AI 用の読み取り専用の道で読んだ（ADR-1024。`ai_ro.public__<表>`）
- 生出力の置き場所（リポジトリ外）: /tmp/CC報告ファイル/product-packaging-design/recon/（SUMMARY.md と a1〜b11.txt、D1〜D4）、/tmp/CC報告ファイル/product-qty-weight/recon/
- 印: 【事実】は出典つき、【未確認】は確かめていないもの。推測は書かない

## 0. 既存 ADR の検索
- `git grep -n -i -E "quantity_unit|packs_per_box|boxes_per_case|box_weight|case_weight|荷姿|入数" docs/adr/` の結果、入数・重さの列に触れる ADR は ADR-093 だけ（docs/adr/ADR-093-inventory-table-product-master-redesign.md:37-38。7列を API と画面に出す決定）。
- docs/adr/FEATURE-INDEX.md に quantity_unit・入数・荷姿の行は無い。
- 関係する決まり: ADR-155（docs/adr/ADR-155-product-master-ssot-csv-app.md:25-26 migration は構造だけ・値の INSERT/UPDATE/DELETE 禁止）、ADR-1007（docs/adr/ADR-1007-migration-structure-only-run-once.md:36 値は画面・CSV・1回だけのデータ変更〈PO 合意、DRY-RUN→COMMIT、docs/handoff/<topic>/ に SQL と記録〉）、ADR-090（docs/adr/ADR-090-products-central-unification.md:18 共用 products は public・tenant_id NULL）、ADR-1026（列を消した前例）。
- 単位の名簿を作った設計: docs/handoff/product-classification-masters/design.md:8,15-17,26-27（quantity_units・weight_classes 新設、「既存商品への紐づけは別 PR」のまま止まっている）。

## 1. 入数・重さの列（products）
- 【事実】列の定義: migrations/082_extend_products_box_attributes.sql:13-19 の先頭コメントの列一覧と同ファイルの ADD COLUMN 文（boxes_per_case INTEGER、packs_per_box INTEGER、box_weight_kg NUMERIC(8,3)、case_weight_kg NUMERIC(8,3)、moq INTEGER＝最小発注数）。volume_weight NUMERIC(8,3) は migrations/20260602_170000_add_products_master_label_columns.sql:32。
- 【事実】本番の件数（全 1424 行、b4.txt）: packs_per_box 134／boxes_per_case 109／box_weight_kg 162／case_weight_kg 134／moq 11／weight 0／volume_weight 0／quantity_unit_id 0／weight_class_id 0。
- 【事実】4列の組み合わせ（b5.txt）: 全て空 1248／4列とも有り 87／ppb+bwk+cwk 31／bwk だけ 26／ppb+bpc 12／bpc+bwk+cwk 10／bwk+cwk 6／ppb だけ 2／ppb+bwk 2。
  - ここから、ケースの値（bpc か cwk）が有る行は 146、ボックスの値（ppb か bwk）が有る行は 176。
- 【事実】moq の 11 行は、全部 box_weight_kg だけが有る行（b6.txt）。moq は保存と表示だけに使い、計算には使っていない（C1_moq.txt）。
- 【事実】products は列番号（attnum）が上限 1600 に達していて、列を足せない（ADR-1026 の記録）。
- 【事実】products.id は INTEGER（SERIAL）。本番 1424 行は全て tenant_id NULL＝共用（b3.txt、b7.txt）。

## 2. 単位の名簿
- 【事実】product_lines（migrations/20260920_130000_create_product_classification.sql:18-27、コメント「商品系統マスタ（小分類）」:46）。本番 10 行（a1.txt）: 1 CASE／2 BOX／3 PACK／4 SINGLE／5 PROMO／6 BULK／7 GRADED／8 DECK（無効）／9 SUPPLY／10 SET（無効）。
  - products.product_line_id の分布（b1.txt）: BOX 1247／SINGLE 17／PROMO 60／GRADED 2／SUPPLY 21／空 77。**商品の行が「何の商品か」を分ける名簿で、使われている**。
- 【事実】quantity_units（migrations/20260921_140000_product_classification_masters.sql:38-48、コメント「正式販売単位マスタ」migrations/20260922_060000_product_unit_condition_infra.sql:89）。本番 3 行 CASE／BOX／PACK、value は全て空（a2.txt）。products.quantity_unit_id は 0 件使用。
- 【事実】product_line_available_units 5 行（a3.txt）: 系統 CASE→単位 CASE、系統 BOX→単位 CASE・BOX・PACK、系統 PACK→単位 PACK。読むのは backend/app/routers/super_admin_quantity_units.py:68,148,222 だけ。
- 【事実】product_quantity_units（migrations/20260922_060000_product_unit_condition_infra.sql。product_id・quantity_unit_id・value、UNIQUE(product_id, quantity_unit_id)）は本番 0 件、migrations 以外のコードから 0 件参照（A1_grep_all_noDocs.txt）。weight_classes も本番 0 件。
- 【事実】product_lines と quantity_units は tenant_id 列なし＝共用（b8.txt）。weight_classes は【未確認】（b8 で見ていない）。値を migration で書かない表として scripts/migration-guard/protected-tables.txt:32-34 に登録済み。
- 【事実】単位の名簿の管理画面がある: backend/app/routers/super_admin_quantity_units.py（CRUD）、frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx。
- 読み取り: product_lines の CASE/BOX/PACK は「商品の種類」、quantity_units の CASE/BOX/PACK は「数える単位」。**名前は同じだが表すものが違う**。

## 3. 値を読み書きしている所（切り替え対象）
- 【事実】見積・請求の重さ: frontend/src/pages/quote-create/quoteDraft.ts:22-45（weightForUnit: box→box_weight_kg、case→case_weight_kg、それ以外→products.weight）。呼び出し frontend/src/pages/quote-create/QuoteCreatePage.tsx:84-85,226、frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:132-133,377。
- 【事実】在庫検索: backend/app/services/inventory_search.py:101-104,343-344,437-441、backend/app/routers/inventory_search.py:122-123、backend/app/schemas/inventory_search.py:62-63（box_weight_kg・case_weight_kg だけ）、frontend/src/components/InventorySearchBar.tsx:53-54。
- 【事実】商品の API: backend/app/routers/products.py:66-67,139-140,407-419、backend/app/schemas/product.py（ProductCreate :68-73、ProductUpdate :116-121、ProductResponse :171-176。6列を Optional で返す）。
- 【事実】商品の画面: frontend/src/pages/products/ProductEditPage.tsx:83-88,149-154,321-341、frontend/src/pages/products/ProductsPage.tsx:373-374,391-392、frontend/src/pages/products/products.types.ts:37-42,78-83,99-101。
- 【事実】取り込み: scripts/seed_products_from_master.py:17-22,70-75,138-143,180-205。
- 【事実】テスト: backend/tests/test_products.py、backend/tests/conftest.py、backend/tests/test_products_required_fields_pg.py、frontend/src/components/CommerceSubmitButtonMigration.test.tsx、frontend/tests-e2e/product-edit-tcg-type.spec.ts、frontend/src/pages/quote-create/quoteDraft.test.ts:39-50。
- 【事実】`git grep` の該当（D1_all.txt）: 全 347 行。migrations 内 31 行、それ以外 316 行。docs・openapi.json・単位の管理画面を除いたコードとテストは 135 行（D2_code.txt）。
- 【未確認】リポジトリ外の GAS が読んでいるか（リポジトリ内の GAS は 0 件）。

## 4. migration の作法
- 【事実】scripts/run_all_migrations.sh:15「新しい migration は末尾に追加」。末尾は 20261017_210000_drop_products_type_master_id.sql。
- 【事実】ai_ro ビューは毎回、先頭で外し最後に全表を作り直す（scripts/run_all_migrations.sh:78-106）。新しい表も次のデプロイ後に ai_ro.public__<表> として読める作り。【未確認】実際に出ることの観測。
- 【事実】新表の前例: migrations/20261016_190000_create_product_blank_confirmations.sql（REFERENCES public.products、RLS は読むのは誰でも・書くのは app.is_operator のときだけ。保護表 scripts/migration-guard/protected-tables.txt に登録）。
- 【事実】.github/workflows/migration-guard.yml:224 の PUBLIC_TABLES は「REFERENCES public.X の X が実在するか」の許可リスト。新しい表を他の表から参照するときだけ要る。

## 5. 外部の出典（ポケモン MEGA シリーズ 9 商品で試した結果）
- 記録: /tmp/CC報告ファイル/mega-pack-specs/RESULT.md、/tmp/CC報告ファイル/source-credibility/SOURCES.md（:57-65 の表）
- 【事実】1ボックスのパック数は 9 商品とも分かった。8 商品は2つ以上の出典で一致、M6a（20 パック）はポケモンセンターオンライン（以下 PCO、株式会社ポケモンの通販）だけ。PO がページ本文（商品コード 9900000008284「1BOX＝20パック」「1パック＝カード6枚入り」）を貼って確かめた（2026-10-17）。
- 【事実】1パックの枚数は公式サイトと PCO で分かる。
- 【事実】ボックスの重さは PCO の商品ページに「重量」として載る（M6a 236 g、サイズ 13.7×13.9×3.6 cm）。M1S・M2・M3・M4・M5 は PCO と輸出店 Samurai Sword Tokyo（以下 SST）で 300 g が一致。M1L・M2a・M6・M6a は一致しない。SST は M6（30 パック）と M6a（20 パック）が同じ 0.32 kg。
- 【事実】カートンの箱数と重さは SST だけ。カートンの重さは同じページのボックス重さ×12 と一致する。
- 【事実】1パックの重さは、どの出典にも無かった。
- 【未確認】PCO の「重量」が外箱込みか中身だけか（ページに書いていない）。
- 【事実】既存の売上データからは取れない（MEGA に紐づく明細 0 行、明細の重さはマスタの写し、order_shipping_details 0 行。/tmp/CC報告ファイル/sales-data-specs/）。

## 6. PO の決定（2026-10-17 チャット）
- 入数・重さは products の列でなく別の表（商品 id・単位 id・中の単位 id・入数・重さ）で持つ: 「y」
- 実測の値も、出典の種類を記録して入れてよい: 「y」
- ボックス重さは PCO ページの値を優先、入数は公式店なら出典1つでも採用・それ以外のサイトは2つ以上一致で採用、カートンとパックの重さは実測: 「y」

## 外部事例
- 使わない。表の形の判断は自社 DB の実測（products に列を足せない・同じ細分類でもパック数が7種に分かれる・名簿の使われ方）だけで決まる。値の出典の信頼度は §5 で実際のサイトを調べて決めた。出典つきの外部事例は集めていないので、設計が正しい証拠には使わない。
