/**
 * FunnelSection — ファネルダッシュボード 第1層（PR4）
 * 8カード構成: ファネル4枚 + 売上(大)1枚 + サイド2枚（新規顧客獲得・アクティブ既存顧客） + フォローアップ1枚
 * モックデータ駆動。実API結線は frontend/src/api/funnel.ts の MOCK_MODE を変更。
 */

import { type KeyboardEvent, type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  getFunnel,
  getRevenueSummary,
  getFollowUps,
  type FunnelResponse,
  type RevenueSummaryResponse,
  type FollowUpsResponse,
} from "../../api/funnel";
import "./FunnelSection.css";

// ─── 型 ─────────────────────────────────────────────────────────────────

type ViewMode = "management" | "player";

interface FunnelSectionProps {
  month: string;
  viewMode: ViewMode;
}

const VIEW_ALL_LABEL = "funnel.viewAll";
const YOKU = String.fromCharCode(0x5104);
const MAN = String.fromCharCode(0x4e07);

function makeCardKeyHandler(onClick?: () => void) {
  if (!onClick) return undefined;
  return (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };
}

// ─── ユーティリティ ───────────────────────────────────────────────────────

function fmtMoney(n: number): string {
  if (n >= 100_000_000) return `¥${(n / 100_000_000).toFixed(1)}${YOKU}`;
  if (n >= 10_000) return `¥${Math.round(n / 10_000)}${MAN}`;
  return `¥${n.toLocaleString("ja-JP")}`;
}

function fmtMoneyFull(n: number): string {
  return `¥${n.toLocaleString("ja-JP")}`;
}

function achievementRate(actual: number, target: number): number {
  if (target === 0) return 0;
  return Math.round((actual / target) * 100);
}

// ─── AchievementBar ─────────────────────────────────────────────────────

function AchievementBar({ rate, isBottleneck }: { rate: number; isBottleneck?: boolean }) {
  const clamped = Math.min(rate, 100);
  const color =
    clamped >= 100
      ? "var(--success)"
      : clamped >= 70
      ? "var(--accent)"
      : clamped >= 40
      ? "var(--warning-text)"
      : "var(--danger)";
  return (
    <div className="fn-progress-wrap">
      <div
        className={`fn-progress-bar${isBottleneck ? " fn-progress-bottleneck" : ""}`}
        style={{ width: `${clamped}%`, background: color }}
      />
    </div>
  );
}

// ─── FunnelCard ──────────────────────────────────────────────────────────

interface FunnelCardProps {
  title: string;
  isBottleneck?: boolean;
  children: ReactNode;
  onClick?: () => void;
  actionLabel?: string;
}

