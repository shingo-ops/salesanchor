-- public スキーマ（共有カタログ面・全テナント共通の取り込みジョブ管理）
CREATE TABLE IF NOT EXISTS public.ingestion_jobs (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER REFERENCES public.suppliers(id),
    trigger VARCHAR(20) CHECK (trigger IN ('discord', 'manual', 'scheduled')),
    status VARCHAR(20) CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    total_lines INTEGER,
    parsed_count INTEGER,
    excluded_count INTEGER,
    unparsed_count INTEGER,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_supplier_id ON public.ingestion_jobs(supplier_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON public.ingestion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_created_at ON public.ingestion_jobs(created_at DESC);
