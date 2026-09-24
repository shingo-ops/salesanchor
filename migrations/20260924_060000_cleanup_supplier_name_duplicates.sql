-- 仕入元マスタ name 重複解消
-- 21組の旧SUP-xxx（line_name=NULL）→ 新SP-xxxxx（line_name あり）への統合
--
-- ⚠️ 本番実行済み（2026-09-24）: 全ステップ合格・本番適用完了
--    Step 1〜5 は既に本番DB で実行済みのため、このファイルは検証SELECTのみ保持
--    再実行時は全ステップ 0件（冪等）
--    PR #3745 本文に実行記録・検証結果を記録済み
--
-- 実行済みステップ（2026-09-24 本番DB）:
--   Step 1: supplier_prompts 引っ越し   → 15件
--   Step 2: supplier_knowledge_links 削除 → 47件
--   Step 3: inventory 引っ越し          → 31件
--   Step 4: discord_inbound_messages 引っ越し → 10件
--   Step 5: 旧レコード無効化            → 21件
--
-- ADR-085 参照（supplier マスタ SSOT）

-- 検証: name重複が0件であること（tenant_id IS NULL のアクティブ仕入元）
SELECT name, COUNT(*) AS cnt
FROM public.suppliers
WHERE is_active = TRUE AND tenant_id IS NULL
GROUP BY name
HAVING COUNT(*) > 1;
