/**
 * リード統合モーダル（ADR-119 PR-E）。
 *
 * 役割:
 *   ソースリード（loser = 消える側）を既存の master リードへ吸収させる UI。
 *   会社統合の MergeCompanyModal と同じ 2 段階 UI を踏襲。
 *
 *   loser に紐づく meta_messages・lead_channels が全て master に付け替えられ、
 *   loser のリードレコードは削除される。
 *
 * 安全策:
 *   1. loser が成約済み（converted_deal_id != null）の場合は backend が 400 を返す。
 *      フロントでも convertedError メッセージを分かりやすく表示する。
 *   2. 確定前に「取り消せません」の警告ダイアログ
 *   3. 任意の reason 入力欄（audit_logs に記録）
 */

import { useEffect, useMemo, useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import { getStatusPresentation } from "../utils/statusPresentation";
import { Modal } from "./Modal";

interface LeadOption {
  id: number;
  lead_code: string | null;
  customer_name: string;
  status: string;
}

interface Props {
  open: boolean;
  /** マージ元（loser = 吸収されて削除される側）のリード */
  source: { id: number; lead_code: string | null; customer_name: string };
  /** 成功後コールバック。master の id を渡す */
  onMerged: (masterId: number) => void;
  onCancel: () => void;
}

const PER_PAGE_CAP = 100;
const SEARCH_DEBOUNCE_MS = 250;

export default function MergeLeadModal({ open, source, onMerged, onCancel }: Props) {
  const { t } = useTranslation();
  const [candidates, setCandidates] = useState<LeadOption[]>([]);
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<LeadOption | null>(null);
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
        ? `/leads?per_page=${PER_PAGE_CAP}&search=${encodeURIComponent(q)}`
        : `/leads?per_page=${PER_PAGE_CAP}`;
      api
        .get<LeadOption[]>(path)
        .then((rows) => {
          if (cancelled) return;
          // 自分自身を除外（master 候補から loser は外す）
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
  }, [open, source.id, search]);

  const selected = useMemo(() => {
    const fromList = candidates.find((c) => c.id === selectedId) || null;
    if (fromList) return fromList;
    if (selectedSnapshot && selectedSnapshot.id === selectedId) return selectedSnapshot;
    return null;
  }, [candidates, selectedId, selectedSnapshot]);

  const sourceCode = source.lead_code ?? `#${source.id}`;

  const handleConfirmSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/leads/${selected.id}/merge`, {
        loser_id: source.id,
        reason: reason.trim() || null,
      });
      onMerged(selected.id);
    } catch (e: unknown) {
      // backend 400 で loser が成約済みの場合は分かりやすいメッセージに差し替える
      const msg = e instanceof Error ? e.message : "";
      if (msg.includes("converted")) {
        setError(t("mergeLead.convertedError"));
      } else {
        setError(msg || t("common.operationError"));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onCancel} title={t("mergeLead.title")} size="md">
      <div className="modal-content-wide">
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-base)", marginTop: "var(--space-1)" }}>
          {t("mergeLead.sourceDesc", { name: source.customer_name, code: sourceCode })}
        </p>

        {error && <div className="error-banner">{error}</div>}

        {stage === "select" && (
          <>
            <div className="form-row">
              <label>{t("mergeLead.selectMaster")}</label>
              <input
                type="text"
                placeholder={t("mergeLead.searchPlaceholder")}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

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
                {t("mergeLead.resultsCapped", { count: PER_PAGE_CAP })}
              </div>
            )}

            <div
              style={{
                maxHeight: 'var(--dropdown-list-h)',
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
                  {t("mergeLead.noResults")}
                </p>
              ) : (
                <table className="data-table" style={{ marginBottom: 0 }}>
                  <thead>
                    <tr>
                      <th style={{ width: 'var(--col-width-checkbox)' }}></th>
                      <th>{t("mergeLead.col_code")}</th>
                      <th>{t("mergeLead.col_name")}</th>
                      <th>{t("mergeLead.col_status")}</th>
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
                        <td>{c.lead_code ?? `#${c.id}`}</td>
                        <td>{c.customer_name}</td>
                        <td>
                          <span className={`badge badge-${getStatusPresentation("lead", c.status).badgeVariant}`}>
                            {t(`leads.statusCode.${c.status}`, { defaultValue: c.status })}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="form-row" style={{ marginTop: "var(--space-4)" }}>
              <label>{t("mergeLead.reasonLabel")}</label>
              <textarea
                rows={2}
                placeholder={t("mergeLead.reasonPlaceholder")}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                maxLength={500}
              />
            </div>

            <div className="form-actions">
              <button type="button" onClick={onCancel}>
                {t("common.cancel")}
              </button>
              <button
                type="button"
                className="btn-primary"
                disabled={!selected}
                onClick={() => setStage("confirm")}
              >
                {t("mergeLead.nextStep")}
              </button>
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
              <strong>{t("mergeLead.confirmWarning")}</strong>
              <ul style={{ marginTop: "var(--space-2)", marginBottom: 0, paddingLeft: "var(--space-5)" }}>
                <li>
                  {t("mergeLead.confirmDesc1", {
                    sourceName: source.customer_name,
                    sourceCode,
                    masterName: selected.customer_name,
                    masterCode: selected.lead_code ?? `#${selected.id}`,
                  })}
                </li>
                <li>
                  {t("mergeLead.confirmDesc2", { sourceName: source.customer_name })}
                </li>
                <li>{t("mergeLead.confirmDesc3")}</li>
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
                <strong>{t("mergeLead.reasonTitle")}:</strong> {reason.trim()}
              </div>
            )}

            <div className="form-actions">
              <button
                type="button"
                onClick={() => setStage("select")}
                disabled={submitting}
              >
                {t("common.back")}
              </button>
              <button
                type="submit"
                className="btn-danger"
                disabled={submitting}
              >
                {submitting
                  ? t("mergeLead.merging")
                  : t("mergeLead.executeLabel", { masterName: selected.customer_name })}
              </button>
            </div>
          </form>
        )}
      </div>
    </Modal>
  );
}