function FunnelCard({ title, isBottleneck, children, onClick, actionLabel }: FunnelCardProps) {
  const { t } = useTranslation();
  const clickable = Boolean(onClick);
  return (
    <div
      className={`fn-card${isBottleneck ? " fn-card--bottleneck" : ""}${clickable ? " fn-card--clickable" : ""}`}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={title}
      onClick={onClick}
      onKeyDown={makeCardKeyHandler(onClick)}
    >
      <div className="fn-card-header">
        <span className="fn-card-title">{title}</span>
        {clickable && onClick && actionLabel && (
          <button
            type="button"
            className="fn-link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onClick();
            }}
          >
            {t(actionLabel)} →
          </button>
        )}
        {isBottleneck && (
          <span className="fn-bottleneck-badge" aria-label={t("funnel.bottleneck")}>
            {t("funnel.bottleneck")}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

// ─── LeadsCard ──────────────────────────────────────────────────────────

function LeadsCard({
  data,
  isBottleneck,
  onOpen,
}: {
  data: FunnelResponse["leads"];
  isBottleneck: boolean;
  onOpen?: () => void;
}) {
  const { t } = useTranslation();
  const rate = achievementRate(data.actual, data.target);
  return (
    <FunnelCard title={t("funnel.leads")} isBottleneck={isBottleneck} onClick={onOpen} actionLabel={VIEW_ALL_LABEL}>
      <div className="fn-card-main">
        <span className="fn-card-value">{data.actual}</span>
        <span className="fn-card-target">/ {data.target} {t("funnel.target")}</span>
      </div>
      <AchievementBar rate={rate} isBottleneck={isBottleneck} />
      <div className="fn-card-rate">{rate}%</div>
    </FunnelCard>
  );
}

// ─── ConversionCard ──────────────────────────────────────────────────────

function ConversionCard({
  data,
  isBottleneck,
  onOpen,
}: {
  data: FunnelResponse["conversion"];
  isBottleneck: boolean;
  onOpen?: () => void;
}) {
  const { t } = useTranslation();
  const rate = achievementRate(data.actual_rate, data.target_rate);
  return (
    <FunnelCard title={t("funnel.conversion")} isBottleneck={isBottleneck} onClick={onOpen} actionLabel={VIEW_ALL_LABEL}>
      <div className="fn-card-main">
        <span className="fn-card-value">{data.actual_rate}%</span>
        <span className="fn-card-target">/ {data.target_rate}% {t("funnel.target")}</span>
      </div>
      <AchievementBar rate={rate} isBottleneck={isBottleneck} />
      <div className="fn-card-sub">
        {t("funnel.converted")}: {data.converted}
        {t("funnel.unitDeal")}
      </div>
    </FunnelCard>
  );
}

// ─── ActiveCard ──────────────────────────────────────────────────────────

function ActiveCard({ data }: { data: FunnelResponse["active"] }) {
  const { t } = useTranslation();
  return (
    <FunnelCard title={t("funnel.active")}>
      <div className="fn-card-main">
        <span className="fn-card-value">{data.count}</span>
        <span className="fn-card-unit">{t("funnel.unitDeal")}</span>
      </div>
      <div className="fn-card-sub">{fmtMoney(data.amount)}</div>
      <div className="fn-card-coverage">
        {t("funnel.coverageOfRemaining")}: {data.coverage_pct_of_remaining_target}%
      </div>
    </FunnelCard>
  );
}

// ─── ClosedCard ──────────────────────────────────────────────────────────

function ClosedCard({
  data,
  isBottleneck,
  onOpen,
}: {
  data: FunnelResponse["closed"];
  isBottleneck: boolean;
  onOpen?: () => void;
}) {
  const { t } = useTranslation();
  const rate = achievementRate(data.won, data.won_target);
  return (
    <FunnelCard title={t("funnel.closed")} isBottleneck={isBottleneck} onClick={onOpen} actionLabel={VIEW_ALL_LABEL}>
      <div className="fn-card-main">
        <span className="fn-card-value">{data.won}</span>
        <span className="fn-card-target">/ {data.won_target} {t("funnel.target")}</span>
      </div>
      <AchievementBar rate={rate} isBottleneck={isBottleneck} />
      <div className="fn-card-sub">
        {t("funnel.wonRate")}: {data.won_rate}% ／ {t("funnel.lost")}: {data.lost}{t("funnel.unitDeal")}
      </div>
    </FunnelCard>
  );
}

// ─── RevenueSummaryCard ──────────────────────────────────────────────────

function RevenueSummaryCard({ data, onOpen }: { data: RevenueSummaryResponse; onOpen?: () => void }) {
  const { t } = useTranslation();
  const { revenue, split, gross_margin } = data;
  const achievePct = achievementRate(revenue.actual, revenue.target);
  const clickable = Boolean(onOpen);

  const paceClass =
    revenue.pace === "ahead"
      ? "fn-pace--ahead"
      : revenue.pace === "behind"
      ? "fn-pace--behind"
      : "fn-pace--on-track";

  const totalSplit = split.new + split.repeat;

  return (
    <div
      className={`fn-revenue-card${clickable ? " fn-revenue-card--clickable" : ""}`}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={t("funnel.revenueTitle")}
      onClick={onOpen}
      onKeyDown={makeCardKeyHandler(onOpen)}
    >
      <div className="fn-card-header">
        <span className="fn-card-title">{t("funnel.revenueTitle")}</span>
        {clickable && onOpen && (
          <button
            type="button"
            className="fn-link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onOpen();
            }}
          >
            {t(VIEW_ALL_LABEL)} →
          </button>
        )}
        <span className={`fn-pace-badge ${paceClass}`}>{t(`funnel.pace_${revenue.pace}`)}</span>
      </div>

      <div className="fn-revenue-main">
        <div className="fn-revenue-actual">{fmtMoneyFull(revenue.actual)}</div>
        <div className="fn-revenue-target">/ {fmtMoneyFull(revenue.target)}</div>
      </div>

      <div className="fn-revenue-bar-row">
        <div className="fn-revenue-bar-track">
          <div
            className="fn-revenue-bar-fill"
            style={{ width: `${Math.min(achievePct, 100)}%` }}
          />
        </div>
        <span className="fn-revenue-rate">{achievePct}%</span>
      </div>

      {/* 新規 / リピート積み上げバー */}
      {totalSplit > 0 && (
        <div className="fn-split-row">
          <div className="fn-split-bar-track">
            <div
              className="fn-split-new"
              style={{ width: `${Math.round((split.new / totalSplit) * 100)}%` }}
            />
            <div className="fn-split-repeat" style={{ flex: 1 }} />
          </div>
          <div className="fn-split-labels">
            <span className="fn-split-label fn-split-label--new">
              {t("funnel.newRevenue")}: {fmtMoney(split.new)}
            </span>
            <span className="fn-split-label fn-split-label--repeat">
              {t("funnel.repeatRevenue")}: {fmtMoney(split.repeat)}
            </span>
          </div>
        </div>
      )}

      {/* 粗利 */}
      <div className="fn-gross-margin-row">
        <span className="fn-gross-label">{t("funnel.grossMargin")}:</span>
        <span className="fn-gross-value">{fmtMoneyFull(gross_margin.amount)}</span>
        {gross_margin.uncosted_orders > 0 && (
          <span className="fn-gross-note">
            ※{t("funnel.uncostedNote", { count: gross_margin.uncosted_orders })}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── SideSummaryCards ────────────────────────────────────────────────────

function SideSummaryCards({ data, onOpen }: { data: RevenueSummaryResponse; onOpen?: () => void }) {
  const { t } = useTranslation();
  const { new_customers, active_existing_customers } = data;
  const ncRate = achievementRate(new_customers.actual, new_customers.target);
  const clickable = Boolean(onOpen);

  return (
    <div className="fn-side-cards">
      <div
        className={`fn-side-card${clickable ? " fn-side-card--clickable" : ""}`}
        role={clickable ? "button" : undefined}
        tabIndex={clickable ? 0 : undefined}
        aria-label={t("funnel.newCustomers")}
        onClick={onOpen}
        onKeyDown={makeCardKeyHandler(onOpen)}
      >
        <div className="fn-side-card-header">
          <div className="fn-side-card-title">{t("funnel.newCustomers")}</div>
          {clickable && onOpen && (
            <button
              type="button"
              className="fn-link-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpen();
              }}
            >
              {t(VIEW_ALL_LABEL)} →
            </button>
          )}
        </div>
        <div className="fn-card-main">
          <span className="fn-card-value">{new_customers.actual}</span>
          <span className="fn-card-target">/ {new_customers.target}</span>
        </div>
        <AchievementBar rate={ncRate} />
      </div>
      <div
        className={`fn-side-card${clickable ? " fn-side-card--clickable" : ""}`}
        role={clickable ? "button" : undefined}
        tabIndex={clickable ? 0 : undefined}
        aria-label={t("funnel.activeExisting")}
        onClick={onOpen}
        onKeyDown={makeCardKeyHandler(onOpen)}
      >
        <div className="fn-side-card-header">
          <div className="fn-side-card-title">{t("funnel.activeExisting")}</div>
          {clickable && onOpen && (
            <button
              type="button"
              className="fn-link-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpen();
              }}
            >
              {t(VIEW_ALL_LABEL)} →
            </button>
          )}
        </div>
        <div className="fn-card-main">
          <span className="fn-card-value">{active_existing_customers}</span>
          <span className="fn-card-unit">{t("funnel.unitCompany")}</span>
        </div>
      </div>
    </div>
  );
}

