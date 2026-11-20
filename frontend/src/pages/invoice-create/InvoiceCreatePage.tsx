/**
 * 請求書作成ページ（invoice-create-portfolio design-v2 §3-1。見本の「見た目と操作」）。
 *
 * 4 枚のカードを上から: 発送先 → 支払いと合計 → 商品一覧 → 操作（K1）。
 *   - 発送先: 顧客を選ぶと、会社の画面で登録した住所を 12 欄で読んで見せるだけ（GET /invoices/draft-context）。
 *   - 支払いと合計: 通貨・支払方法・発送メモ／総重量と便ごとの送料（POST /invoices/draft-shipping-quotes）／合計枠。
 *     合計・税・関税はサーバーの試算（POST /invoices/preview）の答えを見せる。画面で足し算しない。
 *   - 商品一覧: LineItemsTable（値段・在庫数・重さは GET /invoices/draft-inventory の値だけ）。
 *   - 操作: 「クリア」（確認してから空に戻す）と作成。作成は今の道（POST /invoices。下書きで保存）。
 * 「在庫表から／見積から」の切り替えは無い（p8）。見積から作るのは見積の詳細画面の道。
 * 在庫表の画面から選んだ商品（QuoteHandoffState）は先頭の行から入る。
 */
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { useApiQuery } from "../../lib/query/apiQuery";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import CompanyContactSelector from "../../components/CompanyContactSelector";
import ConfirmModal from "../../components/ConfirmModal";
import { PageLayout } from "../../components/PageLayout";
import { SectionCard } from "../../components/SectionCard";
import { Stack } from "../../components/Stack";
import {
  currencyChoices,
  draftContextPath,
  effectivePaymentKey,
  fxRateFor,
  paymentChoicesFor,
  paymentRefFromKey,
  resolveCurrency,
  type DraftContext,
  type InvoicePreviewRequest,
  type ShippingChoice,
} from "../../lib/invoiceDraftContext";
import { LineItemsTable } from "../quote-create/LineItemsTable";
import { allRowsReady, filledRows, handoffRows, padRows, reconvertPrices, toInvoiceItem, totalWeight } from "../quote-create/lineItems";
import type { LineItem, QuoteHandoffState } from "../quote-create/quoteDraft";
import { useDraftInventory } from "../quote-create/useDraftInventory";
import { rateFee, useDraftShippingQuotes } from "../quote-create/useDraftShippingQuotes";
import { InvoicePaymentTotalsSection, SHIPPING_NONE, shippingRateKey } from "./InvoicePaymentTotalsSection";
import { InvoiceShipToSection } from "./InvoiceShipToSection";
import { useInvoicePreview } from "./useInvoicePreview";

/** 材料の答えが請求書の材料の形（object）のときだけ使う。配列などは「まだ無い」と同じに扱う */
function asDraftContext(data: unknown): DraftContext | null {
  return data !== null && typeof data === "object" && !Array.isArray(data) ? (data as DraftContext) : null;
}

