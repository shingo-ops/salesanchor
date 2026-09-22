# マスタSSOT移行 — 現状調査（recon）

> 調査日: 2026-09-19
> 本番DB実測値（prod1 jarvis_db）

## 1. 現在のマスタ配置

### public（SSOT済み）

| テーブル | 行数 | ID型 | 役割 |
|---------|------|------|------|
| `suppliers` | 229 | INTEGER | 仕入元マスタ |
| `products` | 1,627 | INTEGER | 商品マスタ |
| `tcg_type_master` | 12 | INTEGER | 大分類（Pokemon, One Piece等） |
| `tcg_series_master` | 56 | INTEGER | 作品シリーズ（SV1a, OP-01等） |
| `product_attribute_masters` | 30 | — | 属性値（product_kind, set_type等） |
| `supplier_aliases` | — | — | 仕入元別名 |

### tenant_004（LINE解析で使用・未SSOT）

| テーブル | 行数 | ID型 | 役割 |
|---------|------|------|------|
| `tcg_series` | 11 | UUID | **意図と違うテーブル**（IP単位、9/2作成） |
| `units` | 8 | UUID | 単位（Case/Box/Pack等） |
| `unit_aliases` | 39 | UUID | 単位別名 |
| `conditions` | 11 | UUID | 状態（Sealed/Damaged等） |
| `condition_aliases` | 31 | UUID | 状態別名 |
| `tcg_note_master` | 74 | text | 注釈マスタ |
| `tcg_status_master` | 9 | text | ステータスマスタ |
| `tcg_product_categories` | 2 | UUID | カテゴリ |
| `product_search_keywords` | 708 | UUID | 検索キーワード |
| `product_exclude_keywords` | 291 | UUID | 除外キーワード |

## 2. 配線の問題

### products.work_id（最重要）

- **現在**: UUID型 → `tenant_004.tcg_series`（意図と違うテーブル）
- **本来**: INTEGER型 → `public.tcg_series_master`
- **影響**: 1,317件が存在しないUUIDを参照 → LINE抽出パイプライン全停止

### tcg_series_master の不足

`public.tcg_series_master`に以下4作品が未登録:

| 作品 | 孤立商品数 | tcg_type |
|------|----------|----------|
| Weiss Schwarz | 610 | weiss_schwarz |
| Digimon | 63 | digimon |
| hololive | 29 | hololive |
| LORCANA | 11 | lorcana |

## 3. コード参照箇所（配線変更対象）

`tenant_004.tcg_series`を参照している9ファイル16行:

| ファイル | 行 | 参照内容 |
|---------|-----|---------|
| `backend/app/services/tcg_work_reference.py` | 55 | FROM {schema}.tcg_series（抽出の核） |
| `backend/app/services/tcg_analyzer_svc.py` | 425 | SELECT id, display_name, alt_name |
| `backend/app/services/tcg_distribution_svc.py` | 238 | LEFT JOIN tcg_series |
| `backend/app/services/tcg_analysis_review_svc.py` | 41, 303 | JOIN + SELECT |
| `backend/app/routers/tcg_product_import.py` | 135, 318 | SELECT + カラムマッピング |
| `backend/app/services/tcg_product_master_svc.py` | 85, 357, 360 | SELECT（3箇所） |
| `backend/app/services/tcg_product_detail_svc.py` | 17 | マッピング定義 |
| `backend/app/services/tcg_product_import_svc.py` | 65 | マッピング定義 |
| `backend/app/services/tcg_work_comparison_svc.py` | 32 | リスト定義 |

`public.tcg_series_master`を参照している箇所:

| ファイル | 行 | 参照内容 |
|---------|-----|---------|
| `backend/app/routers/super_admin_tcg.py` | 63,85,121,140,252 | CRUD（5箇所） |
| `backend/app/services/inventory_search.py` | 279-280 | 検索JOIN |
| `backend/app/schemas/central_masters.py` | 7,109 | スキーマ定義 |
| `frontend/src/pages/super-admin/TcgSeriesTab.tsx` | 5 | フロント管理画面 |

## 4. 仕入元SSOTパターン（手本）

```
public.suppliers（マスタ・SSOT）
  ├── id: INTEGER（連番）
  ├── tenant_id: テナント所属（NULLなら共通）
  └── 全テナントからFK参照
```

商品マスタ・作品マスタも同じパターンに統一する。

## 5. 型の統一方針（PO決定済み）

- **INTEGER に統一**（商品マスタが整数なので）
- tenant_004 の UUID テーブルは public の INTEGER テーブルに移植
