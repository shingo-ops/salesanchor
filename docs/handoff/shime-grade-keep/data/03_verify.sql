-- limit=500
SELECT 'VERIFY' k, id::text, code, canonical, right(search_kw, 20) tail,
       (search_kw LIKE '%,切れ込み')::text ends_with_word
FROM ai_ro.public__line_conditions WHERE search_kw LIKE '%切れ込み%' OR coalesce(exclude_kw,'') LIKE '%切れ込み%'
