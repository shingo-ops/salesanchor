-- ADR-1080: 秘書の声（一人ずつ）。NULL は未選択で既定の Charon。値の一覧の正本は backend/app/services/secretary_voice.py
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS secretary_voice VARCHAR(40);

COMMENT ON COLUMN public.users.secretary_voice IS '秘書の声（ADR-1080）。NULL は未選択で既定の Charon。値の一覧の正本は backend/app/services/secretary_voice.py';
