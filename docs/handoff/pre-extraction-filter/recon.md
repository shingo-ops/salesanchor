# recon — Gemini呼び出し前事前フィルタ

**仕事名**: pre-extraction-filter  
**日付**: 2026-09-27  
**対象ADR**: ADR-100  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/tasks/tcg_extraction.py:222` | 空チェック処理（if len(raw_text.strip()) == 0:）の位置確認 |
| `backend/app/tasks/tcg_extraction.py:242` | Gemini呼び出し直前（AttemptRecorder）の位置確認 |
| `backend/app/services/tcg_analysis_dashboard_svc.py:31` | get_pipeline_summary() の total_extraction / error_rate 計算 |
| `backend/app/routers/tcg_analysis_dashboard.py:37` | ExtractionByStatus Pydantic モデル定義 |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:43` | RULE_CATEGORIES 定義（現在4カテゴリ） |

---

## 対象ファイル調査

### backend/app/tasks/tcg_extraction.py
- 空チェック: L222-240 (`if len(raw_text.strip()) == 0:`)
- Gemini呼び出し: L242 (`recorder = AttemptRecorder(...)`) の後の `_run_recorded_extraction()`
- knowledge_links取得: L201-220（supplier_id紐付けあり）
- `re` モジュール: 未インポート → 追加必要

### backend/app/services/tcg_analysis_dashboard_svc.py
- `get_pipeline_summary()` L31-33: `total_extraction` / `error_rate` 計算
- `get_supplier_pipeline()` L412-416: `extraction_empty` / `extraction_other` のCOUNT FILTER条件

### backend/app/routers/tcg_analysis_dashboard.py
- `ExtractionByStatus` L37-42: Pydantic モデル（done/error/pending/running/empty）

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx
- `RULE_CATEGORIES` L43: 現在 `["normalize", "split", "alias_normalize", "exclude"]`
- カテゴリ表示: L380 `t(\`superAdmin.knowledge.categories.\${r.category}\`)`

### frontend/src/locales/ja.json / en.json
- `superAdmin.knowledge.categories` L2456-2461: 現在4カテゴリ
- `extractionStatus` L3801-3808: done/empty/error/pending/running/unknown

---

## 既存ADR調査

`git grep -i docs/adr/` でキーワード検索（knowledge_rules, pre_filter, extraction_filter）→ 該当ADRなし。
ADR-100（取り込み・解析パイプライン）が上位ADRとして関連。新機能のため追加ADR不要（設計はタスク指示書で承認済み）。

## DBスキーマ確認

- `knowledge_rules.category`: VARCHAR(50) → 新カテゴリ値追加OK（DB変更不要）
- `extraction_jobs.status`: VARCHAR系 → 'filtered'追加OK（DB変更不要）

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | extraction_jobs.status に 'filtered' を追加してよいか | DBスキーマ確認（VARCHAR型のため追加可能） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
