/**
 * テナント辞書ページ（ADR-SA-17 Layer2 私有辞書 / I-7）
 *
 * 管理センターのサブメニュー。tenant_admin / tenant_staff（translation.glossary.view/edit）のみ。
 * 私有グロッサリの CRUD ＋ 共有ベースへの「共有提案」。共有エントリ（tenant_id=null）は読み取り専用。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { PageLayout } from "../../components/PageLayout";
import {
  createGlossaryEntry,
  deleteGlossaryEntry,
  listGlossary,
  proposeGlossaryShare,
  seedGlossaryFromProducts,
  updateGlossaryEntry,
  type GlossaryEntry,
} from "../../lib/messages";

const LANGUAGE_PAIRS = ["en->ja", "ja->en"];
const TERM_TYPES = ["general", "product_name", "brand", "grade", "abbreviation", "jargon"];

export default function TenantDictionaryPage() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // add form state
  const [sourceTerm, setSourceTerm] = useState("");
  const [targetText, setTargetText] = useState("");
  const [languagePair, setLanguagePair] = useState(LANGUAGE_PAIRS[0]);
  const [termType, setTermType] = useState(TERM_TYPES[0]);
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listGlossary(1, 200);
      setEntries(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    if (!sourceTerm.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createGlossaryEntry({
        source_term: sourceTerm.trim(),
        target_text: targetText.trim() === "" ? null : targetText.trim(),
        language_pair: languagePair,
        term_type: termType,
        notes: notes.trim() === "" ? null : notes.trim(),
      });
      setSourceTerm("");
      setTargetText("");
      setNotes("");
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
      await deleteGlossaryEntry(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const handlePropose = async (id: number) => {
    setBusy(true);
    try {
      await proposeGlossaryShare(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const handleToggleActive = async (entry: GlossaryEntry) => {
    setBusy(true);
    try {
      await updateGlossaryEntry(entry.id, { is_active: !entry.is_active });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const handleSeed = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await seedGlossaryFromProducts();
      window.alert(t("glossary.seedDone", { count: res.seeded }));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("glossary.error"));
    } finally {
      setBusy(false);
    }
  };

  const shareLabel = (status?: string): string => {
    switch (status) {
      case "proposed":
        return t("glossary.proposed");
      case "approved":
        return t("glossary.approved");
      case "rejected":
        return t("glossary.rejected");
      default:
        return "";
    }
  };

  return (
    <PageLayout navKey="nav.tenantDictionary" subtitleKey="glossary.tenantSubtitle">
      {error && (
        <div className="error-message" role="alert">{error}</div>
      )}

      {/* 追加フォーム */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", margin: "var(--space-3) 0", alignItems: "flex-end" }}>
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
        <label style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
          <span>{t("glossary.notes")}</span>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button className="btn-primary" onClick={handleAdd} disabled={busy || !sourceTerm.trim()}>
          {t("glossary.add")}
        </button>
        <button className="btn-secondary" onClick={handleSeed} disabled={busy}>
          {t("glossary.seedProducts")}
        </button>
      </div>

      {loading ? (
        <div>{t("glossary.loading")}</div>
      ) : entries.length === 0 ? (
        <div>{t("glossary.empty")}</div>
      ) : (
        <table className="data-table" style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>{t("glossary.sourceTerm")}</th>
              <th>{t("glossary.targetText")}</th>
              <th>{t("glossary.languagePair")}</th>
              <th>{t("glossary.termType")}</th>
              <th>{t("glossary.scope")}</th>
              <th>{t("glossary.status")}</th>
              <th>{t("glossary.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => {
              const isShared = e.tenant_id === null;
              return (
                <tr key={e.id}>
                  <td>{e.source_term}</td>
                  <td>{e.target_text ?? t("glossary.doNotTranslate")}</td>
                  <td>{t(`glossary.pair.${e.language_pair}`)}</td>
                  <td>{t(`glossary.type.${e.term_type}`)}</td>
                  <td>{isShared ? t("glossary.shared") : t("glossary.private")}</td>
                  <td>{e.is_active ? shareLabel(e.share_status) : t("glossary.inactive")}</td>
                  <td>
                    {isShared ? (
                      <span>{t("glossary.readOnly")}</span>
                    ) : (
                      <span style={{ display: "flex", gap: "var(--space-1)" }}>
                        <button
                          className="btn-ghost"
                          onClick={() => handleToggleActive(e)}
                          disabled={busy}
                        >
                          {e.is_active ? t("glossary.disable") : t("glossary.enable")}
                        </button>
                        <button
                          className="btn-ghost"
                          onClick={() => handlePropose(e.id)}
                          disabled={busy || e.share_status === "proposed" || e.share_status === "approved"}
                        >
                          {t("glossary.proposeShare")}
                        </button>
                        <button
                          className="btn-ghost btn-danger"
                          onClick={() => handleDelete(e.id)}
                          disabled={busy}
                        >
                          {t("glossary.delete")}
                        </button>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </PageLayout>
  );
}
