/**
 * FunnelRevenuePage — 売上・粗利 内訳 下層ページ（PR5）
 * /dashboard/revenue
 * 売上目標対比 + 新規/リピート内訳 + 粗利
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { PageLayout } from "../../components/PageLayout";
import { getRevenueSummary, type RevenueSummaryResponse } from "../../api/funnel";
import "./FunnelRevenuePage.css";

function fmtMoney(n: number): string {
  return `¥${n.toLocaleString("ja-JP")}`;
}

function achievementRate(actual: number, target: number): number {
  if (target === 0) return 0;
  return Math.round((actual / target) * 100);
}

export default function FunnelRevenuePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [data, setData] = useState<RevenueSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const currentMonth = (() => {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Tokyo" }));
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  })();

  useEffect(() => {
    setLoading(true);
    getRevenueSummary(currentMonth)
      .then(setData)
      .finally(() => setLoading(false));
  }, [currentMonth]);

  if (loading) {
    return (
      <PageLayout navKey="nav.dashboard" subtitleKey="funnel.revenuePageTitle">
        <div className="frp-loading">{t("common.loading")}</div>
      </PageLayout>
    );
  }

  if (!data) {
    return (
      <PageLayout navKey="nav.dashboard" subtitleKey="funnel.revenuePageTitle">
        <div className="frp-error">{t("common.errorLoad")}</div>
      </PageLayout>
    );
  }

  const { revenue, split, new_customers, active_existing_customers, gross_margin } = data;
  const achievePct = achievementRate(revenue.actual, revenue.target);
  const totalSplit = split.new + split.repeat;

  return (
    <PageLayout
      navKey="nav.dashboard"
      subtitleKey="funnel.revenuePageTitle"
      headerAction={
        <button
          type="button"
          className="frp-back-btn"
          onClick={() => navigate("/")}
        >
          ← {t("nav.dashboard")}
        </button>
      }
    >
      <div className="frp-grid">

        {/* 売上目標対比カード */}
        <div className="frp-card frp-card--large">
          <h3 className="frp-card-title">{t("funnel.revenueTitle")}</h3>
          <div className="frp-revenue-main">
            <span className="frp-revenue-actual">{fmtMoney(revenue.actual)}</span>
            <span className="frp-revenue-target">/ {fmtMoney(revenue.target)}</span>
            <span className={`frp-pace-badge frp-pace--${revenue.pace}`}>
              {t(`funnel.pace_${revenue.pace}`)}
            </span>
          </div>
          <div className="frp-bar-row">
            <div className="frp-bar-track">
              <div className="frp-bar-fill" style={{ width: `${Math.min(achievePct, 100)}%` }} />
            </div>
            <span className="frp-bar-pct">{achievePct}%</span>
          </div>
        </div>

        {/* 新規 / リピート分割 */}
        <div className="frp-card">
          <h3 className="frp-card-title">{t("funnel.splitTitle")}</h3>
          <div className="frp-split-list">
            <div className="frp-split-row">
              <span className="frp-split-label frp-split--new">{t("funnel.newRevenue")}</span>
              <span className="frp-split-value">{fmtMoney(split.new)}</span>
              {totalSplit > 0 && (
                <span className="frp-split-pct">
                  {Math.round((split.new / totalSplit) * 100)}%
                </span>
              )}
            </div>
            <div className="frp-split-row">
              <span className="frp-split-label frp-split--repeat">{t("funnel.repeatRevenue")}</span>
              <span className="frp-split-value">{fmtMoney(split.repeat)}</span>
              {totalSplit > 0 && (
                <span className="frp-split-pct">
                  {Math.round((split.repeat / totalSplit) * 100)}%
                </span>
              )}
            </div>
          </div>
          {totalSplit > 0 && (
            <div className="frp-split-bar">
              <div
                className="frp-split-bar-new"
                style={{ width: `${Math.round((split.new / totalSplit) * 100)}%` }}
              />
              <div className="frp-split-bar-repeat" />
            </div>
          )}
        </div>

        {/* 顧客数 */}
        <div className="frp-card">
          <h3 className="frp-card-title">{t("funnel.newCustomers")}</h3>
          <div className="frp-stat-main">
            <span className="frp-stat-value">{new_customers.actual}</span>
            <span className="frp-stat-target">/ {new_customers.target}</span>
          </div>
          <div className="frp-active-row">
            <span className="frp-active-label">{t("funnel.activeExisting")}:</span>
            <span className="frp-active-value">{active_existing_customers}{t("funnel.unitCompany")}</span>
          </div>
        </div>

        {/* 粗利 */}
        <div className="frp-card">
          <h3 className="frp-card-title">{t("funnel.grossMargin")}</h3>
          <div className="frp-stat-main">
            <span className="frp-stat-value frp-gross-value">{fmtMoney(gross_margin.amount)}</span>
          </div>
          {gross_margin.uncosted_orders > 0 && (
            <div className="frp-uncosted-note">
              ※{t("funnel.uncostedNote", { count: gross_margin.uncosted_orders })}
            </div>
          )}
        </div>

      </div>
    </PageLayout>
  );
}
