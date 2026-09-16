import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { attemptCopy, getExtractionAttempts, type ExtractionAttempt } from "./extractionAttemptsApi";

export function ExtractionAttemptHistory({ jobId }: { jobId: string }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [offset, setOffset] = useState(0);
  const [reload, setReload] = useState(0);
  const [state, setState] = useState<{ key: string; rows: ExtractionAttempt[] | null; error: boolean }>({ key: "", rows: null, error: false });
  const [copyStatus, setCopyStatus] = useState<"copied" | "copyFailed" | null>(null);
  const generation = useRef(0);
  const copyGeneration = useRef(0);
  const key = `${jobId}:${offset}:${reload}`;
  useEffect(() => {
    const current = ++generation.current;
    setCopyStatus(null);
    if (open) {
      void getExtractionAttempts(jobId, offset).then(rows => {
        if (current === generation.current) setState({ key, rows, error: false });
      }).catch(() => {
        if (current === generation.current) setState({ key, rows: null, error: true });
      });
    }
    return () => { generation.current += 1; };
  }, [jobId, offset, reload, open, key]);
  const loading = open && state.key !== key;
  const rows = !loading && !state.error ? state.rows : null;
  const copy = async (row: ExtractionAttempt) => {
    const current = generation.current;
    const operation = ++copyGeneration.current;
    setCopyStatus(null);
    try { await navigator.clipboard.writeText(attemptCopy(row)); if (current === generation.current && operation === copyGeneration.current) setCopyStatus("copied"); }
    catch { if (current === generation.current && operation === copyGeneration.current) setCopyStatus("copyFailed"); }
  };
  const time = (value: string | null) => value ? new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "medium", timeZone: "Asia/Tokyo" }).format(new Date(value)) : t("pmgAttempt.unrecorded");
  return <div className="pmg-attempt">
    <Button variant="secondary" aria-expanded={open} onClick={() => { if (!open) setReload(value => value + 1); setOpen(value => !value); }}>{t("pmgAttempt.open")}</Button>
    {open && <section aria-label={t("pmgAttempt.title")} aria-busy={loading}>
      <p>{t("pmgAttempt.historyNote")}</p>
      <Button variant="secondary" onClick={() => { setReload(value => value + 1); setCopyStatus(null); }}>{t("pmgAttempt.refresh")}</Button>
      {loading && <p role="status">{t("pmgAttempt.loading")}</p>}
      {!loading && state.error && <p role="alert">{t("pmgAttempt.unavailable")}</p>}
      {rows?.length === 0 && <p>{t("pmgAttempt.empty")}</p>}
      {rows?.map(row => <article className="pmg-attempt__row" key={row.id}>
        <p><strong>{t(`pmgAttempt.completion.${row.completion}`)}</strong></p>
        <p>{t("pmgAttempt.phaseLabel")}: {t(`pmgAttempt.phase.${row.phase}`)}</p>
        {row.completion !== "completed" && <p>{t(`pmgAttempt.reason.${row.code}`)}</p>}
        <p>{t("pmgAttempt.id")}: {row.id}</p>
        <dl>{([["started", row.startedAt], ["received", row.receivedAt], ["finished", row.finishedAt]] as const).map(([label, value]) => <div key={label}><dt>{t(`pmgAttempt.${label}`)}</dt><dd>{time(value)}</dd></div>)}</dl>
        <Button variant="secondary" onClick={() => void copy(row)}>{t("pmgAttempt.copy")}</Button>
      </article>)}
      {copyStatus && !loading && !state.error && <p role={copyStatus === "copyFailed" ? "alert" : "status"}>{t(`pmgAttempt.${copyStatus}`)}</p>}
      <div className="pmg-workflow__pager"><Button variant="secondary" disabled={offset === 0 || loading} onClick={() => setOffset(value => Math.max(0, value - 25))}>{t("pmgWorkflow.previous")}</Button><Button variant="secondary" disabled={loading || !rows || rows.length < 25} onClick={() => setOffset(value => value + 25)}>{t("pmgWorkflow.next")}</Button></div>
    </section>}
  </div>;
}
