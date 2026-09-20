/**
 * ProductCategoriesImportPage — 商品カテゴリマスタ CSVインポート（スーパー管理者）
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。
 */
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
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

function ProductCategoriesImportPanel({ onDone }: { onDone: () => void }) {
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
    if (!next.name.toLowerCase().endsWith(".csv")) { setError(t("productCategoriesCsv.invalidFormat")); return; }
    if (next.size === 0) { setError(t("productCategoriesCsv.invalidFormat")); return; }
    if (next.size > 2 * 1024 * 1024) { setError(t("productCategoriesCsv.fileTooLarge")); return; }
    setFile(next);
  }

  async function doPreview() {
    if (!file || lock.current || result) return;
    lock.current = true; setBusy(true); setError(""); setPreview(null);
    const form = new FormData(); form.append("file", file);
    try {
      setPreview(await api.postForm<PreviewResponse>("/super-admin/product-categories/import/preview", form));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("productCategoriesCsv.commitFail"));
    } finally { lock.current = false; setBusy(false); }
  }

  async function doCommit() {
    if (!file || !preview || lock.current || result || preview.errors.length > 0) return;
    lock.current = true; setBusy(true); setError("");
    const form = new FormData(); form.append("file", file); form.append("digest", preview.digest);
    try {
      setResult(await api.postForm<CommitResponse>("/super-admin/product-categories/import/commit", form));
      setPreview(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setPreview(null); setFile(null); setError(t("productCategoriesCsv.digestMismatch"));
      } else {
        setError(t("productCategoriesCsv.commitFail"));
      }
    } finally { lock.current = false; setBusy(false); }
  }

  if (result) {
    return (
      <section aria-label={t("productCategoriesCsv.commitSuccess")}>
        <p role="status">{t("productCategoriesCsv.commitSuccess")}</p>
        <p>{t("productCategoriesCsv.inserts")}: {result.inserted} / {t("productCategoriesCsv.updates")}: {result.updated}</p>
        <ContentToolbar right={<HeaderButton variant="primary" onClick={onDone}>{t("productCategoriesCsv.backToList")}</HeaderButton>} />
      </section>
    );
  }

  if (preview) {
    const hasErrors = preview.errors.length > 0;
    return (
      <section aria-label={t("productCategoriesCsv.preview")}>
        <p>{t("productCategoriesCsv.total")}: {preview.total} / {t("productCategoriesCsv.inserts")}: {preview.inserts} / {t("productCategoriesCsv.updates")}: {preview.updates} / {t("productCategoriesCsv.errors")}: {preview.errors.length}</p>
        {hasErrors ? (
          <div role="alert">
            {preview.errors.map((msg, i) => <p key={i}>{msg}</p>)}
          </div>
        ) : (
          <p>{t("productCategoriesCsv.noErrors")}</p>
        )}
        <ContentToolbar
          left={<HeaderButton variant="secondary" onClick={() => { if (!lock.current) { setPreview(null); setFile(null); setError(""); } }} disabled={busy}>{t("productCategoriesCsv.cancel")}</HeaderButton>}
          right={<HeaderButton variant="primary" onClick={() => void doCommit()} disabled={busy || hasErrors}>{busy ? t("common.loading") : t("productCategoriesCsv.commit")}</HeaderButton>}
        />
      </section>
    );
  }

  return (
    <>
      {error && <p role="alert">{error}</p>}
      <section
        aria-label={t("productCategoriesCsv.selectFile")}
        onDragOver={e => e.preventDefault()}
        onDrop={e => {
          e.preventDefault();
          if (lock.current || result) return;
          if (e.dataTransfer.files.length !== 1) { setFile(null); setPreview(null); setError(t("productCategoriesCsv.invalidFormat")); return; }
          select(e.dataTransfer.files[0]);
        }}
      >
        <TextField type="file" accept=".csv,text/csv" label={t("productCategoriesCsv.selectFile")} disabled={busy} onChange={e => select(e.target.files?.[0] ?? null)} />
        {file && <p>{file.name}</p>}
      </section>
      <ContentToolbar
        left={<HeaderButton variant="secondary" onClick={onDone} disabled={busy}>{t("productCategoriesCsv.backToList")}</HeaderButton>}
        right={<HeaderButton variant="primary" onClick={() => void doPreview()} disabled={!file || busy}>{busy ? t("common.loading") : t("productCategoriesCsv.preview")}</HeaderButton>}
      />
    </>
  );
}

export default function ProductCategoriesImportPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isSuperAdmin, loading } = useSuperAdmin();
  return (
    <PageLayout titleText={t("productCategoriesCsv.importTitle")}>
      {loading ? <p>{t("common.loading")}</p> : !isSuperAdmin ? <p role="alert">{t("productCsv.denied")}</p> : <ProductCategoriesImportPanel onDone={() => navigate("/super-admin/analysis-rules")} />}
      {!loading && !isSuperAdmin && <HeaderButton variant="secondary" onClick={() => navigate("/super-admin/analysis-rules")}>{t("productCategoriesCsv.backToList")}</HeaderButton>}
    </PageLayout>
  );
}
