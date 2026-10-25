import { useTranslation } from "react-i18next";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ContentToolbar } from "../../components/ContentToolbar";
import { HeaderButton } from "../../components/HeaderButton";
import { reviewCsvMessage, type ReviewCsvApply, type ReviewCsvError, type ReviewCsvPreview } from "./reviewCsvTypes";

interface Props { preview: ReviewCsvPreview; busy: boolean; onCommit: () => void; onCancel: () => void }

export function ReviewCsvPreviewTable({ preview, busy, onCommit, onCancel }: Props) {
  const { t } = useTranslation();
  const applyColumns: DataTableColumn<ReviewCsvApply>[] = [
    { key: "line", header: t("reviewCsv.line") },
    { key: "name", header: t("reviewCsv.name") },
    { key: "kind", header: t("reviewCsv.action"), renderCell: row => row.kind === "product" ? t("reviewCsv.actionProduct", { code: row.product_code }) : t("reviewCsv.actionAck") },
  ];
  const errorColumns: DataTableColumn<ReviewCsvError>[] = [
    { key: "line", header: t("reviewCsv.line") },
    { key: "extraction_item_id", header: t("reviewCsv.itemId") },
    { key: "code", header: t("reviewCsv.reason"), renderCell: row => <>{reviewCsvMessage(row.code, t)}{row.detail ? ` (${row.detail})` : ""}</> },
  ];
  return <section aria-label={t("reviewCsv.previewTitle")}>
    <p>{t("reviewCsv.summary", { total: preview.total_rows, ready: preview.applies.length, errors: preview.errors.length })}</p>
    <h4>{t("reviewCsv.appliesTitle")}</h4>
    <DataTable columns={applyColumns} data={preview.applies} rowKey={row => row.extraction_item_id} emptyState={t("reviewCsv.noApplies")} />
    {preview.errors.length > 0 && <>
      <h4>{t("reviewCsv.errorsTitle")}</h4>
      <DataTable columns={errorColumns} data={preview.errors} rowKey={row => `${row.line}-${row.code}`} emptyState={t("reviewCsv.noApplies")} />
    </>}
    <p>{t("reviewCsv.confirmHint")}</p>
    <ContentToolbar
      left={<HeaderButton variant="secondary" onClick={onCancel} disabled={busy}>{t("reviewCsv.chooseAgain")}</HeaderButton>}
      right={<HeaderButton loading={busy} variant="primary" onClick={onCommit} disabled={busy || preview.applies.length === 0}>{t("reviewCsv.commit")}</HeaderButton>}
    />
  </section>;
}
