-- Add work_id column to analysis_results for tracking resolved work (type_master) ID
-- This enables accuracy measurement of Gemini's work_id extraction

ALTER TABLE public.analysis_results
  ADD COLUMN IF NOT EXISTS work_id integer REFERENCES public.type_master(id);

CREATE INDEX IF NOT EXISTS idx_analysis_results_work_id
  ON public.analysis_results(work_id);
