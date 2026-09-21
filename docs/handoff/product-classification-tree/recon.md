# recon: product-classification-tree（ADR-156 Phase 1）

作成日: 2026-09-21

---

## 1. 既存テーブル調査結果

| テーブル | 状態 | 備考 |
|---------|------|------|
| `public.product_kinds` | 新設（本PR） | 大分類。migration 20260921_010000 で作成 |
| `public.tcg_type_master` | 12件・リネーム対象 | migration 085 で作成。本PR で type_master に改名し、互換ビューを残す |
| `public.type_master` | 新規（rename後） | tcg_type_master のリネーム先 |
| `public.product_lines` | 作成済み・0件 | migration 20260920_130000 で作成。本PR で type_id FK 追加 |
| `public.product_formats` | 作成済み・0件 | migration 20260920_130000 で作成。本PR の変更なし |
| `public.condition_definitions` | 新設（本PR） | コンディション定義マスタ。migration 20260921_040000 で作成 |
| `public.conditions` | 既存 | migration 20260919_020000 で作成。本PR で condition_def_id FK 追加 |
| `public.units` | 既存 | migration 20260919_020000 で作成。本PR で line_id FK 追加 |

---

## 2. 関連 ADR

- ADR-083: `docs/adr/ADR-083-tcg-type-master.md` — TCG 種別マスタ新設（tcg_type_master 原設計）
- ADR-090: `docs/adr/ADR-090-products-central-unification.md` — products 中央一本化
- ADR-155: `docs/adr/ADR-155-product-master-ssot-csv-app.md` — migration での値 INSERT 禁止
- ADR-156: 本PRの根拠（docs/adr/ 未作成・本 Phase の前提となる設計文書）

---

## 3. tcg_type_master の原定義

- 作成 migration: `migrations/085_create_tcg_type_master.sql`
- トリガ関数: `public.set_updated_at_tcg_type_master()`
- トリガ: `trigger_set_updated_at_tcg_type_master` ON `public.tcg_type_master`

リネーム後は互換ビュー `public.tcg_type_master` で透過継続するため、既存コード変更は Phase 1 で不要。
Phase 2 で互換ビューを廃止する際にアプリコードの書き換えが必要。

---

## 4. tcg_type_master 参照箇所（既存コード）

### backend/app/routers/super_admin_tcg.py

- `backend/app/routers/super_admin_tcg.py:38` — コメント ADR-083: TCG 種別マスタ (public.tcg_type_master)
- `backend/app/routers/super_admin_tcg.py:149` — コメント ADR-083: TCG 種別マスタ (public.tcg_type_master) CRUD
- `backend/app/routers/super_admin_tcg.py:164` — SELECT ... FROM public.tcg_type_master
- `backend/app/routers/super_admin_tcg.py:183` — INSERT INTO public.tcg_type_master
- `backend/app/routers/super_admin_tcg.py:186` — SELECT COALESCE(MAX(id), 0) + 1 FROM public.tcg_type_master
- `backend/app/routers/super_admin_tcg.py:221` — UPDATE public.tcg_type_master SET
- `backend/app/routers/super_admin_tcg.py:242` — SELECT code FROM public.tcg_type_master WHERE id
- `backend/app/routers/super_admin_tcg.py:267` — DELETE FROM public.tcg_type_master WHERE id

### backend/app/routers/tcg_product_import.py

- `backend/app/routers/tcg_product_import.py:135` — FROM public.tcg_type_master s
- `backend/app/routers/tcg_product_import.py:316` — コメント work_id → public.tcg_type_master (SSOT)
- `backend/app/routers/tcg_product_import.py:319` — FROM public.tcg_type_master

### backend/app/routers/products.py

- `backend/app/routers/products.py:100` — 関数 _tcg_type_master_ref()
- `backend/app/routers/products.py:101` — return "public.tcg_type_master"
- `backend/app/routers/products.py:108` — SELECT to_regclass('public.tcg_type_master') IS NOT NULL
- `backend/app/routers/products.py:113` — エラーメッセージ内 tcg_type_master.code
- `backend/app/routers/products.py:116` — ref = _tcg_type_master_ref(db)
- `backend/app/routers/products.py:124` — エラーメッセージ内 tcg_type_master.code
- `backend/app/routers/products.py:158` — クエリ説明文 tcg_type_master.code
- `backend/app/routers/products.py:271` — SELECT to_regclass('public.tcg_type_master') IS NOT NULL
- `backend/app/routers/products.py:274` — ref = "public.tcg_type_master"
- `backend/app/routers/products.py:277` — SQLite 互換チェック tcg_type_master
- `backend/app/routers/products.py:281` — ref = "tcg_type_master"

### backend/app/services/tcg_product_import_svc.py

- `backend/app/services/tcg_product_import_svc.py:168` — コメント work_code → public.tcg_type_master (SSOT, INTEGER PK)
- `backend/app/services/tcg_product_import_svc.py:170` — FROM public.tcg_type_master WHERE is_active = TRUE

### backend/app/services/tcg_product_master_svc.py

- `backend/app/services/tcg_product_master_svc.py:83` — コメント work_id → public.tcg_type_master (SSOT)
- `backend/app/services/tcg_product_master_svc.py:86` — FROM public.tcg_type_master
- `backend/app/services/tcg_product_master_svc.py:364` — コメント tcg_type_master.name_ja から導出
- `backend/app/services/tcg_product_master_svc.py:366` — SELECT name_ja FROM public.tcg_type_master WHERE id

### その他サービスファイル

- `backend/app/services/tcg_product_detail_svc.py:73` — FROM public.tcg_type_master
- `backend/app/services/tcg_product_detail_svc.py:76` — FROM public.tcg_type_master
- `backend/app/services/tcg_product_detail_svc.py:128` — SELECT name_ja FROM public.tcg_type_master
- `backend/app/services/tcg_analyzer_svc.py:425` — FROM public.tcg_type_master WHERE is_active = TRUE
- `backend/app/services/tcg_analysis_review_svc.py:41` — LEFT JOIN public.tcg_type_master ws
- `backend/app/services/tcg_analysis_review_svc.py:303` — FROM public.tcg_type_master s
- `backend/app/services/tcg_product_roundtrip_svc.py:102` — LEFT JOIN public.tcg_type_master work
- `backend/app/services/tcg_product_roundtrip_svc.py:192` — FROM public.tcg_type_master r WHERE r.is_active=TRUE
- `backend/app/services/tcg_work_reference.py:63` — FROM public.tcg_type_master s WHERE s.is_active
- `backend/app/services/tcg_distribution_svc.py:238` — LEFT JOIN public.tcg_type_master ser
- `backend/app/services/tcg_work_comparison_svc.py:129` — FROM public.tcg_type_master t

**合計参照箇所: 50箇所以上**（互換ビューで透過継続のため Phase 1 での変更は不要）

---

## 5. マイグレーション依存関係

```
migrations/20260920_130000_create_product_classification.sql   (product_lines 作成)
  ↓
migrations/20260921_010000_create_product_kinds.sql            (product_kinds 新設)
  ↓
migrations/20260921_020000_rename_tcg_type_master_to_type_master.sql
    (tcg_type_master→type_master・互換ビュー・kind_id FK→product_kinds)
  ↓
migrations/20260921_030000_product_lines_add_type_id.sql       (type_id FK→type_master)
  ↓
migrations/20260921_040000_create_condition_definitions.sql    (condition_definitions 新設)
  ↓
migrations/20260921_050000_add_analysis_master_fk.sql          (conditions→condition_definitions, units→product_lines)
```
