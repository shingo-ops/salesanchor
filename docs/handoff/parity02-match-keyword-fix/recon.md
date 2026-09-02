# recon: PARITY-02 match_keyword GAS準拠修正

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "parity02\|match_keyword\|tcg" docs/adr/
```

ヒット: `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`  
対象 ADR: **ADR-154**（TCG PARITY-02 GAS→Python移植）。

---

## 2. 問題箇所の特定

### 修正対象

`backend/app/services/tcg_analyzer_svc.py:307-310`

```python
# 修正前 (L307-310)
# 検索語未登録の商品は候補にしない（GAS: matchPid_ !srchStr → return）
if not search_kw_str:
    return True, "(既定)"   ← GAS: matchPid_ が return（スキップ）するのに
                               Python は全マッチを返していた
```

### GAS 対照

`investigate2.gs:10048 matchPid_`:
```javascript
if (!pid || !srchStr) return;  ← キーワード未登録はスキップ
```

### 影響調査

- `match_keyword` の呼び出し元: `tcg_analyzer_svc.py:373`, `tcg_analyzer_svc.py:586`, `tcg_analyzer_svc.py:597`
- `match_keyword` は `__all__` にエクスポート: `tcg_analyzer_svc.py:1118`
- テスト: `backend/tests/test_tcg_keyword_matching.py`

---

## 3. Phase E 測定での発見

Phase E 測定（2026-09-03）で MULTI 1340件の根本原因として発見。

PM0146（スタートデッキGenerations・キーワード未登録）が `return True, "(既定)"` の挙動で全1626件に全マッチ → MULTI 94%の原因。

修正後シミュレーション（`backend/tcg_migration/scripts/dry_run_parity02_phase_e.py`）:
- pid_resolved: 286件 → 1294件（+1008）
- MULTI: 1340件 → 46件（-1294）

---

## 4. 触らないファイル

- `backend/app/services/tcg_unit_recovery_svc.py`（match_keyword 使用なし）
- `migrations/`（DB変更なし）
- `docs/adr/`（ADR-154は既存・本修正はその実装の一部）
