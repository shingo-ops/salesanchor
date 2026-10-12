#!/usr/bin/env bash
# migrate-pipeline-data-to-public.sh
# Step 3/5: Copy data from tenant_004 pipeline tables to public schema
#
# Usage: bash scripts/migrate-pipeline-data-to-public.sh [--dry-run]
#
# Prerequisites:
#   - Step 1 deployed (public tables exist)
#   - SSH access to production server
#
# Safety:
#   - Uses INSERT ... ON CONFLICT DO NOTHING (idempotent)
#   - Runs in a single transaction
#   - --dry-run shows SQL without executing

set -euo pipefail

SSH_HOST="ubuntu@49.212.137.46"
SSH_KEY="$HOME/.ssh/manual-only/id_ed25519"
CONTAINER="astro-webapp-postgres-1"
DB_USER="jarvis"
DB_NAME="jarvis_db"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE ==="
fi

# Migration SQL — order follows FK dependencies (parents first)
read -r -d '' MIGRATE_SQL << 'EOSQL' || true
BEGIN;

-- ============================================================
-- Pre-check: verify public tables exist
-- ============================================================
DO $$
DECLARE
    missing TEXT[];
    tbl TEXT;
BEGIN
    missing := ARRAY[]::TEXT[];
    FOREACH tbl IN ARRAY ARRAY[
        'supplier_channels', 'source_messages', 'import_jobs',
        'import_job_messages', 'extraction_jobs', 'extraction_items',
        'extraction_attempts', 'analysis_runs', 'analysis_results',
        'analysis_run_snapshots', 'item_corrections', 'tcg_normalization_rules',
        'tcg_distribution_settings', 'tcg_distribution_targets',
        'tcg_product_import_jobs', 'tcg_product_import_rows', 'audit_log'
    ]
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = tbl
        ) THEN
            missing := missing || tbl;
        END IF;
    END LOOP;

    IF array_length(missing, 1) > 0 THEN
        RAISE EXCEPTION 'Missing public tables: %', array_to_string(missing, ', ');
    END IF;
END $$;

-- ============================================================
-- C-1: supplier_channels (no FK deps on other migrating tables)
-- ============================================================
INSERT INTO public.supplier_channels (id, channel, external_id, is_active, supplier_id)
SELECT id, channel, external_id, is_active, supplier_id
FROM tenant_004.supplier_channels
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- C-2: source_messages (FK → supplier_channels)
-- ============================================================
INSERT INTO public.source_messages (id, supplier_channel_id, raw_text, raw_sha256, received_at, superseded_by, is_active, created_at, line_posted_at)
SELECT id, supplier_channel_id, raw_text, raw_sha256, received_at, superseded_by, is_active, created_at, line_posted_at
FROM tenant_004.source_messages
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- B-1: import_jobs
-- ============================================================
INSERT INTO public.import_jobs (id, filename, raw_sha256, message_count, provider_count, unresolved_count, uploaded_by, status, created_at, pending_messages, window_start, window_end, unresolved_names, review_status, messages_linked_at)
SELECT id, filename, raw_sha256, message_count, provider_count, unresolved_count, uploaded_by, status, created_at, pending_messages, window_start, window_end, unresolved_names, review_status, messages_linked_at
FROM tenant_004.import_jobs
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- B-2: import_job_messages (FK → import_jobs, source_messages)
-- ============================================================
INSERT INTO public.import_job_messages (import_job_id, source_message_id, relation_kind, created_at)
SELECT import_job_id, source_message_id, relation_kind, created_at
FROM tenant_004.import_job_messages
ON CONFLICT (import_job_id, source_message_id) DO NOTHING;

