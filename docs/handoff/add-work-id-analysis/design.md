# design: analysis_results に work_id カラム追加

recon: docs/handoff/add-work-id-analysis/recon.md

対象ADR: 該当なし（単純なカラム追加）

## KGI
Gemini の作品ID抽出精度を事実ベースで計測可能にする。

## KPI（観測可能な事象）

| 基準 | 検証方法 |
|------|---------|
| work_id カラムが存在する | `\d public.analysis_results` で work_id integer 列を確認 |
| インデックスが存在する | `SELECT indexname FROM pg_indexes WHERE tablename='analysis_results' AND indexname='idx_analysis_results_work_id'` |
| 新規解析で work_id が保存される | 解析後 `SELECT work_id FROM public.analysis_results WHERE work_id IS NOT NULL LIMIT 1` で値が返る |

## 変更方針

- `ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS work_id integer REFERENCES public.type_master(id)` (nullable)
- `CREATE INDEX IF NOT EXISTS idx_analysis_results_work_id ON public.analysis_results(work_id)`
- `backend/app/services/tcg_analyzer_svc.py` の UPSERT に work_id カラムを追加
- 全て冪等（`IF NOT EXISTS`）

## 影響範囲
- `public.analysis_results` テーブルのみ
- 呼び出し元: `backend/app/services/tcg_analyzer_svc.py`（UPSERT）

## 戻し方
`ALTER TABLE public.analysis_results DROP COLUMN IF EXISTS work_id;` で即時ロールバック可能。nullable なためデータ損失なし。

## 外部・過去事例の参照と我々への応用
標準的な `ALTER TABLE ADD COLUMN` パターン。nullable カラムは既存行に影響しない。

## 維持の仕組み
- work_id は `public.type_master.id` への FK。`type_master` の削除時は ON DELETE SET NULL または ON DELETE RESTRICT で保護する。
- 守り手: `migrations/20260923_120000_add_work_id_to_analysis_results.sql`（カラム定義）
