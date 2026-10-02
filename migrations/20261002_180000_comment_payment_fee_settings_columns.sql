-- §D01 補完: payment_fee_settings 全カラムに COMMENT ON COLUMN を付与
-- 後から見直しても各値の意味が分かるようにする（PO方針: 全migration・schemaのデフォルト仕様）

COMMENT ON COLUMN public.payment_fee_settings.id
    IS '主キー（自動採番）';

COMMENT ON COLUMN public.payment_fee_settings.tenant_id
    IS 'テナントID。NULLは全テナント共用デフォルト（運営者管理）、値ありはテナント独自設定';

COMMENT ON COLUMN public.payment_fee_settings.service
    IS '決済サービス名（例: paypal, wise, stripe）。将来サービス追加時もこの列で区別';

COMMENT ON COLUMN public.payment_fee_settings.fee_type
    IS '手数料種別。サービス内の手数料カテゴリ（例: receiving_domestic=国内受取, withdrawal=出金, fx_receiving=為替受取時）';

COMMENT ON COLUMN public.payment_fee_settings.rate_pct
    IS '料率（%）。手数料計算式: 対象金額 × rate_pct / 100 + fixed_amount。0の場合は固定額のみ適用';

COMMENT ON COLUMN public.payment_fee_settings.fixed_amount
    IS '固定手数料額（通貨単位）。rate_pctと併用: 手数料 = 金額 × rate_pct% + fixed_amount';

COMMENT ON COLUMN public.payment_fee_settings.threshold
    IS '閾値金額。threshold_ruleと組み合わせて適用条件を決定（例: 50000=5万円）。NULLは無条件適用';

COMMENT ON COLUMN public.payment_fee_settings.threshold_rule
    IS '閾値ルール。above=閾値以上で適用, below=閾値未満で適用。thresholdとセットで使用';

COMMENT ON COLUMN public.payment_fee_settings.currency
    IS '通貨コード（ISO 4217、例: JPY, USD）。デフォルトJPY';

COMMENT ON COLUMN public.payment_fee_settings.effective_from
    IS '適用開始日。この日付以降に有効な料率。料金改定時は新行を追加しeffective_toで旧行を終了';

COMMENT ON COLUMN public.payment_fee_settings.effective_to
    IS '適用終了日。NULLは現在有効。料金改定時にこの日付を設定して旧料率を無効化';

COMMENT ON COLUMN public.payment_fee_settings.source_url
    IS '料率の出典URL（公式料金ページ等）。根拠追跡用';

COMMENT ON COLUMN public.payment_fee_settings.note
    IS '補足説明（日本語）。管理画面での表示や運用メモに使用';

COMMENT ON COLUMN public.payment_fee_settings.created_at
    IS 'レコード作成日時（自動設定）';

COMMENT ON COLUMN public.payment_fee_settings.updated_at
    IS 'レコード最終更新日時（トリガーで自動更新）';
