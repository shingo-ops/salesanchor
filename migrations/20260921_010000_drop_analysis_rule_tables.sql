-- Drop analysis_rule system tables
-- SSOT consolidated to tcg_status_master (PR #3621)
-- Order: child tables first to respect FK dependencies
-- CASCADE is added as safety net; all referencing tables are also being dropped.

-- public schema
DROP TABLE IF EXISTS public.analysis_suite_cases CASCADE;
DROP TABLE IF EXISTS public.analysis_test_case_versions CASCADE;
DROP TABLE IF EXISTS public.analysis_test_suites CASCADE;
DROP TABLE IF EXISTS public.analysis_rule_run_results CASCADE;
DROP TABLE IF EXISTS public.analysis_rule_runs CASCADE;
DROP TABLE IF EXISTS public.analysis_revision_rules CASCADE;
DROP TABLE IF EXISTS public.analysis_rule_words CASCADE;
DROP TABLE IF EXISTS public.analysis_rule_versions CASCADE;
DROP TABLE IF EXISTS public.analysis_rules CASCADE;
DROP TABLE IF EXISTS public.analysis_execution_profile_versions CASCADE;
DROP TABLE IF EXISTS public.analysis_instruction_versions CASCADE;
DROP TABLE IF EXISTS public.analysis_policy_revisions CASCADE;
DROP TABLE IF EXISTS public.analysis_policies CASCADE;

-- tenant_004 schema (if exists)
DROP TABLE IF EXISTS tenant_004.analysis_suite_cases CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_test_case_versions CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_test_suites CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_rule_run_results CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_rule_runs CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_revision_rules CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_rule_words CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_rule_versions CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_rules CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_execution_profile_versions CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_instruction_versions CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_policy_revisions CASCADE;
DROP TABLE IF EXISTS tenant_004.analysis_policies CASCADE;

-- tenant_001 schema (if exists)
DROP TABLE IF EXISTS tenant_001.analysis_suite_cases CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_test_case_versions CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_test_suites CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_rule_run_results CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_rule_runs CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_revision_rules CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_rule_words CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_rule_versions CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_rules CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_execution_profile_versions CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_instruction_versions CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_policy_revisions CASCADE;
DROP TABLE IF EXISTS tenant_001.analysis_policies CASCADE;