// ─── FollowUpSummaryCard ─────────────────────────────────────────────────

function FollowUpSummaryCard({ data, onOpen }: { data: FollowUpsResponse; onOpen?: () => void }) {
  const { t } = useTranslation();
  const clickable = Boolean(onOpen);
  const total = data.items.length;
  const orderStopped = data.items.filter((i) => i.segment === "order_stopped").length;
  const noRepeat = data.items.filter((i) => i.segment === "no_repeat_after_first").length;
  const wonNoOrder = data.items.filter((i) => i.segment === "won_no_order").length;

  return (
    <div
      className={`fn-followup-summary-card${clickable ? " fn-followup-summary-card--clickable" : ""}`}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={t("funnel.followUpTitle")}
      onClick={onOpen}
      onKeyDown={makeCardKeyHandler(onOpen)}
    >
      <div className="fn-card-header">
        <span className="fn-card-title">{t("funnel.followUpTitle")}</span>
        {clickable && onOpen && (
          <button
            type="button"
            className="fn-link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onOpen();
            }}
          >
            {t(VIEW_ALL_LABEL)} →
          </button>
        )}
      </div>
      <div className="fn-followup-total">{total}</div>
      <div className="fn-followup-segments">
        <div className="fn-segment-row">
          <span className="fn-segment-badge fn-segment--stopped">{t("funnel.segOrderStopped")}</span>
          <span className="fn-segment-count">{orderStopped}</span>
        </div>
        <div className="fn-segment-row">
          <span className="fn-segment-badge fn-segment--no-repeat">{t("funnel.segNoRepeat")}</span>
          <span className="fn-segment-count">{noRepeat}</span>
        </div>
        <div className="fn-segment-row">
          <span className="fn-segment-badge fn-segment--won">{t("funnel.segWonNoOrder")}</span>
          <span className="fn-segment-count">{wonNoOrder}</span>
        </div>
      </div>
    </div>
  );
}

