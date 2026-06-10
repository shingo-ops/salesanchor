-- Migration: オーナーロールの色を「危険の赤」からインディゴに変更
--
-- 背景:
--   DEFAULT_ROLES でオーナーの color が #ef4444（赤）に設定されていたが、
--   赤は statusPresentation.ts で "danger（失敗/エラー/期限超過）" に予約されており
--   「最高権限」を表すオーナーに赤を使うのは意味的誤用。
--   インディゴ #6366f1 は権限レベルを表す意味ニュートラルな色。
--
-- 対象行の特定（3条件の AND）:
--   1. is_system = TRUE   — システムロールのみ
--   2. color = '#ef4444'  — 旧既定値のまま変更されていない行のみ（カスタム色は保護）
--   3. priority = 1000    — オーナー固有の優先度（tenant.py:45 のみで定義。他ロールは900以下）
--
-- 補足（is_system だけでは不十分な理由）:
--   migration 021:42 / 023:42 で「システム管理者」にも is_system=TRUE が付与されている。
--   ただしシステム管理者の color は #9b59b6 / #a855f7（紫系）であり #ef4444 には一致しない。
--   priority 1000 はオーナーのみ（migration SQL での付与なし・tenant.py:45 のみ）。
--   3条件の AND により「オーナー、かつ旧赤のまま」の行にのみ一致することを保証する。
--
-- 冪等性:
--   初回実行後 color が #6366f1 になるため、2回目以降は WHERE に一致する行なし → no-op。
--
-- ロールバック（手動実行のみ・本番デプロイでは実行しない）:
--   UPDATE {schema}.roles SET color = '#ef4444', updated_at = NOW()
--   WHERE is_system = TRUE AND color = '#6366f1' AND priority = 1000;

DO $$
DECLARE
  r RECORD;
  updated_count INTEGER;
  total_updated INTEGER := 0;
BEGIN
  FOR r IN
    SELECT nspname
    FROM pg_namespace
    WHERE nspname ~ '^tenant_[0-9]+$'
    ORDER BY nspname
  LOOP
    EXECUTE format(
      'UPDATE %I.roles
         SET color = ''#6366f1'', updated_at = NOW()
       WHERE is_system = TRUE
         AND color     = ''#ef4444''
         AND priority  = 1000',
      r.nspname
    );
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    IF updated_count > 0 THEN
      RAISE NOTICE 'schema=%: owner role color updated (#ef4444 → #6366f1)', r.nspname;
      total_updated := total_updated + updated_count;
    END IF;
  END LOOP;

  RAISE NOTICE '--- fix_owner_role_color 完了: % 行を更新 ---', total_updated;
END $$;
