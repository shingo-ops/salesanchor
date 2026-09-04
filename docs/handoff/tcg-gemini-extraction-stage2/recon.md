# MIG-04 Stage 2: Gemini 抽出移植 — Recon

作成日: 2026-09-05  
ブランチ: `release/tcg-gemini-extraction-stage2`  
担当: Hikky-dev

---

## 前提調査

### 移植元ブランチ
- `origin/release/tcg-migration-phase4`（PR #3165 クローズ済み・remote 保持）
- 取得対象ファイル:
  - `backend/app/services/gemini_extraction_svc.py`（274 行）
  - `backend/app/tasks/tcg_extraction.py`（266 行）
  - `backend/tcg_migration/tests/test_mig04_acceptance.py`（389 行）

### 関連 ADR
```
docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
```
（`ls docs/adr/ | grep 154` で実在確認済み）

### 既存ファイル調査
| ファイル | 場所 | 備考 |
|---------|------|------|
| `backend/app/services/tcg_line_import_svc.py` | Stage 1 で作成済み | TCG_SCHEMA パターンの正本 |
| `backend/app/celery_app.py` | `backend/app/celery_app.py:21-36` | include リストを追記 |
| `backend/requirements.txt` | `backend/requirements.txt:27` | google-generativeai 既存・google-genai 追加 |

### GAS との乖離（IMP-R4 実測）

**乖離①: プロンプト連結**

| 側 | 連結式 |
|----|--------|
| 移植元 Python (PR #3165) | `f"{PROMPT_TEXT}\n\n{prompt_input}"` |
| GAS RawExtractionV2.js | `PROMPT_TEXT + '\n\n原文:\n' + input` |

差異: GAS は `原文:\n` セパレーターを挟む。移植元はこれを欠いていた。  
修正: `f"{PROMPT_TEXT}\n\n原文:\n{prompt_input}"` に変更（Stage 2 で適用）。

**乖離②: SPAN 受け入れ（維持決定）**

移植元は L0001 単独 SPAN を受け入れる（GAS の寛容版）。  
GAS の ExtractOnly 関数が本番の抽出経路であり、その設計に合わせているため変更しない。

**乖離③: モデル名・温度**  
`gemini-3.6-flash` / `temperature=0` — 移植元と GAS で一致。変更なし。

### スキーマ修飾（IMP-05 教訓）

PR #3165 の `tcg_extraction.py` は `text(...)` に f-string がなく、SQL 中に `{TCG_SCHEMA}` が文字どおり残っていた（IMP-05 で6箇所を確認）。

Stage 2 対策:
1. 全 4 件の `text()` 呼び出しを `text(f"...")` / `text(f"""...""")` に変更（確認済み）
2. テスト `test_tcg_extraction_sql_has_schema_prefix` でソースを解析し、`tenant_004.` の有無と `{TCG_SCHEMA}` の残存を機械的に検証

### 解析発火フラグ調査

移植元 `tcg_extraction.py` は `status='done'` で無条件に `analyze_extraction_job` を呼ぶ設計。  
Stage 2 では環境変数 `TCG_AUTO_ANALYZE=1` のときのみ発火（既定 OFF）。  
既存 `docker-compose.yml` への変数追加は今回対象外（既定 OFF のため不要）。

### lint_tenant_schema.py

`backend/scripts/lint_tenant_schema.py` は現存しない（`ls backend/scripts/` で確認）。  
代替: テスト `test_tcg_extraction_sql_has_schema_prefix` + `test_tcg_line_import_svc_sql_has_schema_prefix` で SQL 文字列を機械検査。

### マイグレーション確認

Stage 2 が書くテーブル `extraction_jobs`, `extraction_items`, `source_messages` は  
`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql` で作成済み。  
新規 migration は不要。

### 競合確認（append-only 戦略）
| ファイル | 戦略 |
|---------|------|
| `backend/app/celery_app.py` | include リストに 1 行追記（既存 11 タスク不変） |
| `backend/requirements.txt` | `google-genai>=1.0.0` を追記（`google-generativeai` は削除しない） |

`tcg_analyzer_svc.py` は変更しない（origin/main の v2 をそのまま呼ぶ）。
