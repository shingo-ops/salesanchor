/**
 * テナント翻訳グロッサリ管理ページ（ADR-SA-17）。
 *
 * テナント固有の翻訳用語を登録・編集・削除する。
 * 共有行（tenant_id IS NULL）は読み取り専用（sharedBadge 表示）。
 *
 * ルート: /management-center/tenant-glossary
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import { STATUS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";

interface GlossaryEntry {
  id: number;
  tenant_id: number | null;
  source_term: string;
  target_text: string | null;
  language_pair: string;
  term_type: string;
  is_active: boolean;
  source_ref: string | null;
  notes: string | null;
}

interface GlossaryListResponse {
  items: GlossaryEntry[];
  total: number;
  page: number;
  per_page: number;
}

type FormState = {
  source_term: string;
  target_text: string;
  language_pair: string;
  term_type: string;
  notes: string;
};

const emptyForm: FormState = {
  source_term: "",
  target_text: "",
  language_pair: "en->ja",
  term_type: "general",
  notes: "",
};

const LANGUAGE_PAIRS = ["en->ja", "ja->en", "zh->ja", "ko->ja"];
const TERM_TYPES = ["general", "product_name", "brand", "grade", "abbreviation"];

export default function TenantGlossaryPage() {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();

  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<GlossaryEntry | null>(null);
  const [error, setError] = useState("");

  const canEdit = hasPermission("messaging.send");

  const PER_PAGE = 50;

  const load = async (p = page) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<GlossaryListResponse>(
        `/translation/glossary?page=${p}&per_page=${PER_PAGE}`
      );
      setEntries(res.items);
      setTotal(res.total);
      setPage(p);
    } catch {
      setError(t("common.loadError") ?? "");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(1); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openAdd = () => {
    setEditId(null);
    setForm(emptyForm);
    setShowForm(true);
  };

  const openEdit = (e: GlossaryEntry) => {
    if (e.tenant_id === null) return; // 共有行は編集不可
    setEditId(e.id);
    setForm({
      source_term: e.source_term,
      target_text: e.target_text ?? "",
      language_pair: e.language_pair,
      term_type: e.term_type,
      notes: e.notes ?? "",
    });
    setShowForm(true);
  };

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const body = {
        source_term: form.source_term.trim(),
        target_text: form.target_text.trim() || null,
        language_pair: form.language_pair,
        term_type: form.term_type,
        notes: form.notes.trim() || null,
      };
      if (editId === null) {
        await api.post("/translation/glossary", body);
      } else {
        await api.patch(`/translation/glossary/${editId}`, body);
      }
      setShowForm(false);
      await load(page);
    } catch {
      setError(t("common.saveError") ?? "");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/translation/glossary/${deleteTarget.id}`);
      setDeleteTarget(null);
      await load(page);
    } catch {
      setError(t("common.deleteError") ?? "");
    }
  };

  const termTypeLabel = (type: string): string =>
    ({
      general: t("tenantGlossary.termTypeGeneral"),
      product_name: t("tenantGlossary.termTypeProductName"),
      brand: t("tenantGlossary.termTypeBrand"),
      grade: t("tenantGlossary.termTypeGrade"),
      abbreviation: t("tenantGlossary.termTypeAbbreviation"),
    }[type] ?? type);

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <PageLayout
      navKey="nav.tenantGlossary"
      subtitleKey="tenantGlossary.subtitle"
      headerAction={
        canEdit ? (
          <div className="page-header-actions">
            <button className="btn-primary" onClick={openAdd}>
              {t("tenantGlossary.addEntry")}
            </button>
          </div>
        ) : undefined
      }
    >
      {error && <p className="error-message">{error}</p>}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>
              {editId === null
                ? t("tenantGlossary.addEntry")
                : t("tenantGlossary.editEntry")}
            </h3>
            <form onSubmit={handleSubmit}>
              <label>
                {t("tenantGlossary.sourceTerm")}
                <input
                  type="text"
                  value={form.source_term}
                  placeholder={t("tenantGlossary.sourceTermPlaceholder") ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, source_term: e.target.value }))
                  }
                  required
                />
              </label>
              <label>
                {t("tenantGlossary.targetText")}
                <input
                  type="text"
                  value={form.target_text}
                  placeholder={t("tenantGlossary.targetTextPlaceholder") ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, target_text: e.target.value }))
                  }
                />
              </label>
              <label>
                {t("tenantGlossary.languagePair")}
                <select
                  value={form.language_pair}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, language_pair: e.target.value }))
                  }
                >
                  {LANGUAGE_PAIRS.map((lp) => (
                    <option key={lp} value={lp}>
                      {lp}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t("tenantGlossary.termType")}
                <select
                  value={form.term_type}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, term_type: e.target.value }))
                  }
                >
                  {TERM_TYPES.map((tt) => (
                    <option key={tt} value={tt}>
                      {termTypeLabel(tt)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t("tenantGlossary.notes")}
                <input
                  type="text"
                  value={form.notes}
                  placeholder={t("tenantGlossary.notesPlaceholder") ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, notes: e.target.value }))
                  }
                />
              </label>
              <div className="modal-actions">
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "..." : t("common.save")}
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setShowForm(false)}
                >
                  {t("common.cancel")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p>{t("common.loading")}</p>
      ) : entries.length === 0 ? (
        <p className="empty-state">{t("tenantGlossary.empty")}</p>
      ) : (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>{t("tenantGlossary.sourceTerm")}</th>
                <th>{t("tenantGlossary.targetText")}</th>
                <th>{t("tenantGlossary.languagePair")}</th>
                <th>{t("tenantGlossary.termType")}</th>
                <th>{t("tenantGlossary.isActive")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td>
                    {e.source_term}
                    <span
                      className={`badge ${
                        e.tenant_id === null ? "badge-shared" : "badge-tenant"
                      }`}
                    >
                      {e.tenant_id === null
                        ? t("tenantGlossary.sharedBadge")
                        : t("tenantGlossary.tenantBadge")}
                    </span>
                  </td>
                  <td>
                    {e.target_text ?? (
                      <span className="text-muted">
                        {t("tenantGlossary.noTranslate")}
                      </span>
                    )}
                  </td>
                  <td>{e.language_pair}</td>
                  <td>{termTypeLabel(e.term_type)}</td>
                  <td>
                    {e.is_active
                      ? <STATUS_ICONS.check size={ICON.sm} aria-hidden="true" />
                      : null}
                  </td>
                  <td>
                    {canEdit && e.tenant_id !== null && (
                      <>
                        <button
                          className="btn-ghost btn-sm"
                          onClick={() => openEdit(e)}
                        >
                          {t("tenantGlossary.editEntry")}
                        </button>
                        <button
                          className="btn-ghost btn-sm btn-danger"
                          onClick={() => setDeleteTarget(e)}
                        >
                          {t("common.delete")}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn-ghost"
                disabled={page <= 1}
                onClick={() => load(page - 1)}
              >
                &laquo;
              </button>
              <span>
                {page} / {totalPages}
              </span>
              <button
                className="btn-ghost"
                disabled={page >= totalPages}
                onClick={() => load(page + 1)}
              >
                &raquo;
              </button>
            </div>
          )}
        </>
      )}

      {deleteTarget && (
        <ConfirmModal
          message={t("tenantGlossary.deleteConfirm")}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </PageLayout>
  );
}
