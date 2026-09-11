import { useTranslation } from "react-i18next";
import { type ReactNode, useState } from "react";
import { Button } from "../../components/Button";
import { Badge, type BadgeVariant } from "../../components/Badge";
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
  const setFilterAndReset = (next: ImportItemFilter) => { setFilter(next); setOffset(0); };
  const extraction = progress?.extraction;
  const analysis = progress?.analysis;
  const extractionNumbers = extraction && [extraction.total, extraction.completed, extraction.pending, extraction.running, extraction.unknown, extraction.succeeded, extraction.empty, extraction.failed];
  const extractionIsKnown = !!extractionNumbers && extractionNumbers.every((value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && Number.isInteger(value))
    && extraction!.completed === extraction!.succeeded! + extraction!.empty! + extraction!.failed!
    && extraction!.total === extraction!.completed! + extraction!.pending! + extraction!.running! + extraction!.unknown!;
  const finished = extractionIsKnown ? extraction!.completed! : null;
  const canShowProgress = extractionIsKnown && extraction!.total! > 0 && extraction!.unknown! === 0;
  const summary = (() => {
    if (error) return { label: progress || items ? t("pmgWorkflow.summary.stale") : t("pmgWorkflow.summary.fetchFailed"), action: t("pmgWorkflow.summaryAction.retry"), variant: "danger" as BadgeVariant };
    if (!progress) return { label: t("pmgWorkflow.summary.waiting"), action: t("pmgWorkflow.summaryAction.waiting"), variant: "neutral" as BadgeVariant };
    if (progress.coverage === "pending_review") return { label: coverageLabel(progress.coverage), action: t("pmgWorkflow.summaryAction.pendingReview"), variant: "neutral" as BadgeVariant };
    if (progress.coverage === "discarded") return { label: coverageLabel(progress.coverage), action: t("pmgWorkflow.summaryAction.discarded"), variant: "neutral" as BadgeVariant };
    if (progress.coverage === "legacy_unknown") return { label: coverageLabel(progress.coverage), action: t("pmgWorkflow.summaryAction.legacyUnknown"), variant: "neutral" as BadgeVariant };
    if (!extractionIsKnown || extraction!.unknown! > 0) return { label: t("pmgWorkflow.summary.unknown"), action: t("pmgWorkflow.summaryAction.retry"), variant: "neutral" as BadgeVariant };
    if (extraction!.total === 0) return { label: t("pmgWorkflow.extraction.emptyState"), action: t("pmgWorkflow.summaryAction.empty"), variant: "neutral" as BadgeVariant };
    if (extraction!.pending! > 0 || extraction!.running! > 0) return { label: t("pmgWorkflow.summary.running"), action: t("pmgWorkflow.summaryAction.running"), variant: "info" as BadgeVariant };
    if (extraction!.failed! > 0) return { label: t("pmgWorkflow.summary.error"), action: t("pmgWorkflow.summaryAction.error"), variant: "danger" as BadgeVariant };
    return { label: t("pmgWorkflow.summary.finished"), action: t("pmgWorkflow.summaryAction.finished"), variant: "success" as BadgeVariant };
  })();
  const stage = (name: "import" | "extraction" | "analysis", value: { unit: string; total: number | null; reason?: string } | undefined, facts?: ReactNode) => (
    <section className="pmg-workflow__stage">
      <h4>{t(`pmgWorkflow.stage.${name}`)}</h4>
      <p className="pmg-workflow__caption">{unitLabel(value?.unit)}</p>
      {value?.total === null && <p>{t("pmgWorkflow.unknown")}: {reasonLabel(value.reason ?? progress?.reason)}</p>}
      {facts && <div className="pmg-workflow__stage-facts">{facts}</div>}
    </section>
  );
  return <section className="pmg-workflow" aria-busy={loading}>
    <header className="pmg-workflow__header"><div><h4 className="pmg-workflow__conclusion"><Badge className={`pmg-workflow__summary-badge${summary.variant === "info" || summary.variant === "neutral" ? " pmg-workflow__badge-readable" : ""}`} variant={summary.variant} dot>{summary.label}</Badge></h4><p>{summary.action}</p><p>{t("pmgWorkflow.coverage")}: {coverageLabel(progress?.coverage ?? items?.coverage)}</p>{lastAsOf && <p>{t("pmgWorkflow.asOf")}: {new Intl.DateTimeFormat(i18n.language, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tokyo", timeZoneName: "short" }).format(new Date(lastAsOf))}</p>}</div><Button variant="secondary" onClick={refresh}>{t("pmgWorkflow.refresh")}</Button></header>
    {error && <p className="pmg-workflow__error">{progress || items ? t("pmgWorkflow.stale") : t("pmgWorkflow.fetchFailed")}: {error}</p>}
    {((analysis?.needs_review ?? 0) > 0 || (typeof extraction?.failed === "number" && extraction.failed > 0)) && <div className="pmg-workflow__actions">
      {(analysis?.needs_review ?? 0) > 0 && <><Badge className="pmg-workflow__review-badge" variant="warning">{t("pmgWorkflow.analysis.needsReview")}: {formatNumber(analysis?.needs_review)}</Badge><Button variant="secondary" onClick={() => setFilterAndReset("needs_review")}>{t("pmgWorkflow.reviewAction")}</Button></>}
      {typeof extraction?.failed === "number" && extraction.failed > 0 && <><Badge variant="danger">{t("pmgWorkflow.extraction.error")}: {formatNumber(extraction.failed)}</Badge><Button variant="secondary" onClick={() => setFilterAndReset("extraction_error")}>{t("pmgWorkflow.errorAction")}</Button></>}
    </div>}
    <div className="pmg-workflow__stages">
      {stage("import", progress?.messages, progress && <p className="pmg-workflow__metric">{formatNumber(progress.messages.total)}</p>)}
      {stage("extraction", extraction, progress && <><p className="pmg-workflow__metric">{formatNumber(finished)}<span>{extractionIsKnown ? ` / ${formatNumber(extraction?.total)}` : ""}</span></p>{canShowProgress && <progress className="pmg-workflow__progress" aria-label={t("pmgWorkflow.extractionProgressLabel")} aria-valuetext={t("pmgWorkflow.extractionProgressValue", { completed: formatNumber(finished), total: formatNumber(extraction!.total) })} value={finished!} max={extraction!.total!} />}{extractionIsKnown && extraction!.total === 0 && <p>{t("pmgWorkflow.extraction.emptyState")}</p>}{typeof extraction?.failed === "number" && extraction.failed > 0 && <Badge variant="danger">{t("pmgWorkflow.extraction.error")}: {formatNumber(extraction.failed)}</Badge>}{((typeof extraction?.pending === "number" && extraction.pending > 0) || (typeof extraction?.running === "number" && extraction.running > 0)) && <p>{t("pmgWorkflow.extraction.pending")}: {formatNumber(extraction?.pending)} · {t("pmgWorkflow.extraction.running")}: {formatNumber(extraction?.running)}</p>}<p>{t("pmgWorkflow.extraction.done")}: {formatNumber(extraction?.succeeded)} · {t("pmgWorkflow.extraction.empty")}: {formatNumber(extraction?.empty)} · {t("pmgWorkflow.extraction.error")}: {formatNumber(extraction?.failed)}</p></>)}
      {stage("analysis", analysis, progress && <><p className="pmg-workflow__metric">{formatNumber(analysis?.results_present)}</p><p className="pmg-workflow__caption">{t("pmgWorkflow.analysis.resultPresent")}</p><p>{t("pmgWorkflow.analysis.needsReview")}: {formatNumber(analysis?.needs_review)}</p><p>{t("pmgWorkflow.analysis.resultMissing")}: {formatNumber(analysis?.results_missing)}</p></>)}
    </div>
    <details className="pmg-workflow__details"><summary>{t("pmgWorkflow.processingDetails")}</summary><div className="pmg-workflow__stage-facts">{progress?.analysis.execution_state === "unrecorded" && <p>{t("pmgWorkflow.analysisUnrecorded")}</p>}<p>{t("pmgWorkflow.extraction.pending")}: {formatNumber(extraction?.pending)}</p><p>{t("pmgWorkflow.extraction.running")}: {formatNumber(extraction?.running)}</p><p>{t("pmgWorkflow.extraction.residualItems")}: {formatNumber(extraction?.residual_items_on_error)}</p><p>{t("pmgWorkflow.extraction.residualResults")}: {formatNumber(extraction?.residual_results_on_error)}</p><p>{t("pmgWorkflow.analysis.resultMissing")}: {formatNumber(analysis?.results_missing)}</p><p>{t("pmgWorkflow.messagesCreated")}: {formatNumber(progress?.messages.created)}</p><p>{t("pmgWorkflow.messagesReused")}: {formatNumber(progress?.messages.reused)}</p><p>{t("pmgWorkflow.messagesInactive")}: {formatNumber(progress?.messages.inactive)}</p><p>{t("pmgWorkflow.messagesWithoutExtraction")}: {formatNumber(progress?.messages.without_extraction_job)}</p></div></details>
    <div className="pmg-workflow__controls"><Select value={filter} onChange={(event) => setFilterAndReset(event.target.value as ImportItemFilter)} aria-label={t("pmgWorkflow.filter")} options={[{value:"all",label:t("pmgWorkflow.filterAll")},{value:"needs_review",label:t("pmgWorkflow.filterReview")},{value:"extraction_error",label:t("pmgWorkflow.filterError")}]}/></div>
    {items?.items === null ? <p>{t("pmgWorkflow.unknown")}: {reasonLabel(items.reason)}</p> : items?.items?.length === 0 ? <p>{t("pmgWorkflow.noItems")}</p> : <div className="pmg-workflow__table-wrap"><table className="pmg-workflow__table"><thead><tr><th>{t("pmgWorkflow.item.product")}</th><th>{t("pmgWorkflow.item.extractionStatus")}</th><th>{t("pmgWorkflow.item.raw")}</th><th>{t("pmgWorkflow.item.note")}</th><th>{t("pmgWorkflow.item.reasons")}</th><th>{t("pmgWorkflow.item.result")}</th><th>{t("pmgWorkflow.item.details")}</th></tr></thead><tbody>{items?.items?.map((item) => <tr key={item.id}><td>{item.raw_product_name ?? "-"}</td><td>{extractionStatusLabel(item.extraction_status)}</td><td>{formatValue(item.raw_quantity)} / {formatValue(item.raw_price)}</td><td>{item.note_ja ?? "-"}</td><td>{reviewReasonsLabel(item.review_reasons)}</td><td>{item.analysis_result_id ? t("pmgWorkflow.resultPresent") : t("pmgWorkflow.resultMissing")}</td><td><details><summary>{t("pmgWorkflow.item.details")}</summary><p>{t("pmgWorkflow.item.raw")}: {formatValue(item.raw_quantity)} / {formatValue(item.raw_price)} / {formatValue(item.raw_unit)}</p><p>{t("pmgWorkflow.item.rawDetails")}: {formatValue(item.raw_state)} / {formatValue(item.raw_memo)}</p><p>{t("pmgWorkflow.item.normalized")}: {formatValue(item.quantity_normalized)} / {formatValue(item.price_normalized)}</p></details></td></tr>)}</tbody></table></div>}
    <footer className="pmg-workflow__pager"><Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>{t("pmgWorkflow.previous")}</Button><span>{items?.total ?? "-"}</span><Button variant="secondary" disabled={items?.items === null || offset + LIMIT >= (items?.total ?? 0)} onClick={() => setOffset(offset + LIMIT)}>{t("pmgWorkflow.next")}</Button></footer>
  </section>;
}
