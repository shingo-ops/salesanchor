/**
 * 下書きの請求書の支払方法を選び直す（invoice-create-portfolio 便D・design.md §3-2・§6）。
 *
 * 候補は請求書の材料（GET /invoices/draft-context?invoice_id=…）だけから出す。打ち込み欄は置かない。
 * 保存は PATCH /invoices/{id} の payment_method_ref だけ（口座番号などは送らない・持たない）。
 * 出す条件（下書き・作る権限と直す権限の両方）は呼び出し側が決める。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import { Button } from "../../components/Button";
import { Select } from "../../components/Select";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  draftContextPathForInvoice,
  effectivePaymentKey,
  paymentChoicesFor,
  paymentKey,
  paymentRefFromKey,
  type DraftContext,
} from "../../lib/invoiceDraftContext";

export interface InvoicePaymentPickerProps {
  invoiceId: string;
  currency: string;
  onSaved: () => void;
}

export function InvoicePaymentPicker({ invoiceId, currency, onSaved }: InvoicePaymentPickerProps) {
  const { t } = useTranslation();
  const ctxQ = useApiQuery<DraftContext>(draftContextPathForInvoice(invoiceId));
  const rawCtx: unknown = ctxQ.data;
  const ctx = rawCtx !== null && typeof rawCtx === "object" && !Array.isArray(rawCtx) ? (rawCtx as DraftContext) : null;
  const choices = paymentChoicesFor(ctx, currency);
  const [chosen, setChosen] = useState("");
  const value = effectivePaymentKey(choices, chosen);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const ctxError = ctxQ.error ? (ctxQ.error instanceof Error ? ctxQ.error.message : t("common.fetchError")) : "";

  const save = async () => {
    const ref = paymentRefFromKey(choices, value);
    if (ref === null) return;
    setSaving(true);
    setError("");
    try {
      await api.patch(`/invoices/${invoiceId}`, { payment_method_ref: ref });
      setChosen("");
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  if (ctxError !== "") {
    return <p className="error-message" data-testid="invoice-detail-payment-error">{ctxError}</p>;
  }
  if (ctx !== null && choices.length === 0) {
    return <p data-testid="invoice-detail-payment-none">{t("invoiceForm.noPaymentMethods")}</p>;
  }
  return (
    <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end", flexWrap: "wrap" }}>
      <Select
        label={t("invoiceForm.changePayment")}
        value={value}
        onChange={(e) => setChosen(e.target.value)}
        placeholder={t("invoiceForm.paymentPlaceholder")}
        options={choices.map((p) => ({
          value: paymentKey(p),
          label: p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]),
        }))}
        data-testid="invoice-detail-payment-select"
      />
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={save}
        loading={saving}
        disabled={value === "" || saving}
        data-testid="invoice-detail-payment-save"
      >
        {t("common.save")}
      </Button>
      {error !== "" && <p className="error-message" role="alert">{error}</p>}
    </div>
  );
}
