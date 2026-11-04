-- 配信先（シート）とお客さん（閲覧者の名簿）をつなぐ列（追加のみ・冪等）
-- 名簿の行が消えると配信先の行も消える（ON DELETE CASCADE。SET NULL だと特定の人用でないシートに化けて配信が再開するため使わない）
-- 1人1シートまで: NULL でない値は1回だけ（部分一意索引）。NULL は何件でもよい
-- ロールバック: 列と索引は残してコードが使わない（削除は別便・PO GO）

ALTER TABLE public.tcg_distribution_targets
    ADD COLUMN IF NOT EXISTS viewer_account_id BIGINT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_tcg_distribution_targets_viewer_account_id'
          AND conrelid = 'public.tcg_distribution_targets'::regclass
    ) THEN
        ALTER TABLE public.tcg_distribution_targets
            ADD CONSTRAINT fk_tcg_distribution_targets_viewer_account_id
            FOREIGN KEY (viewer_account_id) REFERENCES public.viewer_accounts(id) ON DELETE CASCADE;
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tcg_distribution_targets_viewer_account_id
    ON public.tcg_distribution_targets (viewer_account_id)
    WHERE viewer_account_id IS NOT NULL;

COMMENT ON COLUMN public.tcg_distribution_targets.viewer_account_id IS 'この配信先を使うお客さん（閲覧者の名簿の番号）。NULL は特定の人用でないシート。名簿の行が消えると配信先も消える';
