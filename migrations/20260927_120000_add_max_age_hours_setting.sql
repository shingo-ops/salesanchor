-- max_age_hours setting for distribution time filter
INSERT INTO public.tcg_distribution_settings (key, value, note)
VALUES ('max_age_hours', '48', '配信対象の最大経過時間（時間）。line_posted_atからの経過がこの値を超えた行は配信から除外する')
ON CONFLICT (key) DO NOTHING;
