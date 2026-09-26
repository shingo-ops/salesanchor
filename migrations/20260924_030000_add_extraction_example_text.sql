-- Add example text column for supplier extraction rules
ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS extraction_example_text TEXT;
