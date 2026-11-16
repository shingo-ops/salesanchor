/**
 * 請求書作成ページの「通貨・支払方法・送料・合計」の区切り（invoice-create-portfolio 便D・design.md §3-2）。
 *
 * 人は選ぶだけ。通貨・支払方法の候補はサーバーの材料（draft-context）だけから出す（直書きしない）。
 * 送料は「送料を請求しない」か、FedEx の見積を出して 1 つ選ぶ（打ち込み欄は置かない・K4）。
 * 合計・税・関税はサーバーの試算（preview）の答えをそのまま見せる。答えが無い所は「未計算」と理由を出す（K5）。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Select } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import { FedExRateModal } from "../../components/FedExRateModal";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  formatMoney,
  fxRateFor,
  paymentKey,
  uncomputedReasonKey,
  type DraftContext,
  type DraftContextPayment,
  type InvoicePreview,
  type ShippingChoice,
} from "../../lib/invoiceDraftContext";

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
  shipping: ShippingChoice | null;
  shippingStale: boolean;
  onShippingNone: () => void;
  onShippingClear: () => void;
  quoteOpen: boolean;
  onQuoteOpen: () => void;
  onQuoteClose: () => void;
  onRateSelected: (fee: number, rateCurrency: string, serviceType: string | null, carrier: string) => void;
  totalWeight: number;
  preview: InvoicePreview | null;
  previewError: string;
}

export function InvoicePaymentTotalsSection(props: InvoicePaymentTotalsSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    ctx, currencyOptions, currency, onCurrencyChange, paymentChoices, paymentValue, onPaymentChange,
    notes, onNotesChange, shipping, shippingStale, onShippingNone, onShippingClear,
    quoteOpen, onQuoteOpen, onQuoteClose, onRateSelected, totalWeight, preview, previewError,
  } = props;

  const fx = currency !== "" ? fxRateFor(ctx, currency) : null;
  const paymentLabel = (p: DraftContextPayment) =>
    p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]);
  const canQuote = ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null;
  const shippingSelectValue = shipping === null ? "" : shipping.mode;
  const money = (v: string | null | undefined) => formatMoney(v, currency) ?? t("invoiceForm.notComputed");

  return (
    <div data-testid="invoice-payment-totals">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)", marginBottom: "var(--space-4)" }}>
        <div>
          <Select
            label={t("invoiceForm.currency")}
            required
            fullWidth
            value={currency}
            onChange={(e) => onCurrencyChange(e.target.value)}
            placeholder={t("invoiceForm.currencyPlaceholder")}
            options={currencyOptions.map((c) => ({ value: c, label: c }))}
            data-testid="invoice-currency-select"
          />
          {currencyOptions.length === 0 && ctx !== null && (
            <p data-testid="invoice-no-currency">{t("invoiceForm.noCurrency")}</p>
          )}
          {fx !== null && (
            <p style={{ color: "var(--text-secondary)" }} data-testid="invoice-fx-line">
              {t("invoiceForm.fxRateLine", { currency: fx.currency, rate: fx.rate, at: fx.fetched_at ?? "-" })}
            </p>
          )}
        </div>
        <div>
          {paymentChoices.length > 0 ? (
            <Select
              label={t("invoiceForm.payment")}
              required
              fullWidth
              value={paymentValue}
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
        </div>
      </div>

      <div className="form-group" style={{ marginBottom: "var(--space-4)" }}>
        <label>{t("common.notes")}</label>
        <TextFieldControl value={notes} onChange={(e) => onNotesChange(e.target.value)} data-testid="invoice-notes" />
      </div>

      <div style={{ marginBottom: "var(--space-4)" }}>
        <Select
          label={t("invoiceForm.shipping")}
          required
          value={shippingSelectValue}
          onChange={(e) => {
            if (e.target.value === "none") onShippingNone();
            else onShippingClear();
          }}
          placeholder={t("invoiceForm.shippingPlaceholder")}
          options={[
            { value: "none", label: t("invoiceForm.shippingNone") },
            ...(shipping !== null && shipping.mode === "calculate"
              ? [{ value: "calculate", label: t("invoiceForm.shippingChosen", { carrier: shipping.carrier, service: shipping.service_type ?? "-", fee: formatMoney(shipping.fee, shipping.currency) ?? String(shipping.fee) }) }]
              : []),
          ]}
          data-testid="invoice-shipping-select"
        />
        <div style={{ marginTop: "var(--space-2)" }}>
          <Button type="button" variant="secondary" size="sm" onClick={onQuoteOpen} disabled={!canQuote} data-testid="invoice-shipping-quote">
            {t("invoiceForm.shippingQuote")}
          </Button>
        </div>
        {!canQuote && ctx !== null && (
          <p style={{ color: "var(--text-secondary)" }} data-testid="invoice-shipping-needs-countries">{t("invoiceForm.shippingNeedsCountries")}</p>
        )}
        {shippingStale && (
          <p className="warning-message" data-testid="invoice-shipping-stale">{t("invoiceForm.shippingStale")}</p>
        )}
        {quoteOpen && ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null && (
          <FedExRateModal
            open={quoteOpen}
            onClose={onQuoteClose}
            originCountryCode={ctx.origin_country_code}
            destinationCountryCode={ctx.destination_country_code}
            destinationPostalCode={ctx.destination_postal_code ?? undefined}
            weightKg={totalWeight}
            onSelectRate={(fee, rateCurrency, serviceType, carrier) => onRateSelected(fee, rateCurrency, serviceType, carrier ?? "")}
          />
        )}
      </div>

      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "var(--space-2) var(--space-4)", marginBottom: "var(--space-4)" }}>
        <dt>{t("invoiceForm.totalWeight")}</dt>
        <dd data-testid="invoice-total-weight">{totalWeight.toLocaleString()} kg</dd>
        <dt>{t("invoiceForm.subtotal")}</dt>
        <dd data-testid="invoice-total-subtotal">{preview ? money(preview.subtotal) : t("invoiceForm.notComputed")}</dd>
        <dt>{t("invoiceForm.shippingFee")}</dt>
        <dd data-testid="invoice-total-shipping">{preview ? money(preview.shipping_fee) : t("invoiceForm.notComputed")}</dd>
        <dt>{t("invoiceForm.tax", { rate: preview?.tax_rate_percent ?? "-" })}</dt>
        <dd data-testid="invoice-total-tax">{preview ? money(preview.tax_amount) : t("invoiceForm.notComputed")}</dd>
        <dt>{preview?.duty_label ?? t("invoiceForm.duty")}</dt>
        <dd data-testid="invoice-total-duty">
          {preview ? money(preview.duty_amount) : t("invoiceForm.notComputed")}
          {preview && preview.duty_components.length > 0 && (
            <ul data-testid="invoice-duty-components">
              {preview.duty_components.map((c, i) => (
                <li key={i}>{c.label}: {money(c.amount)}</li>
              ))}
            </ul>
          )}
        </dd>
        <dt>{t("invoiceForm.total")}</dt>
        <dd data-testid="invoice-total-amount" style={{ fontWeight: "var(--font-weight-bold)", fontSize: "var(--font-lg)" }}>
          {preview ? money(preview.total_amount) : t("invoiceForm.notComputed")}
        </dd>
      </dl>
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
        <p className="error-message" data-testid="invoice-preview-error">{previewError}</p>
      )}
    </div>
  );
}
