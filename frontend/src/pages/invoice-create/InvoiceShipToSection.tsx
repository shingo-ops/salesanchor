/**
 * 請求書作成ページの「届け先・請求先」の区切り（invoice-create-portfolio 便D・design.md §3-2）。
 *
 * 住所・担当者は会社の画面で登録した値を読んで見せるだけ（この画面では打たない・K1）。
 * 直したいときは会社の画面へ移るボタンを出す。
 * 請求書を出す側の地域（issuer_region）が決まらないときは、作成できない理由と会社の画面への道を出す。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { LoadingBlock } from "../../components/loading";
import { addressLine, type DraftContext } from "../../lib/invoiceDraftContext";

export interface InvoiceShipToSectionProps {
  companyId: number;
  ctx: DraftContext | null;
  loading: boolean;
  errorText: string;
}

export function InvoiceShipToSection({ companyId, ctx, loading, errorText }: InvoiceShipToSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const openCompany = () => navigate(`/crm/companies/${companyId}`);

  if (errorText !== "") {
    return (
      <div data-testid="invoice-ship-to">
        <Callout variant="warning" title={t("invoiceForm.contextError")}>
          <p data-testid="invoice-context-error">{errorText}</p>
        </Callout>
      </div>
    );
  }
  if (ctx === null) {
    return (
      <div data-testid="invoice-ship-to">
        {loading ? <LoadingBlock /> : <p style={{ color: "var(--text-secondary)" }}>{t("invoiceForm.chooseCompany")}</p>}
      </div>
    );
  }

  const shipTo = addressLine(ctx.ship_to);
  const billTo = addressLine(ctx.bill_to);
  return (
    <div data-testid="invoice-ship-to">
      {ctx.issuer_region === null && (
        <Callout variant="warning" title={t("apiError.billToCountry")}>
          <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company-for-bill-to">
            {t("invoices.openCompanyForBillTo")}
          </Button>
        </Callout>
      )}
      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "var(--space-2) var(--space-4)", margin: "var(--space-3) 0" }}>
        <dt>{t("invoiceForm.shipTo")}</dt>
        <dd data-testid="invoice-ship-to-address">{shipTo !== "" ? shipTo : t("invoiceForm.noAddress")}</dd>
        <dt>{t("invoiceForm.billTo")}</dt>
        <dd data-testid="invoice-bill-to-address">{billTo !== "" ? billTo : t("invoiceForm.noAddress")}</dd>
        <dt>{t("invoiceForm.contact")}</dt>
        <dd data-testid="invoice-contact-line">
          {[ctx.contact_name, ctx.contact_email].filter((s) => s !== null && s !== "").join(" / ") || t("invoiceForm.noAddress")}
        </dd>
      </dl>
      <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company">
        {t("invoiceForm.openCompany")}
      </Button>
    </div>
  );
}
