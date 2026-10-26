-- v102 規則直し 便1 precheck（読み取り）。CAN_PROCEED|1 と PRECHECK_DONE が出ること。1つでも前提と違えば 0 除算で失敗する。
-- 確かめること: (1) CN0001〜CN0004 が各1行だけ (2) 4行の search_kw・exclude_kw の md5 が本番の今の値と一致 (3) 足す4語がどの列にも無い。
\set ON_ERROR_STOP on
SELECT 'ROWS|' || count(*) FROM public.line_conditions WHERE code IN ('CN0001','CN0002','CN0003','CN0004');
SELECT 'CAN_PROCEED|' || CASE WHEN
    (SELECT count(*) FROM public.line_conditions WHERE code IN ('CN0001','CN0002','CN0003','CN0004')) = 4
    AND (SELECT count(DISTINCT code) FROM public.line_conditions WHERE code IN ('CN0001','CN0002','CN0003','CN0004')) = 4
    AND (SELECT count(*) FROM public.line_conditions c
          JOIN (VALUES
    ('CN0001', '454be54ff7f66973b0a737a746d0722f', '47e88628b2211ff61dccdd15e9fb906e'),
    ('CN0002', '47e88628b2211ff61dccdd15e9fb906e', 'd41d8cd98f00b204e9800998ecf8427e'),
    ('CN0003', 'b153520fe5e8291bca582d70ab42877b', '47e88628b2211ff61dccdd15e9fb906e'),
    ('CN0004', 'cd36d603d8a78e03af6e51ecadfac3ba', 'd41d8cd98f00b204e9800998ecf8427e')
          ) AS e(code, search_md5, exclude_md5) ON e.code = c.code
         WHERE md5(c.search_kw) = e.search_md5 AND md5(COALESCE(c.exclude_kw, '')) = e.exclude_md5) = 4
    AND (SELECT count(*) FROM public.line_conditions
          WHERE code IN ('CN0001','CN0002','CN0003','CN0004')
            AND (COALESCE(search_kw, '') || '|' || COALESCE(exclude_kw, '')) LIKE ANY (ARRAY['%傷あり%','%傷有%','%キズあり%','%キズ有%'])) = 0
  THEN 1 ELSE 1 / (SELECT count(*) - count(*) FROM public.line_conditions) END;
SELECT 'PRECHECK_DONE';
