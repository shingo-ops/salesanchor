-- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
ALTER TABLE public.tcg_note_master ADD COLUMN IF NOT EXISTS label_template_en TEXT;
COMMENT ON COLUMN public.tcg_note_master.label_template_en IS
    'REGEX の行の英語の書式。$1 などの捕捉を展開する。空なら label_en';
