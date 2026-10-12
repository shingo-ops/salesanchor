# Recon: 仕入元抽出ルール実装

## 既存ADR確認

- ADR-085: 仕入先別 Gemini プロンプト (`public.supplier_prompts`) — 既存の `supplier_prompts` テーブルに加え、今回は `suppliers` テーブル直接に `extraction_*` 列を追加する設計
- ADR-025: 本番運用フェーズ後のデータ手動INSERT禁止 — 現在開発フェーズのため直接INSERT継続可
- ADR-027: i18n強制 — フロント変更なしのため対象外
- ADR-072: write endpoint の `reset_tenant_context()` 必須 — 本PRはpublicスキーマ直接操作、テナントコンテキスト不要

## 調査結果

### unit_aliases 実態
- `public.unit_aliases` は View → 実テーブルは `public.line_unit_aliases`
  - ファイル: `backend/app/services/tcg_line_import_svc.py:598`
- UNIQUE制約: `uq_unit_aliases_unit_lang` UNIQUE(unit_id, lang, alias_text)
- lang カラム: NOT NULL、既存データはすべて `'ja'`

### 既存仕入元API
- ファイル: `backend/app/routers/super_admin_suppliers.py:1-736`
- 既存エンドポイント: GET/POST/PATCH/DELETE suppliers + CSV export/import + discord-routing + prompt + parse-stats

### ダッシュボード get_supplier_pipeline()
- ファイル: `backend/app/services/tcg_analysis_dashboard_svc.py:362-535`
- 問題: `sc.channel AS channel_name` でチャンネル種別(line等)が表示されていた
- 修正: `COALESCE(s.name, sc.channel)` に変更 + `LEFT JOIN public.suppliers s ON s.id = sc.supplier_id`

### gemini_extraction_svc.py
- ファイル: `backend/app/services/gemini_extraction_svc.py:288-405`
- 現状: v3以上で列数・span不正の行は全体 raise ValueError
- 呼び出し元: `backend/app/tasks/tcg_extraction.py:193`
- テスト: `backend/tests/test_tcg_gemini_extraction.py`, `backend/tests/test_tcg_work_id.py`, `backend/tests/test_tcg_extraction_record_integrity_pg.py`

### Celeryタスク
- ファイル: `backend/app/tasks/tcg_extraction.py:118-209`
- `_run_extraction()` のSELECTで `sm.raw_text` を取得 → ここに `extraction_*` 列を追加
