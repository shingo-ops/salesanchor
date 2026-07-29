-- deals.* 権限を本番DBから削除（deals廃止 deals-perms-rename）
--
-- 背景:
--   deals API・画面は便C(#3129)で削除済み。deals テーブルは便E(#3133)で DROP 済み。
--   deals.* 権限はチェックするコードがなく完全な浮き権限となっている。
--   本 migration で public.permissions の deals.* 4行を削除する。
--   role_permissions は FK ON DELETE CASCADE のため自動削除（全テナント合計70行）。
--
-- 冪等: deals.* が既に存在しない場合は 0行削除で正常終了。
-- 削除順序: role_permissions は CASCADE で自動。手動削除不要。
-- 本番適用前実測 (前recon 2026-07-29):
--   public.permissions deals.* 4行 (id=17,18,19,20)
--   role_permissions deals.* 70行 (5テナント×14行)
--   FK: role_permissions_permission_id_fkey ON DELETE CASCADE 確認済み

DELETE FROM public.permissions WHERE key LIKE 'deals.%';
-- CASCADE により全テナントの role_permissions.deals.* 付与行も削除される