export default function InvoiceCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const handoff = location.state as QuoteHandoffState;
  const draft = handoff?.draft;

  const [companyId, setCompanyId] = useState<number | null>(draft?.companyId ?? null);
  const [contactId, setContactId] = useState<number | null>(draft?.contactId ?? null);
  const [selectorError, setSelectorError] = useState("");
  // 人が選んだ通貨。使う通貨は材料の候補にあるときだけ（resolveCurrency）。
  const [currencyChoice, setCurrencyChoice] = useState<string>(draft?.currency ?? "");
  const [paymentChoice, setPaymentChoice] = useState("");
  // 送料の選択（"" 未選択／SHIPPING_NONE／便の鍵）。便は今の送料の一覧にあるときだけ有効。
  const [shippingPick, setShippingPick] = useState("");
  const [notes, setNotes] = useState(draft?.notes ?? "");
  const [rows, setRows] = useState<LineItem[]>(() => handoffRows(handoff));
  const [showErrors, setShowErrors] = useState(false);
  const [clearOpen, setClearOpen] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const inventory = useDraftInventory();

  // --- 請求書の材料（会社を選んだときだけ取りに行く） ---
  const ctxQ = useApiQuery<DraftContext>(
    companyId !== null ? draftContextPath(companyId, contactId) : "/invoices/draft-context",
    { enabled: companyId !== null },
  );
  const ctx = companyId !== null ? asDraftContext(ctxQ.data) : null;
  const ctxError = companyId !== null && ctxQ.error ? (ctxQ.error instanceof Error ? ctxQ.error.message : t("common.fetchError")) : "";

  const currency = resolveCurrency(ctx, currencyChoice);
  const fx = currency !== "" ? fxRateFor(ctx, currency) : null;
  const rate = fx !== null && fx.rate > 0 ? fx.rate : null;

  // 通貨（または為替）が変わったら、単価を手で直していない行だけ入れ直す（PO 2026-11-18「1」）。
  useEffect(() => {
    setRows((prev) => reconvertPrices(prev, currency, rate));
  }, [currency, rate]);

  const paymentChoices = paymentChoicesFor(ctx, currency);
  const paymentValue = effectivePaymentKey(paymentChoices, paymentChoice);

  const weight = totalWeight(rows);
  const canQuote = ctx !== null && ctx.origin_country_code !== null && ctx.destination_country_code !== null;
  const shippingQuotes = useDraftShippingQuotes(canQuote ? companyId : null, weight);
  const pickedRate = (shippingQuotes.quotes?.results ?? []).find((r) => shippingRateKey(r) === shippingPick);
  const pickedFee = pickedRate ? rateFee(pickedRate) : null;
  const shipping: ShippingChoice | null =
    shippingPick === SHIPPING_NONE
      ? { mode: "none" }
      : pickedRate && pickedFee !== null
        ? { mode: "calculate", carrier: pickedRate.carrier, service_type: pickedRate.service_type, fee: pickedFee, currency: pickedRate.currency }
        : null;

  const filled = filledRows(rows);
  const rowsReady = allRowsReady(rows);
  const previewRequest: InvoicePreviewRequest | null =
    ctx !== null && companyId !== null && currency !== "" && rowsReady
      ? {
          company_id: companyId,
          currency,
          items: filled.map((r) => ({ quantity: r.quantity, unit_price: r.unit_price })),
          shipping,
        }
      : null;
  const { preview, error: previewError, fresh } = useInvoicePreview(previewRequest);

  const canCreate =
    companyId !== null &&
    contactId !== null &&
    ctx !== null &&
    ctx.issuer_region !== null &&
    currency !== "" &&
    rowsReady &&
    shipping !== null &&
    (paymentChoices.length === 0 || paymentValue !== "") &&
    fresh &&
    preview !== null &&
    preview.uncomputed.length === 0 &&
    !saving;

  // 会社・担当者が変わったら、前の会社に合わせて選んだ送料と支払方法を外す。
  const changeCompanyContact = (nextCompanyId: number | null, nextContactId: number | null) => {
    if (nextCompanyId !== companyId || nextContactId !== contactId) {
      setShippingPick("");
      setPaymentChoice("");
    }
    setCompanyId(nextCompanyId);
    setContactId(nextContactId);
  };

  // 「クリア」の確認で「はい」: 12 行・発送先・送料・メモを空に戻す（§3-6・K19）。
  const clearAll = () => {
    changeCompanyContact(null, null);
    setShippingPick("");
    setSelectorError("");
    setCurrencyChoice("");
    setNotes("");
    setRows(padRows([]));
    setShowErrors(false);
    setError("");
    setClearOpen(false);
  };

  const submitInvoice = async () => {
    setError("");
    setSelectorError("");
    setShowErrors(true);
    if (contactId === null) {
      setSelectorError(t("companyContactSelector.contactRequired"));
      return;
    }
    if (!rowsReady) {
      setError(filled.length === 0 ? t("quotes.itemsRequired") : t("invoiceForm.rowsNotReady"));
      return;
    }
    if (!canCreate || shipping === null) {
      setError(t("invoiceForm.createNotReady"));
      return;
    }
    setSaving(true);
    try {
      const inv = await api.post<{ id: number }>("/invoices", {
        company_id: companyId,
        contact_id: contactId,
        currency,
        shipping,
        payment_method_ref: paymentRefFromKey(paymentChoices, paymentValue),
        notes: notes || null,
        items: filled.map(toInvoiceItem),
      });
      navigate(`/invoices/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageLayout
      titleText={t("invoices.createTitle")}
      subtitleKey="invoices.createSubtitle"
      headerAction={
        <Button variant="secondary" size="md" onClick={() => navigate("/management-center/tenant-profile")}>
          {t("nav.tenantProfile")}
        </Button>
      }
    >
      <Stack direction="column" gap="4">
        {error !== "" && (
          <Callout variant="warning" title={t("invoiceForm.createBlocked")}>
            <span data-testid="invoice-error">{error}</span>
          </Callout>
        )}

        <SectionCard title={t("invoiceForm.sectionShipTo")}>
          <Stack direction="column" gap="3">
            <CompanyContactSelector
              value={{ companyId, contactId }}
              onChange={({ companyId: c, contactId: ct }) => changeCompanyContact(c, ct)}
              required
              error={selectorError}
            />
            {companyId !== null && (
              <InvoiceShipToSection companyId={companyId} ctx={ctx} loading={ctxQ.isPending} errorText={ctxError} />
            )}
          </Stack>
        </SectionCard>

        <SectionCard title={t("invoiceForm.sectionPaymentTotals")}>
          <InvoicePaymentTotalsSection
            ctx={ctx}
            currencyOptions={currencyChoices(ctx)}
            currency={currency}
            onCurrencyChange={(next) => { setCurrencyChoice(next); setPaymentChoice(""); }}
            paymentChoices={paymentChoices}
            paymentValue={paymentValue}
            onPaymentChange={setPaymentChoice}
            notes={notes}
            onNotesChange={setNotes}
            totalWeight={weight}
            shippingQuotes={shippingQuotes}
            shippingPick={shippingPick}
            onShippingPick={setShippingPick}
            preview={preview}
            previewError={previewError}
            disabled={saving}
          />
        </SectionCard>

        <SectionCard title={t("invoiceForm.sectionItems")}>
          <LineItemsTable
            rows={rows}
            onChange={setRows}
            inventory={inventory}
            currency={currency}
            rate={rate}
            showErrors={showErrors}
            disabled={saving}
          />
        </SectionCard>

        <SectionCard title={t("invoiceForm.sectionActions")}>
          <Stack direction="row" gap="3">
            {/* 今の画面の「キャンセル」（請求書の一覧へ戻る）はそのまま残す */}
            <Button type="button" variant="secondary" size="md" onClick={() => navigate("/invoices")} disabled={saving}>
              {t("common.cancel")}
            </Button>
            <Button type="button" variant="secondary" size="md" onClick={() => setClearOpen(true)} disabled={saving} data-testid="invoice-clear">
              {t("invoiceForm.clear")}
            </Button>
            <Button type="button" variant="primary" size="md" loading={saving} disabled={saving} onClick={submitInvoice} data-testid="invoice-create-submit">
              {t("invoices.createBtn")}
            </Button>
          </Stack>
        </SectionCard>
      </Stack>

      <ConfirmModal
        open={clearOpen}
        title={t("invoiceForm.clearConfirmTitle")}
        message={t("invoiceForm.clearConfirmMessage")}
        confirmLabel={t("invoiceForm.clearConfirmYes")}
        cancelLabel={t("common.cancel")}
        danger
        onConfirm={clearAll}
        onCancel={() => setClearOpen(false)}
      />
    </PageLayout>
  );
}