// ─── FunnelSection (メイン) ──────────────────────────────────────────────

export function FunnelSection({ month, viewMode }: FunnelSectionProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const scope = viewMode === "player" ? "mine" : undefined;

  const [funnel, setFunnel] = useState<FunnelResponse | null>(null);
  const [revenue, setRevenue] = useState<RevenueSummaryResponse | null>(null);
  const [followUps, setFollowUps] = useState<FollowUpsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      getFunnel(month, scope),
      getRevenueSummary(month, scope),
      getFollowUps(scope),
    ])
      .then(([f, r, fu]) => {
        setFunnel(f);
        setRevenue(r);
        setFollowUps(fu);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [month, scope]);

  // ボトルネック判定（目標があるカードのうち達成率が最低のもの）
  const bottleneck = (() => {
    if (!funnel) return null;
    const candidates: { key: string; rate: number }[] = [
      {
        key: "leads",
        rate: achievementRate(funnel.leads.actual, funnel.leads.target),
      },
      {
        key: "conversion",
        rate: achievementRate(funnel.conversion.actual_rate, funnel.conversion.target_rate),
      },
      {
        key: "closed",
        rate: achievementRate(funnel.closed.won, funnel.closed.won_target),
      },
    ].filter((c) => c.rate < 100);
    if (candidates.length === 0) return null;
    return candidates.reduce((min, c) => (c.rate < min.rate ? c : min)).key;
  })();

  if (loading) {
    return (
      <section className="fn-section" aria-label={t("funnel.sectionTitle")}>
        <div className="fn-loading">{t("common.loading")}</div>
      </section>
    );
  }

  if (error || !funnel || !revenue || !followUps) {
    return (
      <section className="fn-section" aria-label={t("funnel.sectionTitle")}>
        <div className="fn-error">{error || t("common.errorLoad")}</div>
      </section>
    );
  }

  return (
    <section className="fn-section" aria-label={t("funnel.sectionTitle")}>
      {/* ファネル4カード */}
      <div className="fn-funnel-row">
        <LeadsCard
          data={funnel.leads}
          isBottleneck={bottleneck === "leads"}
          onOpen={() => navigate("/dashboard/leads")}
        />
        <ConversionCard
          data={funnel.conversion}
          isBottleneck={bottleneck === "conversion"}
          onOpen={() => navigate("/dashboard/leads")}
        />
        <ActiveCard data={funnel.active} />
        <ClosedCard
          data={funnel.closed}
          isBottleneck={bottleneck === "closed"}
          onOpen={() => navigate("/dashboard/reasons")}
        />
      </div>

      {/* 売上カード(大) + サイドカード */}
      <div className="fn-revenue-row">
        <RevenueSummaryCard data={revenue} onOpen={() => navigate("/dashboard/revenue")} />
        <SideSummaryCards data={revenue} onOpen={() => navigate("/dashboard/revenue")} />
      </div>

      {/* 要フォロー顧客カード */}
      <FollowUpSummaryCard data={followUps} onOpen={() => navigate("/dashboard/follow-ups")} />
    </section>
  );
}
