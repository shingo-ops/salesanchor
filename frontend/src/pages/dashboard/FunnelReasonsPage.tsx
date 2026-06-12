/**
 * FunnelReasonsPage — 成約・失注理由 下層ページ（PR5）
 * /dashboard/reasons
 * 成約/失注タブ切替 + 理由ランキング + メモ一覧（実際の言葉が読める）
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { getReasons, type ReasonsResponse } from "../../api/funnel";
import "./FunnelReasonsPage.css";

type ReasonType = "won" | "lost";

export default function FunnelReasonsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [reasonType, setReasonType] = useState<ReasonType>("won");
  const [data, setData] = useState<ReasonsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const currentMonth = (() => {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Tokyo" }));
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  })();

  useEffect(() => {
    setLoading(true);
    getReasons(reasonType, currentMonth)
      .then(setData)
      .finally(() => setLoading(false));
  }, [reasonType, currentMonth]);

  return (
    <PageLayout
      navKey="nav.dashboard"
      subtitleKey="funnel.reasonsPageTitle"
      headerAction={
        <button
          type="button"
          className="frr-back-btn"
          onClick={() => navigate("/")}
        >
          ← {t("nav.dashboard")}
        </button>
      }
    >
      {/* タブ切替 */}
      <div className="frr-tabs">
        <button
          type="button"
          className={`frr-tab${reasonType === "won" ? " active" : ""}`}
          onClick={() => setReasonType("won")}
        >
          {t("funnel.won")}
        </button>
        <button
          type="button"
          className={`frr-tab${reasonType === "lost" ? " active" : ""}`}
          onClick={() => setReasonType("lost")}
        >
          {t("funnel.lost")}
        </button>
      </div>

      {loading ? (
        <div className="frr-loading">{t("common.loading")}</div>
      ) : !data ? (
        <div className="frr-error">{t("common.errorLoad")}</div>
      ) : (
        <div className="frr-content">
          {/* 理由ランキング */}
          <section className="frr-section">
            <h3 className="frr-section-title">{t("funnel.reasonsRanking")}</h3>
            {data.reasons.length === 0 ? (
              <p className="frr-empty">{t("dashboard.noData")}</p>
            ) : (
              <div className="frr-reasons-list">
                {data.reasons.map((r, i) => (
                  <div key={r.label} className="frr-reason-row">
                    <span className="frr-rank">{i + 1}</span>
                    <span className="frr-reason-label">{r.label}</span>
                    <div className="frr-counts">
                      <span className="frr-primary-count">{t("funnel.primaryCount")}: {r.primary_count}</span>
                      {r.secondary_count > 0 && (
                        <span className="frr-secondary-count">{t("funnel.secondaryCount")}: {r.secondary_count}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* メモ一覧 */}
          {data.memos.length > 0 && (
            <section className="frr-section">
              <h3 className="frr-section-title">{t("funnel.memoList")}</h3>
              <div className="frr-memos-list">
                {data.memos.map((m) => (
                  <div key={m.deal_id} className="frr-memo-card">
                    <div className="frr-memo-header">
                      <span className="frr-memo-label">{m.primary_label}</span>
                      <span className="frr-memo-date">{m.closed_at}</span>
                    </div>
                    <p className="frr-memo-text">{m.memo}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </PageLayout>
  );
}
