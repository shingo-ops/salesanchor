import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { TextField } from "../../components/TextField";
import { ContentToolbar } from "../../components/ContentToolbar";
import { Button } from "../../components/Button";
import { HeaderButton } from "../../components/HeaderButton";
import { TcgProductImportPreview, type PreviewResponse } from "./TcgProductImportPreview";
import { importMessage } from "./importMessages";

interface Result { job_id: string; filename: string; total: number; created: number; skipped: number }
export function TcgProductImportPanel({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const lock = useRef(false);
  function select(next: File | null) {
    if (lock.current || uncertain || result) return;
    setPreview(null); setFile(null); setError("");
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".csv")) { setError(t("productCsv.messages.notCsv")); return; }
    if (next.size === 0) { setError(t("productCsv.messages.csvEmpty")); return; }
    if (next.size > 2 * 1024 * 1024) { setError(t("productCsv.messages.tooLarge")); return; }
    setFile(next);
  }
  function downloadTemplate() {
    const anchor = document.createElement("a");
    anchor.href = "/templates/tcg-product-import-template.csv";
    anchor.download = "tcg-product-import-template.csv";
    document.body.appendChild(anchor);
    try { anchor.click(); }
    finally { anchor.remove(); }
  }
  async function review() {
    if (!file || lock.current || uncertain || result) return;
    lock.current = true; setBusy(true); setError(""); setPreview(null);
    const form = new FormData(); form.append("file", file);
    try { setPreview(await api.postForm<PreviewResponse>("/tcg/products/import/preview", form)); }
    catch (e) { setError(e instanceof ApiError ? importMessage(e.message, t) : t("productCsv.previewFailed")); }
    finally { lock.current = false; setBusy(false); }
  }
  async function commit() {
    if (!file || !preview || lock.current || uncertain || result || preview.ok === 0 || preview.file_errors.length) return;
    lock.current = true; setBusy(true); setError("");
    const form = new FormData(); form.append("file", file); form.append("confirmed_digest", preview.digest);
    try {
      const response = await api.postForm<Result>("/tcg/products/import/commit", form);
      if (typeof response.job_id !== "string" || !Number.isInteger(response.created) || !Number.isInteger(response.skipped)) throw new Error("Invalid import result");
      setResult(response); setPreview(null);
    } catch {
      // A failed response can follow a committed row: never offer an automatic retry.
      setUncertain(true); setError(t("productCsv.uncertain"));
    } finally { lock.current = false; setBusy(false); }
  }
  return <>
    <p>{t("productCsv.steps")}</p>
    {error && <p role="alert">{error}</p>}
    {result ? <section aria-label={t("productCsv.result")}>
      <p role="status">{t("productCsv.resultCounts", { total: result.total, created: result.created, skipped: result.skipped })}</p>
      <p>{t("productCsv.receipt", { id: result.job_id })}</p>
      <ContentToolbar right={<HeaderButton variant="primary" onClick={onDone}>{t("productCsv.back")}</HeaderButton>} />
    </section> : uncertain ? <ContentToolbar right={<HeaderButton variant="secondary" onClick={onDone}>{t("productCsv.back")}</HeaderButton>} /> : preview ? <TcgProductImportPreview preview={preview} busy={busy} onCommit={() => void commit()} onCancel={() => { if (!lock.current) { setPreview(null); setFile(null); setError(""); } }} /> : <>
      <ContentToolbar right={<Button variant="secondary" type="button" disabled={busy} onClick={downloadTemplate}>{t("productCsv.downloadTemplate")}</Button>} />
      <p>{t("productCsv.templateIntro")}</p>
      <p>{t("productCsv.templateRequired")} <code>japanese_title</code> / <code>division_code</code>, <code>work_code</code>, <code>manufacturer_code</code>, <code>product_category_code</code></p>
      <p>{t("productCsv.templateOptional")}</p>
      <section aria-label={t("productCsv.drop")} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (lock.current || uncertain || result) return; if (e.dataTransfer.files.length !== 1) { setFile(null); setPreview(null); setError(t("productCsv.oneFile")); return; } select(e.dataTransfer.files[0]); }}>
        <p>{t("productCsv.drop")}</p>
        <TextField type="file" accept=".csv,text/csv" label={t("productCsv.file")} disabled={busy} onChange={e => select(e.target.files?.[0] ?? null)} />
        {file && <p>{file.name}</p>}
      </section>
      <ContentToolbar left={<HeaderButton variant="secondary" onClick={onDone} disabled={busy}>{t("productCsv.back")}</HeaderButton>} right={<HeaderButton variant="primary" onClick={() => void review()} disabled={!file || busy}>{busy ? t("common.loading") : t("productCsv.review")}</HeaderButton>} />
    </>}
  </>;
}
