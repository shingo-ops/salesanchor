/**
 * 請求書作成ページの「発送先」の中身（invoice-create-portfolio design-v2 §3-2・K2・K3）。
 *
 * 会社の画面で登録した住所を 12 欄・2 列で読んで見せるだけ（この画面では打たない）。空の欄は「未登録」。
 * 届け先の既定の住所を使い、無ければ請求先の既定（サーバーの選び方と同じ）。
 * 直したいときは会社の画面へ移るボタンを出す。
 * 請求書を出す側の地域（issuer_region）が決まらないときは、作成できない理由と会社の画面への道を出す。
 */
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { LoadingBlock } from "../../components/loading";
import { ReadOnlyField } from "../../components/ReadOnlyField";
import { Stack } from "../../components/Stack";
import { TwoColumn } from "../../components/TwoColumn";
import type { DraftAddress, DraftContext } from "../../lib/invoiceDraftContext";

export interface InvoiceShipToSectionProps {
  companyId: number | null;
  ctx: DraftContext | null;
  loading: boolean;
  errorText: string;
}

interface ShipToField {
  key: string;
  labelKey: string;
  value: string | null | undefined;
}

function firstFilled(...values: Array<string | null | undefined>): string | null {
  return values.find((v) => v !== null && v !== undefined && v.trim() !== "") ?? null;
}

/** 12 欄の中身（左 6・右 6）。出どころは design-v2 §3-2 の表 */
export function shipToFields(ctx: DraftContext): { left: ShipToField[]; right: ShipToField[] } {
  const a: DraftAddress | null = ctx.ship_to ?? ctx.bill_to;
  return {
    left: [
      { key: "customer", labelKey: "invoiceForm.fieldCustomer", value: firstFilled(a?.billing_display_name, a?.company_name) },
      { key: "recipient", labelKey: "invoiceForm.fieldRecipient", value: firstFilled(a?.recipient_name, ctx.contact_name) },
      { key: "phone", labelKey: "invoiceForm.fieldPhone", value: a?.phone },
      { key: "email", labelKey: "invoiceForm.fieldEmail", value: firstFilled(a?.email, ctx.contact_email) },
      { key: "tax", labelKey: "invoiceForm.fieldTaxId", value: a?.tax_id },
      { key: "country", labelKey: "invoiceForm.fieldCountry", value: firstFilled(a?.country_name, a?.country) },
    ],
    right: [
      { key: "address1", labelKey: "invoiceForm.fieldAddress1", value: a?.address_line_1 },
      { key: "address2", labelKey: "invoiceForm.fieldAddress2", value: a?.address_line_2 },
      { key: "address3", labelKey: "invoiceForm.fieldAddress3", value: a?.address_line_3 },
      { key: "city", labelKey: "invoiceForm.fieldCity", value: a?.city },
      { key: "state", labelKey: "invoiceForm.fieldState", value: a?.state },
      { key: "zip", labelKey: "invoiceForm.fieldZip", value: a?.postal_code },
    ],
  };
}

export function InvoiceShipToSection({ companyId, ctx, loading, errorText }: InvoiceShipToSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const openCompany = () => {
    if (companyId !== null) navigate(`/crm/companies/${companyId}`);
  };

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
        {loading ? <LoadingBlock /> : <p>{t("invoiceForm.chooseCompany")}</p>}
      </div>
    );
  }

  const { left, right } = shipToFields(ctx);
  const column = (fields: ShipToField[]) => (
    <Stack direction="column" gap="2">
      {fields.map((f) => (
        <div key={f.key} data-testid={`invoice-ship-to-field-${f.key}`}>
          <ReadOnlyField label={t(f.labelKey)} value={f.value ?? null} />
        </div>
      ))}
    </Stack>
  );

  return (
    <div data-testid="invoice-ship-to">
      <Stack direction="column" gap="3">
        {ctx.issuer_region === null && (
          <Callout variant="warning" title={t("apiError.billToCountry")}>
            <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company-for-bill-to">
              {t("invoices.openCompanyForBillTo")}
            </Button>
          </Callout>
        )}
        <div data-testid="invoice-ship-to-address">
          <TwoColumn ratio="1:1" gap="4">
            {column(left)}
            {column(right)}
          </TwoColumn>
        </div>
        <Stack direction="row" gap="2">
          <Button type="button" variant="secondary" size="sm" onClick={openCompany} data-testid="invoice-open-company">
            {t("invoiceForm.openCompany")}
          </Button>
        </Stack>
      </Stack>
    </div>
  );
}
