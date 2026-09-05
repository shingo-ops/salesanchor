# recon: tcg-import-sender-split

## 対象ブランチ
`release/tcg-sender-split`

## 調査日
2026-09-05

---

## 1. 変更対象ファイル

| ファイル | 役割 |
|---|---|
| `backend/app/services/tcg_line_import_svc.py` | LINE輸出テキスト取り込みサービス |
| `backend/tests/test_tcg_line_import.py` | 上記のユニットテスト |

---

## 2. SUP-R1: tcg_suppliers の出どころと照合仕様

### 2-1. INSERT 経路

| 経路 | ファイル | 実行タイミング |
|---|---|---|
| ローカルDB → 本番DB | `backend/tcg_migration/scripts/write_mirror_once.py` | 手動（PO実行）。`ON CONFLICT DO NOTHING`。45行 |

`tcg_suppliers` への自動INSERT経路は存在しない（アプリ側からは SELECT のみ）。

### 2-2. `tcg_suppliers` カラム構成（DDL調査）

```
code       TEXT PRIMARY KEY
name       TEXT UNIQUE NOT NULL   ← LINE 表示名と照合するキー
is_active  BOOLEAN DEFAULT TRUE
```

`supplier_aliases` テーブルは存在しない（`condition_aliases` / `unit_aliases` はある）。

---

## 3. GAS vs Python 比較表（SUP-R1）

| 項目 | GAS（Latest24LineImport.js） | Python OLD | Python NEW（本PR） |
|---|---|---|---|
| 送信者名切り出し関数 | `latest24SplitHeader_(tail, masterNames)` | `rest.split(" ", 1)` | `_split_sender(tail, sorted_names)` |
| マスタ一致判定 | `tail === name` → exact / `tail.startsWith(name + ' ')` → prefix | なし（split のみ） | `tail == name` → exact / `tail.startswith(name + " ")` → prefix |
| フォールバック | `tail.split(' ')[0]` | `rest.split(" ", 1)[0]` | `tail.split(" ", 1)[0]` |
| サプライヤー解決 | `byName[displayName]`（辞書完全一致） | `dn.startswith(sup["name"])`（前方一致・最長優先） | `name_to_supplier.get(dn)`（辞書完全一致） |
| マスタ取得タイミング | parse内（ラムダ引数） | parse後 | parse前（`supplier_names` を引数で渡す） |
| 別名（alias）対応 | なし | なし | なし（テーブル不在） |
| システムイベント除外 | `!m.isSystemEvent`（parse時に判定） | `is_system_event` フラグで除外 | 同左 |
| システムイベント検出文字列 | `displayName + firstBody`（結合して正規表現） | `body` のみ | `display_name + " " + body`（GASに合わせた結合） |

### "提供者名" の定義

`tcg_suppliers.name` = LINE グループ内の**表示名**（LINE display name）。
本名・正式社名ではない。GAS `parseLatest24LineExport` が `displayName` として取り出した値をそのままキーとして使っている。

---

## 4. 変更前後の差分サマリ

### `parse_line_export`

- 引数に `supplier_names: list[str] | None = None` を追加
- 時刻行パース: `_split_sender(rest, sorted_names)` を使用（旧: `rest.split(" ", 1)`）
- システムイベント検出: `display_name + " " + body` を正規表現対象に変更

### `resolve_suppliers`

- 旧: `sorted(db_suppliers, key=len, reverse=True)` + `dn.startswith(sup["name"])`
- 新: `name_to_supplier = {s["name"]: s for s in db_suppliers}` + `name_to_supplier.get(dn)`

### `import_line_export`

- tcg_suppliers の SELECT を parse 前に移動（旧: parse後）
- `supplier_names` を `parse_line_export` に渡す

---

## 5. テスト変更

| テスト名 | 変更種別 | 理由 |
|---|---|---|
| `test_resolve_prefix_match` | 既存テスト更新 | 旧: prefix一致で解決 → 新: exact一致のみ解決（unresolved扱いに） |
| `test_split_sender_multiword_master_name` | 新規追加 | GASの複数語マスタ名が正しく切り出されることを確認 |
| `test_split_sender_unresolved_falls_back_to_first_space` | 新規追加 | マスタ未登録はfirst-spaceフォールバックになることを確認 |
| `test_split_sender_no_prefix_false_match` | 新規追加 | 最長一致優先（false prefix防止）を確認 |

---

## 6. 関連 ADR

- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`（GAS→Python移植方針）
- `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`（テナントスキーマプレフィックス）
