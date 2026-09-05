# design: tcg-import-sender-split

## 目的

`parse_line_export` の送信者名切り出しロジックを GAS `latest24SplitHeader_` に合わせる。
`resolve_suppliers` の照合ロジックを GAS `byName[displayName]`（完全一致）に合わせる。

---

## 方針

ADR-154 準拠: GAS から Python への移植は「GAS の動作を正とし、差分があれば Python を GAS に寄せる」。
GAS にないロジック（正規化・曖昧一致・alias展開）はこの PR では追加しない。

---

## 設計詳細

### `_split_sender(tail, sorted_names)`

GAS `latest24SplitHeader_` の直訳。

```
1. sorted_names から順番に試す（長さ降順 = 最長優先）
   a. tail == name      → (name, "")
   b. tail.startswith(name + " ") → (name, tail[len(name)+1:])
2. いずれも一致しなければ tail.split(" ", 1) でfallback
```

`sorted_names` は `import_line_export` で `sorted(names, key=len, reverse=True)` 済みのリストを受け取る。
`parse_line_export` は `supplier_names` が None の場合 `[]` で動作（後方互換）。

### `resolve_suppliers` の完全一致化

```python
name_to_supplier = {s["name"]: s for s in db_suppliers}
sup = name_to_supplier.get(dn)
```

`_split_sender` によって display_name がマスタ名と一致する形で切り出されるため、
resolveフェーズでは辞書引き（O(1)、完全一致）で十分。
前方一致ループは不要になった（GAS と同等）。

### マスタ先行取得

`import_line_export` 内で tcg_suppliers SELECT を parse 前に実行し、
`supplier_names` を `parse_line_export` に渡す。
parse 内と resolve 内の2回 DB アクセスを 1 回に削減する副次効果もある。

---

## 基準と検証方法

| 基準 | 検証方法 |
|---|---|
| `_split_sender` が GAS の 3 分岐（exact / prefix+space / fallback）に一致する | `test_split_sender_*` 3テスト PASS |
| prefix のみ一致（例: "仕入元A（別支店）" vs "仕入元A"）は unresolved 扱い | `test_resolve_prefix_match` が `len(resolved)==0` で PASS |
| 既存テスト全件 PASS | `pytest backend/tests/test_tcg_line_import.py --no-cov -q` → 36 passed |

---

## 外部事例

GAS `latest24SplitHeader_` 実装（`Latest24LineImport.js`）を正典として採用。
Python 実装は GAS のロジックを一対一で再現する。

---

## 守り手

本 PR 以降、`_split_sender` / `resolve_suppliers` を変更する際は:
- GAS `Latest24LineImport.js` との差分を確認すること
- `test_split_sender_*` 3テストが RED にならないこと
