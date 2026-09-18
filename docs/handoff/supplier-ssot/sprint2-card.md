# Sprint 2 実装カード — コード配線変更（12ファイル）

> 親: [design.md](./design.md) §コード変更
> 前提: Sprint 1 migration 適用済み（supplier_channels.supplier_id = INTEGER → public.suppliers.id）

## 変更の目的

LINE取り込みのコード12ファイルが参照先を `tcg_suppliers` → `public.suppliers` に切り替え、
PC版・Android版の照合ロジックを `resolve_suppliers(line_name)` に統一する。

---

## パターン1: マスタ取得SQL（3箇所）

### 1a. `backend/app/services/tcg_line_import_svc.py` L547-551

```python
# 変更前
suppliers_rows = await db.execute(
    text(f"SELECT code, name FROM {TCG_SCHEMA}.tcg_suppliers WHERE is_active = TRUE")
)
db_suppliers = [{"code": r[0], "name": r[1]} for r in suppliers_rows.fetchall()]
supplier_names = sorted((s["name"] for s in db_suppliers), key=len, reverse=True)

# 変更後
suppliers_rows = await db.execute(
    text("SELECT supplier_code, line_name FROM public.suppliers WHERE is_active = TRUE AND line_name IS NOT NULL")
)
db_suppliers = [{"code": r[0], "line_name": r[1]} for r in suppliers_rows.fetchall()]
supplier_names = sorted((s["line_name"] for s in db_suppliers), key=len, reverse=True)
```

### 1b. `backend/app/routers/tcg_line_import.py` L604-608

```python
# 変更前
suppliers_rows = await db.execute(
    text(f"SELECT code, name FROM {TCG_SCHEMA}.tcg_suppliers WHERE is_active = TRUE")
)
db_suppliers = [{"code": r[0], "name": r[1]} for r in suppliers_rows.fetchall()]

# 変更後
suppliers_rows = await db.execute(
    text("SELECT supplier_code, line_name FROM public.suppliers WHERE is_active = TRUE AND line_name IS NOT NULL")
)
db_suppliers = [{"code": r[0], "line_name": r[1]} for r in suppliers_rows.fetchall()]
```

### 1c. `backend/app/services/line_source_names.py` L103-104

```python
# 変更前
await db.execute(text(f'LOCK TABLE {TCG_SCHEMA}.tcg_suppliers IN SHARE MODE'))
suppliers = (await db.execute(text(f'SELECT id,code,name FROM {TCG_SCHEMA}.tcg_suppliers WHERE is_active=TRUE'))).mappings().all()

# 変更後
await db.execute(text('LOCK TABLE public.suppliers IN SHARE MODE'))
suppliers = (await db.execute(text('SELECT id, supplier_code AS code, line_name AS name FROM public.suppliers WHERE is_active=TRUE AND line_name IS NOT NULL'))).mappings().all()
```

注意: この関数（`link_pending`）はメインフローから外れるが、import時に呼ばれる可能性があるため配線は更新する。AS句でキー名を維持し、呼び出し元への影響を最小化。

---

## パターン2: JOIN変更（14箇所・8ファイル）

共通変換:
```python
# 変更前
JOIN {TCG_SCHEMA}.tcg_suppliers ts ON ts.id = sc.supplier_id
# 変更後
JOIN public.suppliers ps ON ps.id = sc.supplier_id
```

エイリアスは `ts` → `ps` に変更。SELECT句で `ts.code` → `ps.supplier_code`、`ts.name` → `ps.name` に変更。

| ファイル | 行 | 備考 |
|---------|-----|------|
| `tcg_line_import_svc.py` | 351 | WHERE `ts.code = :code` → `ps.supplier_code = :code` |
| `tcg_diagnostics_svc.py` | 46 | 単独SELECT: `FROM {TCG_SCHEMA}.tcg_suppliers` → `FROM public.suppliers` + `code` → `supplier_code` |
| `tcg_diagnostics_svc.py` | 51 | 単独SELECT: 同上 + `name` はビジネス名なのでそのまま |
| `tcg_diagnostics_svc.py` | 59 | LEFT JOIN + `ts.code` → `ps.supplier_code`、`ts.name` → `ps.name` |
| `tcg_distribution_svc.py` | 234 | LEFT JOIN |
| `tcg_import_progress.py` | 160 | LEFT JOIN |
| `tcg_import_progress.py` | 183 | LEFT JOIN |
| `tcg_analysis_review_svc.py` | 39 | LEFT JOIN |
| `tcg_parallel_report_svc.py` | 186 | JOIN |
| `tcg_sold_out_results_svc.py` | 48 | LEFT JOIN |
| `tcg_supplier_quality_svc.py` | 43 | LEFT JOIN |
| `tcg_supplier_quality_svc.py` | 81 | LEFT JOIN |
| `tcg_mirror.py` | 173 | LEFT JOIN + `s` → `ps` |
| `tcg_mirror.py` | 193 | LEFT JOIN + `s` → `ps` + SELECT `s.code` → `ps.supplier_code`、`s.name` → `ps.name` |

