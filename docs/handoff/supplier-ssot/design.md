# 仕入元マスタ SSOT化 — フェーズ1 設計

> この文書は「LINE取り込みの仕入元照合を public.suppliers.line_name に統一する」設計です。
> 親: [仕入元マスタ設計仕様書](../../specs/supplier-master/README.md)
> 現状調査: [recon.md](./recon.md)

## 目的

LINE取り込み（PC版・Android版）の仕入元照合先を `public.suppliers.line_name` に統一し、1つの照合ロジックで両方が動く状態にする。

## 対象と対象外

| 対象 | 対象外 |
|------|--------|
| LINE取り込みの配線を public.suppliers に変更 | フロントCRUD画面の拡張（フェーズ2） |
| supplier_channels のFK変更（UUID→INTEGER） | CSVインポート/エクスポート（フェーズ3） |
| line_supplier_source_names テーブルの廃止 | migration INSERT文の削除（フェーズ4） |
| テスト修正（5ファイル） | CIガード追加（フェーズ5） |
| | tcg_suppliers テーブル自体の廃止（テナント独自用として残す） |

## 変更前後

### 変更前

```
PC版:
  _split_sender(tcg_suppliers.name) → resolve_suppliers(tcg_suppliers.name)
Android版:
  resolve_android(tcg_suppliers.name + line_supplier_source_names)

supplier_channels.supplier_id (UUID) → tcg_suppliers.id (UUID)
```

### 変更後

```
PC版:
  _split_sender(public.suppliers.line_name) → resolve_suppliers(line_name)
Android版:
  resolve_suppliers(public.suppliers.line_name) ← PC版と同じ関数

supplier_channels.supplier_id (INTEGER) → public.suppliers.id (SERIAL)
```

## Migration

### 原則

- テーブル構造の変更のみ。値のINSERT/UPDATE/DELETEは行わない
- 例外: supplier_channels.supplier_id のデータマッピング（FK型変更に伴う一回限りの移行処理）

### 手順

```sql
-- 1. supplier_channels.supplier_id を UUID → INTEGER に変更
--    tcg_suppliers.id → public.suppliers.id へのマッピング
ALTER TABLE {schema}.supplier_channels
  ADD COLUMN supplier_int_id INTEGER;

UPDATE {schema}.supplier_channels sc
  SET supplier_int_id = ps.id
  FROM {schema}.tcg_suppliers ts
  JOIN public.suppliers ps
    ON ps.supplier_code = 'SP-' || LPAD(SUBSTRING(ts.code FROM 3), 5, '0')
  WHERE sc.supplier_id = ts.id;

-- supplier_int_id が NULL の行がないことを確認（マッピング漏れ防止）
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM {schema}.supplier_channels WHERE supplier_int_id IS NULL
  ) THEN
    RAISE EXCEPTION 'supplier_channels にマッピングできない行があります';
  END IF;
END $$;

ALTER TABLE {schema}.supplier_channels
  DROP CONSTRAINT supplier_channels_supplier_id_fkey;
ALTER TABLE {schema}.supplier_channels
  DROP COLUMN supplier_id;
ALTER TABLE {schema}.supplier_channels
  RENAME COLUMN supplier_int_id TO supplier_id;
ALTER TABLE {schema}.supplier_channels
  ALTER COLUMN supplier_id SET NOT NULL;
ALTER TABLE {schema}.supplier_channels
  ADD CONSTRAINT supplier_channels_supplier_id_fkey
    FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id) ON DELETE CASCADE;

-- 2. 別名テーブル廃止
DROP TABLE IF EXISTS public.line_supplier_source_names;
```

### 前提条件

- `tcg_suppliers` の全仕入元が `public.suppliers` に `line_name` 付きで登録済みであること
- 登録はアプリ画面またはCSVで行う（migrationではない）
- `supplier_code` のマッピング: `SP0188` → `SP-00188`

## コード変更（12ファイル + 5テスト）

### パターン1: マスタ取得（3ファイル）

| ファイル | 行 | 変更 |
|---------|-----|------|
| `tcg_line_import_svc.py` | 548-551 | `SELECT supplier_code, line_name FROM public.suppliers WHERE is_active = TRUE AND line_name IS NOT NULL` |
| `tcg_line_import_svc.py` | 552 | `sorted((s["line_name"] for s in db_suppliers), key=len, reverse=True)` |
| `tcg_line_import.py` | 606-608 | 同上パターン |
| `line_source_names.py` | 104 | 同上パターン（※この関数自体がメインフローから外れる） |

### パターン2: JOIN（8ファイル）

```python
# 変更前
JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id = sc.supplier_id

# 変更後
JOIN public.suppliers ps ON ps.id = sc.supplier_id
```

