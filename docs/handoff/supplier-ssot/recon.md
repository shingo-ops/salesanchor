# 仕入元マスタ SSOT化 — 現状調査（recon）

> この文書は「仕入元の名簿が2つに分かれている現状」の調査結果です。
> 親: [仕入元マスタ設計仕様書](../../specs/supplier-master/README.md)

## 既存ADR検索結果

| ADR | 関連 | 内容 |
|-----|------|------|
| ADR-090 | ○ | products中央化。public.productsへの統合パターンが参考になる |
| ADR-093 | ○ | 在庫・マスタ再設計。public.suppliersにline_nameカラム追加（2026-06-03） |
| ADR-085 | △ | 仕入先別Geminiプロンプト。public.supplier_promptsがpublic.suppliers.idを参照 |
| ADR-072 | △ | テナントスキーマ規約。tcg_suppliersはテナントスキーマ内 |

## 1. 現状の仕入元テーブル構造

### public.suppliers（全テナント共有マスタ）

- 定義: `migrations/056_add_suppliers_type_and_promote_public.sql:46-60`
- ID型: SERIAL（整数）
- コード形式: `SP-NNNNN`（`super_admin_suppliers.py:136` で採番）
- line_name カラム: `migrations/20260603_010000_add_suppliers_line_and_address.sql` で追加（ADR-093）
- CRUD画面: `backend/app/routers/super_admin_suppliers.py`（既存・動作中）
- FKを参照するテーブル: 10テーブル（parse_logs, ingestion_jobs, supplier_aliases, inventory, discord_inbound_messages, supplier_discord_routing, supplier_prompts 等）

### tenant_004.tcg_suppliers（TCG LINE取り込み専用）

- 定義: `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:110-119`
- ID型: UUID
- コード形式: `SP0188`（ハイフンなし・4桁）
- CRUD画面: なし
- FKを参照するテーブル: `supplier_channels`（UUID FK・ON DELETE CASCADE）
- 登録件数（migration記録分）: 19件（SP0007, SP0184, SP0188-SP0204, SP9001-SP9003）

### public.line_supplier_source_names（Android別名テーブル）

- 定義: `migrations/20260912_170000_line_supplier_source_names.sql`
- 用途: Android LINE表示名 → tcg_suppliers.id のマッピング
- PK: (tcg_schema, source_format, display_name)
- supplier_id: UUID（tcg_suppliers.idを参照。FK制約なし・アプリ側で検証）

## 2. LINE取り込みの配線（現状）

### PC版フロー

```
parse_line_export（tcg_line_import_svc.py:166-193）
  → _split_sender(rest, sorted_names)  ← tcg_suppliers.name で前方一致
  → display_name 確定
  → resolve_suppliers（tcg_line_import_svc.py:216-266）← tcg_suppliers.name で完全一致
  → sp_code + canonical_name 確定
```

### Android版フロー

```
parse_android_export（tcg_line_android_parser.py）
  → TAB分割 → display_name（LINE表示名そのまま）
  → resolve_android（line_source_names.py:35-54）← tcg_suppliers.name + 別名テーブルで照合
  → sp_code + canonical_name 確定
```

### 問題

1. PC版とAndroid版で異なるresolve関数を使用
2. tcg_suppliersの名前（短縮形）とLINE表示名（フルネーム）が一致しないケースが39件
3. 仕入元データがpublic.suppliersとtcg_suppliersに分散（SSOT違反）
4. supplier_channelsがtcg_suppliers（UUID）を参照しており、public.suppliers（INTEGER）と繋がっていない

## 3. tcg_suppliersを参照しているファイル（全12ファイル・32箇所）

| ファイル | 参照数 | 参照パターン |
|---------|--------|-------------|
| `backend/app/services/tcg_line_import_svc.py` | 3 | SELECT code,name / JOIN |
| `backend/app/routers/tcg_line_import.py` | 7 | SELECT/INSERT/UPDATE/採番 |
| `backend/app/services/line_source_names.py` | 4 | SELECT/LOCK/JOIN |
| `backend/app/line_import_admin.py` | 4 | SELECT/LOCK/正規表現 |
| `backend/app/services/tcg_diagnostics_svc.py` | 3 | SELECT/JOIN |
| `backend/app/services/tcg_distribution_svc.py` | 1 | JOIN |
| `backend/app/services/tcg_import_progress.py` | 2 | JOIN |
| `backend/app/services/tcg_analysis_review_svc.py` | 1 | JOIN |
| `backend/app/services/tcg_parallel_report_svc.py` | 1 | JOIN |
| `backend/app/services/tcg_sold_out_results_svc.py` | 1 | JOIN |
| `backend/app/services/tcg_supplier_quality_svc.py` | 2 | JOIN/コメント |
| `backend/app/tasks/tcg_mirror.py` | 3 | SELECT/JOIN/テーブル名文字列 |

### テストファイル（5ファイル）

| ファイル | 参照内容 |
|---------|---------|
| `backend/tests/test_tcg_import_progress_pg.py` | INSERT/UPDATE文にUUID ID使用 |
| `backend/tests/test_tcg_line_import.py` | Mock判定文字列 "tcg_suppliers" |
| `backend/tests/test_line_source_names.py` | Assert文 |
| `backend/tests/test_tcg_result_order.py` | INSERT文 + クリーンアップ対象 |
| `backend/tests/test_tcg_sold_out_results.py` | INSERT文 |

## 4. LINE表示名の書式比較（2026-09-17 実測）

Android版とPC版のLINEエクスポートファイルを実物比較した結果:

| 項目 | 結果 |
|------|------|
| 送信者名の一致 | 168名全員一致（揺れなし） |
| 本文の一致 | 同時刻投稿で100%一致 |
| 書式の違い | 区切り文字（TAB vs スペース）、日付形式、BOM有無 等 |

詳細: `/tmp/CC報告ファイル/LINE_chat_comparison_report_20260917.txt`

## 5. 根本原因

- PC版: `_split_sender` がマスタ名（短縮形）で前方一致するため、LINE表示名（フルネーム）から短縮名を切り出して照合成功
- Android版: TAB分割でLINE表示名がそのまま `display_name` になるため、マスタ名（短縮形）と完全一致せず39名が未解決

例:
```
マスタ名: 「倉田」（短縮形）
LINE表示名: 「倉田 和博」（フルネーム）

PC版:  _split_sender("倉田 和博 本文...") → "倉田" に切り詰め → マスタ一致 ✅
Android版: display_name="倉田 和博" → マスタ "倉田" と不一致 ❌
```
