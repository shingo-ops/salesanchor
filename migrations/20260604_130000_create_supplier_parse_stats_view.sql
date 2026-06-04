-- Drift detection view: per-supplier parse statistics
CREATE OR REPLACE VIEW public.v_supplier_parse_stats AS
SELECT
    pl.supplier_id,
    s.name AS supplier_name,
    DATE_TRUNC('day', pl.logged_at) AS day,
    COUNT(*) AS total_lines,
    COUNT(*) FILTER (WHERE pl.outcome = 'parsed') AS parsed_count,
    COUNT(*) FILTER (WHERE pl.outcome = 'excluded') AS excluded_count,
    COUNT(*) FILTER (WHERE pl.outcome = 'unparsed') AS unparsed_count,
    ROUND(
        COUNT(*) FILTER (WHERE pl.outcome = 'excluded')::NUMERIC / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS exclude_rate_pct,
    ROUND(AVG(pl.match_confidence) FILTER (WHERE pl.match_confidence IS NOT NULL), 3) AS avg_confidence
FROM public.parse_logs pl
LEFT JOIN public.suppliers s ON s.id = pl.supplier_id
GROUP BY pl.supplier_id, s.name, DATE_TRUNC('day', pl.logged_at);
