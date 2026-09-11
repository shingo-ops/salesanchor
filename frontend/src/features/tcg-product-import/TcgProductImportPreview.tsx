import { useTranslation } from "react-i18next";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { ContentToolbar } from "../../components/ContentToolbar";
import { HeaderButton } from "../../components/HeaderButton";
import { importMessage } from "./importMessages";

export interface PreviewRow { row_no: string; japanese_title: string; mark: string; blocking: string[]; warnings: string[] }
export interface PreviewResponse { filename: string; digest: string; file_errors: string[]; total: number; ok: number; blocked: number; rows: PreviewRow[] }
interface Props { preview: PreviewResponse; busy: boolean; onCommit: () => void; onCancel: () => void }
export function TcgProductImportPreview({ preview, busy, onCommit, onCancel }: Props) {
  const { t } = useTranslation();
  const columns: DataTableColumn<PreviewRow>[] = [
    { key: "row_no", header: t("productCsv.row") },
    { key: "japanese_title", header: t("productCsv.title") },
    { key: "mark", header: t("productCsv.mark") },
    { key: "status", header: t("productCsv.status"), renderCell: row => t(row.blocking.length ? "productCsv.blocked" : row.warnings.length ? "productCsv.warning" : "productCsv.ready") },
    { key: "messages", header: t("productCsv.details"), renderCell: row => <ul>{[...row.blocking, ...row.warnings].map((code, index) => <li key={index}>{importMessage(code, t)}</li>)}</ul> },
  ];
  return <section aria-label={t("productCsv.review")}>
    <p>{t("productCsv.summary", { total: preview.total, ready: preview.ok, blocked: preview.blocked })}</p>
    {preview.file_errors.length > 0 && <div role="alert">{preview.file_errors.map((code, index) => <p key={index}>{importMessage(code, t)}</p>)}</div>}
    <DataTable columns={columns} data={preview.rows} rowKey={row => row.row_no} emptyState={t("productCsv.emptyRows")} />
    <p>{t("productCsv.confirmHint")}</p>
    <ContentToolbar left={<HeaderButton variant="secondary" onClick={onCancel} disabled={busy}>{t("productCsv.chooseAgain")}</HeaderButton>} right={<HeaderButton variant="primary" onClick={onCommit} disabled={busy || preview.ok === 0 || preview.file_errors.length > 0}>{busy ? t("common.loading") : t("productCsv.commit")}</HeaderButton>} />
  </section>;
}
