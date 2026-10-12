import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import { HeaderButton } from "../../components/HeaderButton";
import { TextField } from "../../components/TextField";

interface PreviewResponse {
  digest: string;
  total: number;
  inserts: number;
  updates: number;
  errors: string[];
}

interface CommitResponse {
  inserted: number;
  updated: number;
  errors: string[];
}

function StatusMasterImportPanel({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [result, setResult] = useState<CommitResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);

  function select(next: File | null) {
    if (lock.current || result) return;
    setPreview(null); setFile(null); setError("");
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".csv")) { setError(t("statusMasterCsv.invalidFormat")); return; }
    if (next.size === 0) { setError(t("statusMasterCsv.invalidFormat")); return; }
    if (next.size > 2 * 1024 * 1024) { setError(t("statusMasterCsv.fileTooLarge")); return; }
    setFile(next);
  }

  async function doPreview() {
    if (!file || lock.current || result) return;
    lock.current = true; setBusy(true); setError(""); setPreview(null);
    const form = new FormData(); form.append("file", file);
    try {
      setPreview(await api.postForm<PreviewResponse>("/status-master/import/preview", form));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("statusMasterCsv.commitFail"));
    } finally { lock.current = false; setBusy(false); }
  }

  async function doCommit() {
    if (!file || !preview || lock.current || result || preview.errors.length > 0) return;
    lock.current = true; setBusy(true); setError("");
    const form = new FormData(); form.append("file", file); form.append("digest", preview.digest);
    try {
      setResult(await api.postForm<CommitResponse>("/status-master/import/commit", form));
      setPreview(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setPreview(null); setFile(null); setError(t("statusMasterCsv.digestMismatch"));
      } else {
        setError(t("statusMasterCsv.commitFail"));
      }
    } finally { lock.current = false; setBusy(false); }
  }

  if (result) {
    return (
      <section aria-label={t("statusMasterCsv.commitSuccess")}>
        <p role="status">{t("statusMasterCsv.commitSuccess")}</p>
        <p>{t("statusMasterCsv.inserts")}: {result.inserted} / {t("statusMasterCsv.updates")}: {result.updated}</p>
        <ContentToolbar right={<HeaderButton variant="primary" onClick={onDone}>{t("statusMasterCsv.backToList")}</HeaderButton>} />
      </section>
    );
  }

  if (preview) {
    const hasErrors = preview.errors.length > 0;
    return (
      <section aria-label={t("statusMasterCsv.preview")}>
        <p>{t("statusMasterCsv.total")}: {preview.total} / {t("statusMasterCsv.inserts")}: {preview.inserts} / {t("statusMasterCsv.updates")}: {preview.updates} / {t("statusMasterCsv.errors")}: {preview.errors.length}</p>
        {hasErrors ? (
          <div role="alert">
            {preview.errors.map((msg, i) => <p key={i}>{msg}</p>)}
          </div>
        ) : (
          <p>{t("statusMasterCsv.noErrors")}</p>
        )}
        <ContentToolbar
          left={<HeaderButton variant="secondary" onClick={() => { if (!lock.current) { setPreview(null); setFile(null); setError(""); } }} disabled={busy}>{t("statusMasterCsv.cancel")}</HeaderButton>}
          right={<HeaderButton variant="primary" onClick={() => void doCommit()} disabled={busy || hasErrors}>{busy ? t("common.loading") : t("statusMasterCsv.commit")}</HeaderButton>}
        />
      </section>
    );
  }

  return (
    <>
      {error && <p role="alert">{error}</p>}
      <section
        aria-label={t("statusMasterCsv.selectFile")}
        onDragOver={e => e.preventDefault()}
        onDrop={e => {
          e.preventDefault();
          if (lock.current || result) return;
          if (e.dataTransfer.files.length !== 1) { setFile(null); setPreview(null); setError(t("productCsv.oneFile")); return; }
          select(e.dataTransfer.files[0]);
        }}
      >
        <TextField type="file" accept=".csv,text/csv" label={t("statusMasterCsv.selectFile")} disabled={busy} onChange={e => select(e.target.files?.[0] ?? null)} />
        {file && <p>{file.name}</p>}
      </section>
      <ContentToolbar
        left={<HeaderButton variant="secondary" onClick={onDone} disabled={busy}>{t("statusMasterCsv.backToList")}</HeaderButton>}
        right={<HeaderButton variant="primary" onClick={() => void doPreview()} disabled={!file || busy}>{busy ? t("common.loading") : t("statusMasterCsv.preview")}</HeaderButton>}
      />
    </>
  );
}

export default function StatusMasterImportTenantPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission, loading } = usePermissions();
  const canImport = hasPermission("suppliers.view");
  return (
    <PageLayout titleText={t("statusMasterCsv.importTitle")} subtitleKey="statusMasterCsv.importSubtitle">
      {loading ? <p>{t("common.loading")}</p>
       : !canImport ? <p role="alert">{t("productCsv.denied")}</p>
       : <StatusMasterImportPanel onDone={() => navigate("/management-center/status-master")} />}
      {!loading && !canImport && (
        <HeaderButton variant="secondary" onClick={() => navigate("/management-center/status-master")}>
          {t("statusMasterCsv.backToList")}
        </HeaderButton>
      )}
    </PageLayout>
  );
}
