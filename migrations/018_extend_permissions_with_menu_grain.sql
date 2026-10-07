-- Phase 1 再設計 / Migration 018: public.permissions にメニュー粒度の権限を追加
--
-- 内容:
--   [1] 既存 public.permissions テーブルにメニュー粒度用の列を追加（NULL 許容）
--       - permission_group（chat / sales / settings / buddy / admin）
--       - display_name_jp / display_name_en（UI表示名）
--       - display_order（UI並び順）
--   [2] 新仕様（設計書第2弾 3-3）の19件をシード
--
-- 共存方針（2026-04-23 Q3 確定）:
--   - 既存 65件（key='customers.view' 等の CRUD 粒度）は**そのまま残す**
--   - 新 19件は key='menu.dashboard' 等のプレフィックス付きで追加
--   - 既存の role_permissions・アプリ層 API 認可は従来通り動作
--   - 新 19件はメニュー表示制御（サイドバー）用に別途使用
--
-- 実行方法:
--   docker compose exec postgres psql -U jarvis -d jarvis_db -f /migrations/018_extend_permissions_with_menu_grain.sql
--
-- 変更履歴:
--   2026-04-23: 初版作成

-- === [1] 既存 public.permissions に列追加 ===

ALTER TABLE public.permissions ADD COLUMN IF NOT EXISTS permission_group VARCHAR(50);
ALTER TABLE public.permissions ADD COLUMN IF NOT EXISTS display_name_jp VARCHAR(100);
ALTER TABLE public.permissions ADD COLUMN IF NOT EXISTS display_name_en VARCHAR(100);
ALTER TABLE public.permissions ADD COLUMN IF NOT EXISTS display_order INTEGER;

CREATE INDEX IF NOT EXISTS idx_permissions_group ON public.permissions (permission_group);
CREATE INDEX IF NOT EXISTS idx_permissions_display_order ON public.permissions (display_order);

COMMENT ON COLUMN public.permissions.permission_group IS
  'メニュー粒度権限のグループ（chat / sales / settings / buddy / admin）。CRUD粒度権限は NULL';
COMMENT ON COLUMN public.permissions.display_name_jp IS
  'UI表示用の日本語名。メニュー権限のみ入力、CRUD権限は NULL（description を流用）';
COMMENT ON COLUMN public.permissions.display_order IS
  'サイドバー表示順。メニュー権限のみ設定';

-- === [2] 新仕様 19件のシード（chat: 6件 / sales: 5件 / buddy: 2件 / admin: 5件 / settings: 1件）===

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07): menu.* 19 キーの INSERT を外した（本番には既にある。新しい権限キーは migration では足さない）。列の追加・索引・コメントは構造なので残す。
