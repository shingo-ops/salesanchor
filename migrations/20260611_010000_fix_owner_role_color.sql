-- Migration: オーナーロールの色を「危険の赤」からインディゴに変更
--
-- 背景:
--   DEFAULT_ROLES でオーナーの color が #ef4444（赤）に設定されていたが、
--   赤は statusPresentation.ts で "danger（失敗/エラー/期限超過）" に予約されており
--   「最高権限」を表すオーナーに赤を使うのは意味的誤用。
--   インディゴ #6366f1 は権限レベルを表す意味ニュートラルな色。
--
-- 対象:
--   全テナントスキーマ（tenant_NNN）の roles テーブル
--   条件: is_system = TRUE かつ color = '#ef4444'（旧既定値のまま変更されていない行のみ）
--
-- 安全性:
--   - is_system = TRUE: オーナー固有のフラグ（コメント tenant.py:39 参照）
--   - color = '#ef4444': 旧既定値のままのテナントのみ対象（カスタム色は保護）
--   - 冪等: 2回目以降は WHERE 条件に一致する行がないため no-op
--   - 自由入力の表示名（name）では絞り込まない
--
-- ロールバック:
--   同型の UPDATE で '#6366f1' → '#ef4444' に戻すこと（下記 DOWN コメント参照）
--
-- DOWN（ロールバック用・手動実行のみ・本番デプロイでは実行しない）:
--   UPDATE {schema}.roles SET color = '#ef4444', updated_at = NOW()
--   WHERE is_system = TRUE AND color = '#6366f1';

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
       WHERE is_system = TRUE AND color = ''#ef4444''',
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
