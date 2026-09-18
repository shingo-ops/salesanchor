# Recon: 仕入元マスタ SSOT Phase 2 — テーブル統合

## 既存ADR検索結果

- ADR-090: products 中央化（同パターンを suppliers に適用）
- ADR-093: 在庫・マスタ再設計（public.suppliers に line_name 追加済み 2026-06-03）
- ADR-085: 仕入先別 Gemini プロンプト管理（public.supplier_prompts が public.suppliers.id 参照）
- ADR-072: テナントスキーマ規約
- ADR-135: main マージ＝本番投入可の宣言
- Phase 1 設計: `docs/handoff/supplier-ssot/design.md`（PR #3539 でマージ済み）

## 現状の仕入元テーブル構造（3テーブル分散）

### public.suppliers（中央共有カタログ）
- 定義: `migrations/056_add_suppliers_type_and_promote_public.sql:45-60`
- 追加列: `migrations/20260603_010000_add_suppliers_line_and_address.sql:17-23`
- 本番行数: 229行
- カラム（20列）:
  - id (SERIAL PK), supplier_code (VARCHAR(20) UNIQUE), name (VARCHAR(255) NOT NULL)
  - supplier_type (VARCHAR(20) DEFAULT 'corporate'), default_language (CHAR(2) DEFAULT 'ja')
  - contact_name, email, phone, address, notes
  - is_active (BOOLEAN DEFAULT TRUE), created_by (INTEGER)
  - created_at, updated_at
  - line_name (VARCHAR(255)), postal_code, prefecture, city, address1, address2

### tenant_NNN.suppliers（テナント発注先）
- 定義: `migrations/007_add_phase3_tenant_tables.sql:12-25`
- RLS有効: `migrations/007_add_phase3_tenant_tables.sql:58`
- カラム（12列）:
  - id (SERIAL PK), tenant_id (INTEGER NOT NULL), supplier_code (VARCHAR(20))
  - name (VARCHAR(255) NOT NULL), contact_name, email, phone, address, notes
  - is_active (BOOLEAN DEFAULT TRUE), created_at, updated_at
- public.suppliers にあって tenant にない列: supplier_type, default_language, created_by, line_name, postal_code, prefecture, city, address1, address2

### tenant_NNN.tcg_suppliers（TCG LINE取込専用）
- 定義: `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:109`
- PK: UUID
- Phase 1（PR #3539）で supplier_channels.supplier_id を public.suppliers に移行済み
- 本番残存: tenant_001 に 3行、tenant_004 に 179行

## FK 依存チェーン

### purchase_orders.supplier_id → tenant_NNN.suppliers(id)
- 定義: `migrations/007_add_phase3_tenant_tables.sql:33` — `supplier_id INTEGER NOT NULL REFERENCES {schema}.suppliers(id)`
- 解決ロジック: `backend/app/routers/purchase_orders.py:56-110` — `_resolve_tenant_supplier_id()`
  - public.suppliers.id を受け取り → tenant.suppliers に複製 → tenant id を返却
- PDF生成: `backend/app/services/po_renderer.py:215-250` — tenant→public 2段階照合

### products.supplier_default_id → tenant_NNN.suppliers(id)（条件付き）
- 定義: `migrations/038_add_products_phase1c_columns.sql:83`
  - `ADD COLUMN IF NOT EXISTS supplier_default_id INTEGER REFERENCES %I.suppliers(id)`
- 参照: `backend/app/routers/tcg_product_import.py` — GET/PUT/POST に含む

### supplier_channels.supplier_id → public.suppliers(id)
- Phase 1 で INTEGER に変更済み（PR #3539）
- FK `fk_supplier_channels_supplier_id` → `public.suppliers(id) ON DELETE CASCADE`

### public.supplier_prompts.supplier_id → public.suppliers(id)
- 定義: `migrations/20260612_supplier_prompts.sql`（推定・ADR-085）
- 影響なし（既に public.suppliers を参照）

## コード参照一覧

### tenant_NNN.suppliers を参照するコード（変更必要）
| ファイル | 行 | パターン |
|---|---|---|
| `backend/app/routers/suppliers.py:34-121` | テナント CRUD | `{schema}.suppliers` に SELECT/INSERT/UPDATE/DELETE |
| `backend/app/routers/purchase_orders.py:56-110` | `_resolve_tenant_supplier_id()` | public→tenant コピー |
| `backend/app/services/po_renderer.py:215-250` | PDF supplier 解決 | tenant→public 2段階照合 |

### tcg_suppliers を参照するコード（変更必要）
| ファイル | 行 | パターン |
|---|---|---|
| `backend/app/tcg_config.py:13` | docstring | コメントのみ |
| `backend/app/routers/tcg_line_import.py:406,448,463,478,486,501,606` | JOIN/SELECT/INSERT | tcg_suppliers テーブル操作 |
| `backend/app/line_import_admin.py:117,121,147,148` | SELECT/JOIN | tcg_suppliers 参照 |
| `backend/app/services/tcg_diagnostics_svc.py:46,51,59` | JOIN | tcg_suppliers 参照 |
| `backend/app/services/tcg_sold_out_results_svc.py:48` | JOIN | tcg_suppliers 参照 |
| `backend/app/services/tcg_parallel_report_svc.py:186` | JOIN | tcg_suppliers 参照 |
| `backend/app/services/tcg_analysis_review_svc.py:39` | JOIN | tcg_suppliers 参照 |
| `backend/app/services/tcg_line_import_svc.py:73,132,230,351,490,549` | JOIN/SELECT/INSERT | tcg_suppliers 操作 |
| `backend/app/services/tcg_supplier_quality_svc.py:43,71,81` | JOIN | tcg_suppliers 参照 |
| `backend/app/services/line_source_names.py:29,103,104,113` | JOIN/SELECT | tcg_suppliers 参照 |
| `backend/app/services/tcg_distribution_svc.py:234` | JOIN | tcg_suppliers 参照 |
| `backend/app/services/tcg_import_progress.py:160,183` | JOIN | tcg_suppliers 参照 |

### テストファイル（変更必要）
| ファイル | 行 |
|---|---|
| `backend/tests/test_tcg_import_progress_pg.py:66,154,315,355,386` | tcg_suppliers seed/参照 |
| `backend/tests/test_tcg_line_import.py:538,606,744,863` | tcg_suppliers seed/参照 |
| `backend/tests/test_line_source_names.py:129` | tcg_suppliers 参照 |
| `backend/tests/test_tcg_result_order.py:76,223` | tcg_suppliers seed/参照 |
| `backend/tests/test_tcg_sold_out_results.py:131` | tcg_suppliers seed/参照 |

### public.suppliers を参照するコード（影響なし or 微修正）
| ファイル | 行 | 備考 |
|---|---|---|
| `backend/app/routers/super_admin_suppliers.py` | 全体 | 変更不要（既に public.suppliers 直接操作） |
| `backend/app/routers/suppliers.py:59-82` | GET /suppliers/catalog | 変更不要（既に public.suppliers 参照） |
| supplier_channels 関連 | 全体 | Phase 1 で移行済み |

## PO決定の経緯

- 2026-06-10: PO決定「両系統を役割別の正として維持」（`migrations/056:1-30`）
- 2026-09-18: PO決定「撤回。SSOT 統合に進める」（本セッション）
  - `public.suppliers` に `tenant_id` 追加、tenant テーブル DROP
  - RLS ではなくアプリ層 WHERE 句でテナント分離
