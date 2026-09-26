# ADR-1001: tenant_004.tcg_products を廃止し public.products に統合する

- **Status**: Proposed
- **Date**: 2026-09-14
- **Deciders**: Shingo (PO), Claude Code (Design Partner)
- **Supersedes**: なし
- **Extends**: ADR-090 (products-central-unification)

## Context

ADR-090 で `tenant_NNN.products`（旧テナント別テーブル）を `public.products` へ統合した。
しかし `tenant_004.tcg_products`（TCG専用・UUID PK）は統合対象外のまま残り、以下の問題が発生している。

1. **データ分散**: 商品コード PM0001〜PM0297（297件）が `tenant_004.tcg_products` にあり、`public.products` の seed は別コード体系で重複ゼロだが、同期機構がない
2. **デプロイ停止**: migration が `tcg_products.japanese_title` を固定値と比較し、CSV 編集後に不一致で RAISE EXCEPTION（PR #3500 で応急修正済み）
3. **SSOT 違反**: CSV 取込は `tcg_products` に書き、seed migration は `public.products` に書く。どちらが正かが不定

## Decision

`tenant_004.tcg_products` を廃止し、全商品データを `public.products` に統合する。CSV 取込・詳細編集・検索キーワード管理はすべて `public.products` を参照先とする。

### PO 発話根拠

> 「テーブルを分離している意味がないので統合してくれ tenant_004.tcg_products は廃止する」
> 「配線も public.products に繋いでくれればデータが壊れないと考えている」
> — Shingo, 2026-09-14

## Technical Design

### テーブル構造差分（統合に必要な変更）

| 追加カラム | 型 | 用途 |
|-----------|---|------|
| `tcg_uuid` | UUID UNIQUE | tcg_products.id との FK 互換性維持 |
| `division_id` | UUID | FK → tenant_004.tcg_major_categories |
| `work_id` | UUID | FK → tenant_004.tcg_series |
| `manufacturer_id` | UUID | FK → tenant_004.tcg_manufacturers |
| `product_category_id` | UUID | FK → tenant_004.tcg_product_categories |
| `category_class` | TEXT | Box / Pack / Card 等の分類（既存 `category` はシリーズ名用で別用途） |
| `is_active` | BOOLEAN DEFAULT true | tcg_products の有効フラグ（public.products に存在しないため新規追加） |

既存マッピング（追加不要）:
- `public.products.name` ← `tcg_products.japanese_title`
- `public.products.name_en` ← `tcg_products.english_title`
- `public.products.product_code` ← `tcg_products.code`
- `public.products.mark` ← `tcg_products.mark`（seed migration で既存）
- `public.products.release_date` ← `tcg_products.release_date`（型一致: DATE）

### データ量（実測値）

- `public.products`: 44カラム（SERIAL PK）
- `tcg_products`: 13カラム（UUID PK）、297件（PM0001〜PM0297）
  - 初期作成 268件 + Pokemon batch1 25件 + Magazine promo 3件 + Cardset bundle 1件
- 商品コード重複: **ゼロ**（public.products の seed は DB/OP/UN 等の別コード体系）
- → 統合は全297件 INSERT（UPDATE ではない）
- Python INSERT 経路: `create_product()` が**唯一**（呼出元: POST /api/v1/tcg/products + CSV 一括インポート）

### RLS ポリシーとの整合

`public.products` には RLS が有効（ADR-145, `migrations/20260626_130000_force_rls_public_products.sql`）。

- `tenant_id IS NULL` → 誰でも読取、運営（`is_operator=true`）のみ書込
- `tenant_id = current_tenant` → 該当テナントのみアクセス

tcg_products のデータは商品マスタ（カタログ）であり、テナント横断の共通データ。
→ 移行時に `tenant_id = NULL` で INSERT する。CSV 取込は `is_operator=true` コンテキストで実行する。

### 段階的実装計画

**Phase 2a（本PR: スキーマ拡張 + データ移行）**
1. `public.products` に7カラム追加（IF NOT EXISTS で冪等）
2. `tcg_products` 全件を `public.products` に INSERT（商品コード重複ゼロのため全件 INSERT）
   - `name` ← `japanese_title`, `name_en` ← `english_title`, `product_code` ← `code`
   - `tcg_uuid` ← `id`（UUID 保持）, `tenant_id` ← `NULL`（共通商品）
3. 4種類の FK 依存テーブルの制約を `public.products.tcg_uuid` に張り替え
   - `product_search_keywords` (ON DELETE CASCADE)
   - `product_exclude_keywords` (ON DELETE CASCADE)
   - `products_logistics` (ON DELETE CASCADE)
   - `analysis_results` (FK のみ、CASCADE なし → RESTRICT)
   - FK 制約名は `pg_constraint` から動的取得（anonymous 制約のため）
4. 受入条件: `SELECT count(*) FROM tenant_004.tcg_products` = `SELECT count(*) FROM public.products WHERE tcg_uuid IS NOT NULL`

**Phase 2b（別PR: API 配線変更 — 28ファイル）**

対象ファイル一覧（grep 実測）:

