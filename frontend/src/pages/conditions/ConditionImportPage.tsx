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

function ConditionImportPanel({ onDone }: { onDone: () => void }) {
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
    if (!next.name.toLowerCase().endsWith(".csv")) { setError(t("conditionCsv.invalidFormat")); return; }
    if (next.size === 0) { setError(t("conditionCsv.invalidFormat")); return; }
    if (next.size > 2 * 1024 * 1024) { setError(t("conditionCsv.fileTooLarge")); return; }
    setFile(next);
  }

  async function doPreview() {
    if (!file || lock.current || result) return;
    lock.current = true; setBusy(true); setError(""); setPreview(null);
    const form = new FormData(); form.append("file", file);
    try {
      setPreview(await api.postForm<PreviewResponse>("/conditions/import/preview", form));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("conditionCsv.commitFail"));
    } finally { lock.current = false; setBusy(false); }
  }

  async function doCommit() {
    if (!file || !preview || lock.current || result || preview.errors.length > 0) return;
    lock.current = true; setBusy(true); setError("");
    const form = new FormData(); form.append("file", file); form.append("digest", preview.digest);
    try {
      setResult(await api.postForm<CommitResponse>("/conditions/import/commit", form));
      setPreview(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setPreview(null); setFile(null); setError(t("conditionCsv.digestMismatch"));
      } else {
        setError(t("conditionCsv.commitFail"));
      }
    } finally { lock.current = false; setBusy(false); }
  }

  if (result) {
    return (
      <section aria-label={t("conditionCsv.commitSuccess")}>
        <p role="status">{t("conditionCsv.commitSuccess")}</p>
        <p>{t("conditionCsv.inserts")}: {result.inserted} / {t("conditionCsv.updates")}: {result.updated}</p>
        <ContentToolbar right={<HeaderButton variant="primary" onClick={onDone}>{t("conditionCsv.backToList")}</HeaderButton>} />
      </section>
    );
  }

  if (preview) {
    const hasErrors = preview.errors.length > 0;
    return (
      <section aria-label={t("conditionCsv.preview")}>
        <p>{t("conditionCsv.total")}: {preview.total} / {t("conditionCsv.inserts")}: {preview.inserts} / {t("conditionCsv.updates")}: {preview.updates} / {t("conditionCsv.errors")}: {preview.errors.length}</p>
        {hasErrors ? (
          <div role="alert">
            {preview.errors.map((msg, i) => <p key={i}>{msg}</p>)}
          </div>
        ) : (
          <p>{t("conditionCsv.noErrors")}</p>
        )}
        <ContentToolbar
          left={<HeaderButton variant="secondary" onClick={() => { if (!lock.current) { setPreview(null); setFile(null); setError(""); } }} disabled={busy}>{t("conditionCsv.cancel")}</HeaderButton>}
          right={<HeaderButton variant="primary" onClick={() => void doCommit()} disabled={busy || hasErrors}>{busy ? t("common.loading") : t("conditionCsv.commit")}</HeaderButton>}
        />
      </section>
    );
  }

  return (
    <>
      {error && <p role="alert">{error}</p>}
      <section
        aria-label={t("conditionCsv.selectFile")}
        onDragOver={e => e.preventDefault()}
        onDrop={e => {
          e.preventDefault();
          if (lock.current || result) return;
          if (e.dataTransfer.files.length !== 1) { setFile(null); setPreview(null); setError(t("productCsv.oneFile")); return; }
          select(e.dataTransfer.files[0]);
        }}
      >
        <TextField type="file" accept=".csv,text/csv" label={t("conditionCsv.selectFile")} disabled={busy} onChange={e => select(e.target.files?.[0] ?? null)} />
        {file && <p>{file.name}</p>}
      </section>
      <ContentToolbar
        left={<HeaderButton variant="secondary" onClick={onDone} disabled={busy}>{t("conditionCsv.backToList")}</HeaderButton>}
        right={<HeaderButton variant="primary" onClick={() => void doPreview()} disabled={!file || busy}>{busy ? t("common.loading") : t("conditionCsv.preview")}</HeaderButton>}
      />
    </>
  );
}

export default function ConditionImportTenantPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission, loading } = usePermissions();
  const canImport = hasPermission("conditions.view");
  return (
    <PageLayout titleText={t("conditionCsv.importTitle")} subtitleKey="conditionCsv.importSubtitle">
      {loading ? <p>{t("common.loading")}</p>
       : !canImport ? <p role="alert">{t("productCsv.denied")}</p>
       : <ConditionImportPanel onDone={() => navigate("/management-center/conditions")} />}
      {!loading && !canImport && (
        <HeaderButton variant="secondary" onClick={() => navigate("/management-center/conditions")}>
          {t("conditionCsv.backToList")}
        </HeaderButton>
      )}
    </PageLayout>
  );
}
