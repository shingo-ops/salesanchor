-- v102 規則直し 便1 rollback: 4行を変更前の値（全文）に戻す。WHERE は変更後の md5 一致。件数が4でなければゼロ除算で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
BEGIN;
WITH up AS (
    UPDATE public.line_conditions SET
    search_kw = CASE code
        WHEN 'CN0002' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B,美品'
        WHEN 'CN0004' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B,美品,状態：S,状態:S,状態：A-,状態:A-,状態：B,状態:B'
        ELSE search_kw END,
    exclude_kw = CASE code
        WHEN 'CN0001' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B,美品'
        WHEN 'CN0003' THEN '傷み,箱痛み,痛み,凹み,へこみ,潰れ,つぶれ,破れ,シュリンク破れ,汚れ,スレ,ダメージ,ダメ,難あり,日焼け,色褪せ,折れ,欠け,割れ,状態A-,状態B,美品'
        ELSE exclude_kw END,
    updated_at = NOW()
     WHERE (code = 'CN0001' AND md5(exclude_kw) = '76f0408b4f328a26ea961871770c0213') OR (code = 'CN0002' AND md5(search_kw) = '76f0408b4f328a26ea961871770c0213') OR (code = 'CN0003' AND md5(exclude_kw) = '76f0408b4f328a26ea961871770c0213') OR (code = 'CN0004' AND md5(search_kw) = '8166ec8e5ff7aeac5006589fdbae6f04')
    RETURNING code
)
SELECT CASE WHEN count(*) = 4 THEN 'REVERTED|4' ELSE (1 / (count(*) - count(*)))::text END FROM up;
SELECT CASE WHEN count(*) = 4 THEN 'CHECK_OK 4' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (code = 'CN0001' AND md5(exclude_kw) = '47e88628b2211ff61dccdd15e9fb906e') OR (code = 'CN0002' AND md5(search_kw) = '47e88628b2211ff61dccdd15e9fb906e') OR (code = 'CN0003' AND md5(exclude_kw) = '47e88628b2211ff61dccdd15e9fb906e') OR (code = 'CN0004' AND md5(search_kw) = 'cd36d603d8a78e03af6e51ecadfac3ba');
COMMIT;
SELECT 'ROLLBACK_DONE';