### tcg_mirror.py L223 特殊ケース

```python
# 変更前
'tcg_suppliers', 'supplier_channels', ...

# 変更後（tcg_suppliers をリストから除去。public.suppliers は別スキーマなので不要）
'supplier_channels', ...
```

---

## パターン3: INSERT/UPDATE/採番（`tcg_line_import.py`）

### 3a. assign アクション（L448-478）

```python
# 変更前
SELECT id, name FROM {TCG_SCHEMA}.tcg_suppliers WHERE code = :code AND is_active = TRUE
SELECT id FROM {TCG_SCHEMA}.tcg_suppliers WHERE name = :name AND id != :self_id AND is_active = TRUE
UPDATE {TCG_SCHEMA}.tcg_suppliers SET name = :name WHERE id = :id

# 変更後
SELECT id, name, line_name FROM public.suppliers WHERE supplier_code = :code AND is_active = TRUE
SELECT id FROM public.suppliers WHERE line_name = :name AND id != :self_id AND is_active = TRUE
UPDATE public.suppliers SET line_name = :name WHERE id = :id
```

注意: assign はLINE表示名を設定する操作。`name`（ビジネス名）ではなく `line_name` を更新。

### 3b. create アクション（L486-513）

```python
# 変更前
max_code_row = await db.execute(text(f"SELECT MAX(code) FROM {TCG_SCHEMA}.tcg_suppliers"))
max_code = max_code_row.scalar()
# ... 採番ロジック ...
new_supplier_id = uuid4()
await db.execute(text(f"""
    INSERT INTO {TCG_SCHEMA}.tcg_suppliers (id, code, name, is_active, created_at)
    VALUES (:id, :code, :name, TRUE, now())
"""), {"id": str(new_supplier_id), "code": new_code, "name": body.display_name})

# 変更後（super_admin_suppliers.py L121-136 の既存パターン踏襲）
result = await db.execute(text("""
    INSERT INTO public.suppliers (name, line_name, supplier_type, is_active)
    VALUES (:name, :line_name, 'corporate', TRUE)
    RETURNING id
"""), {"name": body.display_name, "line_name": body.display_name})
new_id = result.scalar_one()
new_code = f"SP-{new_id:05d}"
await db.execute(text("""
    UPDATE public.suppliers SET supplier_code = :code WHERE id = :id AND supplier_code IS NULL
"""), {"code": new_code, "id": new_id})
```

### 3c. supplier_channels INSERT（L506付近、create直後）

```python
# 変更前
{"id": str(uuid4()), "supplier_id": str(new_supplier_id)}  # UUID

# 変更後
{"id": str(uuid4()), "supplier_id": new_id}  # INTEGER
```

---

## パターン4: 正規表現（`line_import_admin.py` L43）

```python
# 変更前
r'SP[0-9]{4,8}'

# 変更後
r'SP-[0-9]{5}'
```

---

## パターン5: Android分岐の統一

### 5a. `tcg_line_import_svc.py` L570-574

```python
# 変更前
if source_format == "android":
    messages = [{**m, '_line_source_format': line_source_names.MARKER} for m in messages]
    resolved_msgs, unresolved = line_source_names.resolve_android(messages, db_suppliers, await line_source_names.load_aliases(db))
else:
    resolved_msgs, unresolved = resolve_suppliers(messages, db_suppliers)

# 変更後
resolved_msgs, unresolved = resolve_suppliers(messages, db_suppliers)
```

### 5b. `tcg_line_import.py` L610-612

