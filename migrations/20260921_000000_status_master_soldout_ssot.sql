-- =============================================================================
-- tcg_status_master SSOT統合: 完売検索ワード6件追加 + 除外パターン2件有効化
-- 根拠: PO合意済み初期データ（sold-out-rules-handoff.md C18/C38/C92）
-- 冪等: ON CONFLICT DO NOTHING / WHERE exclude_pattern = ''
-- =============================================================================

-- 1. 不足している検索ワード6件を追加
INSERT INTO public.tcg_status_master
    (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, match_type, effect, note)
VALUES
    ('ST0015', 'Sold out', 'sold',         '', 55,  TRUE, 'LITERAL', 'EXCLUDE', '完売SSOT統合'),
    ('ST0016', 'Sold out', '売切',         '', 60,  TRUE, 'LITERAL', 'EXCLUDE', '完売SSOT統合'),
    ('ST0017', 'Sold out', 'SOLD OUT',     '', 70,  TRUE, 'LITERAL', 'EXCLUDE', '完売SSOT統合'),
    ('ST0018', 'Sold out', '一旦ストップ', '', 80,  TRUE, 'LITERAL', 'EXCLUDE', '完売SSOT統合'),
    ('ST0019', 'Sold out', '〆',           '', 90,  TRUE, 'LITERAL', 'EXCLUDE', '完売SSOT統合'),
    ('ST0020', 'Sold out', 'ストップ',     '', 100, TRUE, 'LITERAL', 'EXCLUDE', '完売SSOT統合')
ON CONFLICT (status_id) DO NOTHING;

-- 2. 既存行に除外パターンを設定（誤判定防止）
-- ST0012: "売り切れ" → "売り切れの場合がございます" は完売ではない
UPDATE public.tcg_status_master
SET exclude_pattern = '売り切れの場合がございます', updated_at = NOW()
WHERE status_id = 'ST0012' AND exclude_pattern = '';

-- ST0013: "完売" → "予告なく完売となる場合" は完売ではない
UPDATE public.tcg_status_master
SET exclude_pattern = '予告なく完売となる場合', updated_at = NOW()
WHERE status_id = 'ST0013' AND exclude_pattern = '';
