/**
 * 請求書の下書き（ADR-1056 段2）。送る欄は全部見せて、全部直せる。
 * 「作る」は今の請求書の作成画面と同じ口 POST /invoices を、本人のログインで呼ぶ。
 *
 * invoice-create-portfolio 便D（design.md §3-2）: 通貨と支払方法の候補は請求書の材料
 * （GET /invoices/draft-context）から出す（直書きしない）。チャットでは送料の見積を出さないので、
 * 「送料を請求しない」に人がチェックしたときだけ作れる。送料を付けるときは請求書の作成画面で作る。
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import {
  PAYMENT_METHOD_LABEL_KEYS,
  currencyChoices,
  draftContextPath,
  effectivePaymentKey,
  paymentChoicesFor,
  paymentKey,
  paymentRefFromKey,
  resolveCurrency,
  type DraftContext,
} from "../../lib/invoiceDraftContext";
import { Button } from "../../components/Button";
import { Checkbox } from "../../components/Checkbox";
import { Select } from "../../components/Select";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import CompanyContactSelector, {
  type CompanyContactSelectorValue,
} from "../../components/CompanyContactSelector";
import type { Candidates, InvoiceDraftData } from "./secretaryApi";

interface Props {
  draft: InvoiceDraftData;
  candidates: Candidates;
  onCreated: (invoiceId: number) => void;
  onCancel: () => void;
}

interface ItemState {
  name: string;
  quantity: string;
  unitPrice: string;
}

/** 数は整数で 1 以上（口は int・ge=1） */
function isValidQuantity(value: string): boolean {
  return /^\d+$/.test(value.trim()) && Number(value) >= 1;
}

/** 保存側は小数 2 けたまで（backend/app/schemas/invoice.py:35）。"1e-7" のような書き方も 3 けた以上とみなす */
function hasTooManyDecimals(value: string): boolean {
  const trimmed = value.trim();
  return /\.\d{3,}$/.test(trimmed) || /e-/i.test(trimmed);
}

function isValidUnitPrice(value: string): boolean {
  const trimmed = value.trim();
  return trimmed !== "" && Number.isFinite(Number(trimmed)) && Number(trimmed) >= 0 && !hasTooManyDecimals(trimmed);
}