| 区分 | ファイル | 主な変更内容 |
|------|---------|-------------|
| コア | `tcg_product_master_svc.py` (25箇所) | `create_product()`: INSERT 先を `public.products` に変更。`RETURNING id, tcg_uuid` で INT PK と UUID 両方取得 |
| コア | `tcg_product_detail_svc.py` (3箇所) | SELECT/UPDATE の参照先変更 |
| コア | `tcg_product_import_svc.py` (2箇所) | CSV 取込の参照先変更 |
| コア | `tcg_analyzer_svc.py` (5箇所) | 商品コード→ID マッピング変更 |
| 補助 | `tcg_condition_review_svc.py` (2箇所) | スキーマ参照変更 |
| 補助 | `tcg_parallel_report_svc.py` (3箇所) | スキーマ参照変更 |
| 補助 | `tcg_product_roundtrip_svc.py` (3箇所) | スキーマ参照変更 |
| 補助 | `tcg_unit_recovery_svc.py` (3箇所) | スキーマ参照変更 |
| 補助 | `tcg_analysis_review_svc.py` (1箇所) | スキーマ参照変更 |
| 補助 | `tcg_distribution_svc.py` (1箇所) | スキーマ参照変更 |
| 補助 | `tcg_work_comparison_svc.py` (2箇所) | スキーマ参照変更 |
| 補助 | `tcg_work_reference.py` (1箇所) | スキーマ参照変更 |
| 外部 | `tasks/tcg_mirror.py` (3箇所) | ミラーリング対象変更 |
| 外部 | `tasks/tcg_extraction.py` | スキーマ参照変更 |
| 外部 | `tasks/tcg_import_discard.py` | スキーマ参照変更 |
| 外部 | `routers/tcg_product_import.py` (3箇所) | ルーター参照変更 |
| 外部 | `routers/tcg_line_import.py` | スキーマ参照変更 |
| 外部 | `line_import_admin.py` | スキーマ参照変更 |

キーワードテーブル操作（product_search_keywords / product_exclude_keywords）:
- INSERT: `tcg_product_master_svc.py:404,420` — `product_id` に `tcg_uuid` を使用
- SELECT: `tcg_product_detail_svc.py:40,42`, `tcg_analyzer_svc.py:189,207` 他
- DELETE→INSERT: `tcg_product_detail_svc.py:117,121`

受入条件: CSV 取込→DB 確認→検索の一連が `public.products` 経由で動作

**Phase 2c（別PR: tcg_products DROP）**
1. 検証期間（1週間）後に DROP TABLE
2. tcg_uuid カラムの除去は後日判断
3. PO 立会い + バックアップ必須

### FK 依存テーブルの移行（4種類 × 2スキーマ = 8テーブル）

```
現在:  {テーブル}.product_id (UUID) → {schema}.tcg_products.id (UUID)
移行後: {テーブル}.product_id (UUID) → public.products.tcg_uuid (UUID)
```

| テーブル | ON DELETE | 移行方法 |
|---------|-----------|---------|
| product_search_keywords | CASCADE | FK DROP → 再 CREATE |
| product_exclude_keywords | CASCADE | FK DROP → 再 CREATE |
| products_logistics | CASCADE | FK DROP → 再 CREATE |
| analysis_results | なし（RESTRICT） | FK DROP → 再 CREATE。Phase 2c の DROP TABLE 前に NULL 化または FK 解除が必要 |

- FK 制約名は anonymous（名前なし）。DROP 時は `pg_constraint` + `conrelid` + `confrelid` で動的取得
- データ変更なし（UUID 値は同一、参照先テーブルが変わるだけ）
- 対象スキーマ: tenant_004（本番）+ tenant_001（QA）

### リスクと対処

| リスク | 対処 |
|-------|------|
| 28ファイルの SQL 書き換えで漏れ | grep で全参照箇所を機械的に列挙（上表）、CI テストで検証 |
| UUID/INT 混在による混乱 | tcg_uuid はテナントスキーマ→public 移行の橋渡し。4種類の FK テーブルは UUID FK のまま `public.products.tcg_uuid` を参照。Phase 2c 後に INT 化可能 |
| cross-schema FK（tenant_004 → public） | PostgreSQL は cross-schema FK を許容。4種類のテーブル（tenant_004）→ `public.products.tcg_uuid` の FK は技術的に有効 |
| RLS による書込ブロック | `tenant_id = NULL` の行は `is_operator=true` コンテキストでのみ書込可能。CSV 取込・migration は運営コンテキストで実行 |
| 移行中のデータ不整合 | Phase 2a で全297件 INSERT 後に `SELECT count(*)` で件数照合。Phase 2b 完了まで tcg_products は READ-ONLY で残置 |
| anonymous FK 制約の DROP | `pg_constraint` + `conrelid` + `confrelid` で動的に制約名を取得してから DROP |
| analysis_results の RESTRICT FK | Phase 2c（DROP TABLE）前に analysis_results.product_id を NULL 化するか FK 制約を解除する必要がある |
| 297件の INSERT 冪等性 | `ON CONFLICT (product_code) DO UPDATE` で冪等化。毎デプロイ再実行でもデータ破壊しない |

## Consequences

- CSV が唯一の正（SSOT）: 商品データの書込先が `public.products` 1箇所に統一
- migration は構造のみ: 商品名・キーワードを SQL にハードコードしない
- 将来的にキーワードテーブルの FK を INT 化し、tcg_uuid を除去できる
