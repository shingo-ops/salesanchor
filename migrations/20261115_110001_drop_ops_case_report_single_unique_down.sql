-- ADR-1012 段階4 便2b の戻し（手動実行のみ・本番デプロイでは実行しない）。
-- 先に「SELECT count(*) FROM (SELECT incident_id FROM ops_case.reports GROUP BY 1 HAVING count(*) > 1) t」が 0 か確かめる。
-- 0 でなければ流さない（報告は消さない。PO に聞く）。
BEGIN;
ALTER TABLE ops_case.reports ADD CONSTRAINT reports_incident_id_key UNIQUE (incident_id);
COMMENT ON TABLE ops_case.reports IS '相談係の報告。1 件につき 1 通';
COMMIT;
