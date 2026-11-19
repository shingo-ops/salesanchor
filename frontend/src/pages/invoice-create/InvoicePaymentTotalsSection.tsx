/**
 * 請求書作成ページの「支払いと合計」の中身（invoice-create-portfolio design-v2 §3-1・§3-5・K5〜K8）。
 *
 * 3 列（ThreeColumn。狭い画面では縦 1 列）:
 *   左: 通貨・支払方法・発送メモ（候補はサーバーの材料 draft-context だけ。直書きしない）
 *   中: 総重量と便ごとの送料の一覧（POST /invoices/draft-shipping-quotes の答え）。1 つ選ぶか「送料を請求しない」。
 *       各行に出所の印（ライブ／静的。ADR-125 D6）。
 *   右: 合計枠（TotalsBox）。額はサーバーの試算（preview）の答えをそのまま見せる。答えが無い所は「未計算」と理由。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { LoadingBlock } from "../../components/loading";
import { Radio } from "../../components/Radio";
import { Select } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { ThreeColumn } from "../../components/ThreeColumn";
import { TotalsBox } from "../../components/TotalsBox";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  formatMoney,
  fxRateFor,
  paymentKey,
  uncomputedReasonKey,
  type DraftContext,
  type DraftContextPayment,
  type InvoicePreview,
} from "../../lib/invoiceDraftContext";
import { rateFee, type DraftShippingQuotesState, type DraftShippingRate } from "../quote-create/useDraftShippingQuotes";

/** 送料の選択の値。「送料を請求しない」は SHIPPING_NONE、便は shippingRateKey */
export const SHIPPING_NONE = "none";

export function shippingRateKey(rate: DraftShippingRate): string {
  return `${rate.source}|${rate.carrier}|${rate.service_type ?? ""}`;
}

export interface InvoicePaymentTotalsSectionProps {
  ctx: DraftContext | null;
  currencyOptions: string[];
  currency: string;
  onCurrencyChange: (next: string) => void;
  paymentChoices: DraftContextPayment[];
  paymentValue: string;
  onPaymentChange: (next: string) => void;
  notes: string;
  onNotesChange: (next: string) => void;
  totalWeight: number;
  shippingQuotes: DraftShippingQuotesState;
  /** 選んだ送料の値（"" は未選択） */
  shippingPick: string;
  onShippingPick: (next: string) => void;
  preview: InvoicePreview | null;
  previewError: string;
  disabled?: boolean;
}