```python
# 変更前
if line_source_names.is_android(messages):
    resolved_msgs, still_unresolved = line_source_names.resolve_android(messages, db_suppliers, await line_source_names.load_aliases(db))
else:
    resolved_msgs, still_unresolved = resolve_suppliers(messages, db_suppliers)

# 変更後
resolved_msgs, still_unresolved = resolve_suppliers(messages, db_suppliers)
```

---

## パターン6: resolve_suppliers 照合キー変更

### `tcg_line_import_svc.py` L238, L245-247

```python
# 変更前
name_to_supplier: dict[str, dict] = {s["name"]: s for s in db_suppliers}
# ...
sup = name_to_supplier.get(dn)
if sup:
    sp_code = sup["code"]
    canonical_name = sup["name"]

# 変更後
name_to_supplier: dict[str, dict] = {s["line_name"]: s for s in db_suppliers}
# ...
sup = name_to_supplier.get(dn)
if sup:
    sp_code = sup["code"]
    canonical_name = sup["line_name"]
```

---

## パターン7: LOCK TABLE（2箇所）

### `line_source_names.py` L103
```python
# 変更前
LOCK TABLE {TCG_SCHEMA}.tcg_suppliers IN SHARE MODE
# 変更後
LOCK TABLE public.suppliers IN SHARE MODE
```

### `line_import_admin.py` L147-148
```python
# 変更前
LOCK TABLE {TCG_SCHEMA}.tcg_suppliers IN SHARE ROW EXCLUSIVE MODE
SELECT count(*) FROM {TCG_SCHEMA}.tcg_suppliers WHERE name=:name
# 変更後
LOCK TABLE public.suppliers IN SHARE ROW EXCLUSIVE MODE
SELECT count(*) FROM public.suppliers WHERE line_name=:name AND is_active=TRUE
```

---

## パターン8: line_source_names.py 残り参照

### L29（load_aliases）
```python
# 変更前
LEFT JOIN {TCG_SCHEMA}.tcg_suppliers s ON s.id=a.supplier_id AND s.is_active=TRUE

# 変更後（line_supplier_source_names は Sprint 1 で DROP 済み）
# load_aliases 関数全体を空リスト返却に変更（テーブルが存在しない）
async def load_aliases(db) -> list:
    return []
```

### L113（link_pending内のJOIN）
```python
# 変更前
JOIN {TCG_SCHEMA}.tcg_suppliers s ON s.id=sc.supplier_id
# 変更後
JOIN public.suppliers ps ON ps.id=sc.supplier_id
```

---

## パターン9: コメント・docstring 更新

| ファイル | 行 | 内容 |
|---------|-----|------|
| `tcg_line_import_svc.py` | 73 | `tcg_suppliers.name` → `public.suppliers.line_name` |
| `tcg_line_import_svc.py` | 132 | 同上 |
| `tcg_line_import_svc.py` | 230 | docstring `tcg_suppliers` → `public.suppliers` |
| `tcg_line_import_svc.py` | 490 | コメント `tcg_suppliers` → `public.suppliers` |
| `tcg_line_import.py` | 406 | コメント `tcg_suppliers` → `public.suppliers` |
| `tcg_supplier_quality_svc.py` | 71 | docstring `tcg_suppliers.code` → `public.suppliers.supplier_code` |

---

## 触らないもの

| 対象 | 理由 |
|------|------|
| `tcg_line_android_parser.py` | パーサー。DB参照なし。正常動作中 |
| `super_admin_suppliers.py` | 既に public.suppliers + line_name 対応済み |
| `public.suppliers.name` | ビジネス名。変更なし |
| `source_messages` 以下のFK連鎖 | supplier_channels.id（PK）は変わらない |
| `tcg_suppliers` テーブル | テナント独自用として残す |
| migrations/ | Sprint 1 で完了済み |

---

## 受入条件

| # | 基準 | 検証方法 |
|---|------|---------|
| 1 | `grep -rn "tcg_suppliers" backend/app/` が 0件（コメント除く実行コード） | grep |
| 2 | PC版: `_split_sender` が `line_name` リストで前方一致する | テスト |
| 3 | Android版: `resolve_suppliers` で `line_name` に完全一致する | テスト |
| 4 | Android分岐（`resolve_android`呼び出し）が消えている | コード確認 |
| 5 | 採番が `SP-{id:05d}` 形式 | コード確認 |
| 6 | 既存テスト全パス | CI |
