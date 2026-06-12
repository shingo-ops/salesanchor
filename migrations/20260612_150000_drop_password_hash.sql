-- ADR 実装: password_hash 列廃止（PO決定 2026-06-12）
-- 認証は Firebase Authentication が担当しており DB への password_hash 保存は不要。
-- 攻撃面削減のため public.users から列を物理削除する。
--
-- 冪等性: DROP COLUMN IF EXISTS により再実行 no-op
-- 影響テーブル: public.users のみ（tenant スキーマには password_hash 列なし）
-- ロールバック: 不可逆操作（PO確認済み）

ALTER TABLE public.users DROP COLUMN IF EXISTS password_hash;