該当ファイル: `tcg_analysis_review_svc.py`, `tcg_diagnostics_svc.py`, `tcg_distribution_svc.py`, `tcg_import_progress.py`, `tcg_parallel_report_svc.py`, `tcg_sold_out_results_svc.py`, `tcg_supplier_quality_svc.py`, `tcg_mirror.py`

### パターン3: INSERT/UPDATE/採番（tcg_line_import.py）

```python
# 変更前
SELECT MAX(code) FROM {TCG_SCHEMA}.tcg_suppliers  # SP0204 → SP0205
INSERT INTO {TCG_SCHEMA}.tcg_suppliers (id, code, name, is_active, created_at) ...

# 変更後
SELECT MAX(supplier_code) FROM public.suppliers WHERE supplier_code LIKE 'SP-%'
INSERT INTO public.suppliers (name, line_name, supplier_type, is_active) ...
# supplier_code は RETURNING id → UPDATE で SP-{id:05d} 採番（既存パターン踏襲）
```

### パターン4: 正規表現（line_import_admin.py:43）

```python
# 変更前
r'SP[0-9]{4,8}'

# 変更後
r'SP-[0-9]{5}'
```

### パターン5: Android分岐の統一（tcg_line_import_svc.py:555-560）

```python
# 変更前
if source_format == "android":
    messages = [{**m, '_line_source_format': line_source_names.MARKER} for m in messages]
    resolved_msgs, unresolved = line_source_names.resolve_android(messages, db_suppliers, await line_source_names.load_aliases(db))
else:
    resolved_msgs, unresolved = resolve_suppliers(messages, db_suppliers)

# 変更後（PC版・Android版ともに同じ関数）
resolved_msgs, unresolved = resolve_suppliers(messages, db_suppliers)
```

### パターン6: resolve_suppliers の照合キー変更（tcg_line_import_svc.py:216-266）

```python
# 変更前
name_to_supplier = {s["name"]: s for s in db_suppliers}

# 変更後
name_to_supplier = {s["line_name"]: s for s in db_suppliers}
```

## 触らないもの

| 対象 | 理由 |
|------|------|
| `tcg_line_android_parser.py` | パーサーは正常動作中。DB参照なし |
| `super_admin_suppliers.py` | 既に public.suppliers + line_name 対応済み |
| `public.suppliers.name` | ビジネス名。変更なし |
| `source_messages` 以下のFK連鎖 | supplier_channels.id（PK）は変わらない |
| `tcg_suppliers` テーブル | テナント独自用として残す |

## 受入条件

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | PC版: `_split_sender` が `line_name` で前方一致する | テスト: `_split_sender("倉田 和博 本文", ["倉田 和博"])` → "倉田 和博" |
| 2 | Android版: `display_name` が `line_name` で完全一致する | テスト: resolve_suppliers で line_name="倉田 和博" に一致 |
| 3 | PC版とAndroid版が同じ `resolve_suppliers` を使う | コード確認: Android分岐の `resolve_android` 呼び出しが消えている |
| 4 | `supplier_channels.supplier_id` が `public.suppliers.id` (INTEGER) を参照する | migration適用後: `\d supplier_channels` でFK確認 |
| 5 | `line_supplier_source_names` テーブルが存在しない | migration適用後: `\dt line_supplier_source_names` で確認 |
| 6 | 既存テストが全て通る | CI緑 |
| 7 | マッピング漏れがない | migration内のRAISE EXCEPTIONチェック |

## リスクと対処

| リスク | 影響 | 対処 |
|--------|------|------|
| tcg_suppliers の仕入元が public.suppliers に未登録 | migration失敗（マッピング漏れ） | 前提条件: migration実行前にアプリ/CSVで全件登録。migrationにNULLチェックあり |
| supplier_code 形式の不一致 | JOIN失敗 | マッピングSQL: `'SP-' \|\| LPAD(SUBSTRING(ts.code FROM 3), 5, '0')` で変換 |
| line_name が NULL の仕入元 | LINE照合対象外 | `WHERE line_name IS NOT NULL` で除外。画面から登録可能 |

## 外部・過去事例の参照

商品マスタ（`public.products`）の中央化（ADR-090）で同じパターンを実施済み:
- テナント個別テーブル → public テーブルへの統合
- migration は構造のみ、値はアプリ/CSVで管理
- CIガードで migration からの値操作を禁止

本設計は同じパターンを仕入元マスタに適用する。

## 維持の仕組み

- 守り手: `.github/workflows/migration-guard.yml`（フェーズ5で public.suppliers を保護対象に追加）
- 対象: public.suppliers への migration からのデータ操作（INSERT/UPDATE/DELETE）が入り込むと、アプリ/CSVとの値の競合が発生する
- フェーズ5までの暫定: 人手で守る（PRレビューで migration に値操作がないことを確認）
