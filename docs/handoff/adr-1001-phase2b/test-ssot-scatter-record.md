# Phase 2b テスト側 SSOT 分散箇所の記録

Phase 2b（tcg_products → public.products 統一）で発見された、テストコード内の分散箇所の記録。
本番コードは1箇所の修正で済むが、テスト側は複数ファイル・複数関数に同じ前提が散在していた。

作成: 2026-09-14（CI赤の原因調査中に記録）

---

## 問題の構造

public.products を SSOT にすると、以下の前提が変わる：

| 旧前提 | 新前提 | 影響 |
|--------|--------|------|
| 商品はスキーマローカル tcg_products に存在 | 商品は public.products に存在 | FK参照先の変更が必要 |
| keyword FK → {schema}.tcg_products(id) | keyword FK → public.products(tcg_uuid) | `_rewire_keyword_fks()` 呼出が必須 |
| カラム名: code, japanese_title, english_title | カラム名: product_code, name, name_en | dict アクセスキーの変更 |
| 各テナントの商品は他テナントから不可視 | public.products は全テナント共有 | 件数アサーションの変更 |
| partial unique index (WHERE NOT NULL) でOK | FK参照には完全 unique 制約が必要 | インデックス定義の変更 |

---

## 分散箇所一覧（CI赤から発見）

### A. FK rewire 漏れ（_rewire_keyword_fks 未呼出）

keyword テーブルの FK が旧 tcg_products を指したまま。

| ファイル | 行 | 関数/テスト | スキーマ |
|---------|-----|-----------|---------|
| test_tcg_work_matching_integration.py | 695 | `seed_guard_dictionary()` | 引数 schema |
| test_tcg_work_matching_integration.py | 455 | `test_condition_note_18_items...` | tenant_004 |
| test_tcg_work_matching_integration.py | 1082 | `test_cardset_duplicate_target...` | tenant_004 |
| test_tcg_work_matching_integration.py | 1344 | `test_bundle_collision_and_late_failure...` | tenant_004 |

修正パターン: keyword INSERT の前に `cursor.execute(_rewire_keyword_fks(schema))` を追加。
ただし `_PUBLIC_PRODUCTS_DDL` も事前に実行済みであること（public.products が存在する必要あり）。

### B. カラム名の旧名参照

| ファイル | 行 | コード | 修正 |
|---------|-----|-------|------|
| tcg_product_roundtrip_svc.py (本番) | 176 | `s["product"]["code"]` | → `s["product"]["product_code"]` |
| test_tcg_product_detail_pg.py | 184 | `audit["old_values"]["product"]["japanese_title"]` | → `["product"]["name"]` |
| test_tcg_product_detail_pg.py | 185 | `audit["new_values"]["product"]["japanese_title"]` | → `["product"]["name"]` |

### C. 件数アサーション（public.products 共有による差分）

| ファイル | 行 | 旧期待値 | 新期待値 | 理由 |
|---------|-----|---------|---------|------|
| test_tcg_product_roundtrip_pg.py | 86 | count+1 | count+2 | SENTINEL が public.products に可視 |
| test_tcg_product_roundtrip_pg.py | 95 | count | count+1 | 同上 |
| test_tcg_product_roundtrip_pg.py | 97 | count | count+1 | 同上 |
| test_tcg_work_matching_integration.py | 202 | 3 | 要確認 | seed_products の商品数 |
| test_tcg_work_matching_integration.py | 246 | 3 | 4 | pid_resolved カウント |

### D. fixture DDL の不足

| ファイル | 行 | 内容 | 修正 |
|---------|-----|------|------|
| fixtures/public_products_test.sql | 37 | 部分ユニークインデックス | WHERE 句除去 → 済 |
| fixtures/public_products_test.sql | - | required_output_value 列不在 | 列追加 → 済 |

### E. テスト間の product_code 衝突

| ファイル | 行 | 旧コード | 新コード | 理由 |
|---------|-----|---------|---------|------|
| test_tcg_product_roundtrip_pg.py | 43 | SENTINEL | RTSENT | atomic_pg の SENTINEL と衝突 → 済 |

### F. 並列実行時の pg_type race condition

| ファイル | 行 | 状態 |
|---------|-----|------|
| test_tcg_distribution_pg.py | 28-33 | advisory lock 追加 → 済 |
| test_tcg_product_list_pg.py | 32 | 未対応（同じ _PUBLIC_PRODUCTS_DDL.split パターン） |

---

## 教訓

1. **テストの商品参照も SSOT に従う**: テスト固有の seed 関数が多数あり、それぞれが独自に INSERT + FK を前提としていた。本番コードの参照先を変えるだけではテストが追従しない。
2. **shared public テーブルの可視性**: スキーマローカルからパブリックに移行すると、テスト間の分離が弱まる。件数アサーション・ユニーク制約・SENTINEL パターンすべてに影響。
3. **FK rewire の適用範囲**: `_rewire_keyword_fks()` は tenant_901 (SCHEMA定数) にのみ適用されていたが、tenant_004 等の他スキーマでも必要だった。
4. **Phase 2c（DROP tcg_products）の前提**: FK rewire 済みスキーマの網羅確認が必要。未 rewire のスキーマがあると DROP 時に FK エラー。

---

## Phase 2c への引き継ぎ

DROP tcg_products を実行するためには、以下が前提：
- 全テナントスキーマの keyword FK が public.products(tcg_uuid) を参照していること
- tcg_products への参照が本番コード・テストコードともにゼロであること
- テスト fixture の seed 関数すべてが public.products 前提であること
