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

### G. seed 関数ごとの FK rewire 漏れ（第2回調査で追加発見）

`_rewire_keyword_fks()` を呼んでいる seed 関数と呼んでいない seed 関数の一覧。
keyword INSERT を含む seed 関数は全て rewire 必須だが、一部が漏れていた。

| 関数 | ファイル:行 | keyword INSERT | rewire 呼出 | 影響テスト数 |
|------|------------|---------------|------------|------------|
| `seed_guard_dictionary()` | test_tcg_work_matching_integration.py:683-700 | あり (699-700) | **あり (687)** | ✓ 修正済 |
| `seed_cardset_dictionary()` | test_tcg_work_matching_integration.py:1000-1020 | あり (1019-1020) | **なし** | **7テスト** FK違反 |
| `seed_bundle_dictionary()` | test_tcg_work_matching_integration.py:1230-1245 | あり (1244-1245) | **なし** | **18テスト** FK違反 |
| `seed_products()` | test_tcg_work_matching_integration.py:127-147 | あり (141-143) | migrate() 経由で済 | ✓ OK |
| `seed_condition_note()` | test_tcg_work_matching_integration.py:309-319 | なし | N/A | ✓ OK |

修正方針: `seed_cardset_dictionary()` と `seed_bundle_dictionary()` の keyword INSERT 前に
`cursor.execute(_PUBLIC_PRODUCTS_DDL)` + `cursor.execute(_rewire_keyword_fks(schema))` を追加。

### H. Mock テストの snapshot 構造乖離

test_tcg_product_roundtrip.py（SQLite 非依存の単体テスト）の mock snapshot が
public.products の実構造と乖離していた。

| 項目 | mock (旧) | public.products (実) | 影響 |
|------|----------|---------------------|------|
| `product.tcg_uuid` | **欠落** | `gen_random_uuid()` で生成 | roundtrip_svc:211 `plan["id"] = snapshot["product"]["tcg_uuid"]` で **KeyError** |
| `product.id` | UUID 文字列 | SERIAL INT | revision hash が実際と異なる（テスト内では一貫するため動作には影響せず） |

影響: 7テスト（test_date_binding×2, test_export_and_unchanged, test_invalid_updates×4）

### I. SENTINEL の可視性問題（roundtrip_pg テスト群）

atomic_pg fixture が作る SENTINEL 商品は public.products に入るため、
roundtrip_pg テスト群の全操作に混入する。

| 分散パターン | ファイル:関数 | 影響 |
|------------|-------------|------|
| `observe()` フィルタなし | test_tcg_product_roundtrip_pg.py:21-33 | SENTINEL 含む全商品を取得 → snapshot 比較ズレ |
| `export_csv(db)` フィルタなし | 各テスト関数内 | SENTINEL が CSV に含まれ件数・操作対象がズレ |
| `edit(original, changes, single=True)` | テスト内 | product_code DESC ソートで SENTINEL が最上位 → 意図しない商品を編集 |
| direct SQL `UPDATE public.products SET ...` WHERE句なし | test_stale:228 | SENTINEL も更新される → teardown assertion 違反 |
| `for row in records[1:]` 全行編集 | test_atomic:305-308 | SENTINEL 行も編集される → 件数アサーション不一致 |

影響: 3テスト FAIL（exclude_keywords KeyError, stale[code] assert False, commit_after 状態不一致）
      + 8テスト ERROR（teardown sentinel_snapshot 不一致）

修正方針: export_csv 呼出時に `query="商品"` で seeded products のみに絞り、
direct SQL UPDATE に `WHERE product_code LIKE 'RT%'` を追加。

### J. 非FK・非mock の追加失敗（第2回調査で発見、原因調査中）

seed_guard_dictionary() の FK rewire 済みテストでも、FK 以外の理由で失敗するケースがある。

| テスト | エラー | 想定原因 |
|-------|--------|---------|
| test_dictionary_idempotent_and_identity_guard | keyword 5件(期待6件、'コロ'欠落) | seed_products の除外キーワード処理変更の可能性 |
| test_normal_limited_memo_scope | pid_resolved 4==3 | public.products の商品が追加で可視 |
| test_false_positive_guards_exact_changes | UniqueViolation uq_public_products_code | 商品コード衝突（seed重複） |
| test_false_positive_guards_duplicate×3 | Regex pattern not match | 出力形式の変化（カラム名変更影響） |
| test_false_positive_guards_lock_timeout | PM0230 identity mismatch | identity check のカラム名変更影響 |

---

## 教訓

1. **テストの商品参照も SSOT に従う**: テスト固有の seed 関数が多数あり、それぞれが独自に INSERT + FK を前提としていた。本番コードの参照先を変えるだけではテストが追従しない。
2. **shared public テーブルの可視性**: スキーマローカルからパブリックに移行すると、テスト間の分離が弱まる。件数アサーション・ユニーク制約・SENTINEL パターンすべてに影響。
3. **FK rewire の適用範囲**: `_rewire_keyword_fks()` は tenant_901 (SCHEMA定数) にのみ適用されていたが、tenant_004 等の他スキーマでも必要だった。さらに seed 関数レベルでも rewire 漏れがあり、`seed_cardset_dictionary()` と `seed_bundle_dictionary()` の2関数が未対応だった。
4. **Phase 2c（DROP tcg_products）の前提**: FK rewire 済みスキーマの網羅確認が必要。未 rewire のスキーマがあると DROP 時に FK エラー。
5. **SENTINEL パターンの脆弱性**: canary 商品が public.products に入ると、フィルタなしの CSV 操作・SQL UPDATE で意図せず変更される。テストの操作対象を明示的にフィルタするか、SENTINEL を操作から除外する仕組みが必要。
6. **mock と実構造の同期**: mock snapshot が本番テーブル構造と乖離すると、列追加（tcg_uuid）や列名変更（code→product_code）で一斉に壊れる。mock の形状を実テーブルの DDL から自動生成する仕組みがあればリスク低減。

---

## Phase 2c への引き継ぎ

DROP tcg_products を実行するためには、以下が前提：
- 全テナントスキーマの keyword FK が public.products(tcg_uuid) を参照していること
- tcg_products への参照が本番コード・テストコードともにゼロであること
- テスト fixture の seed 関数すべてが public.products 前提であること