-- ============================================================
-- A-1: extraction_jobs (FK → source_messages)
-- ============================================================
INSERT INTO public.extraction_jobs (id, source_message_id, status, extracted_at, error_message, prompt_version, created_at, work_reference_snapshot, work_reference_sha256)
SELECT id, source_message_id, status, extracted_at, error_message, prompt_version, created_at, work_reference_snapshot, work_reference_sha256
FROM tenant_004.extraction_jobs
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- A-2: extraction_items (FK → extraction_jobs)
-- ============================================================
INSERT INTO public.extraction_items (id, extraction_job_id, line_start, line_end, raw_product_name, raw_quantity, raw_price, raw_unit, raw_state, raw_memo, created_at, raw_work_name, raw_work_source_line_span, resolved_work_id, resolved_product_code)
SELECT id, extraction_job_id, line_start, line_end, raw_product_name, raw_quantity, raw_price, raw_unit, raw_state, raw_memo, created_at, raw_work_name, raw_work_source_line_span, resolved_work_id, resolved_product_code
FROM tenant_004.extraction_items
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- A-3: extraction_attempts (FK → extraction_jobs)
-- ============================================================
INSERT INTO public.extraction_attempts (id, extraction_job_id, source_message_id, parent_attempt_id, started_at, response_received_at, finished_at, phase, input_payload, input_sha256, input_bytes, requested_model, prompt_version, code_version, response_text, response_sha256, response_bytes, parsed_items, parsed_bytes, item_count, validation_result, error_code)
SELECT id, extraction_job_id, source_message_id, parent_attempt_id, started_at, response_received_at, finished_at, phase, input_payload, input_sha256, input_bytes, requested_model, prompt_version, code_version, response_text, response_sha256, response_bytes, parsed_items, parsed_bytes, item_count, validation_result, error_code
FROM tenant_004.extraction_attempts
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- D-1: analysis_runs (FK → extraction_jobs)
-- ============================================================
INSERT INTO public.analysis_runs (id, extraction_job_id, run_type, triggered_by, engine_version, started_at, completed_at, total, pid_resolved, unit_resolved, needs_review, multi_count, none_count)
SELECT id, extraction_job_id, run_type, triggered_by, engine_version, started_at, completed_at, total, pid_resolved, unit_resolved, needs_review, multi_count, none_count
FROM tenant_004.analysis_runs
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- D-2: analysis_results (FK → extraction_items, public.conditions, etc.)
-- ============================================================
INSERT INTO public.analysis_results (id, extraction_item_id, pid_resolved, pid_basis, unit_canonical, unit_resolved, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja, status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, unit_inferred, unit_basis, unit_confidence, unit_infer_reason, product_id, unit_id, condition_id)
SELECT id, extraction_item_id, pid_resolved, pid_basis, unit_canonical, unit_resolved, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja, status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, unit_inferred, unit_basis, unit_confidence, unit_infer_reason, product_id, unit_id, condition_id
FROM tenant_004.analysis_results
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- D-3: analysis_run_snapshots (FK → analysis_runs)
-- ============================================================
INSERT INTO public.analysis_run_snapshots (id, run_id, analysis_result_id, extraction_item_id, pid_resolved, pid_basis, unit_id, unit_canonical, unit_resolved, condition_id, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja, status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, snapshotted_at, product_id)
SELECT id, run_id, analysis_result_id, extraction_item_id, pid_resolved, pid_basis, unit_id, unit_canonical, unit_resolved, condition_id, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja, status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, snapshotted_at, product_id
FROM tenant_004.analysis_run_snapshots
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- E-1: item_corrections (BIGSERIAL PK — needs sequence reset)
-- ============================================================
INSERT INTO public.item_corrections (id, extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by, corrected_at)
SELECT id, extraction_item_id, source_message_id, field_name, system_value, human_value, corrected_by, corrected_at
FROM tenant_004.item_corrections
ON CONFLICT (id) DO NOTHING;
-- Reset sequence to max id
SELECT setval('public.item_corrections_id_seq', COALESCE((SELECT MAX(id) FROM public.item_corrections), 0));

-- ============================================================
-- E-2: tcg_normalization_rules (TEXT PK)
-- ============================================================
INSERT INTO public.tcg_normalization_rules (normalization_rule_id, field, rule_type, from_val, to_val, enabled, priority, note, created_at)
SELECT normalization_rule_id, field, rule_type, from_val, to_val, enabled, priority, note, created_at
FROM tenant_004.tcg_normalization_rules
ON CONFLICT (normalization_rule_id) DO NOTHING;

