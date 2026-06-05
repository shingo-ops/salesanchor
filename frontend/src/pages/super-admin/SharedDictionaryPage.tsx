/**
 * 共有辞書ページ（ADR-SA-17 Layer1 共有ベース辞書 + 昇格レビュー / I-7・I-9）
 *
 * SaaS管理者（is_super_admin）専用。useSuperAdmin で 403 ガード（サイドバー導線も非表示の二重ガード）。
 * バックエンドも require_super_admin で構造的に保護され、いかなるテナント権限でも到達不可。
 *   - 共有エントリ（tenant_id=null）の CRUD
 *   - 昇格レビューキュー（テナントからの共有提案）の承認 / 却下（匿名）
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import {
  approvePromotion,
  createSharedGlossary,
  deleteSharedGlossary,
  listPromotionQueue,
  listSharedGlossary,
  rejectPromotion,
  updateSharedGlossary,
  type PromotionQueueItem,
  type SharedGlossaryEntry,
} from "../../lib/messages";

const LANGUAGE_PAIRS = ["en->ja", "ja->en"];
const TERM_TYPES = ["general", "product_name", "brand", "grade", "abbreviation", "jargon"];

type TabKey = "shared" | "queue";

export default function SharedDictionaryPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: authLoading } = useSuperAdmin();
  const [tab, setTab] = useState<TabKey>("shared");

  const [entries, setEntries] = useState<SharedGlossaryEntry[]>([]);
  const [queue, setQueue] = useState<PromotionQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [sourceTerm, setSourceTerm] = useState("");
  const [targetText, setTargetText] = useState("");
  const [languagePair, setLanguagePair] = useState(LANGUAGE_PAIRS[0]);
  const [termType, setTermType] = useState(TERM_TYPES[0]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [shared, promotions] = await Promise.all([
        listSharedGlossary(1, 200),
        listPromotionQueue(1, 200),
      ]);
      setEntries(shared.items);
      setQueue(promotions.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (isSuperAdmin) load();
  }, [isSuperAdmin, load]);

  if (authLoading) {
    return <div className="page">{t("common.loading")}</div>;
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.sharedDictionary">
        <div className="error-message" role="alert">{t("superAdmin.accessDenied")}</div>
      </PageLayout>
    );
  }

  const handleAdd = async () => {
    if (!sourceTerm.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createSharedGlossary({
        source_term: sourceTerm.trim(),
        target_text: targetText.trim() === "" ? null : targetText.trim(),
        language_pair: languagePair,
        term_type: termType,
      });
      setSourceTerm("");
      setTargetText("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const handleToggleActive = async (entry: SharedGlossaryEntry) => {
    setBusy(true);
    try {
      await updateSharedGlossary(entry.id, { is_active: !entry.is_active });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(t("glossary.confirmDelete"))) return;
    setBusy(true);
    try {
      await deleteSharedGlossary(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const handleApprove = async (id: number) => {
    setBusy(true);
    try {
      await approvePromotion(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const handleReject = async (id: number) => {
    setBusy(true);
    try {
      await rejectPromotion(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageLayout navKey="nav.sharedDictionary" subtitleKey="glossary.sharedSubtitle">
      {error && <div className="error-message" role="alert">{error}</div>}

      <div
        role="tablist"
        aria-label="shared dictionary tabs"
        style={{ display: "flex", gap: "var(--space-2)", margin: "var(--space-3) 0", borderBottom: "1px solid var(--border-light)" }}
      >
        <button
          role="tab"
          aria-selected={tab === "shared"}
          className={tab === "shared" ? "btn-primary" : "btn-secondary"}
          onClick={() => setTab("shared")}
          data-testid="shared-dict-tab-shared"
        >
          {t("glossary.tabShared")}
        </button>
        <button
          role="tab"
          aria-selected={tab === "queue"}
          className={tab === "queue" ? "btn-primary" : "btn-secondary"}
          onClick={() => setTab("queue")}
          data-testid="shared-dict-tab-queue"
        >
          {t("glossary.tabQueue")} ({queue.length})
        </button>
      </div>

      {loading && <div>{t("glossary.loading")}</div>}

      {!loading && tab === "shared" && (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginBottom: "var(--space-3)", alignItems: "flex-end" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
              <span>{t("glossary.sourceTerm")}</span>
              <input value={sourceTerm} onChange={(e) => setSourceTerm(e.target.value)} />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
              <span>{t("glossary.targetText")}</span>
              <input
                value={targetText}
                onChange={(e) => setTargetText(e.target.value)}
                placeholder={t("glossary.targetTextPlaceholder")}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
              <span>{t("glossary.languagePair")}</span>
              <select value={languagePair} onChange={(e) => setLanguagePair(e.target.value)}>
                {LANGUAGE_PAIRS.map((p) => (
                  <option key={p} value={p}>{t(`glossary.pair.${p}`)}</option>
                ))}
              </select>
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
              <span>{t("glossary.termType")}</span>
              <select value={termType} onChange={(e) => setTermType(e.target.value)}>
                {TERM_TYPES.map((tt) => (
                  <option key={tt} value={tt}>{t(`glossary.type.${tt}`)}</option>
                ))}
              </select>
            </label>
            <button className="btn-primary" onClick={handleAdd} disabled={busy || !sourceTerm.trim()}>
              {t("glossary.add")}
            </button>
          </div>

          {entries.length === 0 ? (
            <div>{t("glossary.empty")}</div>
          ) : (
            <table className="data-table" style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th>{t("glossary.sourceTerm")}</th>
                  <th>{t("glossary.targetText")}</th>
                  <th>{t("glossary.languagePair")}</th>
                  <th>{t("glossary.termType")}</th>
                  <th>{t("glossary.status")}</th>
                  <th>{t("glossary.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td>{e.source_term}</td>
                    <td>{e.target_text ?? t("glossary.doNotTranslate")}</td>
                    <td>{t(`glossary.pair.${e.language_pair}`)}</td>
                    <td>{t(`glossary.type.${e.term_type}`)}</td>
                    <td>{e.is_active ? t("glossary.active") : t("glossary.inactive")}</td>
                    <td>
                      <span style={{ display: "flex", gap: "var(--space-1)" }}>
                        <button className="btn-ghost" onClick={() => handleToggleActive(e)} disabled={busy}>
                          {e.is_active ? t("glossary.disable") : t("glossary.enable")}
                        </button>
                        <button className="btn-ghost btn-danger" onClick={() => handleDelete(e.id)} disabled={busy}>
                          {t("glossary.delete")}
                        </button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {!loading && tab === "queue" && (
        queue.length === 0 ? (
          <div>{t("glossary.queueEmpty")}</div>
        ) : (
          <table className="data-table" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>{t("glossary.sourceTerm")}</th>
                <th>{t("glossary.targetText")}</th>
                <th>{t("glossary.languagePair")}</th>
                <th>{t("glossary.termType")}</th>
                <th>{t("glossary.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((q) => (
                <tr key={q.id}>
                  <td>{q.source_term}</td>
                  <td>{q.target_text ?? t("glossary.doNotTranslate")}</td>
                  <td>{t(`glossary.pair.${q.language_pair}`)}</td>
                  <td>{t(`glossary.type.${q.term_type}`)}</td>
                  <td>
                    <span style={{ display: "flex", gap: "var(--space-1)" }}>
                      <button className="btn-primary" onClick={() => handleApprove(q.id)} disabled={busy}>
                        {t("glossary.approve")}
                      </button>
                      <button className="btn-ghost btn-danger" onClick={() => handleReject(q.id)} disabled={busy}>
                        {t("glossary.reject")}
                      </button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </PageLayout>
  );
}