export function SecretaryDraftInvoice({ draft, candidates, onCreated, onCancel }: Props) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ItemState[]>(() =>
    draft.items.map((i) => ({
      name: i.product_name,
      quantity: String(i.quantity),
      unitPrice: i.unit_price === null ? "" : String(i.unit_price),
    })),
  );
  // 秘書が読んだ通貨。使う通貨は材料の候補にあるときだけ（resolveCurrency）。
  const [currencyChoice, setCurrencyChoice] = useState<string>(draft.currency ?? "");
  const [paymentChoice, setPaymentChoice] = useState("");
  const [shippingNone, setShippingNone] = useState(false);
  const [dueDate, setDueDate] = useState(draft.due_date ?? "");
  const [notes, setNotes] = useState(draft.notes ?? "");
  const [changing, setChanging] = useState(false);
  const [customer, setCustomer] = useState<CompanyContactSelectorValue>(() => ({
    companyId: candidates.companies.length === 1 ? candidates.companies[0].id : null,
    contactId: candidates.companies.length === 1 && candidates.contacts.length === 1 ? candidates.contacts[0].id : null,
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // 会社が 1 件に決まり、担当者の候補もあるときだけ候補の選び方。それ以外は今の選択の金型
  const candidateMode = !changing && candidates.companies.length === 1 && candidates.contacts.length >= 1;
  const selectorCompanies =
    !changing && candidates.companies.length >= 1
      ? candidates.companies.map((c) => ({ id: c.id, company_code: "", name: c.name }))
      : undefined;

  const itemsValid =
    items.length > 0 &&
    items.every((i) => i.name.trim() !== "" && isValidQuantity(i.quantity) && isValidUnitPrice(i.unitPrice));
  const priceMissing = items.some((i) => i.unitPrice.trim() === "");
  const priceTooPrecise = items.some((i) => hasTooManyDecimals(i.unitPrice));
  const customerReady = customer.companyId !== null && customer.contactId !== null;

  // 請求書の材料（会社と担当者が決まったときだけ取りに行く）
  const ctxQ = useApiQuery<DraftContext>(
    customerReady ? draftContextPath(customer.companyId as number, customer.contactId) : "/invoices/draft-context",
    { enabled: customerReady },
  );
  const rawCtx: unknown = ctxQ.data;
  const ctx = customerReady && rawCtx !== null && typeof rawCtx === "object" && !Array.isArray(rawCtx) ? (rawCtx as DraftContext) : null;
  const currencyOptions = currencyChoices(ctx);
  const currency = resolveCurrency(ctx, currencyChoice);
  const paymentChoices = paymentChoicesFor(ctx, currency);
  const paymentValue = effectivePaymentKey(paymentChoices, paymentChoice);
  const paymentReady = paymentChoices.length === 0 || paymentValue !== "";
  const canCreate =
    itemsValid && customerReady && ctx !== null && ctx.issuer_region !== null && currency !== "" && paymentReady && shippingNone && !saving;

  const updateItem = (index: number, patch: Partial<ItemState>) =>
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)));

  const submit = async () => {
    if (!canCreate) return;
    setSaving(true);
    setError("");
    try {
      const inv = await api.post<{ id: number }>("/invoices", {
        company_id: customer.companyId,
        contact_id: customer.contactId,
        currency,
        shipping: { mode: "none" },
        payment_method_ref: paymentRefFromKey(paymentChoices, paymentValue),
        due_date: dueDate || null,
        notes: notes || null,
        items: items.map((i) => ({
          product_name: i.name.trim(),
          quantity: Number(i.quantity),
          unit_price: Number(i.unitPrice),
        })),
      });
      onCreated(inv.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
      setSaving(false);
    }
  };

  return (
    <div className="secretary-draft">
      <p className="secretary-draft__title">{t("secretary.invoice.title")}</p>

      {candidateMode ? (
        <div className="secretary-draft__section">
          <p className="secretary-draft__text">
            {t("secretary.invoice.company")}: {candidates.companies[0].name}
          </p>
          <Select
            fullWidth
            label={t("secretary.invoice.contact")}
            value={customer.contactId === null ? "" : String(customer.contactId)}
            onChange={(e) => {
              setPaymentChoice("");
              setCustomer({ companyId: customer.companyId, contactId: e.target.value ? Number(e.target.value) : null });
            }}
            placeholder={t("companyContactSelector.selectContact")}
            options={candidates.contacts.map((c) => ({ value: String(c.id), label: c.name }))}
          />
          <Button variant="ghost" size="sm" onClick={() => setChanging(true)}>
            {t("secretary.invoice.changeCustomer")}
          </Button>
        </div>
      ) : (
        <div className="secretary-draft__section">
          <CompanyContactSelector
            value={customer}
            onChange={(next) => { setPaymentChoice(""); setCustomer(next); }}
            companies={selectorCompanies}
          />
        </div>
      )}

      <div className="secretary-draft__section">
        {items.map((item, index) => (
          <div className="secretary-draft__item" key={index}>
            <TextField
              fullWidth
              label={t("secretary.invoice.itemName")}
              value={item.name}
              onChange={(e) => updateItem(index, { name: e.target.value })}
            />
            <TextField
              fullWidth
              label={t("secretary.invoice.quantity")}
              type="number"
              min={1}
              step={1}
              value={item.quantity}
              onChange={(e) => updateItem(index, { quantity: e.target.value })}
            />
            <TextField
              fullWidth
              label={t("secretary.invoice.unitPrice")}
              type="number"
              min={0}
              step={0.01}
              value={item.unitPrice}
              onChange={(e) => updateItem(index, { unitPrice: e.target.value })}
            />
          </div>
        ))}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setItems((prev) => [...prev, { name: "", quantity: "1", unitPrice: "" }])}
        >
          {t("secretary.invoice.addItem")}
        </Button>
        {priceMissing && <p className="secretary-draft__hint">{t("secretary.priceRequired")}</p>}
        {priceTooPrecise && <p className="secretary-draft__hint">{t("secretary.priceDecimals")}</p>}
      </div>

      <div className="secretary-draft__section">
        {ctx !== null && ctx.issuer_region === null && (
          <p className="secretary-draft__hint" data-testid="secretary-invoice-bill-to">{t("apiError.billToCountry")}</p>
        )}
        <Select
          fullWidth
          required
          label={t("secretary.invoice.currency")}
          value={currency}
          onChange={(e) => { setCurrencyChoice(e.target.value); setPaymentChoice(""); }}
          placeholder={t("invoiceForm.currencyPlaceholder")}
          options={currencyOptions.map((c) => ({ value: c, label: c }))}
          data-testid="secretary-invoice-currency"
        />
        {paymentChoices.length > 0 ? (
          <Select
            fullWidth
            required
            label={t("invoiceForm.payment")}
            value={paymentValue}
            onChange={(e) => setPaymentChoice(e.target.value)}
            placeholder={t("invoiceForm.paymentPlaceholder")}
            options={paymentChoices.map((p) => ({
              value: paymentKey(p),
              label: p.display_name !== null && p.display_name !== "" ? p.display_name : t(PAYMENT_METHOD_LABEL_KEYS[p.method_type]),
            }))}
            data-testid="secretary-invoice-payment"
          />
        ) : (
          ctx !== null && ctx.issuer_region !== null && (
            <p className="secretary-draft__hint" data-testid="secretary-invoice-no-payment">{t("invoiceForm.noPaymentMethods")}</p>
          )
        )}
        <Checkbox
          label={t("invoiceForm.shippingNone")}
          description={t("secretary.invoice.shippingNoneHelp")}
          checked={shippingNone}
          onChange={(e) => setShippingNone(e.target.checked)}
          data-testid="secretary-invoice-shipping-none"
        />
        <TextField
          fullWidth
          label={t("secretary.invoice.dueDate")}
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
        />
        <Textarea
          fullWidth
          label={t("secretary.invoice.notes")}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      {error && (
        <p className="secretary-draft__error" role="alert">
          {error}
        </p>
      )}
      <div className="secretary-draft__actions">
        <Button variant="secondary" size="sm" onClick={onCancel} disabled={saving}>
          {t("secretary.cancel")}
        </Button>
        <Button size="sm" onClick={submit} disabled={!canCreate} loading={saving}>
          {t("secretary.create")}
        </Button>
      </div>
    </div>
  );
}
