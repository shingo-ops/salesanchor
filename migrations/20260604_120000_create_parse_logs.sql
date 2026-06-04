-- public スキーマ（共有カタログ面・解析ログは仕入元単位で共有）
CREATE TABLE IF NOT EXISTS public.parse_logs (
    id SERIAL PRIMARY KEY,
    ingestion_job_id INTEGER REFERENCES public.ingestion_jobs(id),
    inbound_message_id INTEGER,
    supplier_id INTEGER REFERENCES public.suppliers(id),
    raw_line TEXT NOT NULL,
    matched_product_id INTEGER REFERENCES public.products(id),
    match_confidence NUMERIC(4,3) CHECK (match_confidence BETWEEN 0 AND 1),
    extracted_qty INTEGER,
    extracted_price INTEGER,
    extracted_condition VARCHAR(50),
    knowledge_version VARCHAR(50),
    parse_engine VARCHAR(50),
    outcome VARCHAR(20) CHECK (outcome IN ('parsed', 'excluded', 'unparsed')),
    exclude_reason TEXT,
    reasoning TEXT,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parse_logs_ingestion_job_id ON public.parse_logs(ingestion_job_id);
CREATE INDEX IF NOT EXISTS idx_parse_logs_supplier_id ON public.parse_logs(supplier_id);
CREATE INDEX IF NOT EXISTS idx_parse_logs_outcome ON public.parse_logs(outcome);
CREATE INDEX IF NOT EXISTS idx_parse_logs_logged_at ON public.parse_logs(logged_at DESC);
