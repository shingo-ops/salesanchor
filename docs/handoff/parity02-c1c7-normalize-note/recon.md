# recon: PARITY-02 C-1+C-7+Status 正規化・注記・ステータス解決

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "normalization\|note_ja\|status_master\|resolveStatus" docs/adr/
```

ヒットなし。対象 ADR: なし（TCG パリティ移植は ADR 起案前）。

---

## 2. 既存実装の確認

### analyze_extraction_job の現状（本 PR 適用前）

`backend/app/services/tcg_analyzer_svc.py:922`
- `note_ja = NULL`（ハードコード）
- `status = 'active'`（ハードコード）
- `exclusion = NULL`（ハードコード）
- `raw_memo` を SELECT していない
- 正規化ルール未適用（装飾記号がついたままキーワード照合）

### 依存マスタ（A系 PR）

| マスタ | テーブル | PR | 状態 |
|---|---|---|---|
| 正規化ルール 135件 | `tenant_004.tcg_normalization_rules` | A-1 | 作成済み・未マージ |
| 注記マスタ 22件 | `tenant_004.tcg_note_master` | A-3 | 作成済み・未マージ |
| ステータスマスタ 9件 | `tenant_004.tcg_status_master` | A-4 | 作成済み・未マージ |

### 正規化ルール フィールド名（A-1 migration より）

| DB field 値 | 適用対象 raw フィールド |
|---|---|
| `PRODUCT_NAME` | raw_product_name |
| `CONDITION` | raw_state（状態解決前） |
| `STATUS` | raw_state（ステータス解決前） |
| `NOTE` | raw_memo（注記生成前） |
| `UNIT` | raw_unit（単位解決前） |
| `PRICE` | raw_price（本 PR 対象外） |
| `QUANTITY` | raw_quantity（本 PR 対象外） |
| `PRODUCT_NAME_MATCH` | GAS 側未実装につき除外（T-5） |
| `SCORING_COMPARE` | 本 PR 対象外 |

### ステータスマスタ effect / match_type

| effect | 説明 |
|---|---|
| `EXCLUDE` | マッチ → exclusion='excluded' 付与（在庫切れ系） |
| `OUTPUT` | マッチ → status=canonical（Pre-order 等） |
| `OUTPUT` + `DEFAULT` | フォールバック（In Stock） |

### extraction_items テーブル

`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql`
- `raw_memo TEXT` 列: 確認済み存在
- SELECT に追加するだけで OK（migration 不要）

---

## 3. 変更箇所

| ファイル | 変更内容 |
|---|---|
| `backend/app/services/tcg_analyzer_svc.py` | 新関数 7件追加・`analyze_extraction_job` 更新・ENGINE_VERSION 更新 |
| `backend/tcg_migration/MIGRATION_LOG.md` | C-1+C-7+Status 実施記録を追記 |

### 新規関数（tcg_analyzer_svc.py）

| 関数 | 目的 |
|---|---|
| `load_normalization_rules(session)` | tcg_normalization_rules ロード → `{field: [rules]}` |
| `apply_field_normalization(raw, rules)` | REMOVE/REPLACE/REGEX_REPLACE 適用 |
| `load_note_master(session)` | tcg_note_master ロード（graceful fallback） |
| `build_note_ja(raw_memo, entries)` | matchKeyword_ 再利用・label_ja カンマ連結 |
| `load_status_master(session)` | tcg_status_master ロード（graceful fallback） |
| `_match_status_pattern(text, pattern, match_type)` | LITERAL/REGEX/DEFAULT 照合 |
| `resolve_status_v2(raw_state, entries)` | EXCLUDE優先 → OUTPUT → DEFAULT |

---

## 4. 循環インポート / 依存関係

なし。追加関数はすべて `tcg_analyzer_svc.py` 内に完結。

---

## 5. 触らないファイル

- `backend/tcg_migration/scripts/` 配下（dry-run スクリプト）
- `backend/app/services/tcg_unit_recovery_svc.py`
- migrations/（C-1/C-7 は新テーブル不要・A-1/A-3/A-4 が担当）