export function InvoicePaymentTotalsSection(props: InvoicePaymentTotalsSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    ctx, currencyOptions, currency, onCurrencyChange, paymentChoices, paymentValue, onPaymentChange,
    notes, onNotesChange, totalWeight, shippingQuotes, shippingPick, onShippingPick, preview, previewError,
    disabled = false,
  } = props;

  const fx = currency !== "" ? fxRateFor(ctx, currency) : null;
  const paymentLabel = (p: DraftContextPayment) =>
    p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]);
  const money = (v: string | null | undefined) => formatMoney(v, currency) ?? t("invoiceForm.notComputed");
  const rates = shippingQuotes.quotes?.results ?? [];
  const liveError = shippingQuotes.quotes?.live_error ?? null;
  const canQuote = ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null;

  const left = (
    <Stack direction="column" gap="3">
      <div data-testid="invoice-currency">
        <Select
          label={t("invoiceForm.currency")}
          required
          fullWidth
          value={currency}
          disabled={disabled}
          onChange={(e) => onCurrencyChange(e.target.value)}
          placeholder={t("invoiceForm.currencyPlaceholder")}
          options={currencyOptions.map((c) => ({ value: c, label: c }))}
          helperText={
            fx !== null
              ? t("invoiceForm.fxRateLine", { currency: fx.currency, rate: fx.rate, at: fx.fetched_at ?? "-" })
              : currencyOptions.length === 0 && ctx !== null
                ? t("invoiceForm.noCurrency")
                : undefined
          }
          data-testid="invoice-currency-select"
        />
      </div>
      {paymentChoices.length > 0 ? (
        <Select
          label={t("invoiceForm.payment")}
          required
          fullWidth
          value={paymentValue}
          disabled={disabled}
          onChange={(e) => onPaymentChange(e.target.value)}
          placeholder={t("invoiceForm.paymentPlaceholder")}
          options={paymentChoices.map((p) => ({ value: paymentKey(p), label: paymentLabel(p) }))}
          data-testid="invoice-payment-select"
        />
      ) : ctx !== null && ctx.issuer_region !== null ? (
        <Callout variant="info" title={t("invoiceForm.noPaymentMethods")}>
          <Button type="button" variant="secondary" size="sm" onClick={() => navigate("/management-center/tenant-profile")} data-testid="invoice-open-tenant-profile">
            {t("invoiceForm.openTenantProfile")}
          </Button>
        </Callout>
      ) : null}
      <TextField
        label={t("invoiceForm.shippingMemo")}
        fullWidth
        value={notes}
        disabled={disabled}
        onChange={(e) => onNotesChange(e.target.value)}
        data-testid="invoice-notes"
      />
    </Stack>
  );

  const middle = (
    <Stack direction="column" gap="2">
      <p data-testid="invoice-total-weight">{t("invoiceForm.totalWeightLine", { value: totalWeight })}</p>
      <div role="radiogroup" aria-label={t("invoiceForm.shipping")} data-testid="invoice-shipping-list">
        <Stack direction="column" gap="2">
          <Radio
            name="invoice-shipping"
            value={SHIPPING_NONE}
            label={t("invoiceForm.shippingNone")}
            checked={shippingPick === SHIPPING_NONE}
            disabled={disabled}
            onChange={() => onShippingPick(SHIPPING_NONE)}
            data-testid="invoice-shipping-none"
          />
          {rates.map((r) => {
            const key = shippingRateKey(r);
            const fee = rateFee(r);
            return (
              <Stack key={key} direction="row" gap="2">
                <Radio
                  name="invoice-shipping"
                  value={key}
                  label={t("invoiceForm.shippingRateLine", {
                    carrier: r.carrier,
                    service: r.service_name ?? r.service_type ?? "-",
                    fee: fee === null ? "-" : formatMoney(fee, r.currency) ?? String(fee),
                  })}
                  description={r.transit_days !== null ? t("invoiceForm.transitDays", { count: r.transit_days }) : undefined}
                  checked={shippingPick === key}
                  disabled={disabled || fee === null}
                  onChange={() => onShippingPick(key)}
                  data-testid={`invoice-shipping-rate-${key}`}
                />
                <Badge variant={r.source === "fedex_live" ? "success" : "neutral"} size="sm">
                  {t(r.source === "fedex_live" ? "invoiceForm.sourceLive" : "invoiceForm.sourceStatic")}
                </Badge>
              </Stack>
            );
          })}
        </Stack>
      </div>
      {!canQuote && ctx !== null && (
        <p data-testid="invoice-shipping-needs-countries">{t("invoiceForm.shippingNeedsCountries")}</p>
      )}
      {canQuote && shippingQuotes.key === "" && (
        <p data-testid="invoice-shipping-needs-weight">{t("invoiceForm.shippingNeedsWeight")}</p>
      )}
      {shippingQuotes.loading && (
        <div data-testid="invoice-shipping-loading">
          <LoadingBlock inline label={t("invoiceForm.shippingLoading")} />
        </div>
      )}
      {shippingQuotes.error !== "" && (
        <Callout variant="warning" title={t("invoiceForm.shippingQuoteError")}>
          <span data-testid="invoice-shipping-error">{shippingQuotes.error}</span>
        </Callout>
      )}
      {liveError !== null && (
        <Callout variant="info" title={t("invoiceForm.fedexLiveUnavailable")}>
          <span data-testid="invoice-shipping-live-error">{liveError}</span>
        </Callout>
      )}
    </Stack>
  );

  const taxLabel = preview?.duty_label ?? t("invoiceForm.tax", { rate: preview?.tax_rate_percent ?? "-" });
  const taxValue = preview === null ? t("invoiceForm.notComputed") : preview.duty_label !== null ? money(preview.duty_amount) : money(preview.tax_amount);
  const right = (
    <Stack direction="column" gap="2">
      <div data-testid="invoice-totals">
        <TotalsBox
          rows={[
            { key: "subtotal", label: t("invoiceForm.subtotal"), value: <span data-testid="invoice-total-subtotal">{preview ? money(preview.subtotal) : t("invoiceForm.notComputed")}</span> },
            { key: "shipping", label: t("invoiceForm.shippingFee"), value: <span data-testid="invoice-total-shipping">{preview ? money(preview.shipping_fee) : t("invoiceForm.notComputed")}</span> },
            { key: "tax", label: taxLabel, value: <span data-testid="invoice-total-tax">{taxValue}</span> },
          ]}
          total={{ label: t("invoiceForm.total"), value: <span data-testid="invoice-total-amount">{preview ? money(preview.total_amount) : t("invoiceForm.notComputed")}</span> }}
        />
      </div>
      {preview && preview.uncomputed.length > 0 && (
        <Callout variant="warning" title={t("invoiceForm.uncomputedTitle")}>
          <ul data-testid="invoice-uncomputed">
            {preview.uncomputed.map((r) => (
              <li key={r} data-testid={`invoice-uncomputed-${r}`}>{t(uncomputedReasonKey(r))}</li>
            ))}
          </ul>
        </Callout>
      )}
      {previewError !== "" && (
        <Callout variant="warning" title={t("invoiceForm.previewErrorTitle")}>
          <span data-testid="invoice-preview-error">{previewError}</span>
        </Callout>
      )}
    </Stack>
  );

  return (
    <div data-testid="invoice-payment-totals">
      <ThreeColumn gap="4">
        <div data-testid="invoice-col-payment">{left}</div>
        <div data-testid="invoice-col-shipping">{middle}</div>
        <div data-testid="invoice-col-totals">{right}</div>
      </ThreeColumn>
    </div>
  );
}
