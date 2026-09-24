-- 仕入元マスタ name 重複解消
-- 21組の旧SUP-xxx（line_name=NULL）→ 新SP-xxxxx（line_name あり）への統合
-- 実行条件: 旧レコードが is_active=TRUE の場合のみ動作（冪等）
--
-- 手順:
--   DRY-RUN: BEGIN → 確認 → ROLLBACK
--   本番:    BEGIN → 確認 → COMMIT

BEGIN;

-- IDマッピング（旧→新の21組、本番DB 2026-09-24 実測値に基づく）
-- CTE を1回定義して全ステップで参照する（冗長な VALUES 繰り返しを排除）
WITH id_map (old_id, new_id, name) AS (VALUES
  (329, 25542, 'INスタッフ'),
  (314, 25499, 'JUN OKUBAYASHI'),
  (301, 25547, 'kyosuke'),
  (303, 25496, 'SAMURAI-T'),
  (317, 25501, 'T'),
  (318, 25500, 'Yasu Kishi'),
  (295, 25494, 'yusuke'),
  (312, 26014, 'yuya'),
  (319, 25502, 'かあ'),
  (290, 25492, 'カンジン'),
  (33,  25536, 'シンソク'),
  (311, 25579, 'ヒロト'),
  (299, 25572, 'むらお'),
  (309, 25546, 'やまちゃん'),
  (300, 25618, '三海'),
  (327, 25505, '平田光希'),
  (315, 25643, '村上 宝聡'),
  (308, 25498, '株式会社N&U'),
  (328, 25506, '武'),
  (316, 25596, '竹内'),
  (325, 25605, '馬場和也')
)
-- 安全確認: マッピングの旧IDが全てis_active=TRUEかチェック
SELECT m.old_id, m.new_id, m.name,
  old_s.is_active AS old_active, new_s.is_active AS new_active,
  old_s.supplier_code AS old_code, new_s.supplier_code AS new_code
FROM id_map m
JOIN public.suppliers old_s ON old_s.id = m.old_id
JOIN public.suppliers new_s ON new_s.id = m.new_id;

-- Step 1: supplier_prompts 引っ越し（最大15件）
-- UNIQUE(supplier_id) があるため、UPDATE で旧→新へ付け替え
-- 新側に既にpromptがある場合は競合するため、旧側のみ存在するものだけ移行
UPDATE public.supplier_prompts sp
SET supplier_id = m.new_id
FROM (VALUES
  (329, 25542), (314, 25499), (301, 25547), (303, 25496),
  (317, 25501), (318, 25500), (295, 25494), (312, 26014),
  (319, 25502), (290, 25492), (33,  25536), (311, 25579),
  (299, 25572), (309, 25546), (300, 25618), (327, 25505),
  (315, 25643), (308, 25498), (328, 25506), (316, 25596),
  (325, 25605)
) AS m(old_id, new_id)
WHERE sp.supplier_id = m.old_id
  AND NOT EXISTS (
    SELECT 1 FROM public.supplier_prompts sp2 WHERE sp2.supplier_id = m.new_id
  );

-- Step 2: supplier_knowledge_links 削除（47件、全て新側にDUPLICATEが存在）
DELETE FROM public.supplier_knowledge_links skl
USING (VALUES
  (329, 25542), (314, 25499), (301, 25547), (303, 25496),
  (317, 25501), (318, 25500), (295, 25494), (312, 26014),
  (319, 25502), (290, 25492), (33,  25536), (311, 25579),
  (299, 25572), (309, 25546), (300, 25618), (327, 25505),
  (315, 25643), (308, 25498), (328, 25506), (316, 25596),
  (325, 25605)
) AS m(old_id, new_id)
WHERE skl.supplier_id = m.old_id;

-- Step 3: inventory 引っ越し（31件、4名分）
UPDATE public.inventory inv
SET supplier_id = m.new_id
FROM (VALUES
  (329, 25542), (314, 25499), (301, 25547), (303, 25496),
  (317, 25501), (318, 25500), (295, 25494), (312, 26014),
  (319, 25502), (290, 25492), (33,  25536), (311, 25579),
  (299, 25572), (309, 25546), (300, 25618), (327, 25505),
  (315, 25643), (308, 25498), (328, 25506), (316, 25596),
  (325, 25605)
) AS m(old_id, new_id)
WHERE inv.supplier_id = m.old_id;

-- Step 4: discord_inbound_messages 引っ越し（10件）
UPDATE public.discord_inbound_messages dim
SET supplier_id = m.new_id
FROM (VALUES
  (329, 25542), (314, 25499), (301, 25547), (303, 25496),
  (317, 25501), (318, 25500), (295, 25494), (312, 26014),
  (319, 25502), (290, 25492), (33,  25536), (311, 25579),
  (299, 25572), (309, 25546), (300, 25618), (327, 25505),
  (315, 25643), (308, 25498), (328, 25506), (316, 25596),
  (325, 25605)
) AS m(old_id, new_id)
WHERE dim.supplier_id = m.old_id;

-- Step 5: 旧レコード無効化（21件）
-- is_active=TRUE の場合のみ UPDATE（冪等性保証）
UPDATE public.suppliers
SET is_active = FALSE,
    supplier_code = NULL
FROM (VALUES
  (329), (314), (301), (303), (317), (318), (295), (312),
  (319), (290), (33),  (311), (299), (309), (300), (327),
  (315), (308), (328), (316), (325)
) AS m(old_id)
WHERE public.suppliers.id = m.old_id
  AND public.suppliers.is_active = TRUE;

-- Step 6: 検証
-- 6a: name重複が0件であること（tenant_id IS NULL のアクティブ仕入元）
SELECT name, COUNT(*) AS cnt
FROM public.suppliers
WHERE is_active = TRUE AND tenant_id IS NULL
GROUP BY name
HAVING COUNT(*) > 1;

-- 6b: 旧21件が全てis_active=FALSEであること
SELECT id, name, supplier_code, is_active
FROM public.suppliers
WHERE id IN (329, 314, 301, 303, 317, 318, 295, 312, 319, 290, 33, 311, 299, 309, 300, 327, 315, 308, 328, 316, 325)
ORDER BY name;

-- 6c: 新SP-xxxxx側にsupplier_promptsが存在すること（最大15件）
SELECT sp.supplier_id, s.name, s.supplier_code
FROM public.supplier_prompts sp
JOIN public.suppliers s ON s.id = sp.supplier_id
WHERE sp.supplier_id IN (25542, 25499, 25547, 25496, 25501, 25500, 25494, 26014, 25502, 25492, 25536, 25579, 25572, 25546, 25618, 25505, 25643, 25498, 25506, 25596, 25605)
ORDER BY s.name;

-- DRY-RUN の場合: ROLLBACK;
-- 本番実行の場合: COMMIT;
COMMIT;
