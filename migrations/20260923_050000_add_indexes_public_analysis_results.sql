-- Migration: add missing indexes to public.analysis_results
-- Background: public.analysis_results was created without UNIQUE index on
--   extraction_item_id, causing ON CONFLICT (extraction_item_id) to fail
--   with InvalidColumnReference, resulting in ANALYSIS_FAILED for all jobs.
-- tenant_001.analysis_results has 9 indexes; this migration aligns public schema.

-- Required: without this, ON CONFLICT (extraction_item_id) fails
CREATE UNIQUE INDEX IF NOT EXISTS analysis_results_extraction_item_id_key
    ON public.analysis_results USING btree (extraction_item_id);

-- Align with tenant_001 for consistency
CREATE INDEX IF NOT EXISTS idx_public_ar_unit_id
    ON public.analysis_results USING btree (unit_id);

CREATE INDEX IF NOT EXISTS idx_public_ar_condition_id
    ON public.analysis_results USING btree (condition_id);

CREATE INDEX IF NOT EXISTS ix_public_analysis_results_needs_review
    ON public.analysis_results USING btree (needs_review);

CREATE INDEX IF NOT EXISTS ix_public_analysis_results_pid_resolved
    ON public.analysis_results USING btree (pid_resolved);

CREATE INDEX IF NOT EXISTS ix_public_analysis_results_unit_resolved
    ON public.analysis_results USING btree (unit_resolved);

CREATE INDEX IF NOT EXISTS idx_public_analysis_results_unit_basis
    ON public.analysis_results USING btree (unit_basis) WHERE (unit_basis <> ''::text);

CREATE INDEX IF NOT EXISTS idx_public_ar_product_id
    ON public.analysis_results USING btree (product_id);
