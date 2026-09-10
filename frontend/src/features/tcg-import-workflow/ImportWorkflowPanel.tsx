import { useTranslation } from "react-i18next";
import { type ReactNode, useState } from "react";
import { Button } from "../../components/Button";
import { Select } from "../../components/Select";
import { type Coverage, type ImportItemFilter } from "./importWorkflowApi";
import { useImportWorkflow } from "./useImportWorkflow";
import "./import-workflow.css";

const LIMIT = 25;
export function ImportWorkflowPanel({ importJobId }: { importJobId: string | null }) {
  const { t, i18n } = useTranslation();
  const [filter, setFilter] = useState<ImportItemFilter>("all");
  const [offset, setOffset] = useState(0);
  const { progress, items, error, loading, refresh, lastAsOf } = useImportWorkflow(importJobId, filter, offset, LIMIT);
  if (!importJobId) return <p className="pmg-workflow__empty">{t("pmgWorkflow.selectImport")}</p>;

  const coverageLabel = (coverage: Coverage | undefined) => t(`pmgWorkflow.coverageValue.${coverage ?? "unknown"}`);
  const reasonLabel = (reason: string | null | undefined) => reason === "message_association_not_recorded"
    ? t("pmgWorkflow.reason.associationNotRecorded")
    : t("pmgWorkflow.reason.unknown");
  const unitLabel = (unit: string | undefined) => t(`pmgWorkflow.unitValue.${unit ?? "unknown"}`);
  const extractionStatusLabel = (status: string) => {
    const knownStatuses = ["done", "empty", "error", "pending", "running", "unknown"];
    return t(`pmgWorkflow.extractionStatus.${knownStatuses.includes(status) ? status : "unknown"}`);
  };
  const reviewReasonsLabel = (reasons: string | null) => reasons
    ? reasons.split(",").map((reason) => {
      const key = reason.trim();
      return ["pid_unresolved", "multi_candidate", "note_unmatched"].includes(key)
        ? t(`pmgWorkflow.reviewReason.${key}`)
        : key;
    }).join(", ")
    : "-";
  const formatNumber = (value: number | null | undefined) => value === null || value === undefined ? "-" : value.toLocaleString(i18n.language);
  const formatValue = (value: number | string | null | undefined) => value === null || value === undefined || value === "" ? "-" : String(value);
  const stage = (name: "import" | "extraction" | "analysis", value: { unit: string; total: number | null; reason?: string } | undefined, facts?: ReactNode) => (
    <section className="pmg-workflow__stage">
      <h4>{t(`pmgWorkflow.stage.${name}`)}</h4>
      <p>{t("pmgWorkflow.unit")}: {unitLabel(value?.unit)}</p>
      {value?.total === null ? <p>{t("pmgWorkflow.unknown")}: {reasonLabel(value.reason ?? progress?.reason)}</p> : <p>{t("pmgWorkflow.total")}: {formatNumber(value?.total)}</p>}
      {facts && <div className="pmg-workflow__stage-facts">{facts}</div>}
    </section>
  );
  return <section className="pmg-workflow" aria-busy={loading}>
    <header className="pmg-workflow__header"><div><p>{t("pmgWorkflow.coverage")}: {coverageLabel(progress?.coverage ?? items?.coverage)}</p>{lastAsOf && <p>{t("pmgWorkflow.asOf")}: {new Intl.DateTimeFormat(i18n.language, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tokyo", timeZoneName: "short" }).format(new Date(lastAsOf))}</p>}</div><Button variant="secondary" onClick={refresh}>{t("pmgWorkflow.refresh")}</Button></header>
    {error && <p className="pmg-workflow__error">{progress || items ? t("pmgWorkflow.stale") : t("pmgWorkflow.fetchFailed")}: {error}</p>}
    <div className="pmg-workflow__stages">
      {stage("import", progress?.messages)}
      {stage("extraction", progress?.extraction, progress && <><p>{t("pmgWorkflow.extraction.completed")}: {formatNumber(progress.extraction.completed)}</p><p>{t("pmgWorkflow.extraction.done")}: {formatNumber(progress.extraction.succeeded)}</p><p>{t("pmgWorkflow.extraction.empty")}: {formatNumber(progress.extraction.empty)}</p><p>{t("pmgWorkflow.extraction.error")}: {formatNumber(progress.extraction.failed)}</p><p>{t("pmgWorkflow.extraction.pending")}: {formatNumber(progress.extraction.pending)}</p><p>{t("pmgWorkflow.extraction.running")}: {formatNumber(progress.extraction.running)}</p><p>{t("pmgWorkflow.extraction.residualItems")}: {formatNumber(progress.extraction.residual_items_on_error)}</p><p>{t("pmgWorkflow.extraction.residualResults")}: {formatNumber(progress.extraction.residual_results_on_error)}</p></>)}
      {stage("analysis", progress?.analysis, progress && <><p>{t("pmgWorkflow.analysis.resultPresent")}: {formatNumber(progress.analysis.results_present)}</p><p>{t("pmgWorkflow.analysis.resultMissing")}: {formatNumber(progress.analysis.results_missing)}</p><p>{t("pmgWorkflow.analysis.needsReview")}: {formatNumber(progress.analysis.needs_review)}</p></>)}
    </div>
    {progress?.analysis.execution_state === "unrecorded" && <p>{t("pmgWorkflow.analysisUnrecorded")}</p>}
    <div className="pmg-workflow__controls"><Select value={filter} onChange={(event) => { setFilter(event.target.value as ImportItemFilter); setOffset(0); }} aria-label={t("pmgWorkflow.filter")} options={[{value:"all",label:t("pmgWorkflow.filterAll")},{value:"needs_review",label:t("pmgWorkflow.filterReview")},{value:"extraction_error",label:t("pmgWorkflow.filterError")}]}/></div>
    {items?.items === null ? <p>{t("pmgWorkflow.unknown")}: {reasonLabel(items.reason)}</p> : items?.items?.length === 0 ? <p>{t("pmgWorkflow.noItems")}</p> : <div className="pmg-workflow__table-wrap"><table className="pmg-workflow__table"><thead><tr><th>{t("pmgWorkflow.item.product")}</th><th>{t("pmgWorkflow.item.extractionStatus")}</th><th>{t("pmgWorkflow.item.raw")}</th><th>{t("pmgWorkflow.item.note")}</th><th>{t("pmgWorkflow.item.reasons")}</th><th>{t("pmgWorkflow.item.result")}</th><th>{t("pmgWorkflow.item.details")}</th></tr></thead><tbody>{items?.items?.map((item) => <tr key={item.id}><td>{item.raw_product_name ?? "-"}</td><td>{extractionStatusLabel(item.extraction_status)}</td><td>{formatValue(item.raw_quantity)} / {formatValue(item.raw_price)}</td><td>{item.note_ja ?? "-"}</td><td>{reviewReasonsLabel(item.review_reasons)}</td><td>{item.analysis_result_id ? t("pmgWorkflow.resultPresent") : t("pmgWorkflow.resultMissing")}</td><td><details><summary>{t("pmgWorkflow.item.details")}</summary><p>{t("pmgWorkflow.item.raw")}: {formatValue(item.raw_quantity)} / {formatValue(item.raw_price)} / {formatValue(item.raw_unit)}</p><p>{t("pmgWorkflow.item.rawDetails")}: {formatValue(item.raw_state)} / {formatValue(item.raw_memo)}</p><p>{t("pmgWorkflow.item.normalized")}: {formatValue(item.quantity_normalized)} / {formatValue(item.price_normalized)}</p></details></td></tr>)}</tbody></table></div>}
    <footer className="pmg-workflow__pager"><Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>{t("pmgWorkflow.previous")}</Button><span>{items?.total ?? "-"}</span><Button variant="secondary" disabled={items?.items === null || offset + LIMIT >= (items?.total ?? 0)} onClick={() => setOffset(offset + LIMIT)}>{t("pmgWorkflow.next")}</Button></footer>
  </section>;
}