-- ============================================================
-- F-1: tcg_distribution_settings (TEXT PK)
-- ============================================================
INSERT INTO public.tcg_distribution_settings (key, value, note, updated_at)
SELECT key, value, note, updated_at
FROM tenant_004.tcg_distribution_settings
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- F-2: tcg_distribution_targets
-- ============================================================
INSERT INTO public.tcg_distribution_targets (id, name, spreadsheet_id, sheet_name, is_active, sa_key_secret_name, last_distributed_at, last_distributed_count, last_result, created_at, updated_at)
SELECT id, name, spreadsheet_id, sheet_name, is_active, sa_key_secret_name, last_distributed_at, last_distributed_count, last_result, created_at, updated_at
FROM tenant_004.tcg_distribution_targets
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- F-3: tcg_product_import_jobs
-- ============================================================
INSERT INTO public.tcg_product_import_jobs (id, filename, raw_sha256, total_rows, created_rows, skipped_rows, executed_by, status, started_at, completed_at)
SELECT id, filename, raw_sha256, total_rows, created_rows, skipped_rows, executed_by, status, started_at, completed_at
FROM tenant_004.tcg_product_import_jobs
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- F-4: tcg_product_import_rows (FK → tcg_product_import_jobs)
-- ============================================================
INSERT INTO public.tcg_product_import_rows (id, job_id, row_no, japanese_title, mark, result, product_code, messages, created_at)
SELECT id, job_id, row_no, japanese_title, mark, result, product_code, messages, created_at
FROM tenant_004.tcg_product_import_rows
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- F-5: audit_log (BIGSERIAL PK — needs sequence reset)
-- ============================================================
INSERT INTO public.audit_log (id, table_name, record_id, action, changed_by, changed_at, old_values, new_values)
SELECT id, table_name, record_id, action, changed_by, changed_at, old_values, new_values
FROM tenant_004.audit_log
ON CONFLICT (id) DO NOTHING;
-- Reset sequence to max id
SELECT setval('public.audit_log_id_seq', COALESCE((SELECT MAX(id) FROM public.audit_log), 0));

-- ============================================================
-- Post-migration verification
-- ============================================================
DO $$
DECLARE
    tbl TEXT;
    src_count BIGINT;
    dst_count BIGINT;
    mismatches TEXT[];
BEGIN
    mismatches := ARRAY[]::TEXT[];
    FOREACH tbl IN ARRAY ARRAY[
        'supplier_channels', 'source_messages', 'import_jobs',
        'import_job_messages', 'extraction_jobs', 'extraction_items',
        'extraction_attempts', 'analysis_runs', 'analysis_results',
        'analysis_run_snapshots', 'item_corrections', 'tcg_normalization_rules',
        'tcg_distribution_settings', 'tcg_distribution_targets',
        'tcg_product_import_jobs', 'tcg_product_import_rows', 'audit_log'
    ]
    LOOP
        EXECUTE format('SELECT count(*) FROM tenant_004.%I', tbl) INTO src_count;
        EXECUTE format('SELECT count(*) FROM public.%I', tbl) INTO dst_count;
        IF src_count != dst_count THEN
            mismatches := mismatches || format('%s: tenant_004=%s public=%s', tbl, src_count, dst_count);
        END IF;
        RAISE NOTICE 'OK: % — tenant_004=% public=%', tbl, src_count, dst_count;
    END LOOP;

    IF array_length(mismatches, 1) > 0 THEN
        RAISE EXCEPTION 'Row count mismatch: %', array_to_string(mismatches, '; ');
    END IF;

    RAISE NOTICE 'All 17 tables verified — row counts match';
END $$;

COMMIT;
EOSQL

echo "=== Pipeline Data Migration: tenant_004 → public ==="
echo "Target: $SSH_HOST (container: $CONTAINER)"
echo ""

if $DRY_RUN; then
    echo "--- SQL to execute ---"
    echo "$MIGRATE_SQL"
    echo "--- End SQL ---"
    echo ""
    echo "Re-run without --dry-run to execute."
    exit 0
fi

echo "Connecting to production..."
ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$SSH_HOST" \
    "docker exec -i $CONTAINER psql -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1" \
    <<< "$MIGRATE_SQL"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=== Migration completed successfully ==="
else
    echo ""
    echo "=== Migration FAILED (exit code: $EXIT_CODE) ==="
    echo "Transaction was rolled back — no data was changed."
    exit $EXIT_CODE
fi
