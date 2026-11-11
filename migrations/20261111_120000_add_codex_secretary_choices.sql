-- ADR-1058 段3: 秘書（secretary_intent）の選択肢に ChatGPT（codex）の3つを足す。足すだけ。今の担当は変えない（Claude のまま）。
-- 設計: docs/handoff/secretary-chatgpt/design.md §4-1（「codex の3行は段3の migration で足す」）・§7 の段3。
-- モデルの名前は手元の Codex CLI の一覧（docs/handoff/secretary-chatgpt/recon.md の 2026-11-02 の取得）で3つとも答えを返したもの。
-- 流し直しても壊れない: UNIQUE(job_key, provider, model) に当たれば何もしない（ON CONFLICT DO NOTHING）。
-- 表と provider の CHECK は migrations/20261103_120000_create_ai_job_assignments.sql が作る（その後に流す）。
--
-- 戻し方（流すのは PO。先に画面で秘書の担当を Claude に戻す。担当が codex の行を指していると外部キーで止まる）:
--   選択肢の表から job_key='secretary_intent' かつ provider='codex' の3行を外す。
BEGIN;

INSERT INTO public.ai_job_choices (job_key, provider, model) VALUES
    ('secretary_intent', 'codex', 'gpt-6-luna'),
    ('secretary_intent', 'codex', 'gpt-5.6-terra'),
    ('secretary_intent', 'codex', 'gpt-5.6-luna')
ON CONFLICT DO NOTHING;

COMMIT;
