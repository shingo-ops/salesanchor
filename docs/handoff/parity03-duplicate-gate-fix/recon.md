# PARITY-03 重複判定 GAS 準拠修正 + 確認導線追加 — recon.md

作成日: 2026-09-04  
ブランチ: release/duplicate-gate-fix

---

## 既存 ADR 検索結果

`git grep -i "parity\|product.master\|duplicate" docs/adr/` → ADR-154-tcg-parity02-gas-python-migration  
ADR-154 方針（GAS→Python 段階移植）の延長実施。PARITY-03 固有 ADR は未起案（軽量修正のため起案不要と判断）。

---

## 問題の所在

### 【B】重複判定が GAS より緩い

`backend/app/services/tcg_product_master_svc.py:163` — `_build_duplicate_candidates`

旧ロジック（変更前）:
```
exact_title OR same_cls（work_id AND manufacturer_id AND product_category_id）
```

GAS 実装（~/db01_work/ProductMasterV2Registration.js lines 77-88、リポジトリ外）:
```
exactTitle OR (sameClassification AND (sameMark OR sameSearch))
```

差異: Python は `same_cls` のみで候補になるため、同一作品 × 同一メーカー × 同一カテゴリの全商品が候補になる（例: One Piece × Bandai × BOX の全弾）。

### 【A】確認導線が存在しない（ハードブロック）

`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:249` — 登録ボタン disabled 条件:
```tsx
disabled={!required || candidates.length > 0 || status === 'saving'}
```

`backend/app/services/tcg_product_master_svc.py:314` — 登録関数の早期 return:
```python
if dup_result["candidates"]:
    return {"ok": False, "code": "DUPLICATE_CANDIDATE", ...}
```

GAS はソフトブロック（`ok:false` を返すだけでユーザーが再送信可能）。Python はハードブロック（UI から先に進めない）。

---

## 変更ファイル一覧（file:line）

| ファイル | 変更種別 | 主要変更箇所 |
|---|---|---|
| `backend/app/services/tcg_product_master_svc.py:163` | 修正 | `_build_duplicate_candidates` GAS準拠ロジック |
| `backend/app/services/tcg_product_master_svc.py:195` | 修正 | `check_duplicates` SQL に mark/search_keywords 追加 |
| `backend/app/services/tcg_product_master_svc.py:281` | 修正 | `create_product` に `force: bool = False` 追加 |
| `backend/app/routers/tcg_product_master.py:72` | 修正 | `DuplicateCheckRequest` に `mark` 追加 |
| `backend/app/routers/tcg_product_master.py:89` | 修正 | `CreateProductRequest` に `force` 追加 |
| `backend/tests/test_tcg_product_master.py:426` | 追加 | force/GAS ロジック単体テスト 9件 |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:101` | 修正 | `confirmed` state 追加 |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:230` | 修正 | 確認チェックボックス + disabled 条件変更 |

---

## 触らない範囲

- `migrations/` — DB スキーマ変更なし（mark 列は #3246 で追加済み）
- `backend/app/routers/tcg_analysis_review.py` — 分析レビュー API は別ルーター
- `frontend/src/features/tcg-analysis-review/` 内の他ファイル
