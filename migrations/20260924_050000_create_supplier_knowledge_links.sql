-- Migration: Create supplier_knowledge_links junction table
-- 仕入元と共用Knowledgeルールの紐付けテーブル

CREATE TABLE IF NOT EXISTS public.supplier_knowledge_links (
    id          SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES public.suppliers(id) ON DELETE CASCADE,
    knowledge_rule_id INTEGER NOT NULL REFERENCES public.knowledge_rules(id) ON DELETE CASCADE,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_supplier_knowledge_links
    ON public.supplier_knowledge_links (supplier_id, knowledge_rule_id);
CREATE INDEX IF NOT EXISTS idx_skl_supplier_id
    ON public.supplier_knowledge_links (supplier_id) WHERE is_active = TRUE;
