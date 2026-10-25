import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { TextField } from "../../components/TextField";
import { ContentToolbar } from "../../components/ContentToolbar";
import { Button } from "../../components/Button";
import { HeaderButton } from "../../components/HeaderButton";
import { ReviewCsvPreviewTable } from "./ReviewCsvPreviewTable";
import { MAX_CSV_BYTES, reviewCsvMessage, type ReviewCsvPreview, type ReviewCsvResult } from "./reviewCsvTypes";

const EXPORT_FILE_NAME = "tcg-needs-review.csv";

export function ReviewCsvPanel({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ReviewCsvPreview | null>(null);
  const [result, setResult] = useState<ReviewCsvResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const lock = useRef(false);

  function select(next: File | null) {
    if (lock.current || uncertain || result) return;
    setPreview(null); setFile(null); setError("");
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".csv")) { setError(reviewCsvMessage("REVIEW_CSV_NOT_CSV", t)); return; }
    if (next.size === 0) { setError(reviewCsvMessage("REVIEW_CSV_EMPTY_FILE", t)); return; }
    if (next.size > MAX_CSV_BYTES) { setError(reviewCsvMessage("PRODUCT_IMPORT_FILE_TOO_LARGE", t)); return; }
    setFile(next);
  }

  async function download() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    let url: string | undefined;
    const anchor = document.createElement("a");
    try {
      const blob = await api.getBlob("/tcg/review/csv/export");
      url = URL.createObjectURL(blob); anchor.href = url; anchor.download = EXPORT_FILE_NAME;
      document.body.appendChild(anchor); anchor.click();
    } catch { setError(t("reviewCsv.downloadFailed")); }
    finally { anchor.remove(); if (url) URL.revokeObjectURL(url); lock.current = false; setBusy(false); }
  }

  async function review() {
    if (!file || lock.current || uncertain || result) return;
    lock.current = true; setBusy(true); setError(""); setPreview(null);
    const form = new FormData(); form.append("file", file);
    try { setPreview(await api.postForm<ReviewCsvPreview>("/tcg/review/csv/preview", form)); }
    catch (e) { setError(e instanceof ApiError ? reviewCsvMessage(e.message, t) : t("reviewCsv.previewFailed")); }
    finally { lock.current = false; setBusy(false); }
  }

  async function commit() {
    if (!file || !preview || lock.current || uncertain || result || preview.applies.length === 0) return;
    lock.current = true; setBusy(true); setError("");
    const form = new FormData(); form.append("file", file); form.append("confirmed_digest", preview.digest);
    try {
      setResult(await api.postForm<ReviewCsvResult>("/tcg/review/csv/commit", form)); setPreview(null);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 409 || e.status === 422)) {
        setPreview(null); setFile(null); setError(t("reviewCsv.rejected")); return;
      }
      // 失敗の応答が保存のあとに返ることがある。自動で再送はしない。
      setUncertain(true); setError(t("reviewCsv.uncertain"));
    } finally { lock.current = false; setBusy(false); }
  }

  return <>
    <p>{t("reviewCsv.steps")}</p>
    {error && <p role="alert">{error}</p>}
    {result ? <section aria-label={t("reviewCsv.resultTitle")}>
      <p role="status">{t("reviewCsv.resultCounts", { saved: result.saved, failed: result.failed.length })}</p>
      <p>{t("reviewCsv.reanalyzeNote")}</p>
      <ContentToolbar right={<HeaderButton variant="primary" onClick={onDone}>{t("reviewCsv.done")}</HeaderButton>} />
    </section> : uncertain ? <ContentToolbar right={<HeaderButton variant="secondary" onClick={onDone}>{t("reviewCsv.done")}</HeaderButton>} />
    : preview ? <ReviewCsvPreviewTable preview={preview} busy={busy} onCommit={() => void commit()} onCancel={() => { if (!lock.current) { setPreview(null); setFile(null); setError(""); } }} />
    : <>
      <ContentToolbar right={<Button variant="secondary" type="button" disabled={busy} onClick={() => void download()}>{t("reviewCsv.download")}</Button>} />
      <p>{t("reviewCsv.inputHint")}</p>
      <TextField type="file" accept=".csv,text/csv" label={t("reviewCsv.file")} disabled={busy} onChange={e => select(e.target.files?.[0] ?? null)} />
      {file && <p>{file.name}</p>}
      <ContentToolbar right={<HeaderButton loading={busy} variant="primary" onClick={() => void review()} disabled={!file || busy}>{t("reviewCsv.review")}</HeaderButton>} />
    </>}
  </>;
}
