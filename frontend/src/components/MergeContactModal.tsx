/**
 * 担当者統合モーダル（ADR-098 SA-04 J3）。
 *
 * 役割:
 *   ソース担当者（loser = 消える側）を同一会社内の master 担当者へ吸収させる UI。
 *   MergeLeadModal と同じ 2 段階 UI を踏襲。
 *
 *   loser に紐づく contact_contact_channels が全て master に付け替えられ、
 *   loser の担当者レコードは削除される。
 *
 * 安全策:
 *   1. loser が deals/orders/quotes/invoices を持つ場合は backend が 400 を返す。
 *   2. 確定前に「取り消せません」の警告ダイアログ
 *   3. 任意の reason 入力欄（audit_logs に記録）
 */

import { useEffect, useMemo, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { TextField } from "./TextField";
import { Textarea } from "./Textarea";
import { getStatusPresentation } from "../utils/statusPresentation";

interface ContactOption {
  id: number;
  contact_code: string;
  display_name: string | null;
  surname: string | null;
  given_name: string | null;
  status: string;
}

interface Props {
  open: boolean;
  companyId: number;
  /** マージ元（loser = 吸収されて削除される側）の担当者 */
  source: { id: number; contact_code: string; display_name: string | null; surname: string | null; given_name: string | null };
  /** 成功後コールバック。master の id を渡す */
  onMerged: (masterId: number) => void;
  onCancel: () => void;
}

const PER_PAGE_CAP = 100;
const SEARCH_DEBOUNCE_MS = 250;

function contactDisplayName(c: ContactOption | Props["source"]): string {
  return (
    c.display_name ||
    [c.surname, c.given_name].filter(Boolean).join(" ") ||
    `#${"id" in c ? c.id : "?"}`
  );
}

export default function MergeContactModal({ open, companyId, source, onMerged, onCancel }: Props) {
  const { t } = useTranslation();
  const [candidates, setCandidates] = useState<ContactOption[]>([]);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<ContactOption | null>(null);
  const [reason, setReason] = useState("");
  const [stage, setStage] = useState<"select" | "confirm">("select");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultsCapped, setResultsCapped] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSelectedId(null);
    setSelectedSnapshot(null);
    setReason("");
    setStage("select");
    setError(null);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const q = search.trim();
    let cancelled = false;
    const handle = window.setTimeout(() => {
      setLoading(true);
      const path = q
        ? `/companies/${companyId}/contacts?per_page=${PER_PAGE_CAP}&search=${encodeURIComponent(q)}`
        : `/companies/${companyId}/contacts?per_page=${PER_PAGE_CAP}`;
      api
        .get<ContactOption[]>(path)
        .then((rows) => {
          if (cancelled) return;
          const filtered = rows.filter((r) => r.id !== source.id);
          setCandidates(filtered);
          setResultsCapped(rows.length >= PER_PAGE_CAP);
        })
        .catch((e: unknown) => {
          if (cancelled) return;
          setError(e instanceof Error ? e.message : t("common.fetchError"));
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, q ? SEARCH_DEBOUNCE_MS : 0);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, companyId, source.id, search]);

  const selected = useMemo(() => {
    const fromList = candidates.find((c) => c.id === selectedId) || null;
    if (fromList) return fromList;
    if (selectedSnapshot && selectedSnapshot.id === selectedId) return selectedSnapshot;
    return null;
  }, [candidates, selectedId, selectedSnapshot]);

  const sourceCode = source.contact_code ?? `#${source.id}`;
  const sourceName = contactDisplayName(source);

  const handleConfirmSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/contacts/${selected.id}/merge`, {
        loser_id: source.id,
        reason: reason.trim() || null,
      });
      onMerged(selected.id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "";
      // eslint-disable-next-line local/no-japanese-literal
      if (msg.includes("関連レコード") || msg.includes("related")) {
        setError(t("mergeContact.relatedError"));
      } else {
        setError(msg || t("common.operationError"));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onCancel} title={t("mergeContact.title")} size="md">
      <div className="modal-content-wide">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-base)", marginTop: "var(--space-1)" }}>
          {t("mergeContact.sourceDesc", { name: sourceName, code: sourceCode })}
        </p>

        {error && <div className="error-banner">{error}</div>}

        {stage === "select" && (
          <>
            <TextField
              label={t("mergeContact.selectMaster")}
              type="text"
              placeholder={t("mergeContact.searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />

            {resultsCapped && (
              <div
                style={{
                  background: "var(--warning-bg)",
                  border: "1px solid var(--warning-text)",
                  padding: "var(--space-2)",
                  borderRadius: "var(--radius-sm)",
                  marginTop: "var(--space-2)",
                  fontSize: "var(--font-sm)",
                  color: "var(--warning-text)",
                }}
              >
                {t("mergeContact.resultsCapped", { count: PER_PAGE_CAP })}
              </div>
            )}

            <div
              style={{
                maxHeight: "var(--dropdown-list-h)",
                overflowY: "auto",
                border: "1px solid var(--border-light)",
                borderRadius: "var(--radius-sm)",
                marginTop: "var(--space-2)",
              }}
            >
              {loading ? (
                <p style={{ padding: "var(--space-4)", textAlign: "center" }}>{t("common.loading")}</p>
              ) : candidates.length === 0 ? (
                <p style={{ padding: "var(--space-4)", textAlign: "center", color: "var(--text-muted)" }}>
                  {t("mergeContact.noResults")}
                </p>
              ) : (
                <table className="data-table" style={{ marginBottom: 0 }}>
                  <thead>
                    <tr>
                      <th style={{ width: "var(--col-width-checkbox)" }}></th>
                      <th>{t("mergeContact.col_code")}</th>
                      <th>{t("mergeContact.col_name")}</th>
                      <th>{t("mergeContact.col_status")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c) => (
                      <tr
                        key={c.id}
                        onClick={() => {
                          setSelectedId(c.id);
                          setSelectedSnapshot(c);
                        }}
                        style={{
                          cursor: "pointer",
                          background: c.id === selectedId ? "var(--warning-bg)" : undefined,
                        }}
                      >
                        <td>
                          {/* radio は TextField 対象外のため残置 */}
                          <input
                            type="radio"
                            name="master-candidate"
                            checked={c.id === selectedId}
                            onChange={() => {
                              setSelectedId(c.id);
                              setSelectedSnapshot(c);
                            }}
                          />
                        </td>
                        <td>{c.contact_code}</td>
                        <td>{contactDisplayName(c)}</td>
                        <td>
                          <span className={`badge badge-${getStatusPresentation("contact", c.status).badgeVariant}`}>
                            {t(`contacts.statusCode.${c.status}`, { defaultValue: c.status })}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div style={{ marginTop: "var(--space-4)" }}>
              <Textarea
                label={t("mergeContact.reasonLabel")}
                rows={2}
                placeholder={t("mergeContact.reasonPlaceholder")}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                maxLength={500}
              />
            </div>

            <div className="form-actions">
              <Button type="button" variant="secondary" onClick={onCancel}>
                {t("common.cancel")}
              </Button>
              <Button
                type="button"
                variant="primary"
                disabled={!selected}
                onClick={() => setStage("confirm")}
              >
                {t("mergeContact.nextStep")}
              </Button>
            </div>
          </>
        )}

        {stage === "confirm" && selected && (
          <form onSubmit={handleConfirmSubmit}>
            <div
              style={{
                background: "var(--warning-bg)",
                border: "1px solid var(--warning-text)",
                padding: "var(--space-3)",
                borderRadius: "var(--radius-sm)",
                marginBottom: "var(--space-4)",
              }}
            >
              <strong>{t("mergeContact.confirmWarning")}</strong>
              <ul style={{ marginTop: "var(--space-2)", marginBottom: 0, paddingLeft: "var(--space-5)" }}>
                <li>
                  {t("mergeContact.confirmDesc1", {
                    sourceName,
                    sourceCode,
                    masterName: contactDisplayName(selected),
                    masterCode: selected.contact_code,
                  })}
                </li>
                <li>
                  {t("mergeContact.confirmDesc2", { sourceName })}
                </li>
                <li>{t("mergeContact.confirmDesc3")}</li>
              </ul>
            </div>

            {reason.trim() && (
              <div
                style={{
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--border)",
                  padding: "var(--space-2)",
                  borderRadius: "var(--radius-sm)",
                  marginBottom: "var(--space-4)",
                  fontSize: "var(--font-base)",
                }}
              >
                <strong>{t("mergeContact.reasonTitle")}:</strong> {reason.trim()}
              </div>
            )}

            <div className="form-actions">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setStage("select")}
                disabled={submitting}
              >
                {t("common.back")}
              </Button>
              <Button
                type="submit"
                variant="danger"
                disabled={submitting}
              >
                {submitting
                  ? t("mergeContact.merging")
                  : t("mergeContact.executeLabel", { masterName: contactDisplayName(selected) })}
              </Button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
}
