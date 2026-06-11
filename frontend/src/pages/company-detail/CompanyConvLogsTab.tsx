/**
 * CompanyConvLogsTab — 会社別会話ログ一覧（SA-02 Stage 4）
 *
 * 会社の全 conversation_logs を時系列で表示（読み取り専用）。
 * contact フィルタで絞り込み可能。
 * 自動受信・手動記録の混在スレッド表示。
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";

interface ConvLogEntry {
  id: number;
  contact_id: number | null;
  lead_id: number | null;
  channel_type: string;
  direction: "inbound" | "outbound";
  content_text: string | null;
  translated_text: string | null;
  occurred_at: string | null;
  recorded_by_user_id: number | null;
  contact_display_name: string | null;
}

interface Contact {
  id: number;
  display_name: string | null;
  surname: string | null;
  given_name: string | null;
}

interface Props {
  companyId: number;
  contacts: Contact[];
}

export function CompanyConvLogsTab({ companyId, contacts }: Props) {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<ConvLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedContactId, setSelectedContactId] = useState<string>("");

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const params = selectedContactId ? `?contact_id=${selectedContactId}` : "";
    api
      .get<ConvLogEntry[]>(`/api/v1/companies/${companyId}/conv-logs${params}`)
      .then((res) => {
        const data: ConvLogEntry[] = Array.isArray(res) ? res : (res as { data?: ConvLogEntry[] }).data ?? [];
        setLogs(data);
      })
      .catch(() => setError(t("companies.convHistory.loadError")))
      .finally(() => setLoading(false));
  }, [companyId, selectedContactId, t]);

  useEffect(() => { load(); }, [load]);

  const contactName = (log: ConvLogEntry): string => {
    if (log.contact_display_name) return log.contact_display_name;
    if (log.contact_id) return `#${log.contact_id}`;
    return t("companies.convHistory.noContact");
  };

  return (
    <div className="company-conv-logs-tab">
      {/* フィルタ行 */}
      <div className="conv-logs-filter-row">
        <label htmlFor="conv-contact-filter" className="conv-logs-filter-label">
          {t("companies.convHistory.filterByContact")}
        </label>
        <select
          id="conv-contact-filter"
          className="conv-logs-filter-select"
          value={selectedContactId}
          onChange={(e) => setSelectedContactId(e.target.value)}
          aria-label={t("companies.convHistory.filterByContact")}
        >
          <option value="">{t("companies.convHistory.allContacts")}</option>
          {contacts.map((c) => {
            const name = c.display_name || `${c.surname ?? ""} ${c.given_name ?? ""}`.trim() || `#${c.id}`;
            return (
              <option key={c.id} value={String(c.id)}>
                {name}
              </option>
            );
          })}
        </select>
      </div>

      {loading && <p className="conv-logs-loading">{t("common.loading")}</p>}
      {error && <p className="conv-logs-error" role="alert">{error}</p>}
      {!loading && !error && logs.length === 0 && (
        <p className="conv-logs-empty">{t("companies.convHistory.empty")}</p>
      )}

      {/* タイムライン */}
      <div className="conv-logs-timeline">
        {logs.map((log) => (
          <div
            key={log.id}
            className={`conv-log-item conv-log-item--${log.direction}`}
          >
            <div className="conv-log-meta">
              <span className="conv-log-contact">{contactName(log)}</span>
              <span className="conv-log-channel">{log.channel_type}</span>
              <span className={`conv-log-direction conv-log-direction--${log.direction}`}>
                {log.direction === "inbound"
                  ? t("companies.convHistory.inbound")
                  : t("companies.convHistory.outbound")}
              </span>
              {log.recorded_by_user_id && (
                <span className="conv-log-manual-badge">
                  {t("companies.convHistory.manual")}
                </span>
              )}
              <span className="conv-log-time">
                {log.occurred_at
                  ? new Date(log.occurred_at).toLocaleString("ja-JP", {
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "—"}
              </span>
            </div>
            <div className="conv-log-content">
              {log.content_text || "—"}
              {log.translated_text && log.translated_text !== log.content_text && (
                <div className="conv-log-translation">
                  {t("companies.convHistory.translation")}: {log.translated_text}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
