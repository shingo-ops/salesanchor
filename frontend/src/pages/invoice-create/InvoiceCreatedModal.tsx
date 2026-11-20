/**
 * 請求書を作ったあとに出す小さな枠（invoice-create-portfolio design-v2 §3-6・K15。便 R6）。
 *
 * PDF は画面に埋め込まない（本番の守りの設定 nginx/nginx.conf:96 が blob の PDF の埋め込みを止めるため）。
 * 「PDF を保存」は GET /invoices/{id}/pdf（権限 invoices.view）を blob で読み、{請求書番号}.pdf で保存する。
 * 番号の正本はサーバー（POST /invoices の返事の invoice_number）。番号が空なら保存のボタンを出さない。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { saveBlob } from "../../lib/saveBlob";
import { usePermissions } from "../../hooks/usePermissions";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Modal } from "../../components/Modal";
import { ReadOnlyField } from "../../components/ReadOnlyField";
import { Stack } from "../../components/Stack";

/** POST /invoices の返事のうち、枠が使う 2 つ（backend/app/schemas/invoice.py InvoiceResponse） */
export interface CreatedInvoice {
  id: number;
  invoice_number: string | null;
}

interface InvoiceCreatedModalProps {
  invoice: CreatedInvoice;
  onClose: () => void;
  onOpenDetail: () => void;
}

export function InvoiceCreatedModal({ invoice, onClose, onOpenDetail }: InvoiceCreatedModalProps) {
  const { t } = useTranslation();
  const { hasPermission, loading } = usePermissions();
  const [pdfSaving, setPdfSaving] = useState(false);
  const [pdfError, setPdfError] = useState(false);
  const canView = !loading && hasPermission("invoices.view");
  const canSavePdf = canView && invoice.invoice_number !== null && invoice.invoice_number !== "";

  const savePdf = async () => {
    if (!canSavePdf) return;
    setPdfError(false);
    setPdfSaving(true);
    try {
      const blob = await api.getBlob(`/invoices/${invoice.id}/pdf`);
      saveBlob(blob, `${invoice.invoice_number}.pdf`);
    } catch {
      setPdfError(true);
    } finally {
      setPdfSaving(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={t("invoiceForm.createdTitle")}
      size="sm"
      dismissOnOverlay={false}
      footer={
        <>
          <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={pdfSaving} data-testid="invoice-created-close">
            {t("common.close")}
          </Button>
          <Button type="button" variant="secondary" size="md" onClick={onOpenDetail} disabled={pdfSaving} data-testid="invoice-created-detail">
            {t("invoiceForm.createdOpenDetail")}
          </Button>
          {canSavePdf && (
            <Button
              type="button"
              variant="primary"
              size="md"
              loading={pdfSaving}
              disabled={pdfSaving}
              onClick={() => void savePdf()}
              data-testid="invoice-created-save-pdf"
            >
              {t("invoiceForm.createdSavePdf")}
            </Button>
          )}
        </>
      }
    >
      <Stack gap="4">
        <div data-testid="invoice-created-number">
          <ReadOnlyField label={t("invoiceForm.createdNumber")} value={invoice.invoice_number} />
        </div>
        <Callout variant="info" title={t("invoiceForm.createdDraftNote")} />
        {!loading && !canView && (
          <div data-testid="invoice-created-pdf-no-permission">
            <Callout variant="info" title={t("invoiceForm.createdPdfNoPermission")} />
          </div>
        )}
        {pdfError && (
          <div data-testid="invoice-created-pdf-error">
            <Callout variant="warning" title={t("invoiceForm.createdPdfError")} />
          </div>
        )}
      </Stack>
    </Modal>
  );
}
