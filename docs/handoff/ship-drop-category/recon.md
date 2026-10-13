# recon: 発送欄除外（ship-drop-category）

実測基準: origin/main f9beaa23c2b725dfab22e8cb859797c5f1ee2131（本便の commit 前）。事実のみ。評価・提案なし。

## 現在地（file:line）
- backend/app/services/gemini_raw_copy_v101.py:809 _ship_for の定義
- backend/app/services/gemini_raw_copy_v10.py:180 _SHIP_WORD_RE = re.compile(r"発送|出荷|入荷|発売|着")
- backend/app/services/tcg_analyzer_svc.py:1013 load_note_master（category を条件にしない）
- backend/app/services/tcg_analyzer_svc.py:1116 SHIP_NOTE_CATEGORY = "発送時期系"
- backend/app/services/tcg_analyzer_svc.py:1117 _SHIP_PART_SEPARATOR = " / "
- backend/app/services/tcg_analyzer_svc.py:1120 load_ship_master
- backend/app/services/tcg_analyzer_svc.py:1156 build_ship_labels(ship, ship_entries)
- backend/app/services/line_analysis_v102_svc.py:181 _SHIP_ENTRIES_KEY = "ship_entries"
- backend/app/services/line_analysis_v102_svc.py:196 masters に load_ship_master を登録
- backend/app/services/line_analysis_v102_svc.py:329 extract_items へ渡す masters から _SHIP_ENTRIES_KEY を除外
- backend/app/services/line_analysis_v102_svc.py:671 build_ship_labels の呼び出し
- backend/tests/test_line_analysis_v102_svc.py:199 test_pipeline_does_not_pass_ship_entries_to_extract_items
- masters に ship_entries を持つ既存 fixture（drop キー無し）:
  - backend/tests/test_line_analysis_v102_svc.py:28
  - backend/tests/test_line_analysis_v102_pg.py:60
  - backend/tests/test_v102_buyback_unit.py:218
  - backend/tests/test_v102_unit_price_check.py:172
- migrations/20260919_020000_master_ssot_public_tables.sql:230 Step 5: public.tcg_note_master

## 既存 ADR 検索（git grep -il docs/adr/、docs/adr/FEATURE-INDEX.md 確認済み）
- note_master: docs/adr/ADR-154-tcg-parity02-gas-python-migration.md（26行目に tcg_note_master 不在時の graceful fallback の記述あり。category や発送欄の記述は無し）
- 備考マスタ: ヒット0件
- ship_ja: docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md（16行目に在庫表の列へ note_ja と ship_ja を足す記述あり。ship_ja の組み立て方の記述は無し）
- 発送（出荷計算・受注・販売系の ADR。発送日の欄の組み立てとは別の主題）:
  - docs/adr/ADR-021-order-management.md, ADR-067-design-token-enforcement.md, ADR-093-inventory-table-product-master-redesign.md, ADR-093-sales-management-page.md, ADR-094-sales-management-page.md, ADR-095-sa-ssot-two-backbone-architecture.md, ADR-097-sa-customer-registration-form.md, ADR-099-sa-inventory-model.md, ADR-101-sa-quotation-invoice-generation.md, ADR-102-sa-order-management.md, ADR-103-sa-shipping-dispatch-timing.md, ADR-104-sa-payment-confirmation-status-pnl.md, ADR-106-sa-multitenant-policy.md, ADR-147-common-6roles-standardization.md, ADR-151-jst-date-basis.md, README.md, FEATURE-INDEX.md
- FEATURE-INDEX.md:17 「発送 / 出荷 / shipping ...」→ ADR-103 / ADR-123 / ADR-128（出荷タイミング・キャリア連携）。tcg_note_master・ship_ja の項目は FEATURE-INDEX.md に無し
- design.md が参照する docs/adr/ADR-155-product-master-ssot-csv-app.md は実在する（マスタ SSOT・管理画面編集）
