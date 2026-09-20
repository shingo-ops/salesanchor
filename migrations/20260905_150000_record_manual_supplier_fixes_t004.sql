-- Migration: 20260905_150000_record_manual_supplier_fixes_t004
-- 目的: 2026-09-05 17:25〜17:45 に直接SQL で適用した仕入元マスタ変更4件を
--       migration として記録する（既に本番適用済み・再実行は冪等）
--
-- 変更内容:
--   (1) SP0007 name → '倉田 和博'（#3306/#3309 確認画面誤操作で上書きされた name の復旧）
--   (2) SP0184 name → 'overlap'  （同誤操作で上書きされた name の復旧）
--   (3) SP0203 '株式会社AXISグリーン' 新規登録 + LINE チャンネル行
--       （HTTP 422 で画面登録できなかったため直接 INSERT）
--   (4) SP0204 'Ryuta' 新規登録 + LINE チャンネル行（同上）
--
-- 冪等性:
--   UPDATE は "name <> '期待値'" 条件付き（既に正しければ 0 行変更）
--   INSERT は ON CONFLICT (code) DO NOTHING
--   supplier_channels は NOT EXISTS で重複挿入防止
--
-- 本番では既に適用済みのため、実行しても実質何も変更しない
--
-- 注意: import_jobs の DELETE（c32e7aa2-...）は一時データの削除であり
--       再現する意味がないため migration にしない（recon.md に事実として記録）

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    -- DEPRECATED: values now managed via app UI/CSV per ADR-155
    RAISE NOTICE '20260905_150000: no-op (values deprecated per ADR-155)';
END $$;
