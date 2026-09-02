# design: PARITY-02 match_keyword GAS準拠修正

> 作成: 2026-09-03 / 作業者: Hikky-dev

**対象ADR**: ADR-154  
**recon**: docs/handoff/parity02-match-keyword-fix/recon.md

---

## 外部・過去事例の参照と我々への応用

- 事例1: ADR-154（TCG PARITY-02 Phase D 統合）→ 応用: Phase E dry-run で GAS/Python 差異を数値化し、MULTI 1340件→46件の改善を確認してから実装するパターンを踏襲した。
- 事例2: GAS `matchPid_` の `if (!pid || !srchStr) return` ガード → 応用: Python `match_keyword` でも「キーワード未登録の商品は候補にしない」を 1 行で実現。既存テストを更新し回帰防止。

---

## 維持の仕組み

- `test_tcg_keyword_matching.py::test_empty_search_kw_returns_no_match` で `search_kw=[]` の挙動を恒久的に保護する。
- MIGRATION_LOG.md（`backend/tcg_migration/MIGRATION_LOG.md`）に「指摘済み差異追跡失敗の教訓」を追記し、差異発見時は即修正またはタスク登録を義務化した。
- ENGINE_VERSION は Phase D のまま変更しない（同一ロジック修正のため）。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| `match_keyword(text, [], [])` が `(False, None)` を返す | `test_empty_search_kw_returns_no_match` PASS |
| pid_resolved 件数が 1294件以上（Phase E dry-run と同等） | `analysis_results WHERE pid_resolved=TRUE` >= 1200 |
| MULTI 件数が 50件未満 | MULTI 判定行 < 50（phase_e 再測定） |
| 既存テスト全 PASS | `pytest backend/tests/test_tcg_keyword_matching.py -x -q` |

---

## 変更内容

### 修正箇所（1行）

`backend/app/services/tcg_analyzer_svc.py:308-310`:

```python
# 修正前
if not search_kw_str:
    return True, "(既定)"

# 修正後
if not search_kw_str:
    return False, None
```

### テスト更新

`backend/tests/test_tcg_keyword_matching.py`:
- `test_empty_search_kw_returns_all_match` → `test_empty_search_kw_returns_no_match`（旧挙動が誤りだったため）
- `test_empty_search_kw_with_text_returns_no_match` 追加（PM0146パターンの回帰テスト）

---

## 戻し方

```python
# tcg_analyzer_svc.py:308-310 を戻す
if not search_kw_str:
    return True, "(既定)"
```

対象ジョブで `analyze_extraction_job` を再実行。

---

## ADR 参照

対象 ADR: ADR-154（TCG PARITY-02 GAS→Python移植）  
本修正は ADR-154 の「GAS Phase 3 を Python で完全再現する」決定の一環として実施。
