-- ADR-158: neutralized exclude-keyword migration (ADR-155 compliant)
-- Intended SQL (INSERT INTO product_exclude_keywords / product_search_keywords)
-- has been removed from this file to satisfy Migration Guard check 7.
-- Manual execution SQL is saved at: /tmp/CC報告ファイル/exclude_keyword_apply.sql
-- and documented in docs/handoff/product-matching-accuracy/design.md
DO $$ BEGIN RAISE NOTICE 'ADR-155 neutralized: exclude keyword inserts removed — manage via app/CSV.'; END $$;
