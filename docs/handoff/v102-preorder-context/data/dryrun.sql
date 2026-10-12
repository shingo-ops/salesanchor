-- 便PO: 予約の手がかりの規則（候補6行）。設計 docs/handoff/v102-preorder-context/card-PO.md 1-4。
-- dryrun（書き込みを試して必ず ROLLBACK する。読み取り専用の接続では実行できない）。
BEGIN;
WITH base AS (
  SELECT COALESCE(MAX(CAST(SUBSTRING(status_id FROM 3) AS INTEGER)), 0) AS n
  FROM public.tcg_status_master WHERE status_id SIMILAR TO 'ST[0-9]+'
), cand (ord, canonical, effect, match_type, search_pattern, exclude_pattern, priority, note) AS (
  VALUES
    (1, 'Pre-order', 'RELEASE_AHEAD', 'RELEASE', '', '', 10, 'v102-preorder-context:1'),
    (2, 'Pre-order', 'DATE_AHEAD', 'REGEX', '(?P<m>\d{1,2})/(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)', '', 10, 'v102-preorder-context:2'),
    (3, 'Pre-order', 'DATE_AHEAD', 'REGEX', '(?P<m>\d{1,2})月(?P<d>\d{1,2})日[^0-9]{0,4}(?:入荷|発送|発売)', '', 20, 'v102-preorder-context:3'),
    (4, 'Pre-order', 'DATE_AHEAD', 'REGEX', '(?P<m>\d{1,2})月(?P<part>上旬|中旬|下旬|末|頃)?[^0-9]{0,4}(?:入荷|発送|発売)', '', 30, 'v102-preorder-context:4'),
    (5, 'Pre-order', 'HEADING', 'REGEX', '予約', 'ご予約可能|集荷予約', 10, 'v102-preorder-context:5'),
    (6, 'In Stock', 'HEADING', 'REGEX', '在庫|現物|即納', '在庫なし|ご注文で当日発送|弊社在庫品につき|記載商品以外の在庫|記載していない在庫|在庫・商品の入荷について|保管中', 20, 'v102-preorder-context:6')
)
INSERT INTO public.tcg_status_master
  (status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type, effect, tenant_id)
SELECT 'ST' || LPAD((base.n + cand.ord)::text, 4, '0'), cand.canonical, cand.search_pattern, cand.exclude_pattern,
       cand.priority, TRUE, cand.note, cand.match_type, cand.effect, NULL
FROM cand CROSS JOIN base;
SELECT 1 / (CASE WHEN COUNT(*) = 6 THEN 1 ELSE 0 END) AS inserted_must_be_six
FROM public.tcg_status_master WHERE note LIKE 'v102-preorder-context:%' AND tenant_id IS NULL;
SELECT status_id, canonical, effect, match_type, priority, enabled, note FROM public.tcg_status_master WHERE note LIKE 'v102-preorder-context:%' ORDER BY status_id;
ROLLBACK;
