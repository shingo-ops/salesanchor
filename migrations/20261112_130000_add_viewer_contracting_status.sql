-- ADR-1061 便2-1: 閲覧者の状態に contracting（契約手続き中）を足し、
-- 状態の履歴の操作に start_contract・form_sent・invoice_issued・confirm_payment を足す
-- 足すだけ（今の行の値は変えない）。RLS は付けない（名簿は public の全体共通の表のまま）
-- 冪等（CHECK は DROP CONSTRAINT IF EXISTS → ADD で同じ名前のまま付け替え）
-- ロールバック: contracting の行と新しい操作の行が無いことを確かめてから、
--   20261016_150000_add_viewer_accounts.sql の2つの CHECK に付け替え直す（PO GO）

BEGIN;

ALTER TABLE public.viewer_accounts DROP CONSTRAINT IF EXISTS ck_viewer_accounts_status;
ALTER TABLE public.viewer_accounts ADD CONSTRAINT ck_viewer_accounts_status
    CHECK (status IN ('pending', 'verified', 'trial', 'contracting', 'active', 'suspended'));
COMMENT ON COLUMN public.viewer_accounts.status IS 'pending／verified／trial／contracting／active／suspended。verified は将来用。contracting は契約手続き中（ADR-1061）';
COMMENT ON COLUMN public.viewer_accounts.trial_expires_at IS 'お試しと契約手続き中の、見られる期限';

ALTER TABLE public.viewer_status_changes DROP CONSTRAINT IF EXISTS ck_viewer_status_changes_action;
ALTER TABLE public.viewer_status_changes ADD CONSTRAINT ck_viewer_status_changes_action
    CHECK (action IN ('activate', 'suspend', 'unsuspend', 'extend', 'start_trial',
                      'start_contract', 'form_sent', 'invoice_issued', 'confirm_payment'));
COMMENT ON COLUMN public.viewer_status_changes.action IS 'activate／suspend／unsuspend／extend／start_trial／start_contract／form_sent／invoice_issued／confirm_payment';

COMMIT;
