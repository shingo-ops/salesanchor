# recon: TCG 状態解決エンジン v2 不一致修正 (PR #3190)

**PR #3188** (name-first-v2-cond-r4) のdry-run検証で判明した2件の不一致を修正する。

## 関連 ADR

- ADR-090: products アーキテクチャ統一（TCG データ構造定義）

## 現状把握

### 不一致原因 A: R5:パック既定 ステップ未実装

| 調査対象 | 観察内容 | 引用 |
|---|---|---|
| GAS R5 実装箇所 | `applyPackConditionDefault` — unit=パック系(UN0003) かつ R4b=FLAG_SINGLE の行を Searched pack に変換 | `sqr01_pullback2/AnalysisV2PackCondition.gs:66` |
| GAS basisDist実測 | R5=60件（clasp run reportConditionCanonicalDistribution 実測値） | - |
| v2 before 分布 | FLAG_SINGLE=829件（GAS=764件、差+65件） | - |
| 修正箇所 | `resolve_condition_v2` R4bフォールバック後に `kubun == "パック系"` 判定を追加 | `backend/app/services/tcg_analyzer_svc.py:572` |

### 不一致原因 B: ORDER BY code ASC タイブレーカー欠落

| 調査対象 | 観察内容 | 引用 |
|---|---|---|
| GAS R3 判定順 | SHURI キーワード群 → PERI キーワード群（CN0005 → CN0006 の順） | `sqr01_pullback2/investigate2.gs:9705` |
| DB ストレージ順 | CN0006 が CN0005 より先に格納されていた（priority 同値・app_kubun 長 同値） | - |
| v2 before 分布 | No shrink box=68件(-3)、Opened box=8件(+3) | - |
| 修正箇所 | `load_condition_entries` ORDER BY に `c.code ASC` 追加 | `backend/app/services/tcg_analyzer_svc.py:437` |

### v1 compat エンジン実装確認

v1 は `gemini_all.json` の `sys_v.get("condition")` を直接コピーしていた（GAS出力=R5適用済みを引き写し）。
Python 側に R5 相当ロジックは存在しなかった。

- 確認箇所: `git show cd45c309:backend/tcg_migration/compat_engine.py`
